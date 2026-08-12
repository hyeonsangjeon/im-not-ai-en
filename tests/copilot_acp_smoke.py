#!/usr/bin/env python3
"""Live Copilot plugin and ACP discovery smoke test.

This test is intentionally opt-in: it requires GitHub Copilot CLI and network
access. It isolates the Copilot home while preserving the caller's runtime
environment, so personal or project skills cannot mask a discovery failure.
"""

from __future__ import annotations

import argparse
from collections import deque
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time
from typing import Any


SKILL_NAME = "im-not-ai-en"
DEFAULT_SOURCE = "hyeonsangjeon/im-not-ai-en"
EXPECTED_SKILL_SUFFIX = "/.claude/skills/im-not-ai-en"


class SmokeFailure(RuntimeError):
    """Raised when the live Copilot contract is not met."""


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        details = "\n".join(
            part.strip()
            for part in (completed.stdout, completed.stderr)
            if part.strip()
        )
        raise SmokeFailure(
            f"Copilot command failed with exit {completed.returncode}: {details}"
        )
    return completed


def _isolated_environment(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    locations = {
        "COPILOT_HOME": root / "copilot",
        "COPILOT_CACHE_HOME": root / "copilot-cache",
    }
    for path in locations.values():
        path.mkdir(parents=True, exist_ok=True)
    env.update({key: str(path) for key, path in locations.items()})
    env["NO_COLOR"] = "1"
    return env


def _install_plugin(
    *,
    copilot: str,
    install_mode: str,
    source: str,
    marketplace_name: str,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
) -> tuple[bool, str]:
    if install_mode == "marketplace":
        _run(
            [copilot, "plugin", "marketplace", "add", source],
            cwd=cwd,
            env=env,
            timeout=timeout,
        )
        install_target = f"{SKILL_NAME}@{marketplace_name}"
    else:
        install_target = source

    completed = _run(
        [copilot, "plugin", "install", install_target],
        cwd=cwd,
        env=env,
        timeout=timeout,
    )
    combined = f"{completed.stdout}\n{completed.stderr}"
    deprecation_warning = (
        "direct plugin installs" in combined.lower()
        and "deprecated" in combined.lower()
    )
    return deprecation_warning, combined


def _registry_entry(
    *,
    copilot: str,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
) -> dict[str, Any]:
    completed = _run(
        [copilot, "skill", "list", "--json"],
        cwd=cwd,
        env=env,
        timeout=timeout,
    )
    try:
        skills = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise SmokeFailure("copilot skill list did not return valid JSON") from exc
    if not isinstance(skills, list):
        raise SmokeFailure("copilot skill list JSON is not an array")

    matches = [
        skill
        for skill in skills
        if isinstance(skill, dict) and skill.get("name") == SKILL_NAME
    ]
    if len(matches) != 1:
        raise SmokeFailure(
            f"expected exactly one {SKILL_NAME} registry entry, found {len(matches)}"
        )
    entry = matches[0]
    if entry.get("source") != "plugin" or entry.get("enabled") is not True:
        raise SmokeFailure(
            f"unexpected registry state: source={entry.get('source')!r}, "
            f"enabled={entry.get('enabled')!r}"
        )
    normalized_path = str(entry.get("path", "")).replace("\\", "/").rstrip("/")
    if not normalized_path.endswith(EXPECTED_SKILL_SUFFIX):
        raise SmokeFailure(
            "plugin registry path does not use the Claude-compatible skill mirror"
        )
    entry["path"] = normalized_path
    return entry


def _verify_installed_bundle(
    *,
    entry: dict[str, Any],
    env: dict[str, str],
    expected_version: str,
) -> None:
    skill_root = Path(entry["path"])
    required = (
        "LICENSE",
        "SKILL.md",
        "agents/openai.yaml",
        "references/editorial-guide.md",
        "references/sentence-copyediting.md",
        "scripts/verify_fidelity.py",
    )
    missing = [
        relative for relative in required if not (skill_root / relative).is_file()
    ]
    if missing:
        raise SmokeFailure(f"installed skill is incomplete: {missing}")

    personal_copy = Path(env["COPILOT_HOME"]) / "skills" / SKILL_NAME
    if personal_copy.exists():
        raise SmokeFailure("personal skill workaround unexpectedly exists")

    plugin_root = skill_root.parents[2]
    manifest_path = plugin_root / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        raise SmokeFailure("installed plugin is missing .claude-plugin/plugin.json")
    if (plugin_root / "plugin.json").exists():
        raise SmokeFailure("root plugin.json shadows the compatibility manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("version") != expected_version:
        raise SmokeFailure(
            f"expected plugin version {expected_version}, got {manifest.get('version')!r}"
        )
    if manifest.get("skills") != ["./.claude/skills/"]:
        raise SmokeFailure("installed manifest has an unexpected skills path")


def _stderr_pump(stream: Any, output: deque[str]) -> None:
    for line in iter(stream.readline, ""):
        output.append(line.rstrip())


def _acp_skill_visible(
    *,
    copilot: str,
    cwd: Path,
    env: dict[str, str],
    timeout: float,
    expected_copilot_version: str | None,
) -> tuple[bool, int, str, bool]:
    process = subprocess.Popen(
        [
            copilot,
            "--no-remote",
            "--no-remote-export",
            "--log-level",
            "none",
            "--acp",
            "--stdio",
            "-C",
            str(cwd),
        ],
        cwd=cwd,
        env=env,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    if process.stdin is None or process.stdout is None or process.stderr is None:
        process.kill()
        raise SmokeFailure("failed to open Copilot ACP stdio pipes")

    stdout_queue: queue.Queue[str | None] = queue.Queue()
    stderr_tail: deque[str] = deque(maxlen=20)

    def stdout_pump() -> None:
        for line in iter(process.stdout.readline, ""):
            stdout_queue.put(line)
        stdout_queue.put(None)

    threading.Thread(target=stdout_pump, daemon=True).start()
    threading.Thread(
        target=_stderr_pump,
        args=(process.stderr, stderr_tail),
        daemon=True,
    ).start()

    def send(message: dict[str, Any]) -> None:
        try:
            process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
            process.stdin.flush()
        except BrokenPipeError as exc:
            raise SmokeFailure("Copilot ACP process closed its input") from exc

    initialized = False
    session_created = False
    visible = False
    command_count = 0
    latest_names: list[str] = []
    acp_version = ""
    session_id = ""
    info_probe_sent = False
    info_probe_complete = False
    info_probe_text = ""
    deadline = time.monotonic() + timeout

    def maybe_send_info_probe() -> None:
        nonlocal info_probe_sent
        if not visible or not session_created or info_probe_sent:
            return
        send(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "session/prompt",
                "params": {
                    "sessionId": session_id,
                    "prompt": [
                        {
                            "type": "text",
                            "text": f"/skills info {SKILL_NAME}",
                        }
                    ],
                },
            }
        )
        info_probe_sent = True

    try:
        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": 1,
                    "clientCapabilities": {
                        "fs": {"readTextFile": False, "writeTextFile": False},
                        "terminal": False,
                    },
                    "clientInfo": {
                        "name": "im-not-ai-en-acp-smoke",
                        "version": "1.0.0",
                    },
                },
            }
        )

        while time.monotonic() < deadline:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                line = stdout_queue.get(timeout=min(1.0, remaining))
            except queue.Empty:
                if process.poll() is not None:
                    break
                continue
            if line is None:
                break
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SmokeFailure(
                    "Copilot ACP stdout contained non-JSON data"
                ) from exc

            if message.get("id") == 1:
                if "error" in message:
                    raise SmokeFailure(f"ACP initialize failed: {message['error']}")
                acp_version = str(
                    message.get("result", {}).get("agentInfo", {}).get("version", "")
                )
                if expected_copilot_version and acp_version != expected_copilot_version:
                    raise SmokeFailure(
                        f"expected ACP Copilot {expected_copilot_version}, got {acp_version!r}"
                    )
                initialized = True
                send(
                    {
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "session/new",
                        "params": {"cwd": str(cwd), "mcpServers": []},
                    }
                )
                continue

            if message.get("id") == 2:
                if "error" in message:
                    raise SmokeFailure(f"ACP session/new failed: {message['error']}")
                session_id = str(message.get("result", {}).get("sessionId", ""))
                if not session_id:
                    raise SmokeFailure("ACP session/new returned no sessionId")
                session_created = True
                maybe_send_info_probe()

            if message.get("id") == 3:
                if "error" in message:
                    raise SmokeFailure(
                        f"ACP /skills info probe failed: {message['error']}"
                    )
                stop_reason = message.get("result", {}).get("stopReason")
                if stop_reason != "end_turn":
                    raise SmokeFailure(
                        f"ACP /skills info ended with stopReason={stop_reason!r}"
                    )
                info_probe_complete = True
                if visible:
                    break
                continue

            if "id" in message and "method" in message:
                send(
                    {
                        "jsonrpc": "2.0",
                        "id": message["id"],
                        "error": {
                            "code": -32601,
                            "message": "Method not implemented by smoke client",
                        },
                    }
                )
                continue

            if message.get("method") != "session/update":
                continue
            update = message.get("params", {}).get("update", {})
            if (
                update.get("sessionUpdate") == "agent_message_chunk"
                and update.get("content", {}).get("type") == "text"
            ):
                info_probe_text += str(update.get("content", {}).get("text", ""))
                continue
            if update.get("sessionUpdate") != "available_commands_update":
                continue
            commands = update.get("availableCommands", [])
            names = {
                command.get("name") for command in commands if isinstance(command, dict)
            }
            latest_names = sorted(name for name in names if isinstance(name, str))
            command_count = len(commands)
            visible = SKILL_NAME in names
            maybe_send_info_probe()
            if visible and info_probe_complete:
                break
    finally:
        try:
            process.stdin.close()
        except BrokenPipeError:
            pass
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)

    source_is_plugin = "Source: Plugin" in info_probe_text
    location_is_mirror = EXPECTED_SKILL_SUFFIX + "/SKILL.md" in info_probe_text.replace(
        "\\", "/"
    )
    info_identifies_skill = f"Skill: {SKILL_NAME}" in info_probe_text
    if (
        not initialized
        or not session_created
        or not visible
        or not info_probe_complete
        or not info_identifies_skill
        or not source_is_plugin
        or not location_is_mirror
    ):
        diagnostics = "; ".join(stderr_tail)
        raise SmokeFailure(
            "ACP discovery failed: "
            f"initialized={initialized}, session_created={session_created}, "
            f"skill_visible={visible}, info_probe_complete={info_probe_complete}, "
            f"info_identifies_skill={info_identifies_skill}, "
            f"source_is_plugin={source_is_plugin}, "
            f"location_is_mirror={location_is_mirror}, "
            f"command_count={command_count}; "
            f"commands={latest_names!r}; "
            f"stderr_tail={diagnostics!r}"
        )
    return visible, command_count, acp_version, source_is_plugin


