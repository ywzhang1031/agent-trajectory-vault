import tempfile
import unittest
from pathlib import Path

from agent_trajectory_vault.jsonl_io import read_jsonl, upsert_jsonl, write_jsonl
from agent_trajectory_vault.schema import make_trajectory, stable_id, validate_required_fields


class SchemaIoTests(unittest.TestCase):
    def test_stable_id_is_deterministic(self):
        first = stable_id("codex", "session-1", "0-3")
        second = stable_id("codex", "session-1", "0-3")
        third = stable_id("cursor", "session-1", "0-3")
        self.assertEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertTrue(first.startswith("traj_"))

    def test_make_trajectory_has_required_fields(self):
        row = make_trajectory(
            source_app="codex",
            source_session_id="session-1",
            source_ref={"path": "<LOCAL_PATH>/rollout.jsonl"},
            created_at="2026-06-30T00:00:00+00:00",
            ingested_at="2026-06-30T01:00:00+00:00",
            task="Build a validator",
            messages=[{"role": "user", "content": "Build a validator"}],
            tool_calls=[],
            observations=[],
            commands=[],
            edits=[],
            outcome="unknown",
            failure_type="unknown",
            privacy_review_status="auto_redacted",
            redaction_summary={},
            quality_flags=[],
        )
        validate_required_fields(row)
        self.assertEqual(row["source_app"], "codex")
        self.assertEqual(row["task"], "Build a validator")

    def test_jsonl_write_read_and_upsert(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rows.jsonl"
            write_jsonl(path, [{"id": "a", "value": 1}])
            self.assertEqual(read_jsonl(path), [{"id": "a", "value": 1}])
            upsert_jsonl(path, [{"id": "a", "value": 2}, {"id": "b", "value": 3}], key="id")
            self.assertEqual(read_jsonl(path), [{"id": "a", "value": 2}, {"id": "b", "value": 3}])


if __name__ == "__main__":
    unittest.main()
