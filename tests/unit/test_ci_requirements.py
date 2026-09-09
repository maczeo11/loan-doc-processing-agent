"""
Regression checks for CI dependency manifest completeness.
"""

from pathlib import Path


def test_requirements_ci_includes_api_test_dependencies():
    requirements_path = Path(__file__).resolve().parents[2] / "requirements-ci.txt"
    requirements = requirements_path.read_text(encoding="utf-8")

    for dependency in ("pytest-asyncio", "sqlalchemy", "aiosqlite", "fakeredis"):
        assert dependency in requirements
