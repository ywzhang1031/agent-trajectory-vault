import unittest

from agent_trajectory_vault.schema import make_trajectory
from agent_trajectory_vault.training_views import build_dpo_records, build_grpo_rollouts, build_sft_records


def _trajectory(**overrides):
    data = {
        "source_app": "codex",
        "source_session_id": "s1",
        "source_ref": {"path": "<LOCAL_PATH>"},
        "created_at": "2026-06-30T00:00:00+00:00",
        "ingested_at": "2026-06-30T01:00:00+00:00",
        "task": "Fix test",
        "messages": [{"role": "user", "content": "Fix test"}],
        "tool_calls": [],
        "observations": [],
        "commands": [],
        "edits": [],
        "outcome": "unknown",
        "failure_type": "unknown",
        "privacy_review_status": "auto_redacted",
        "redaction_summary": {},
        "quality_flags": [],
    }
    data.update(overrides)
    return make_trajectory(**data)


class TrainingViewTests(unittest.TestCase):
    def test_build_sft_records_from_successful_trajectory(self):
        trajectory = _trajectory(
            messages=[
                {"role": "user", "content": "Fix test"},
                {"role": "assistant", "content": "I fixed it."},
            ],
            outcome="success",
            privacy_review_status="manual_reviewed",
        )
        records = build_sft_records([trajectory])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["target"], "I fixed it.")
        self.assertEqual(records[0]["trajectory_id"], trajectory["trajectory_id"])

    def test_build_sft_records_skips_needs_manual_review(self):
        trajectory = _trajectory(
            messages=[
                {"role": "user", "content": "Fix test"},
                {"role": "assistant", "content": "I fixed it."},
            ],
            outcome="success",
            privacy_review_status="needs_manual_review",
        )
        self.assertEqual(build_sft_records([trajectory]), [])

    def test_build_dpo_records_from_manual_correction(self):
        trajectory = _trajectory(outcome="failure", failure_type="planning_error")
        trajectory["manual_correction"] = {
            "chosen": "Inspect the failure first.",
            "rejected": "Edit blindly.",
            "reason": "chosen observes before editing",
        }
        records = build_dpo_records([trajectory])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["chosen"], "Inspect the failure first.")
        self.assertEqual(records[0]["rejected"], "Edit blindly.")
        self.assertEqual(records[0]["failure_type"], "planning_error")
        self.assertEqual(records[0]["trajectory_id"], trajectory["trajectory_id"])

    def test_build_dpo_records_normalizes_missing_failure_type(self):
        trajectory = _trajectory(outcome="failure", failure_type=None)
        trajectory["manual_correction"] = {
            "chosen": "Inspect the failure first.",
            "rejected": "Edit blindly.",
        }

        records = build_dpo_records([trajectory])

        self.assertEqual(records[0]["failure_type"], "unknown")

    def test_build_grpo_rollouts_marks_single_rollout_partial(self):
        trajectory = _trajectory()
        groups = build_grpo_rollouts([trajectory])
        self.assertEqual(groups[0]["group_status"], "partial")
        self.assertEqual(groups[0]["trajectory_ids"], [trajectory["trajectory_id"]])


if __name__ == "__main__":
    unittest.main()
