from pathlib import Path
from unittest import FunctionTestCase, TestSuite


ROOT = Path(__file__).resolve().parents[1]


def test_required_files_exist():
    required = [
        "README.md",
        "docs/README.en.md",
        "LICENSE",
        "DATA_LICENSE.md",
        ".gitignore",
        "data/raw_index.jsonl",
        "data/trajectories.jsonl",
        "data/sft.jsonl",
        "data/dpo.jsonl",
        "data/grpo_rollouts.jsonl",
        "reports/latest.md",
        "reports/weekly/.gitkeep",
        "src/agent_trajectory_vault/__init__.py",
    ]
    missing = [path for path in required if not (ROOT / path).exists()]
    assert missing == []


def test_readme_language_and_license_policy():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    data_license = (ROOT / "DATA_LICENSE.md").read_text(encoding="utf-8")
    assert "项目初衷" in readme
    assert "docs/README.en.md" in readme
    assert "agentic RL" in readme
    assert "CC BY 4.0" in data_license
    assert "Responsible Use" in data_license


def load_tests(loader, tests, pattern):
    return TestSuite(
        [
            FunctionTestCase(test_required_files_exist),
            FunctionTestCase(test_readme_language_and_license_policy),
        ]
    )
