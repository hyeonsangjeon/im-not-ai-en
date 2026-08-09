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


class EvalContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((ROOT / "evals" / "manifest.json").read_text(encoding="utf-8"))

    def test_manifest_is_complete_and_unique(self) -> None:
        self.assertEqual(self.manifest["version"], 1)
        ids = [case["id"] for case in self.manifest["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            set(ids),
            {
                "concise-workplace",
                "standard-technical",
                "long-form-publication",
                "standard-mixed-technical",
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
                self.assertIs(case["output_contract"].get("copy_ready"), True)

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