def main() -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--copilot", default=shutil.which("copilot") or "copilot")
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument(
        "--install-mode",
        choices=("direct", "marketplace"),
        default="direct",
    )
    parser.add_argument("--marketplace-name", default="im-not-ai-en")
    parser.add_argument("--expected-version", default="0.1.4")
    parser.add_argument("--expected-copilot-version")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--require-direct-deprecation-warning", action="store_true")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.require_direct_deprecation_warning and args.install_mode != "direct":
        parser.error(
            "--require-direct-deprecation-warning requires --install-mode direct"
        )

    with tempfile.TemporaryDirectory(prefix="im-not-ai-en-acp-") as temp_dir:
        root = Path(temp_dir)
        work = root / "work"
        work.mkdir()
        env = _isolated_environment(root)
        deprecation_warning, _install_output = _install_plugin(
            copilot=args.copilot,
            install_mode=args.install_mode,
            source=args.source,
            marketplace_name=args.marketplace_name,
            cwd=work,
            env=env,
            timeout=args.timeout,
        )
        if args.require_direct_deprecation_warning and not deprecation_warning:
            raise SmokeFailure("expected direct-install deprecation warning was absent")

        entry = _registry_entry(
            copilot=args.copilot,
            cwd=work,
            env=env,
            timeout=args.timeout,
        )
        _verify_installed_bundle(
            entry=entry,
            env=env,
            expected_version=args.expected_version,
        )
        visible, command_count, acp_version, source_is_plugin = _acp_skill_visible(
            copilot=args.copilot,
            cwd=work,
            env=env,
            timeout=args.timeout,
            expected_copilot_version=args.expected_copilot_version,
        )

    print(
        json.dumps(
            {
                "status": "pass",
                "copilot_acp_version": acp_version,
                "install_mode": args.install_mode,
                "plugin_version": args.expected_version,
                "registry_source": entry["source"],
                "registry_enabled": entry["enabled"],
                "registry_path_suffix": EXPECTED_SKILL_SUFFIX,
                "personal_workaround_present": False,
                "direct_install_deprecation_warning": deprecation_warning,
                "acp_session_created": True,
                "acp_skill_visible": visible,
                "acp_skill_source_is_plugin": source_is_plugin,
                "acp_skill_location_is_mirror": True,
                "available_command_count": command_count,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SmokeFailure, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"smoke test failed: {exc}") from exc
