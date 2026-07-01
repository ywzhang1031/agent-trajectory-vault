import tempfile
import unittest
import json
import sqlite3
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

    def test_load_codex_real_payload_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rollout-real.jsonl"
            events = [
                {
                    "type": "session_meta",
                    "timestamp": "2026-07-01T00:00:00+00:00",
                    "payload": {"id": "codex-real", "timestamp": "2026-07-01T00:00:00+00:00"},
                },
                {
                    "type": "response_item",
                    "timestamp": "2026-07-01T00:00:01+00:00",
                    "payload": {"type": "user_message", "message": "Run tests"},
                },
                {
                    "type": "response_item",
                    "timestamp": "2026-07-01T00:00:02+00:00",
                    "payload": {
                        "type": "function_call",
                        "name": "functions.exec_command",
                        "call_id": "call-1",
                        "arguments": json.dumps({"cmd": "python3 -m unittest"}),
                    },
                },
                {
                    "type": "response_item",
                    "timestamp": "2026-07-01T00:00:03+00:00",
                    "payload": {"type": "function_call_output", "call_id": "call-1", "output": "OK"},
                },
                {
                    "type": "response_item",
                    "timestamp": "2026-07-01T00:00:04+00:00",
                    "payload": {"type": "agent_message", "message": "Tests pass."},
                },
            ]
            path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            rows = load_codex_file(path, ingested_at="2026-07-01T00:01:00+00:00")

        self.assertEqual(rows[0]["source_session_id"], "codex-real")
        self.assertEqual(rows[0]["messages"][0], {"role": "user", "content": "Run tests"})
        self.assertEqual(rows[0]["messages"][-1], {"role": "assistant", "content": "Tests pass."})
        self.assertEqual(rows[0]["tool_calls"][0]["tool"], "functions.exec_command")
        self.assertEqual(rows[0]["commands"][0]["cmd"], "python3 -m unittest")
        self.assertEqual(rows[0]["observations"][0]["content"], "OK")

    def test_load_codex_skips_empty_rollout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rollout-empty.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "type": "session_meta",
                        "timestamp": "2026-07-01T00:00:00+00:00",
                        "payload": {"id": "empty"},
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(load_codex_file(path, ingested_at="2026-07-01T00:01:00+00:00"), [])

    def test_load_cursor_fixture(self):
        rows = load_cursor_file(FIXTURES / "cursor" / "session.json", ingested_at="2026-06-30T01:00:00+00:00")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_app"], "cursor")
        self.assertEqual(rows[0]["messages"][0]["role"], "user")

    def test_load_cursor_agent_transcript_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cursor-agent.jsonl"
            events = [
                {"role": "user", "message": {"content": [{"type": "text", "text": "Explain rewards"}]}},
                {
                    "role": "assistant",
                    "message": {
                        "content": [
                            {"type": "text", "text": "Rewards score rollouts."},
                            {"type": "tool_use", "name": "read_file", "input": {"path": "/Users/evan/project/a.py"}},
                        ]
                    },
                },
            ]
            path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

            rows = load_cursor_file(path, ingested_at="2026-07-01T00:01:00+00:00")

        self.assertEqual(rows[0]["task"], "Explain rewards")
        self.assertEqual(rows[0]["messages"][1]["content"], "Rewards score rollouts.")
        self.assertEqual(rows[0]["tool_calls"][0]["tool"], "read_file")

    def test_load_opencode_fixture(self):
        rows = load_opencode_file(FIXTURES / "opencode" / "session.jsonl", ingested_at="2026-06-30T01:00:00+00:00")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_app"], "opencode")
        self.assertEqual(rows[0]["tool_calls"][0]["tool"], "grep")

    def test_load_opencode_sqlite_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "opencode.db"
            conn = sqlite3.connect(path)
            conn.executescript(
                """
                CREATE TABLE session (
                    id text PRIMARY KEY,
                    title text NOT NULL,
                    directory text NOT NULL,
                    time_created integer NOT NULL,
                    time_updated integer NOT NULL
                );
                CREATE TABLE message (
                    id text PRIMARY KEY,
                    session_id text NOT NULL,
                    time_created integer NOT NULL,
                    data text NOT NULL
                );
                CREATE TABLE part (
                    id text PRIMARY KEY,
                    message_id text NOT NULL,
                    session_id text NOT NULL,
                    time_created integer NOT NULL,
                    data text NOT NULL
                );
                """
            )
            conn.execute(
                "INSERT INTO session VALUES (?, ?, ?, ?, ?)",
                ("ses_1", "Fix bug", "/Users/evan/project", 1782890000000, 1782890001000),
            )
            conn.execute(
                "INSERT INTO message VALUES (?, ?, ?, ?)",
                ("msg_1", "ses_1", 1782890000100, json.dumps({"role": "user"})),
            )
            conn.execute(
                "INSERT INTO part VALUES (?, ?, ?, ?, ?)",
                ("prt_1", "msg_1", "ses_1", 1782890000110, json.dumps({"type": "text", "text": "Run tests"})),
            )
            conn.execute(
                "INSERT INTO message VALUES (?, ?, ?, ?)",
                ("msg_2", "ses_1", 1782890000200, json.dumps({"role": "assistant"})),
            )
            conn.execute(
                "INSERT INTO part VALUES (?, ?, ?, ?, ?)",
                (
                    "prt_2",
                    "msg_2",
                    "ses_1",
                    1782890000210,
                    json.dumps(
                        {
                            "type": "tool",
                            "tool": "bash",
                            "callID": "tool_1",
                            "state": {
                                "input": {"command": "python3 -m unittest"},
                                "output": "OK",
                                "status": "completed",
                                "metadata": {"exit": 0},
                            },
                        }
                    ),
                ),
            )
            conn.commit()
            conn.close()

            rows = load_opencode_file(path, ingested_at="2026-07-01T00:01:00+00:00")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_session_id"], "ses_1")
        self.assertEqual(rows[0]["task"], "Run tests")
        self.assertEqual(rows[0]["messages"][0]["content"], "Run tests")
        self.assertEqual(rows[0]["tool_calls"][0]["tool"], "bash")
        self.assertEqual(rows[0]["commands"][0]["cmd"], "python3 -m unittest")


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

    def test_discover_cursor_sources_reads_agent_transcripts_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            jsonl_path = root / "project" / "agent-transcripts" / "abc" / "abc.jsonl"
            ignored = root / "extensions" / "package.json"
            jsonl_path.parent.mkdir(parents=True)
            ignored.parent.mkdir(parents=True)
            jsonl_path.write_text("{}\n", encoding="utf-8")
            ignored.write_text("ignore", encoding="utf-8")

            self.assertEqual(
                discover_cursor_sources(root),
                [SourceFile("cursor", jsonl_path)],
            )

    def test_discover_opencode_sources_prefers_sqlite_database(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db = root / "opencode.db"
            diff = root / "storage" / "session_diff" / "ses_1.json"
            diff.parent.mkdir(parents=True)
            db.write_text("", encoding="utf-8")
            diff.write_text("{}", encoding="utf-8")

            self.assertEqual(discover_opencode_sources(root), [SourceFile("opencode", db)])

    def test_discover_opencode_sources_returns_empty_for_missing_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing"

            self.assertEqual(discover_opencode_sources(missing), [])


if __name__ == "__main__":
    unittest.main()
