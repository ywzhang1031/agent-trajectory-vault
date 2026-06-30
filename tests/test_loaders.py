import tempfile
import unittest
from pathlib import Path

from agent_trajectory_vault.codex_loader import load_codex_file
from agent_trajectory_vault.cursor_loader import load_cursor_file
from agent_trajectory_vault.opencode_loader import load_opencode_file
from agent_trajectory_vault.source_discovery import (
    SourceFile,
    discover_codex_sources,
    discover_cursor_sources,
    discover_opencode_sources,
)


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class LoaderTests(unittest.TestCase):
    def test_load_codex_fixture(self):
        rows = load_codex_file(FIXTURES / "codex" / "rollout.jsonl", ingested_at="2026-06-30T01:00:00+00:00")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_app"], "codex")
        self.assertEqual(rows[0]["task"], "Fix failing tests in <LOCAL_PATH>")
        self.assertIn("api_key", rows[0]["redaction_summary"])

    def test_load_cursor_fixture(self):
        rows = load_cursor_file(FIXTURES / "cursor" / "session.json", ingested_at="2026-06-30T01:00:00+00:00")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_app"], "cursor")
        self.assertEqual(rows[0]["messages"][0]["role"], "user")

    def test_load_opencode_fixture(self):
        rows = load_opencode_file(FIXTURES / "opencode" / "session.jsonl", ingested_at="2026-06-30T01:00:00+00:00")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_app"], "opencode")
        self.assertEqual(rows[0]["tool_calls"][0]["tool"], "grep")


class SourceDiscoveryTests(unittest.TestCase):
    def test_discover_codex_sources_uses_root_without_local_scan(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "2026" / "06" / "rollout-b.jsonl"
            second = root / "2026" / "06" / "rollout-a.jsonl"
            ignored = root / "2026" / "06" / "session.jsonl"
            first.parent.mkdir(parents=True)
            first.write_text("{}\n", encoding="utf-8")
            second.write_text("{}\n", encoding="utf-8")
            ignored.write_text("{}\n", encoding="utf-8")

            self.assertEqual(
                discover_codex_sources(root),
                [SourceFile("codex", second), SourceFile("codex", first)],
            )

    def test_discover_cursor_sources_reads_json_and_jsonl_from_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            json_path = root / "nested" / "session.json"
            jsonl_path = root / "nested" / "session.jsonl"
            ignored = root / "nested" / "notes.txt"
            json_path.parent.mkdir(parents=True)
            json_path.write_text("{}", encoding="utf-8")
            jsonl_path.write_text("{}\n", encoding="utf-8")
            ignored.write_text("ignore", encoding="utf-8")

            self.assertEqual(
                discover_cursor_sources(root),
                [SourceFile("cursor", json_path), SourceFile("cursor", jsonl_path)],
            )

    def test_discover_opencode_sources_returns_empty_for_missing_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"

            self.assertEqual(discover_opencode_sources(missing), [])


if __name__ == "__main__":
    unittest.main()
