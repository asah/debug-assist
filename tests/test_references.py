"""
Validation of reference files — no LLM calls required.

Tests that each reference file is well-structured, has required sections,
and is consistent with SKILL.md and other reference files.
"""

import re
from pathlib import Path

import pytest

REFERENCES_DIR = Path(__file__).parent.parent / "references"


def _read_ref(name):
    """Read a reference file and return its content."""
    return (REFERENCES_DIR / name).read_text()


# ══════════════════════════════════════════════════════════════════════════════
# Logging Patterns reference
# ══════════════════════════════════════════════════════════════════════════════

class TestLoggingPatterns:
    """Validate references/logging-patterns.md."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = _read_ref("logging-patterns.md")

    def test_has_title(self):
        assert "# Logging Patterns Reference" in self.content

    def test_has_when_logging_beats_debugger(self):
        assert "When Logging Beats a Debugger" in self.content

    def test_has_placement_heuristics(self):
        assert "Strategic Placement Heuristics" in self.content

    def test_has_three_tiers(self):
        assert "Tier 1" in self.content
        assert "Tier 2" in self.content
        assert "Tier 3" in self.content

    def test_has_what_to_include(self):
        assert "What to Include" in self.content

    def test_has_language_idioms(self):
        assert "Language-Specific Idioms" in self.content

    def test_covers_multiple_languages(self):
        for lang in ["Python", "JavaScript", "Go", "Rust", "Java", "C /", "Ruby"]:
            assert lang in self.content, f"Missing language: {lang}"

    def test_has_structured_logging(self):
        assert "Structured Logging" in self.content

    def test_has_correlation_ids(self):
        assert "Correlation ID" in self.content

    def test_has_log_level_guide(self):
        assert "Log Level Guide" in self.content

    def test_has_anti_patterns(self):
        assert "Anti-pattern" in self.content or "anti-pattern" in self.content

    def test_code_blocks_have_language_annotations(self):
        """Most opening code fences should specify a language."""
        # Fence lines are paired: even-indexed (0, 2, 4...) are openings,
        # odd-indexed are closings.
        fences = re.findall(r"^```(\w*)$", self.content, re.MULTILINE)
        openings = [fences[i] for i in range(0, len(fences), 2)]
        annotated = sum(1 for lang in openings if lang)
        total = len(openings)
        assert total > 0, "No code blocks found"
        ratio = annotated / total
        assert ratio >= 0.8, (
            f"Only {annotated}/{total} opening code blocks have language annotations"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Debugger Strategies reference
# ══════════════════════════════════════════════════════════════════════════════

class TestDebuggerStrategies:
    """Validate references/debugger-strategies.md."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = _read_ref("debugger-strategies.md")

    def test_has_title(self):
        assert "# Debugger Strategies Reference" in self.content

    def test_has_when_debugger_beats_logging(self):
        assert "When a Debugger Beats Logging" in self.content

    def test_has_breakpoint_placement(self):
        assert "Breakpoint Placement Strategy" in self.content

    def test_has_inspection_checklist(self):
        assert "Systematic Inspection Checklist" in self.content

    def test_has_7_inspection_items(self):
        """Should have numbered items 1-7 in the inspection checklist."""
        for i in range(1, 8):
            assert f"### {i}." in self.content, (
                f"Missing inspection item #{i}"
            )

    def test_has_debugger_workflow(self):
        assert "Debugger Workflow" in self.content

    def test_has_platform_specific(self):
        assert "Platform-Specific" in self.content

    def test_covers_major_debuggers(self):
        for debugger in ["pdb", "Node", "Delve", "GDB", "LLDB"]:
            assert debugger in self.content, f"Missing debugger: {debugger}"

    def test_has_watchpoints(self):
        assert "Watchpoint" in self.content or "watchpoint" in self.content

    def test_has_debugger_repl(self):
        assert "REPL" in self.content

    def test_code_blocks_have_language_annotations(self):
        fences = re.findall(r"^```(\w*)$", self.content, re.MULTILINE)
        openings = [fences[i] for i in range(0, len(fences), 2)]
        annotated = sum(1 for lang in openings if lang)
        total = len(openings)
        assert total > 0
        ratio = annotated / total
        # Threshold is 0.7 because some blocks are generic CLI/pseudocode
        assert ratio >= 0.7, (
            f"Only {annotated}/{total} opening code blocks have language annotations"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Debug Lifecycle reference
# ══════════════════════════════════════════════════════════════════════════════

class TestDebugLifecycle:
    """Validate references/debug-lifecycle.md."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = _read_ref("debug-lifecycle.md")

    def test_has_title(self):
        assert "# Debug Code Lifecycle Reference" in self.content

    def test_has_core_problem(self):
        assert "Core Problem" in self.content

    def test_has_marker_convention(self):
        assert "Marker Convention" in self.content

    def test_has_both_markers(self):
        assert "DEBUG-TEMP" in self.content
        assert "DEBUG-KEEP" in self.content

    def test_has_language_prefix_table(self):
        """Should have a table mapping languages to comment prefixes."""
        assert "Language" in self.content and "TEMP marker" in self.content

    def test_has_pre_commit_hook(self):
        assert "Pre-Commit Hook" in self.content or "pre-commit" in self.content.lower()

    def test_has_hook_script(self):
        """Should include an actual hook script."""
        assert "#!/bin/bash" in self.content

    def test_has_bypass_instructions(self):
        assert "--no-verify" in self.content

    def test_has_cleanup_checklist(self):
        assert "Cleanup Checklist" in self.content or "cleanup" in self.content.lower()

    def test_has_promotion_guidance(self):
        assert "Promoting" in self.content or "promotion" in self.content.lower()

    def test_has_workflow_summary(self):
        assert "Workflow Summary" in self.content

    def test_marker_prefix_covers_languages(self):
        """The prefix table should cover Python, JS/TS, HTML, SQL at minimum."""
        for lang in ["Python", "JS", "HTML", "SQL"]:
            assert lang in self.content, f"Missing language in prefix table: {lang}"


# ══════════════════════════════════════════════════════════════════════════════
# Parallel Debug Agents reference
# ══════════════════════════════════════════════════════════════════════════════

class TestParallelDebugAgents:
    """Validate references/parallel-debug-agents.md."""

    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = _read_ref("parallel-debug-agents.md")

    def test_has_title(self):
        assert "# Parallel Debug Agents Reference" in self.content

    def test_has_when_to_parallelize(self):
        assert "When Parallel Agents" in self.content

    def test_has_anti_patterns(self):
        """Should mention when NOT to parallelize."""
        assert "NOT worth it" in self.content or "not worth it" in self.content.lower()

    def test_has_coordination_pattern(self):
        assert "Coordination Pattern" in self.content

    def test_has_three_phases(self):
        assert "Phase 1" in self.content
        assert "Phase 2" in self.content
        assert "Phase 3" in self.content

    def test_has_agent_prompt_templates(self):
        assert "Agent Prompt Templates" in self.content

    def test_has_five_templates(self):
        for template in [
            "Data Flow Tracer",
            "State Mutation Inspector",
            "External Call Boundary Auditor",
            "Error Propagation Tracer",
            "Async/Concurrency Reviewer",
        ]:
            assert template in self.content, f"Missing template: {template}"

    def test_has_synthesis_pattern(self):
        assert "Synthesis Pattern" in self.content

    def test_has_capacity_considerations(self):
        assert "Capacity" in self.content

    def test_has_example(self):
        assert "Example" in self.content

    def test_templates_have_steps(self):
        """Each template should include numbered Steps."""
        # Count how many template sections contain "Steps:"
        templates = self.content.split("### Template")
        # First element is before any template
        template_sections = templates[1:]
        assert len(template_sections) == 5, f"Expected 5 templates, found {len(template_sections)}"
        for i, section in enumerate(template_sections, 1):
            assert "Steps:" in section or "steps:" in section.lower(), (
                f"Template {i} missing Steps section"
            )


# ══════════════════════════════════════════════════════════════════════════════
# Cross-reference consistency
# ══════════════════════════════════════════════════════════════════════════════

class TestCrossReferenceConsistency:
    """Verify consistency between reference files."""

    def test_logging_and_lifecycle_agree_on_markers(self):
        """Both logging-patterns and debug-lifecycle should reference the same markers."""
        logging = _read_ref("logging-patterns.md")
        lifecycle = _read_ref("debug-lifecycle.md")
        # lifecycle defines the markers; logging may reference DEBUG level
        assert "DEBUG" in logging
        assert "DEBUG-TEMP" in lifecycle
        assert "DEBUG-KEEP" in lifecycle

    def test_debugger_and_parallel_complement(self):
        """debugger-strategies should mention breakpoints; parallel-agents should too."""
        debugger = _read_ref("debugger-strategies.md")
        parallel = _read_ref("parallel-debug-agents.md")
        assert "breakpoint" in debugger.lower()
        assert "breakpoint" in parallel.lower()

    def test_lifecycle_markers_consistent_across_languages(self):
        """The lifecycle file should define consistent markers for all listed languages."""
        lifecycle = _read_ref("debug-lifecycle.md")
        # Both TEMP and KEEP markers should appear with # and // prefixes
        assert "# DEBUG-TEMP:" in lifecycle
        assert "// DEBUG-TEMP:" in lifecycle
        assert "# DEBUG-KEEP:" in lifecycle
        assert "// DEBUG-KEEP:" in lifecycle
