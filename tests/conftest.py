"""Shared fixtures for debug-assist skill tests."""

import os
import subprocess
import textwrap
from pathlib import Path

import frontmatter
import pytest

SKILL_PATH = Path(__file__).parent.parent / "SKILL.md"
REFERENCES_DIR = Path(__file__).parent.parent / "references"


# ── Schema fixtures (session-scoped: parse SKILL.md once) ──────────────────

@pytest.fixture(scope="session")
def skill():
    """Parse SKILL.md and return the full frontmatter Post object."""
    return frontmatter.load(str(SKILL_PATH))


@pytest.fixture(scope="session")
def skill_metadata(skill):
    """Return just the YAML frontmatter dict."""
    return dict(skill.metadata)


@pytest.fixture(scope="session")
def skill_body(skill):
    """Return just the markdown body."""
    return skill.content


# ── Integration test fixtures ──────────────────────────────────────────────

@pytest.fixture
def make_test_repo(tmp_path):
    """Factory fixture: creates a fresh, initialized git repo in a temp dir."""

    def _make(name="test-repo"):
        repo_dir = tmp_path / name
        repo_dir.mkdir(parents=True, exist_ok=True)
        _run(repo_dir, "git init")
        _run(repo_dir, "git config user.email test@example.com")
        _run(repo_dir, "git config user.name 'Test User'")
        return repo_dir

    return _make


# ── Helpers for integration tests ──────────────────────────────────────────

def _run(cwd, cmd, check=True):
    """Run a shell command in the given directory."""
    return subprocess.run(
        cmd, shell=True, cwd=str(cwd),
        capture_output=True, text=True, check=check,
    )


def build_prompt_from_skill(error_message):
    """Read SKILL.md, extract the body, substitute $ARGUMENTS."""
    post = frontmatter.load(str(SKILL_PATH))
    body = post.content
    # The skill uses $ARGUMENTS as the placeholder
    prompt = body.replace("$ARGUMENTS", error_message)
    return prompt


def run_skill(prompt, cwd):
    """
    Invoke the debug-assist skill via `claude -p` (Claude Code in pipe mode).

    Returns the LLM's text output.
    """
    # Strip CLAUDE_CODE / CLAUDECODE env vars to allow nested invocation
    env = {
        k: v for k, v in os.environ.items()
        if k not in ("CLAUDE_CODE", "CLAUDECODE")
    }

    result = subprocess.run(
        ["claude", "-p", "--allowedTools", "Bash(git *),Read,Glob,Grep"],
        input=prompt,
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=env,
        timeout=180,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"claude -p failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    return result.stdout
