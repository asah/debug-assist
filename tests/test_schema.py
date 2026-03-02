"""
Fast structural validation of SKILL.md — no LLM calls required.

Tests that the skill definition is well-formed: frontmatter fields are correct,
body has the required sections and phases, tools are consistent, and internal
references resolve to existing files.
"""

import re
from pathlib import Path

import pytest

REFERENCES_DIR = Path(__file__).parent.parent / "references"


# ══════════════════════════════════════════════════════════════════════════════
# Frontmatter validation
# ══════════════════════════════════════════════════════════════════════════════

class TestFrontmatter:
    """Validate YAML frontmatter fields in SKILL.md."""

    def test_name_exists(self, skill_metadata):
        assert "name" in skill_metadata

    def test_name_is_string(self, skill_metadata):
        assert isinstance(skill_metadata["name"], str)

    def test_name_is_kebab_case(self, skill_metadata):
        assert re.match(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$", skill_metadata["name"]), (
            f"name must be kebab-case, got: {skill_metadata['name']}"
        )

    def test_name_value(self, skill_metadata):
        assert skill_metadata["name"] == "debug-assist"

    def test_description_exists(self, skill_metadata):
        assert "description" in skill_metadata

    def test_description_is_string(self, skill_metadata):
        assert isinstance(skill_metadata["description"], str)

    def test_description_minimum_length(self, skill_metadata):
        assert len(skill_metadata["description"]) >= 10, (
            "description must be at least 10 characters"
        )

    def test_description_mentions_debug(self, skill_metadata):
        desc = skill_metadata["description"].lower()
        assert "debug" in desc, "description should mention debugging"

    def test_version_exists(self, skill_metadata):
        assert "version" in skill_metadata

    def test_version_is_semver_like(self, skill_metadata):
        version = str(skill_metadata["version"])
        assert re.match(r"^\d+\.\d+\.\d+", version), (
            f"version should be semver-like, got: {version}"
        )

    def test_tools_exists(self, skill_metadata):
        assert "tools" in skill_metadata

    def test_tools_is_string(self, skill_metadata):
        assert isinstance(skill_metadata["tools"], str)

    def test_tools_includes_required(self, skill_metadata):
        tools = skill_metadata["tools"]
        for tool in ["Read", "Glob", "Grep", "Bash"]:
            assert tool in tools, f"tools should include {tool}"


# ══════════════════════════════════════════════════════════════════════════════
# Body structure validation
# ══════════════════════════════════════════════════════════════════════════════

class TestBody:
    """Validate that the markdown body has all required sections."""

    def test_body_not_empty(self, skill_body):
        assert len(skill_body) > 100, "skill body should be substantial"

    def test_has_title(self, skill_body):
        assert "# Debug Assist" in skill_body

    def test_has_phase_1(self, skill_body):
        assert "## Phase 1" in skill_body

    def test_has_phase_2(self, skill_body):
        assert "## Phase 2" in skill_body

    def test_has_phase_3(self, skill_body):
        assert "## Phase 3" in skill_body

    def test_has_phase_4(self, skill_body):
        assert "## Phase 4" in skill_body

    def test_has_phase_5(self, skill_body):
        assert "## Phase 5" in skill_body

    def test_has_strategy_selection(self, skill_body):
        assert "## Strategy Selection" in skill_body

    def test_has_auto_detection(self, skill_body):
        assert "Auto-Detection" in skill_body

    def test_has_additional_resources(self, skill_body):
        assert "## Additional Resources" in skill_body

    def test_strategy_table_has_rows(self, skill_body):
        """The strategy selection table should have multiple scenario rows."""
        # Count table rows (lines starting with |) in the Strategy Selection section
        in_section = False
        row_count = 0
        for line in skill_body.splitlines():
            if "## Strategy Selection" in line:
                in_section = True
                continue
            if in_section and line.startswith("##"):
                break
            if in_section and line.startswith("|") and "---" not in line and "Scenario" not in line:
                row_count += 1
        assert row_count >= 5, f"Strategy table should have at least 5 scenario rows, found {row_count}"

    def test_logging_placement_hierarchy(self, skill_body):
        """Phase 3 should list the 7-tier logging placement hierarchy."""
        for i in range(1, 8):
            assert f"{i}. **" in skill_body, (
                f"Missing numbered placement point {i} in logging hierarchy"
            )

    def test_breakpoint_types_present(self, skill_body):
        """Phase 4 should cover primary, secondary, tertiary, error, and conditional breakpoints."""
        for bp_type in ["Primary", "Secondary", "Tertiary", "Error", "Conditional"]:
            assert f"**{bp_type}" in skill_body, (
                f"Missing breakpoint type: {bp_type}"
            )

    def test_inspection_checklist_present(self, skill_body):
        """Phase 4 should have the 7-item inspection checklist."""
        for item in ["Local variables", "Call stack", "Closure", "Object internals",
                      "Global", "Thread", "Heap"]:
            assert item in skill_body, f"Missing inspection checklist item: {item}"

    def test_marker_convention_present(self, skill_body):
        """Phase 5 should define DEBUG-TEMP and DEBUG-KEEP markers."""
        assert "DEBUG-TEMP" in skill_body
        assert "DEBUG-KEEP" in skill_body

    def test_cleanup_procedure_present(self, skill_body):
        """Phase 5 should include a cleanup procedure."""
        assert "Cleanup" in skill_body


