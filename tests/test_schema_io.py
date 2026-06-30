import tempfile
import unittest
from pathlib import Path

from agent_trajectory_vault.jsonl_io import read_jsonl, upsert_jsonl, write_jsonl
from agent_trajectory_vault.schema import SchemaError, make_trajectory, stable_id, validate_required_fields


class SchemaIoTests(unittest.TestCase):
    def test_stable_id_is_deterministic(self):
        first = stable_id("codex", "session-1", "0-3")
        second = stable_id("codex", "session-1", "0-3")
        third = stable_id("cursor", "session-1", "0-3")
        self.assertEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertTrue(first.startswith("traj_"))

    def test_stable_id_preserves_part_boundaries(self):
        self.assertNotEqual(stable_id("a\x1fb"), stable_id("a", "b"))

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

    def test_make_trajectory_accepts_null_failure_type(self):
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
            failure_type=None,
            privacy_review_status="auto_redacted",
            redaction_summary={},
            quality_flags=[],
        )
        validate_required_fields(row)
        self.assertIsNone(row["failure_type"])

    def test_validate_required_fields_rejects_invalid_failure_type(self):
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
            failure_type=None,
            privacy_review_status="auto_redacted",
            redaction_summary={},
            quality_flags=[],
        )
        row["failure_type"] = "not-a-real-failure"
        with self.assertRaisesRegex(SchemaError, "invalid failure_type: not-a-real-failure"):
            validate_required_fields(row)

    def test_jsonl_write_read_and_upsert(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rows.jsonl"
            write_jsonl(path, [{"id": "a", "value": 1}])
            self.assertEqual(read_jsonl(path), [{"id": "a", "value": 1}])
            upsert_jsonl(path, [{"id": "a", "value": 2}, {"id": "b", "value": 3}], key="id")
            self.assertEqual(read_jsonl(path), [{"id": "a", "value": 2}, {"id": "b", "value": 3}])

    def test_upsert_jsonl_rejects_existing_rows_missing_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rows.jsonl"
            write_jsonl(path, [{"id": "a", "value": 1}, {"value": 2}])
            with self.assertRaisesRegex(ValueError, "existing record missing key: id"):
                upsert_jsonl(path, [{"id": "b", "value": 3}], key="id")

    def test_upsert_jsonl_rejects_existing_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rows.jsonl"
            write_jsonl(path, [{"id": "a", "value": 1}, {"id": "a", "value": 2}])
            with self.assertRaisesRegex(ValueError, "duplicate existing key: a"):
                upsert_jsonl(path, [{"id": "b", "value": 3}], key="id")

    def test_read_jsonl_rejects_invalid_json_with_path_and_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rows.jsonl"
            path.write_text('{"id": "a"}\n{"id": \n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, f"{path}:2: invalid JSONL"):
                read_jsonl(path)

    def test_read_jsonl_rejects_non_object_rows_with_path_and_line(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rows.jsonl"
            path.write_text('{"id": "a"}\n[]\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, f"{path}:2: expected JSON object"):
                read_jsonl(path)

    def test_write_jsonl_preserves_non_ascii_and_sorts_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rows.jsonl"
            write_jsonl(path, [{"z": "中文", "a": 1}])
            self.assertEqual(path.read_text(encoding="utf-8"), '{"a": 1, "z": "中文"}\n')


if __name__ == "__main__":
    unittest.main()
