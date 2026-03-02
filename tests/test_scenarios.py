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

def assert_output_relevant(output: str, scenario: dict, min_matches: int = 3):
    """Assert the LLM output demonstrates understanding of the bug.

    Checks a combined pool of expected terms: filenames, function names,
    module names, and domain keywords. The LLM may use any combination —
    what matters is that enough relevant terms appear, not which specific
    ones it chose.
    """
    # Build a combined pool from all scenario identifiers
    pool = list(scenario["expected_mentions"])
    pool.append(scenario["buggy_file"].rsplit("/", 1)[-1])          # e.g. "user_service.py"
    pool.append(scenario["buggy_file"].rsplit("/", 1)[-1].rsplit(".", 1)[0])  # e.g. "user_service"
    pool.extend(scenario.get("alt_identifiers", []))

    lower = output.lower()
    matches = [term for term in pool if term.lower() in lower]
    # Deduplicate (e.g. a function name might appear in both lists)
    unique_matches = list(dict.fromkeys(matches))

    assert len(unique_matches) >= min_matches, (
        f"Expected at least {min_matches} of {pool} in output, "
        f"but only found: {unique_matches}\n\nOutput excerpt:\n{output[:1500]}"
    )


def assert_has_actionable_guidance(output: str):
    """Assert the output contains actionable debugging guidance."""
    lower = output.lower()
    has_guidance = any(term in lower for term in [
        "log", "breakpoint", "inspect", "add", "check", "debug",
        "print", "trace", "recommend", "suggest",
        "fix", "root cause", "affected", "issue", "problem",
        "solution", "change", "replace", "update", "modify",
        "formula", "ceiling", "guard", "lock", "mutex",
    ])
    assert has_guidance, (
        f"Expected actionable debugging guidance in output.\n\nOutput excerpt:\n{output[:1500]}"
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

        assert_output_relevant(output, scenario)
        assert_has_actionable_guidance(output)


@pytest.mark.integration
class TestRaceConditionBug:
    """Test that the skill diagnoses a threading race condition."""

    def test_detects_race_condition(self, make_test_repo):
        repo_dir = make_test_repo("race-cond")
        scenario = build_race_condition_bug(repo_dir)

        prompt = build_prompt_from_skill(scenario["error_message"])
        output = run_skill(prompt, repo_dir)

        assert_output_relevant(output, scenario)
        assert_has_actionable_guidance(output)


@pytest.mark.integration
class TestSwallowedErrorBug:
    """Test that the skill diagnoses silently swallowed exceptions."""

    def test_detects_swallowed_error(self, make_test_repo):
        repo_dir = make_test_repo("swallowed-err")
        scenario = build_swallowed_error_bug(repo_dir)

        prompt = build_prompt_from_skill(scenario["error_message"])
        output = run_skill(prompt, repo_dir)

        assert_output_relevant(output, scenario)
        assert_has_actionable_guidance(output)


@pytest.mark.integration
class TestPaginationBug:
    """Test that the skill diagnoses an off-by-one pagination bug."""

    def test_detects_pagination_bug(self, make_test_repo):
        repo_dir = make_test_repo("pagination")
        scenario = build_pagination_bug(repo_dir)

        prompt = build_prompt_from_skill(scenario["error_message"])
        output = run_skill(prompt, repo_dir)

        assert_output_relevant(output, scenario)
        assert_has_actionable_guidance(output)
