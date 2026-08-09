from __future__ import annotations

import importlib.util
import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "im-not-ai-en" / "scripts" / "verify_fidelity.py"
SPEC = importlib.util.spec_from_file_location("verify_fidelity", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def source_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^~~~text\n(.*?)\n~~~$", text)
    if not match:
        raise AssertionError(f"Missing source block in {path}")
    return match.group(1)


def immutable_spans(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    try:
        section = text.split("## Immutable spans\n", 1)[1].split("\n## ", 1)[0]
    except IndexError as exc:
        raise AssertionError(f"Missing Immutable spans section in {path}") from exc

    spans: list[str] = []
    for line in section.splitlines():
        if not line.strip():
            continue
        if not line.startswith("- "):
            raise AssertionError(f"Invalid immutable-span line in {path}: {line!r}")
        item = line[2:]
        index = 0
        count_before = len(spans)
        while index < len(item):
            if item[index] != "`":
                index += 1
                continue
            end_run = index
            while end_run < len(item) and item[end_run] == "`":
                end_run += 1
            delimiter = item[index:end_run]
            close = item.find(delimiter, end_run)
            if close < 0:
                raise AssertionError(f"Unclosed code span in {path}: {line!r}")
            value = item[end_run:close]
            if (
                len(value) >= 2
                and value.startswith(" ")
                and value.endswith(" ")
                and value.strip()
            ):
                value = value[1:-1]
            spans.append(value)
            index = close + len(delimiter)
        if len(spans) == count_before:
            raise AssertionError(
                f"Immutable-span bullet has no code span in {path}: {line!r}"
            )
    return spans


class EvalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((ROOT / "evals" / "manifest.json").read_text(encoding="utf-8"))

    def test_manifest_is_complete_and_unique(self) -> None:
        self.assertEqual(self.manifest["version"], 2)
        ids = [case["id"] for case in self.manifest["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            set(ids),
            {
                "concise-workplace",
                "standard-technical",
                "long-form-publication",
                "standard-mixed-technical",
                "concise-copyedit-workplace",
                "standard-copyedit-technical",
                "long-form-dialect-rhythm",
                "concise-clean-voice",
            },
        )
        sources = [case["source"] for case in self.manifest["cases"]]
        outputs = [case["output"] for case in self.manifest["cases"]]
        self.assertEqual(len(sources), len(set(sources)))
        self.assertEqual(len(outputs), len(set(outputs)))
        fixture_paths = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "evals" / "fixtures").glob("*.md")
        }
        self.assertEqual(set(sources), fixture_paths)
        for case in self.manifest["cases"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(
                    set(case),
                    {"id", "source", "output", "protected_spans", "output_contract"},
                )
                contract = case["output_contract"]
                self.assertLessEqual(
                    set(contract),
                    {"copy_ready", "must_repair_spans", "identity"},
                )
                self.assertIs(contract.get("copy_ready"), True)
                repair_spans = contract.get("must_repair_spans", [])
                self.assertEqual(len(repair_spans), len(set(repair_spans)))
                source = source_block(ROOT / case["source"])
                for span in repair_spans:
                    self.assertIsInstance(span, str)
                    self.assertTrue(span)
                    self.assertIn(span, source)

    def test_targeted_copyedits_are_repaired_in_recorded_outputs(self) -> None:
        for case in self.manifest["cases"]:
            with self.subTest(case=case["id"]):
                output = (ROOT / case["output"]).read_text(encoding="utf-8")
                for span in case["output_contract"].get("must_repair_spans", []):
                    self.assertNotIn(span, output)

    def test_fixture_immutable_spans_match_manifest(self) -> None:
        for case in self.manifest["cases"]:
            with self.subTest(case=case["id"]):
                expected = [
                    span if isinstance(span, str) else span["text"]
                    for span in case["protected_spans"]
                ]
                self.assertEqual(immutable_spans(ROOT / case["source"]), expected)

    def test_identity_contract_preserves_clean_prose_verbatim(self) -> None:
        identity_cases = [
            case
            for case in self.manifest["cases"]
            if case["output_contract"].get("identity") is True
        ]
        self.assertEqual([case["id"] for case in identity_cases], ["concise-clean-voice"])
        for case in identity_cases:
            source = source_block(ROOT / case["source"])
            output = (ROOT / case["output"]).read_text(encoding="utf-8")
            self.assertEqual(output.removesuffix("\n"), source)

    def test_recorded_outputs_pass_hard_contracts(self) -> None:
        for case in self.manifest["cases"]:
            with self.subTest(case=case["id"]):
                source = source_block(ROOT / case["source"])
                output = (ROOT / case["output"]).read_text(encoding="utf-8")
                result = MODULE.verify(
                    source,
                    output,
                    protected_spans=case["protected_spans"],
                    copy_ready=case["output_contract"]["copy_ready"],
                )
                self.assertEqual(result["status"], "pass", result)


if __name__ == "__main__":
    unittest.main()
