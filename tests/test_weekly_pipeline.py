import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_trajectory_vault.jsonl_io import read_jsonl
from agent_trajectory_vault.validation import validate_dataset


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "tests" / "fixtures"
DATA_FILES = ["raw_index.jsonl", "trajectories.jsonl", "sft.jsonl", "dpo.jsonl", "grpo_rollouts.jsonl"]


def _empty_worktree(root: Path) -> None:
    (root / "data").mkdir()
    (root / "reports" / "weekly").mkdir(parents=True)
    for filename in DATA_FILES:
        (root / "data" / filename).write_text("", encoding="utf-8")


def _run_weekly_update(root: Path, *extra_args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "weekly_update.py"),
            "--root",
            str(root),
            "--fixture-root",
            str(FIXTURE_ROOT),
            *extra_args,
        ],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
        text=True,
        capture_output=True,
        check=False,
    )


class WeeklyPipelineTests(unittest.TestCase):
    def test_weekly_update_dry_run_on_fixtures(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            work = Path(temp_dir)
            _empty_worktree(work)

            result = _run_weekly_update(work, "--dry-run")

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("dry_run=True", result.stdout)
            self.assertFalse((work / "data" / "trajectories.jsonl").read_text(encoding="utf-8").strip())

    def test_weekly_update_imports_fixtures_and_writes_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            work = Path(temp_dir)
            _empty_worktree(work)

            result = _run_weekly_update(work)

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("imported=3", result.stdout)
            self.assertEqual(len(read_jsonl(work / "data" / "trajectories.jsonl")), 3)
            self.assertEqual(len(read_jsonl(work / "data" / "raw_index.jsonl")), 3)
            report = (work / "reports" / "latest.md").read_text(encoding="utf-8")
            self.assertIn("Agent Trajectory Vault Report", report)
            self.assertEqual(validate_dataset(work).error_count, 0)


if __name__ == "__main__":
    unittest.main()