# ══════════════════════════════════════════════════════════════════════════════
# Reference link integrity
# ══════════════════════════════════════════════════════════════════════════════

class TestReferenceLinks:
    """Verify that all reference links in SKILL.md point to existing files."""

    EXPECTED_REFERENCES = [
        "references/logging-patterns.md",
        "references/debugger-strategies.md",
        "references/debug-lifecycle.md",
        "references/parallel-debug-agents.md",
    ]

    def test_all_reference_links_present(self, skill_body):
        """SKILL.md should contain links to all four reference files."""
        for ref in self.EXPECTED_REFERENCES:
            assert ref in skill_body, f"Missing reference link: {ref}"

    @pytest.mark.parametrize("ref_path", EXPECTED_REFERENCES)
    def test_reference_file_exists(self, ref_path):
        """Each referenced file should exist on disk."""
        full_path = Path(__file__).parent.parent / ref_path
        assert full_path.exists(), f"Referenced file not found: {ref_path}"

    @pytest.mark.parametrize("ref_path", EXPECTED_REFERENCES)
    def test_reference_file_not_empty(self, ref_path):
        """Each referenced file should have substantial content."""
        full_path = Path(__file__).parent.parent / ref_path
        content = full_path.read_text()
        assert len(content) > 100, f"Reference file is too short: {ref_path}"


# ══════════════════════════════════════════════════════════════════════════════
# Tool consistency
# ══════════════════════════════════════════════════════════════════════════════

class TestToolConsistency:
    """Verify that tools declared in frontmatter match what the body references."""

    def test_body_references_glob_grep(self, skill_body):
        """The body should reference Glob/Grep since they are declared tools."""
        assert "Glob" in skill_body or "grep" in skill_body.lower()
        assert "Grep" in skill_body or "grep" in skill_body.lower()

    def test_body_references_task_for_parallel(self, skill_body):
        """Since Task is declared, body should reference parallel subagents."""
        assert "Task" in skill_body or "subagent" in skill_body.lower()

    def test_body_references_read(self, skill_body):
        """Since Read is declared, body should reference reading code."""
        assert "Read" in skill_body


# ══════════════════════════════════════════════════════════════════════════════
# Marker convention consistency
# ══════════════════════════════════════════════════════════════════════════════

class TestMarkerConsistency:
    """Verify that marker conventions in SKILL.md match those in references/debug-lifecycle.md."""

    def test_markers_match_lifecycle_reference(self, skill_body):
        """Both SKILL.md and debug-lifecycle.md should define the same markers."""
        lifecycle_path = REFERENCES_DIR / "debug-lifecycle.md"
        lifecycle = lifecycle_path.read_text()

        # Both should reference DEBUG-TEMP and DEBUG-KEEP
        for marker in ["DEBUG-TEMP", "DEBUG-KEEP"]:
            assert marker in skill_body, f"SKILL.md missing marker: {marker}"
            assert marker in lifecycle, f"debug-lifecycle.md missing marker: {marker}"

    def test_language_marker_prefixes_present(self, skill_body):
        """SKILL.md should list marker prefixes for multiple language families."""
        # Python-style
        assert "# DEBUG-TEMP:" in skill_body
        # C-style
        assert "// DEBUG-TEMP:" in skill_body
