import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DocsContractTests(unittest.TestCase):
    def test_required_docs_exist_and_private_upload_is_explicit(self):
        docs = [
            "docs/schema.md",
            "docs/redaction_policy.md",
            "docs/weekly_pipeline.md",
            "docs/github_private_upload.md",
        ]
        for path in docs:
            self.assertTrue((ROOT / path).exists(), path)
        upload = (ROOT / "docs" / "github_private_upload.md").read_text(encoding="utf-8")
        self.assertIn("--private", upload)
        self.assertIn("validate_dataset.py", upload)

    def test_chinese_readme_links_docs(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/schema.md", readme)
        self.assertIn("docs/redaction_policy.md", readme)
        self.assertIn("docs/weekly_pipeline.md", readme)
        self.assertIn("docs/github_private_upload.md", readme)


if __name__ == "__main__":
    unittest.main()
