from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_SKILL_ROOT = ROOT / "im-not-ai-en"
COPILOT_SKILL_ROOT = ROOT / ".claude" / "skills" / "im-not-ai-en"


class PluginManifestTests(unittest.TestCase):
    def test_copilot_manifest_exposes_canonical_skill(self) -> None:
        manifest_path = ROOT / ".claude-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "im-not-ai-en")
        self.assertEqual(manifest["version"], "0.1.3")
        self.assertEqual(manifest["license"], "MIT")
        self.assertEqual(
            manifest["homepage"],
            "https://github.com/hyeonsangjeon/im-not-ai-en",
        )
        self.assertEqual(manifest["repository"], manifest["homepage"])
        self.assertEqual(manifest["skills"], ["./.claude/skills/"])

        skill_container = ROOT / manifest["skills"][0]
        self.assertEqual(skill_container.resolve(), COPILOT_SKILL_ROOT.parent.resolve())
        self.assertTrue((COPILOT_SKILL_ROOT / "SKILL.md").is_file())
        self.assertTrue((COPILOT_SKILL_ROOT / "agents" / "openai.yaml").is_file())
        self.assertTrue(
            (COPILOT_SKILL_ROOT / "references" / "editorial-guide.md").is_file()
        )
        self.assertTrue(
            (COPILOT_SKILL_ROOT / "references" / "sentence-copyediting.md").is_file()
        )
        self.assertTrue(
            (COPILOT_SKILL_ROOT / "scripts" / "verify_fidelity.py").is_file()
        )
        for higher_priority_manifest in (
            ROOT / ".plugin" / "plugin.json",
            ROOT / "plugin.json",
            ROOT / ".github" / "plugin" / "plugin.json",
        ):
            with self.subTest(manifest=higher_priority_manifest.relative_to(ROOT)):
                self.assertFalse(higher_priority_manifest.exists())

    def test_copilot_marketplace_exposes_compatibility_plugin(self) -> None:
        marketplace_path = ROOT / ".claude-plugin" / "marketplace.json"
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        self.assertEqual(marketplace["name"], "im-not-ai-en")
        self.assertEqual(marketplace["owner"]["name"], "hyeonsangjeon")
        self.assertEqual(marketplace["metadata"]["version"], "0.1.3")
        self.assertEqual(marketplace["metadata"]["pluginRoot"], ".")
        self.assertEqual(len(marketplace["plugins"]), 1)
        plugin = marketplace["plugins"][0]
        self.assertEqual(plugin["name"], "im-not-ai-en")
        self.assertEqual(plugin["version"], "0.1.3")
        self.assertEqual(plugin["source"], "./")

        for higher_priority_manifest in (
            ROOT / "marketplace.json",
            ROOT / ".plugin" / "marketplace.json",
            ROOT / ".github" / "plugin" / "marketplace.json",
        ):
            with self.subTest(manifest=higher_priority_manifest.relative_to(ROOT)):
                self.assertFalse(higher_priority_manifest.exists())

    def test_copilot_skill_mirror_matches_canonical_tree(self) -> None:
        def files_under(root: Path) -> list[Path]:
            return sorted(
                path.relative_to(root)
                for path in root.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix not in {".pyc", ".pyo"}
            )

        canonical_files = files_under(CANONICAL_SKILL_ROOT)
        copilot_files = files_under(COPILOT_SKILL_ROOT)
        self.assertEqual(copilot_files, canonical_files)

        for relative_path in canonical_files:
            with self.subTest(path=relative_path.as_posix()):
                self.assertEqual(
                    (COPILOT_SKILL_ROOT / relative_path).read_bytes(),
                    (CANONICAL_SKILL_ROOT / relative_path).read_bytes(),
                )

    def test_copilot_acp_smoke_is_valid_python(self) -> None:
        smoke_path = ROOT / "tests" / "copilot_acp_smoke.py"
        source = smoke_path.read_text(encoding="utf-8")
        compile(source, str(smoke_path), "exec")

    def test_skill_frontmatter_uses_portable_mit_metadata(self) -> None:
        skill = (CANONICAL_SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", skill, flags=re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)
        self.assertRegex(frontmatter, r"(?m)^name: im-not-ai-en$")
        self.assertRegex(frontmatter, r"(?m)^license: MIT$")

    def test_skill_bundles_the_full_mit_license(self) -> None:
        bundled = (CANONICAL_SKILL_ROOT / "LICENSE").read_text(encoding="utf-8")
        project = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertEqual(bundled, project)
        self.assertTrue(bundled.startswith("MIT License\n\n"))
        self.assertIn("Permission is hereby granted, free of charge", bundled)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', bundled)

    def test_openai_interface_uses_canonical_identity(self) -> None:
        metadata = (CANONICAL_SKILL_ROOT / "agents" / "openai.yaml").read_text(
            encoding="utf-8"
        )

        def quoted_value(key: str) -> str:
            match = re.search(rf'(?m)^  {re.escape(key)}: (".*")$', metadata)
            self.assertIsNotNone(match)
            return json.loads(match.group(1))

        self.assertEqual(quoted_value("display_name"), "I'm Not AI — English")
        short_description = quoted_value("short_description")
        self.assertGreaterEqual(len(short_description), 25)
        self.assertLessEqual(len(short_description), 64)
        self.assertEqual(
            quoted_value("default_prompt"),
            "Use $im-not-ai-en to make this English natural and idiomatic while "
            "preserving my meaning and voice.",
        )


if __name__ == "__main__":
    unittest.main()
