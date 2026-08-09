from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginManifestTests(unittest.TestCase):
    def test_copilot_manifest_exposes_canonical_skill(self) -> None:
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "im-not-ai-en")
        self.assertEqual(manifest["version"], "0.1.2")
        self.assertEqual(manifest["license"], "MIT")
        self.assertEqual(
            manifest["homepage"],
            "https://github.com/hyeonsangjeon/im-not-ai-en",
        )
        self.assertEqual(manifest["repository"], manifest["homepage"])
        self.assertEqual(manifest["skills"], ["./im-not-ai-en/"])

        skill_root = ROOT / "im-not-ai-en"
        self.assertEqual((ROOT / manifest["skills"][0]).resolve(), skill_root.resolve())
        self.assertTrue((skill_root / "SKILL.md").is_file())
        self.assertTrue((skill_root / "agents" / "openai.yaml").is_file())
        self.assertTrue((skill_root / "references" / "editorial-guide.md").is_file())
        self.assertTrue(
            (skill_root / "references" / "sentence-copyediting.md").is_file()
        )
        self.assertTrue((skill_root / "scripts" / "verify_fidelity.py").is_file())

    def test_skill_frontmatter_uses_portable_mit_metadata(self) -> None:
        skill = (ROOT / "im-not-ai-en" / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", skill, flags=re.DOTALL)
        self.assertIsNotNone(match)
        frontmatter = match.group(1)
        self.assertRegex(frontmatter, r"(?m)^name: im-not-ai-en$")
        self.assertRegex(frontmatter, r"(?m)^license: MIT$")

    def test_skill_bundles_the_full_mit_license(self) -> None:
        bundled = (ROOT / "im-not-ai-en" / "LICENSE").read_text(encoding="utf-8")
        project = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertEqual(bundled, project)
        self.assertTrue(bundled.startswith("MIT License\n\n"))
        self.assertIn("Permission is hereby granted, free of charge", bundled)
        self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"', bundled)

    def test_openai_interface_uses_canonical_identity(self) -> None:
        metadata = (ROOT / "im-not-ai-en" / "agents" / "openai.yaml").read_text(
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
