import tempfile
import unittest
from pathlib import Path

from agent_trajectory_vault.jsonl_io import write_jsonl
from agent_trajectory_vault.schema import make_trajectory
from agent_trajectory_vault.validation import validate_dataset


def _write_empty_dataset_files(root: Path) -> None:
    (root / "data").mkdir()
    write_jsonl(root / "data" / "raw_index.jsonl", [])
    write_jsonl(root / "data" / "trajectories.jsonl", [])
    write_jsonl(root / "data" / "sft.jsonl", [])
    write_jsonl(root / "data" / "dpo.jsonl", [])
    write_jsonl(root / "data" / "grpo_rollouts.jsonl", [])


def _make_trajectory(*, task: str = "Task") -> dict:
    return make_trajectory(
        source_app="codex",
        source_session_id="s1",
        source_ref={"path": "<LOCAL_PATH>"},
        created_at="2026-06-30T00:00:00+00:00",
        ingested_at="2026-06-30T01:00:00+00:00",
        task=task,
        messages=[{"role": "user", "content": task}],
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


class ValidationTests(unittest.TestCase):
    def test_validation_accepts_clean_dataset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_empty_dataset_files(root)
            row = make_trajectory(
                source_app="codex",
                source_session_id="s1",
                source_ref={"path": "<LOCAL_PATH>"},
                created_at="2026-06-30T00:00:00+00:00",
                ingested_at="2026-06-30T01:00:00+00:00",
                task="Task",
                messages=[{"role": "user", "content": "Task"}],
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
            write_jsonl(root / "data" / "trajectories.jsonl", [row])
            report = validate_dataset(root)
            self.assertEqual(report.error_count, 0)

    def test_validation_rejects_secret_and_unredacted_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_empty_dataset_files(root)
            row = make_trajectory(
                source_app="codex",
                source_session_id="s1",
                source_ref={"path": "/Users/evan/.codex/raw.jsonl"},
                created_at="2026-06-30T00:00:00+00:00",
                ingested_at="2026-06-30T01:00:00+00:00",
                task="Task",
                messages=[{"role": "user", "content": "secret sk-test1234567890abcdef"}],
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
            write_jsonl(root / "data" / "trajectories.jsonl", [row])
            report = validate_dataset(root)
            self.assertGreaterEqual(report.error_count, 2)

    def test_validation_rejects_sensitive_patterns_from_redaction_rules(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_empty_dataset_files(root)
            row = _make_trajectory()
            row["messages"] = [
                {
                    "role": "user",
                    "content": (
                        "Authorization: Bearer abcdefgh1234\n"
                        "api_key=abcdef1234567890\n"
                        "Cookie: sessionid=abcdef123456"
                    ),
                }
            ]
            write_jsonl(root / "data" / "trajectories.jsonl", [row])
            report = validate_dataset(root)
            self.assertGreaterEqual(report.error_count, 3)
            self.assertTrue(any("token" in error for error in report.errors))
            self.assertTrue(any("api_key" in error for error in report.errors))
            self.assertTrue(any("cookie" in error for error in report.errors))

    def test_raw_index_is_scanned_for_secret_and_unredacted_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_empty_dataset_files(root)
            write_jsonl(
                root / "data" / "raw_index.jsonl",
                [
                    {
                        "source_ref": {"path": "/Users/evan/.codex/sessions/raw.jsonl"},
                        "token": "ghp_abcdefghijklmnopqrstuvwxyz123456",
                    }
                ],
            )
            report = validate_dataset(root)
            self.assertGreaterEqual(report.error_count, 2)

    def test_validation_reports_missing_required_data_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report = validate_dataset(Path(temp_dir))
            self.assertEqual(report.error_count, 5)
            self.assertTrue(any("missing required data file" in error for error in report.errors))

    def test_validation_reports_invalid_jsonl_without_raising(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_empty_dataset_files(root)
            (root / "data" / "sft.jsonl").write_text('{"trajectory_id": \n', encoding="utf-8")
            report = validate_dataset(root)
            self.assertGreaterEqual(report.error_count, 1)
            self.assertTrue(any("invalid JSONL" in error for error in report.errors))

    def test_sft_row_with_unknown_trajectory_id_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_empty_dataset_files(root)
            write_jsonl(root / "data" / "sft.jsonl", [{"trajectory_id": "traj_missing"}])
            report = validate_dataset(root)
            self.assertGreaterEqual(report.error_count, 1)
            self.assertTrue(any("unknown trajectory_id" in error for error in report.errors))

    def test_grpo_row_with_unknown_trajectory_ids_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_empty_dataset_files(root)
            write_jsonl(root / "data" / "grpo_rollouts.jsonl", [{"trajectory_ids": ["traj_missing"]}])
            report = validate_dataset(root)
            self.assertGreaterEqual(report.error_count, 1)
            self.assertTrue(any("unknown trajectory_id" in error for error in report.errors))

    def test_derived_row_validates_trajectory_id_and_trajectory_ids_together(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_empty_dataset_files(root)
            row = _make_trajectory()
            write_jsonl(root / "data" / "trajectories.jsonl", [row])
            write_jsonl(
                root / "data" / "grpo_rollouts.jsonl",
                [{"trajectory_id": row["trajectory_id"], "trajectory_ids": ["traj_missing"]}],
            )
            report = validate_dataset(root)
            self.assertGreaterEqual(report.error_count, 1)
            self.assertTrue(
                any("grpo_rollouts.jsonl:1: unknown trajectory_ids[0]" in error for error in report.errors)
            )

    def test_duplicate_canonical_trajectory_id_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_empty_dataset_files(root)
            row = _make_trajectory()
            duplicate = dict(row)
            write_jsonl(root / "data" / "trajectories.jsonl", [row, duplicate])
            report = validate_dataset(root)
            self.assertGreaterEqual(report.error_count, 1)
            self.assertTrue(any("duplicate trajectory_id" in error for error in report.errors))


if __name__ == "__main__":
    unittest.main()
