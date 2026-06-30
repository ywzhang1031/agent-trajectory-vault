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

    def test_redacts_fine_grained_github_pat(self):
        token = (
            "github_pat_11ABCDEF0abcdefghijklmnopqrstuvwxyz_"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
        )
        redacted, summary = redact_text(f"token {token}")
        self.assertNotIn(token, redacted)
        self.assertIn("<TOKEN>", redacted)
        self.assertGreaterEqual(summary["token"], 1)

    def test_redacts_cookie_header_values(self):
        text = "Cookie: sessionid=abcdef123456; csrftoken=qwerty123456"
        redacted, summary = redact_text(text)
        self.assertNotIn("abcdef123456", redacted)
        self.assertNotIn("qwerty123456", redacted)
        self.assertEqual(redacted, "Cookie: <COOKIE>")
        self.assertGreaterEqual(summary["cookie"], 2)

    def test_redacts_generic_cookie_header_value(self):
        redacted, summary = redact_text("Cookie: sid=secret12345; theme=light")
        self.assertEqual(redacted, "Cookie: <COOKIE>")
        self.assertGreaterEqual(summary["cookie"], 1)

    def test_redacts_mixed_cookie_header_value(self):
        redacted, summary = redact_text("Cookie: sessionid=secret12345; theme=alsosecret")
        self.assertEqual(redacted, "Cookie: <COOKIE>")
        self.assertNotIn("alsosecret", redacted)
        self.assertGreaterEqual(summary["cookie"], 1)

    def test_redacts_set_cookie_header_value(self):
        redacted, summary = redact_text("Set-Cookie: sid=secret12345; Path=/")
        self.assertEqual(redacted, "Set-Cookie: <COOKIE>")
        self.assertGreaterEqual(summary["cookie"], 1)

    def test_redacts_csrf_and_xsrf_header_values(self):
        text = "X-CSRF-Token: abcdef123456\nxsrf-token=abcdef123456"
        redacted, summary = redact_text(text)
        self.assertNotIn("abcdef123456", redacted)
        self.assertIn("X-CSRF-Token: <COOKIE>", redacted)
        self.assertIn("xsrf-token=<COOKIE>", redacted)
        self.assertGreaterEqual(summary["cookie"], 2)

    def test_redacts_generic_api_key_values(self):
        text = "api_key=abcdef1234567890 and X-API-Key: abcdef1234567890"
        redacted, summary = redact_text(text)
        self.assertNotIn("abcdef1234567890", redacted)
        self.assertIn("api_key=<API_KEY>", redacted)
        self.assertIn("X-API-Key: <API_KEY>", redacted)
        self.assertGreaterEqual(summary["api_key"], 2)

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

    def test_public_scp_style_repo_url_is_not_redacted_as_email(self):
        text = "clone git@github.com:org/public.git"
        redacted, summary = redact_text(text)
        self.assertEqual(redacted, text)
        self.assertEqual(summary.get("email", 0), 0)
        self.assertEqual(summary.get("private_repo_url", 0), 0)

    def test_local_path_redaction_preserves_trailing_punctuation(self):
        redacted, summary = redact_text("open /Users/evan/project/file.py, then continue")
        self.assertIn("<LOCAL_PATH>, then", redacted)
        self.assertGreaterEqual(summary["local_path"], 1)


if __name__ == "__main__":
    unittest.main()
