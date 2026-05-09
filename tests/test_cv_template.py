"""Tests for the bundled CV template + ``phdtaketaketake-cv-template`` CLI.

These pin Sprint-7-c1 invariants:

- The template file ships with the wheel (its path resolves and the
  file exists).
- The template carries the documented "agent contract" markers
  (``<angle-bracket>`` placeholders, ``OPTIONAL_BLOCK`` boundaries,
  ``DO NOT EDIT`` preamble guard) so future edits don't accidentally
  break the agent's parsing of the file.
- The CLI in default mode prints the path; with ``--print`` it prints
  the full template contents to stdout.

The compile pipeline lives in Sprint-7-c2; this file does not depend
on having a TeX install present.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from phd_matcher.cv import TEMPLATE_PATH

# --- Template integrity ---------------------------------------------------


def test_template_file_exists() -> None:
    assert TEMPLATE_PATH.exists(), (
        f"bundled CV template not found at {TEMPLATE_PATH} — did the wheel "
        "package the .tex correctly?"
    )
    assert TEMPLATE_PATH.is_file()


def test_template_is_a_complete_latex_document() -> None:
    """The template must be a syntactically complete LaTeX file (compilable
    as-is to the placeholder demo CV). Cheap structural check only — the
    actual compile is exercised by Sprint-7-c2 tests."""
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "\\documentclass" in text
    # Strip comments before counting begin/end to avoid false positives from
    # the preamble's "DO NOT EDIT until \begin{document}" guidance comment.
    stripped = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("%")
    )
    assert stripped.count("\\begin{document}") == 1
    assert stripped.count("\\end{document}") == 1


def test_template_has_all_default_sections() -> None:
    """Per Sprint-7-c1 contract: all sections shipped on by default; user
    deletes what doesn't apply. Pin so future edits don't silently drop one."""
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    expected_sections = [
        "\\section{Education}",
        "\\section{Research Experience}",
        "\\section{Publications \\& Presentations}",
        "\\section{Technical Skills}",
        "\\section{Teaching Experience}",
        "\\section{Leadership Experience}",
        "\\section{Honors and Awards}",
    ]
    for sect in expected_sections:
        assert sect in text, f"template missing required default section: {sect}"


def test_template_optional_blocks_use_canonical_markers() -> None:
    """Optional content (Coursework table, multi-affiliation emails) is
    wrapped in ``OPTIONAL_BLOCK_START`` / ``OPTIONAL_BLOCK_END`` markers.
    The agent finds these by string match, so they must remain stable."""
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    # Each START must have a matching END.
    starts = text.count("OPTIONAL_BLOCK_START:")
    ends = text.count("OPTIONAL_BLOCK_END:")
    assert starts == ends, (
        f"unbalanced OPTIONAL_BLOCK markers: {starts} START vs {ends} END"
    )
    assert starts >= 2, (
        "expected at least 2 optional blocks (Coursework + multi-email); "
        f"found {starts}"
    )


def test_template_uses_angle_bracket_placeholders() -> None:
    """The agent contract uses ``<placeholder>`` style. Pin a few canonical
    ones so future edits don't switch to a different convention without
    updating SKILL.md / cv_optimization.md."""
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    expected_placeholders = [
        "<Your Full Name>",
        "<primary@example.edu>",
        "<University Name>",
        "<Research Project Title>",
    ]
    for placeholder in expected_placeholders:
        assert placeholder in text, (
            f"template missing canonical placeholder: {placeholder}"
        )


def test_template_preamble_has_dont_edit_guard() -> None:
    """The custom resume commands block must carry a clearly-worded
    "DO NOT EDIT" guard so agents leave the preamble alone."""
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert "DO NOT EDIT" in text


# --- CLI behaviour --------------------------------------------------------


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke the CLI in-process via ``python -m`` so the test does not
    depend on the console-script being installed in the test env."""
    return subprocess.run(
        [sys.executable, "-m", "phd_matcher.cv.cli.template", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_default_prints_path() -> None:
    result = _run_cli()
    assert result.returncode == 0, result.stderr
    out = result.stdout.strip()
    assert out == str(TEMPLATE_PATH)


def test_cli_print_flag_emits_full_template() -> None:
    result = _run_cli("--print")
    assert result.returncode == 0, result.stderr
    expected = TEMPLATE_PATH.read_text(encoding="utf-8")
    assert result.stdout == expected


def test_cli_help_does_not_crash() -> None:
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "phdtaketaketake-cv-template" in result.stdout


# --- Module API -----------------------------------------------------------


def test_template_path_is_exported() -> None:
    """``TEMPLATE_PATH`` must be importable from ``phd_matcher.cv``
    (the agent's documented entry-point for reading the template
    programmatically)."""
    from phd_matcher.cv import TEMPLATE_PATH as imported

    assert imported == TEMPLATE_PATH
    assert imported.exists()


def test_template_module_is_runnable_via_dash_m() -> None:
    """The agent contract documents
    ``python -m phd_matcher.cv.cli.template --print > cv.tex``
    as the canonical way to bootstrap a fresh CV without depending on
    ``pip install``."""
    result = _run_cli("--print")
    assert result.returncode == 0
    assert "\\documentclass" in result.stdout


# Allow running this file standalone for quick iteration.
if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
