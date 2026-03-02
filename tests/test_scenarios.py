"""
LLM-based integration tests — require `claude` CLI and ANTHROPIC_API_KEY.

Each test builds a synthetic repo with a known bug, invokes the debug-assist
skill via `claude -p`, and verifies the output mentions the expected concepts.

Run with: pytest tests/test_scenarios.py -v --timeout=120 -x
"""

import pytest

from tests.conftest import build_prompt_from_skill, run_skill
from tests.fixtures.repo_builders import (
    build_null_reference_bug,
    build_race_condition_bug,
    build_swallowed_error_bug,
    build_pagination_bug,
)


# ── Fuzzy assertion helpers ────────────────────────────────────────────────

def assert_mentions_any(output: str, keywords: list[str], min_matches: int = 2):
    """Assert the output mentions at least `min_matches` of the given keywords (case-insensitive)."""
    lower = output.lower()
    matches = [kw for kw in keywords if kw.lower() in lower]
    assert len(matches) >= min_matches, (
        f"Expected at least {min_matches} of {keywords} in output, "
        f"but only found: {matches}\n\nOutput excerpt:\n{output[:1000]}"
    )


def assert_mentions_file(output: str, filename: str, alt_identifiers: list[str] | None = None):
    """Assert the output references a file — by filename, module name, or key identifiers.

    The LLM may refer to code by filename, module name (stem without extension),
    or by function/class names within the file rather than the filename itself.
    """
    candidates = [filename, filename.rsplit(".", 1)[0]]  # e.g. ["user_service.py", "user_service"]
    if alt_identifiers:
        candidates.extend(alt_identifiers)
    found = any(c in output for c in candidates)
    assert found, (
        f"Expected any of {candidates} in output.\n\nOutput excerpt:\n{output[:1000]}"
    )


def assert_has_actionable_guidance(output: str):
    """Assert the output contains actionable debugging guidance."""
    lower = output.lower()
    has_guidance = any(term in lower for term in [
        "log", "breakpoint", "inspect", "add", "check", "debug",
        "print", "trace", "recommend", "suggest",
        "fix", "root cause", "affected", "issue", "problem",
        "solution", "change", "replace", "update", "modify",
    ])
    assert has_guidance, (
        f"Expected actionable debugging guidance in output.\n\nOutput excerpt:\n{output[:1000]}"
    )


# ── Integration tests ─────────────────────────────────────────────────────

@pytest.mark.integration
class TestNullReferenceBug:
    """Test that the skill diagnoses a null reference / missing guard bug."""

    def test_detects_null_reference(self, make_test_repo):
        repo_dir = make_test_repo("null-ref")
        scenario = build_null_reference_bug(repo_dir)

        prompt = build_prompt_from_skill(scenario["error_message"])
        output = run_skill(prompt, repo_dir)

        assert_mentions_file(output, "user_service.py", scenario["alt_identifiers"])
        assert_mentions_any(output, scenario["expected_mentions"])
        assert_has_actionable_guidance(output)


@pytest.mark.integration
class TestRaceConditionBug:
    """Test that the skill diagnoses a threading race condition."""

    def test_detects_race_condition(self, make_test_repo):
        repo_dir = make_test_repo("race-cond")
        scenario = build_race_condition_bug(repo_dir)

        prompt = build_prompt_from_skill(scenario["error_message"])
        output = run_skill(prompt, repo_dir)

        assert_mentions_file(output, "counter.py", scenario["alt_identifiers"])
        assert_mentions_any(output, scenario["expected_mentions"])
        assert_has_actionable_guidance(output)


@pytest.mark.integration
class TestSwallowedErrorBug:
    """Test that the skill diagnoses silently swallowed exceptions."""

    def test_detects_swallowed_error(self, make_test_repo):
        repo_dir = make_test_repo("swallowed-err")
        scenario = build_swallowed_error_bug(repo_dir)

        prompt = build_prompt_from_skill(scenario["error_message"])
        output = run_skill(prompt, repo_dir)

        assert_mentions_file(output, "api_client.py", scenario["alt_identifiers"])
        assert_mentions_any(output, scenario["expected_mentions"])
        assert_has_actionable_guidance(output)


@pytest.mark.integration
class TestPaginationBug:
    """Test that the skill diagnoses an off-by-one pagination bug."""

    def test_detects_pagination_bug(self, make_test_repo):
        repo_dir = make_test_repo("pagination")
        scenario = build_pagination_bug(repo_dir)

        prompt = build_prompt_from_skill(scenario["error_message"])
        output = run_skill(prompt, repo_dir)

        assert_mentions_file(output, "paginator.py", scenario["alt_identifiers"])
        assert_mentions_any(output, scenario["expected_mentions"])
        assert_has_actionable_guidance(output)
