import copy
import unittest

from agent_trajectory_vault.redaction import redact_record, redact_text


class RedactionTests(unittest.TestCase):
    def test_redacts_common_sensitive_text(self):
        text = "token sk-test1234567890abcdef and email user@example.com in /Users/evan/private/repo"
        redacted, summary = redact_text(text)
        self.assertNotIn("sk-test1234567890abcdef", redacted)
        self.assertNotIn("user@example.com", redacted)
        self.assertNotIn("/Users/evan", redacted)
        self.assertIn("<API_KEY>", redacted)
        self.assertIn("<EMAIL>", redacted)
        self.assertIn("<LOCAL_PATH>", redacted)
        self.assertGreaterEqual(summary["api_key"], 1)
        self.assertGreaterEqual(summary["email"], 1)
        self.assertGreaterEqual(summary["local_path"], 1)

    def test_redacts_nested_record(self):
        record = {
            "messages": [{"role": "user", "content": "my ghp_abcdefghijklmnopqrstuvwxyz123456 token"}],
            "source_ref": {"path": "/Users/evan/.codex/sessions/a.jsonl"},
        }
        redacted, summary = redact_record(record)
        self.assertIn("<TOKEN>", redacted["messages"][0]["content"])
        self.assertEqual(redacted["source_ref"]["path"], "<LOCAL_PATH>")
        self.assertGreaterEqual(summary["token"], 1)

    def test_redact_record_does_not_mutate_original_record(self):
        record = {
            "messages": [{"role": "user", "content": "email user@example.com"}],
            "source_ref": {"path": "/Users/evan/.codex/sessions/a.jsonl"},
        }
        original = copy.deepcopy(record)
        redacted, _summary = redact_record(record)
        self.assertEqual(record, original)
        self.assertIsNot(redacted, record)

    def test_redacts_private_key_block(self):
        text = """before
-----BEGIN OPENSSH PRIVATE KEY-----
abc123
-----END OPENSSH PRIVATE KEY-----
after"""
        redacted, summary = redact_text(text)
        self.assertNotIn("OPENSSH PRIVATE KEY", redacted)
        self.assertIn("<SECRET>", redacted)
        self.assertEqual(summary["ssh_key"], 1)

    def test_redacts_scp_style_private_repo_url_before_email(self):
        redacted, summary = redact_text("clone git@github.com:acme/internal-tools.git before sharing")
        self.assertIn("<PRIVATE_REPO_URL>", redacted)
        self.assertNotIn("git@github.com", redacted)
        self.assertGreaterEqual(summary["private_repo_url"], 1)
        self.assertEqual(summary.get("email", 0), 0)


if __name__ == "__main__":
    unittest.main()
