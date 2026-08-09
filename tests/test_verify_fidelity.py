from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "im-not-ai-en" / "scripts" / "verify_fidelity.py"
SPEC = importlib.util.spec_from_file_location("verify_fidelity", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifyFidelityTests(unittest.TestCase):
    def invoke_subprocess(
        self,
        arguments: list[str],
        *,
        timeout: float = 5,
    ) -> tuple[subprocess.CompletedProcess[str], dict]:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        self.assertEqual(completed.stderr, "")
        return completed, json.loads(completed.stdout)

    def test_identity_passes(self) -> None:
        text = "The API may return 2 results from `GET /v1/items`."
        result = MODULE.verify(text, text)
        self.assertEqual(result["status"], "pass")

    def test_missing_and_injected_literals_fail(self) -> None:
        source = "Version 2.4.1 may call https://example.test/a once."
        revised = "Version 2.4.2 may call https://example.test/b once."
        result = MODULE.verify(source, revised)
        self.assertEqual(result["status"], "fail")
        self.assertIn("protected_literal_changed", {f["code"] for f in result["failures"]})
        categories = {f.get("category") for f in result["failures"]}
        self.assertIn("numbers", categories)
        self.assertIn("urls", categories)

    def test_empty_output_fails(self) -> None:
        result = MODULE.verify("Keep this.", "")
        self.assertEqual(result["status"], "fail")
        self.assertIn("empty_output", {f["code"] for f in result["failures"]})

    def test_explicit_span_multiplicity_is_preserved(self) -> None:
        source = "ExamplePay retries ExamplePay requests."
        revised = "ExamplePay retries requests."
        result = MODULE.verify(source, revised, protected_spans=["ExamplePay"])
        self.assertEqual(result["status"], "fail")
        failure = next(f for f in result["failures"] if f["code"] == "protected_span_changed")
        self.assertEqual(failure["expected_count"], 2)
        self.assertEqual(failure["actual_count"], 1)

    def test_at_least_contract_allows_clarifying_repetition(self) -> None:
        source = "The parser accepts delta-seconds. Only delta-seconds appeared."
        revised = "The parser accepts delta-seconds. All samples used delta-seconds, so delta-seconds remain supported."
        result = MODULE.verify(
            source,
            revised,
            protected_spans=[{"text": "delta-seconds", "mode": "at_least"}],
        )
        self.assertEqual(result["status"], "pass")

    def test_long_direct_quote_is_protected(self) -> None:
        source = 'The log says “Do not approve this request.” and then stops.'
        revised = 'The log says “Approve this request.” and then stops.'
        result = MODULE.verify(source, revised)
        self.assertEqual(result["status"], "fail")

    def test_common_markdown_code_forms_are_protected(self) -> None:
        cases = [
            (
                "four-backtick fence",
                "````python\nvalue = alpha\n````\n",
                "````python\nvalue = beta\n````\n",
                "fenced_code",
            ),
            (
                "tilde fence",
                "~~~~text\nalpha\n~~~~\n",
                "~~~~text\nbeta\n~~~~\n",
                "fenced_code",
            ),
            (
                "multi-backtick span",
                "Use ``alpha`beta`` exactly.",
                "Use ``alpha`gamma`` exactly.",
                "inline_code",
            ),
        ]
        for label, source, revised, category in cases:
            with self.subTest(label=label):
                result = MODULE.verify(source, revised)
                categories = {f.get("category") for f in result["failures"]}
                self.assertEqual(result["status"], "fail")
                self.assertIn(category, categories)

    def test_markdown_link_destinations_are_parsed_without_titles(self) -> None:
        source = '[docs](https://example.test/a_(b) "original title") and more.'
        title_only = '[docs](https://example.test/a_(b) "new title") and more.'
        multiline_source = '[docs](https://example.test/a_(b)\n  "original title") and more.'
        multiline_title_only = '[docs](https://example.test/a_(b)\n  "new title") and more.'
        changed_target = '[docs](https://example.test/a_(c) "original title") and more.'
        reference_source = "[docs][ref]\n\n[ref]: https://example.test/a_(b)\n"
        reference_bad = "[docs][ref]\n\n[ref]: https://example.test/a_(c)\n"
        reference_title_source = (
            '[docs][ref]\n\n[ref]: https://example.test/a_(b)\n  "original title"\n'
        )
        reference_title_only = (
            '[docs][ref]\n\n[ref]: https://example.test/a_(b)\n  "new title"\n'
        )

        self.assertEqual(MODULE.verify(source, title_only)["status"], "pass")
        self.assertEqual(
            MODULE.verify(multiline_source, multiline_title_only)["status"],
            "pass",
        )
        self.assertEqual(
            MODULE.verify(reference_title_source, reference_title_only)["status"],
            "pass",
        )
        inline_result = MODULE.verify(source, changed_target)
        reference_result = MODULE.verify(reference_source, reference_bad)
        for result in (inline_result, reference_result):
            categories = {f.get("category") for f in result["failures"]}
            self.assertEqual(result["status"], "fail")
            self.assertIn("markdown_targets", categories)

    def test_reference_link_usage_is_preserved(self) -> None:
        source = "Read [the guide][docs].\n\n[docs]: /guide\n"
        revised = "Read the guide.\n\n[docs]: /guide\n"
        result = MODULE.verify(source, revised)
        categories = {f.get("category") for f in result["failures"]}
        self.assertEqual(result["status"], "fail")
        self.assertIn("reference_uses", categories)

        equivalent = "Read [the guide][manual].\n\n[manual]: /guide\n"
        self.assertEqual(MODULE.verify(source, equivalent)["status"], "pass")

    def test_url_sentence_punctuation_is_not_part_of_destination(self) -> None:
        source = "See https://example.test/docs."
        revised = "See (https://example.test/docs)."
        self.assertEqual(MODULE.verify(source, revised)["status"], "pass")

        uppercase_source = "See HTTPS://example.test/a."
        uppercase_bad = "See HTTPS://example.test/b."
        result = MODULE.verify(uppercase_source, uppercase_bad)
        categories = {f.get("category") for f in result["failures"]}
        self.assertEqual(result["status"], "fail")
        self.assertIn("urls", categories)

    def test_dates_citations_and_block_quotes_are_protected(self) -> None:
        cases = [
            ("time", "Run at 9am.", "Run at 10am.", "date_times"),
            ("month", "Ship in August.", "Ship in September.", "month_names"),
            ("footnote", "See [^limit].", "See [^other].", "citations"),
            ("Pandoc citation", "See [@smith2024].", "See [@jones2025].", "citations"),
            ("numeric citation", "See [3].", "See [4].", "citations"),
            (
                "email",
                "Contact owner@example.test.",
                "Contact admin@example.test.",
                "emails",
            ),
            ("block quote", "> Keep this exact.\n", "> Change this text.\n", "block_quotes"),
        ]
        for label, source, revised, category in cases:
            with self.subTest(label=label):
                result = MODULE.verify(source, revised)
                categories = {f.get("category") for f in result["failures"]}
                self.assertEqual(result["status"], "fail")
                self.assertIn(category, categories)

    def test_markdown_structure_categories_fail_independently(self) -> None:
        cases = [
            ("heading", "Decision\n========\n", "Decision\n", "markdown_headings"),
            (
                "table",
                "Owner | Date\n--- | ---\nAna | Today\n",
                "Owner: Ana, Today\n",
                "markdown_tables",
            ),
            ("list", "- First\n- Second\n", "First, then second.\n", "markdown_lists"),
            ("task", "- [ ] Deploy\n", "- [x] Deploy\n", "markdown_lists"),
        ]
        for label, source, revised, structure in cases:
            with self.subTest(label=label):
                result = MODULE.verify(source, revised)
                failures = {
                    f.get("structure")
                    for f in result["failures"]
                    if f["code"] == "structure_changed"
                }
                self.assertEqual(result["status"], "fail")
                self.assertIn(structure, failures)

    def test_copy_ready_preamble_fails(self) -> None:
        source = "Please move the demo."
        revisions = [
            "Here is the revised text:\n\nPlease move the demo.",
            "Certainly! Here is the revision:\n\nPlease move the demo.",
            "Please move the demo.\n\nNotes:\n- Tightened the sentence.",
        ]
        for revised in revisions:
            with self.subTest(revised=revised):
                result = MODULE.verify(source, revised, copy_ready=True)
                self.assertEqual(result["status"], "fail")
                self.assertIn("output_contract", {f["code"] for f in result["failures"]})

        source_with_wrapper = "Sure, please move the demo."
        self.assertEqual(
            MODULE.verify(source_with_wrapper, source_with_wrapper, copy_ready=True)["status"],
            "pass",
        )

    def test_change_rate_threshold_is_opt_in(self) -> None:
        source = "This is an intentionally padded sentence."
        revised = "This sentence is padded."
        default = MODULE.verify(source, revised)
        warned = MODULE.verify(source, revised, warn_change_rate=0.10)
        self.assertEqual(default["status"], "pass")
        self.assertEqual(warned["status"], "warn")

    def test_hedge_changes_are_exposed_for_manual_review(self) -> None:
        source = "We should perhaps consider updating the runbook."
        revised = "We should consider updating the runbook."
        result = MODULE.verify(source, revised)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(
            result["manual_review"]["force_markers_before"]["hedges"],
            {"perhaps": 1},
        )
        self.assertEqual(
            result["manual_review"]["force_markers_after"]["hedges"],
            {},
        )

    def test_sensitive_diagnostic_values_are_redacted_by_default(self) -> None:
        source = (
            "Contact owner-secret@example.test at https://private.example.test/alpha.\n"
            "```python\napi_token = 'private-alpha'\n```\n"
            "The log says “Private quote alpha.”\n"
            "KEEP-SPAN\n"
        )
        revised = (
            "Here is the revised text: confidential opening\n"
            "Contact editor-secret@example.test at https://private.example.test/beta.\n"
            "```python\napi_token = 'private-beta'\n```\n"
            "The log says “Private quote beta.”\n"
        )
        sensitive_values = [
            "owner-secret@example.test",
            "editor-secret@example.test",
            "https://private.example.test/alpha",
            "https://private.example.test/beta",
            "private-alpha",
            "private-beta",
            "“Private quote alpha.”",
            "“Private quote beta.”",
            "KEEP-SPAN",
            "Here is the revised text: confidential opening",
        ]

        redacted = MODULE.verify(
            source,
            revised,
            protected_spans=["KEEP-SPAN"],
            copy_ready=True,
        )
        redacted_json = json.dumps(redacted, ensure_ascii=False)
        self.assertFalse(redacted["values_shown"])
        self.assertIn(MODULE.REDACTED_VALUE, redacted_json)
        for value in sensitive_values:
            with self.subTest(value=value):
                self.assertNotIn(value, redacted_json)

        disclosed = MODULE.verify(
            source,
            revised,
            protected_spans=["KEEP-SPAN"],
            copy_ready=True,
            show_values=True,
        )
        disclosed_json = json.dumps(disclosed, ensure_ascii=False)
        self.assertTrue(disclosed["values_shown"])
        for value in sensitive_values:
            with self.subTest(disclosed_value=value):
                self.assertIn(value, disclosed_json)

    def test_cli_redacts_values_and_paths_unless_explicitly_requested(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.md"
            revised = root / "revised.md"
            original.write_text(
                "Contact owner-secret@example.test at https://private.example.test/alpha.",
                encoding="utf-8",
            )
            revised.write_text(
                "Contact editor-secret@example.test at https://private.example.test/beta.",
                encoding="utf-8",
            )

            completed, payload = self.invoke_subprocess([str(original), str(revised)])
            self.assertEqual((completed.returncode, payload["status"]), (2, "fail"))
            self.assertFalse(payload["values_shown"])
            self.assertNotIn("owner-secret@example.test", completed.stdout)
            self.assertNotIn("https://private.example.test/alpha", completed.stdout)

            completed, payload = self.invoke_subprocess(
                ["--show-values", str(original), str(revised)]
            )
            self.assertEqual((completed.returncode, payload["status"]), (2, "fail"))
            self.assertTrue(payload["values_shown"])
            self.assertIn("owner-secret@example.test", completed.stdout)
            self.assertIn("https://private.example.test/alpha", completed.stdout)

            missing = root / "private-owner-directory" / "missing.md"
            completed, payload = self.invoke_subprocess([str(missing), str(revised)])
            self.assertEqual((completed.returncode, payload["status"]), (3, "error"))
            self.assertNotIn(str(missing), completed.stdout)
            self.assertNotIn("private-owner-directory", completed.stdout)

            completed, payload = self.invoke_subprocess(
                ["--show-values", str(missing), str(revised)]
            )
            self.assertEqual((completed.returncode, payload["status"]), (3, "error"))
            self.assertIn(str(missing), completed.stdout)

    def test_large_repetitive_change_rate_is_bounded_and_advisory(self) -> None:
        nearly_identical_rate, method = MODULE._change_rate(
            "a" * 200_000,
            ("a" * 199_999) + "b",
        )
        self.assertEqual(method, "sampled")
        self.assertLess(nearly_identical_rate, 0.01)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.md"
            revised = root / "revised.md"
            original.write_text("a" * 200_000, encoding="utf-8")
            revised.write_text("b" * 200_000, encoding="utf-8")
            completed, payload = self.invoke_subprocess(
                ["--warn-change-rate", "0.10", str(original), str(revised)],
                timeout=5,
            )

        self.assertEqual((completed.returncode, payload["status"]), (1, "warn"))
        self.assertEqual(payload["change_rate_method"], "sampled")
        self.assertEqual(payload["change_rate"], 1.0)
        self.assertEqual(payload["warnings"][0]["method"], "sampled")

    def test_malformed_markdown_scanning_fails_closed_within_timeout(self) -> None:
        cases = {
            "nested destinations": ("x](" * 16_000) + "x",
            "many unlinked quotes": '"abcdefgh" ' * 30_000,
            "many inline link titles on one line": '[x](url "abcdefgh") ' * 30_000,
        }
        for label, malformed in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                original = root / "original.md"
                revised = root / "revised.md"
                original.write_text(malformed, encoding="utf-8")
                revised.write_text(malformed, encoding="utf-8")
                completed, payload = self.invoke_subprocess(
                    [str(original), str(revised)],
                    timeout=5,
                )

                self.assertEqual(
                    (completed.returncode, payload["status"]),
                    (3, "error"),
                )
                self.assertEqual(
                    payload["configuration_errors"],
                    ["Markdown literal scanning exceeded the safe complexity limit."],
                )

    def test_unclosed_delimiter_scans_are_bounded(self) -> None:
        cases = {
            "reference brackets": ("[" * 16_000) + ("a" * 16_000),
            "Pandoc citations": ("[@" * 8_000) + ("a" * 8_000),
            "smart double quotes": ("“" * 16_000) + ("a" * 16_000),
            "smart single quotes": ("‘" * 16_000) + ("a" * 16_000),
        }
        for label, malformed in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                original = root / "original.md"
                revised = root / "revised.md"
                original.write_text(malformed, encoding="utf-8")
                revised.write_text(malformed, encoding="utf-8")
                completed, payload = self.invoke_subprocess(
                    [str(original), str(revised)],
                    timeout=5,
                )

                self.assertEqual(
                    (completed.returncode, payload["status"]),
                    (0, "pass"),
                )

    def test_invalid_explicit_span_is_configuration_error(self) -> None:
        result = MODULE.verify("Source text.", "Source text.", protected_spans=["absent"])
        self.assertEqual(result["status"], "error")

    def test_malformed_contracts_return_configuration_error(self) -> None:
        malformed = [None, 7, ["Source"], {"text": 7}, {"text": "Source", "mode": []}]
        result = MODULE.verify(
            "Source text.",
            "Source text.",
            protected_spans=malformed,  # type: ignore[arg-type]
            warn_change_rate=2,
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(len(result["configuration_errors"]), 6)

    def test_cli_exit_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.md"
            revised = root / "revised.md"
            invalid_utf8 = root / "invalid.md"
            original.write_text("A padded sentence.", encoding="utf-8")
            revised.write_text("A padded sentence.", encoding="utf-8")
            invalid_utf8.write_bytes(b"\xff")

            def invoke(arguments: list[str]) -> tuple[int, dict]:
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = MODULE.main(arguments)
                return code, json.loads(stdout.getvalue())

            code, payload = invoke([str(original), str(revised)])
            self.assertEqual((code, payload["status"]), (0, "pass"))

            revised.write_text("A short sentence.", encoding="utf-8")
            code, payload = invoke(
                ["--warn-change-rate", "0.01", str(original), str(revised)]
            )
            self.assertEqual((code, payload["status"]), (1, "warn"))

            revised.write_text("", encoding="utf-8")
            code, payload = invoke([str(original), str(revised)])
            self.assertEqual((code, payload["status"]), (2, "fail"))

            error_cases = [
                ["--warn-change-rate", "2", str(original), str(revised)],
                [str(root / "missing.md"), str(revised)],
                [str(invalid_utf8), str(revised)],
                ["--protect", "absent", str(original), str(revised)],
                ["--unknown-option"],
            ]
            for arguments in error_cases:
                with self.subTest(arguments=arguments):
                    code, payload = invoke(arguments)
                    self.assertEqual((code, payload["status"]), (3, "error"))

            code, payload = invoke(["--s", str(original), str(revised)])
            self.assertEqual((code, payload["status"]), (3, "error"))
            self.assertFalse(payload["values_shown"])
            self.assertEqual(payload["error"], "Invalid command-line arguments.")


if __name__ == "__main__":
    unittest.main()
