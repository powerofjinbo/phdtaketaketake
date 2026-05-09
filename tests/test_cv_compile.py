"""Tests for the CV LaTeX compile pipeline (Sprint-7-c2).

These tests are written to be **environment-tolerant**:

- On a CI / dev box with no TeX → exercises the ``tex_not_installed``
  branch.
- With TeX but missing extra packages (BasicTeX / TinyTeX) → exercises
  the ``failed`` branch and verifies the diagnostic excerpt surfaces
  the missing-file line.
- With a full TeX install → exercises the success branch.

The unit tests (no TeX needed) are unconditional. The integration tests
that actually invoke ``latexmk`` / ``pdflatex`` adapt to whatever the
host environment provides.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from phd_matcher.cv import TEMPLATE_PATH
from phd_matcher.cv.compile import (
    INSTALL_HINT,
    CompileResult,
    _find_compiler,
    classify_failure,
    compile_cv,
    extract_error_excerpt,
)
from phd_matcher.cv.template_helpers import uncomment_optional_blocks

# --- Pure-function tests (no TeX needed) ----------------------------------


def test_extract_error_excerpt_pulls_latex_error_lines() -> None:
    """The diagnostic extractor should keep ``! LaTeX Error:`` lines and
    drop the surrounding noise."""
    log = textwrap.dedent(
        """\
        This is pdfTeX, Version 3.141592653-2.6-1.40.28
        (./cv.tex
        LaTeX2e <2024-06-01> patch level 2
        L3 programming layer <2024-06-01>
        ! LaTeX Error: File `unknown.sty' not found.

        Type X to quit or <RETURN> to proceed,
        or enter new name. (Default extension: sty)

        Enter file name:
        ! Emergency stop.
        <read *>
        l.10 \\usepackage
                         {unknown}
        """
    )
    excerpt = extract_error_excerpt(log)
    # Two interesting lines should be picked out: the error and l.10
    assert any("LaTeX Error" in line for line in excerpt)
    assert any(line.startswith("l.10") for line in excerpt)
    assert any("Emergency stop" in line for line in excerpt)
    # Boilerplate noise should NOT be in the excerpt
    assert not any("pdfTeX, Version" in line for line in excerpt)
    assert not any("L3 programming" in line for line in excerpt)


def test_extract_error_excerpt_picks_up_undefined_control_sequence() -> None:
    log = textwrap.dedent(
        """\
        ! Undefined control sequence.
        l.42 \\notarealcommand
        """
    )
    excerpt = extract_error_excerpt(log)
    assert any("Undefined control sequence" in line for line in excerpt)
    assert any(line.startswith("l.42") for line in excerpt)


def test_extract_error_excerpt_caps_at_max_lines() -> None:
    log = "\n".join(["! Error: thing " + str(i) for i in range(100)])
    excerpt = extract_error_excerpt(log, max_lines=5)
    assert len(excerpt) == 5


def test_extract_error_excerpt_returns_empty_for_clean_log() -> None:
    log = textwrap.dedent(
        """\
        This is pdfTeX, Version 3.14
        (./cv.tex)
        Output written on cv.pdf (1 page).
        """
    )
    assert extract_error_excerpt(log) == []


def test_install_hint_mentions_recovery_paths() -> None:
    """The install hint must mention all three platforms + Overleaf
    fallback + the minimal-TeX extras gotcha (titlesec / enumitem)."""
    assert "macOS" in INSTALL_HINT or "mactex" in INSTALL_HINT.lower()
    assert "apt install" in INSTALL_HINT or "Debian" in INSTALL_HINT
    assert "MiKTeX" in INSTALL_HINT or "TeX Live" in INSTALL_HINT
    assert "overleaf.com" in INSTALL_HINT.lower()
    assert "titlesec" in INSTALL_HINT
    assert "enumitem" in INSTALL_HINT


# --- Compiler-discovery test ---------------------------------------------


def test_find_compiler_returns_none_when_neither_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """When neither latexmk nor pdflatex is on PATH, ``_find_compiler``
    must return ``(None, None)`` so callers can short-circuit to the
    ``tex_not_installed`` branch."""
    monkeypatch.setattr("phd_matcher.cv.compile.shutil.which", lambda _name: None)
    assert _find_compiler() == (None, None)


def test_find_compiler_prefers_latexmk(monkeypatch: pytest.MonkeyPatch) -> None:
    """When both are installed, latexmk wins because it handles
    multi-pass internally."""

    def fake_which(name: str) -> str | None:
        return f"/fake/bin/{name}" if name in {"latexmk", "pdflatex"} else None

    monkeypatch.setattr("phd_matcher.cv.compile.shutil.which", fake_which)
    path, name = _find_compiler()
    assert name == "latexmk"
    assert path == "/fake/bin/latexmk"


def test_find_compiler_falls_back_to_pdflatex(monkeypatch: pytest.MonkeyPatch) -> None:
    """When only pdflatex is available, return that."""

    def fake_which(name: str) -> str | None:
        return "/fake/bin/pdflatex" if name == "pdflatex" else None

    monkeypatch.setattr("phd_matcher.cv.compile.shutil.which", fake_which)
    path, name = _find_compiler()
    assert name == "pdflatex"


# --- compile_cv top-level behaviour --------------------------------------


def test_compile_cv_raises_on_missing_input_file(tmp_path: Path) -> None:
    """Bad input is an *input* error, not a compile error — distinguish
    via FileNotFoundError vs. CompileResult."""
    with pytest.raises(FileNotFoundError):
        compile_cv(tmp_path / "does_not_exist.tex")


def test_compile_cv_returns_tex_not_installed_when_no_compiler(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When neither latexmk nor pdflatex is present, compile_cv must
    return a structured ``tex_not_installed`` result with the
    install_hint populated."""
    tex = tmp_path / "cv.tex"
    tex.write_text(r"\documentclass{article}\begin{document}hi\end{document}", encoding="utf-8")
    monkeypatch.setattr("phd_matcher.cv.compile.shutil.which", lambda _: None)
    result = compile_cv(tex)
    assert result.status == "tex_not_installed"
    assert result.install_hint is not None
    assert "overleaf" in result.install_hint.lower()
    assert result.pdf_path is None


# --- Integration tests (require TeX) --------------------------------------


def _has_tex() -> bool:
    return shutil.which("latexmk") is not None or shutil.which("pdflatex") is not None


@pytest.mark.skipif(not _has_tex(), reason="TeX (latexmk/pdflatex) not installed")
def test_compile_failure_surfaces_actionable_diagnostic(tmp_path: Path) -> None:
    """Compile a deliberately-broken .tex (unescaped percent sign breaks
    out of the comment trick we want it to fail in) and verify the
    failure path produces a structured CompileResult with at least one
    actionable error line."""
    bad = tmp_path / "bad.tex"
    bad.write_text(
        textwrap.dedent(
            r"""
            \documentclass{article}
            \begin{document}
            \notarealcommand
            \end{document}
            """
        ).strip(),
        encoding="utf-8",
    )
    result = compile_cv(bad)
    # Either compile failed (TeX present) or TeX wasn't installed (skipped above).
    assert result.status == "failed"
    assert result.compiler in {"latexmk", "pdflatex"}
    # Must surface the undefined-control-sequence error.
    joined = "\n".join(result.error_excerpt)
    assert "Undefined control sequence" in joined or "\\notarealcommand" in joined


@pytest.mark.skipif(not _has_tex(), reason="TeX (latexmk/pdflatex) not installed")
def test_compile_bundled_template_does_not_raise(tmp_path: Path) -> None:
    """Compile the bundled CV template. We don't assert success — some
    minimal TeX installs are missing titlesec / enumitem, in which case
    the diagnostic path should fire cleanly. We just assert compile_cv
    returns a structured CompileResult either way (no exceptions)."""
    cv = tmp_path / "cv.tex"
    cv.write_text(TEMPLATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    result = compile_cv(cv)
    assert isinstance(result, CompileResult)
    assert result.status in {"ok", "failed"}
    if result.status == "ok":
        assert result.pdf_path is not None
        assert result.pdf_path.exists()
        assert result.pdf_path.stat().st_size > 0
    else:
        # On envs missing texlive-latex-extra (TinyTeX, BasicTeX, etc),
        # we should at least surface what package is missing.
        joined = "\n".join(result.error_excerpt)
        assert ".sty' not found" in joined or "Undefined control sequence" in joined


# --- CLI behaviour -------------------------------------------------------


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "phd_matcher.cv.cli.compile", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_help_does_not_crash() -> None:
    result = _run_cli("--help")
    assert result.returncode == 0
    assert "phdtaketaketake-cv-compile" in result.stdout


def test_cli_missing_input_returns_exit_code_3(tmp_path: Path) -> None:
    """File not found → exit code 3 (input error), distinct from
    compile failure (1) and tex-not-installed (2)."""
    result = _run_cli(str(tmp_path / "does_not_exist.tex"))
    assert result.returncode == 3
    assert "not found" in result.stderr.lower()


@pytest.mark.skipif(not _has_tex(), reason="TeX (latexmk/pdflatex) not installed")
def test_cli_compile_failure_returns_exit_code_1(tmp_path: Path) -> None:
    bad = tmp_path / "bad.tex"
    bad.write_text(
        r"\documentclass{article}\begin{document}\notarealcmd\end{document}",
        encoding="utf-8",
    )
    result = _run_cli(str(bad))
    assert result.returncode == 1
    # Friendly hint about LaTeX special-char escaping should appear.
    assert "Overleaf" in result.stderr or "overleaf" in result.stderr.lower()


# --- Failure classifier (Sprint-7-c6) ------------------------------------


def test_classify_failure_missing_package_extracts_name() -> None:
    excerpt = [
        "! LaTeX Error: File `titlesec.sty' not found.",
        "! Emergency stop.",
        "l.41 \\usepackage",
    ]
    kind, missing = classify_failure(excerpt)
    assert kind == "missing_package"
    assert missing == ["titlesec"]


def test_classify_failure_missing_class_also_caught() -> None:
    excerpt = ["! LaTeX Error: File `unknown.cls' not found."]
    kind, missing = classify_failure(excerpt)
    assert kind == "missing_package"
    assert missing == ["unknown"]


def test_classify_failure_missing_package_dedupes() -> None:
    """Same .sty failure can appear multiple times in the excerpt
    (once from latexmk's first invocation, once from the rerun) — the
    `missing_packages` list should de-duplicate."""
    excerpt = [
        "! LaTeX Error: File `enumitem.sty' not found.",
        "! LaTeX Error: File `enumitem.sty' not found.",
    ]
    kind, missing = classify_failure(excerpt)
    assert kind == "missing_package"
    assert missing == ["enumitem"]


def test_classify_failure_structure_for_missing_item() -> None:
    """The user-found-bug template variants triggered "Something's
    wrong--perhaps a missing \\item" — that must classify as structure,
    not as the catch-all unescaped-chars hint."""
    excerpt = [
        "! LaTeX Error: Something's wrong--perhaps a missing \\item.",
        "l.180",
    ]
    kind, missing = classify_failure(excerpt)
    assert kind == "structure"
    assert missing == []


def test_classify_failure_undefined_command_after_missing_package_check() -> None:
    """A pure typo (no missing-package context) should classify as
    undefined_command. Order matters: missing_package check runs first
    because a missing package can downstream-trigger undefined-command,
    and we want the user to fix the root cause (install the package)
    not chase phantom typos."""
    excerpt = [
        "! Undefined control sequence.",
        "l.42 \\notarealcommand",
    ]
    kind, missing = classify_failure(excerpt)
    assert kind == "undefined_command"
    assert missing == []


def test_classify_failure_missing_package_outranks_undefined_command() -> None:
    """If the log has BOTH a missing-package error AND a downstream
    undefined-command, the classifier must pick missing_package — that's
    the actionable root cause."""
    excerpt = [
        "! LaTeX Error: File `marvosym.sty' not found.",
        "! Undefined control sequence.",
        "l.42 \\Mundus",
    ]
    kind, missing = classify_failure(excerpt)
    assert kind == "missing_package"
    assert missing == ["marvosym"]


def test_classify_failure_unescaped_chars_for_alignment_tab() -> None:
    excerpt = [
        "! Misplaced alignment tab character &.",
        "l.10 R&D engineer",
    ]
    kind, _missing = classify_failure(excerpt)
    assert kind == "unescaped_chars"


def test_classify_failure_unknown_when_nothing_matches() -> None:
    excerpt = ["! Some unexpected error nobody has seen before."]
    kind, missing = classify_failure(excerpt)
    assert kind == "unknown"
    assert missing == []


# --- Compile-result wiring (Sprint-7-c6) ---------------------------------


def test_compile_result_default_has_no_failure_kind() -> None:
    """Sanity: the dataclass defaults preserve back-compat — older
    callers that construct `CompileResult(status="ok", pdf_path=...)`
    without specifying `failure_kind` keep working."""
    r = CompileResult(status="ok", pdf_path=Path("/tmp/cv.pdf"))
    assert r.failure_kind is None
    assert r.missing_packages == []


@pytest.mark.skipif(not _has_tex(), reason="TeX (latexmk/pdflatex) not installed")
def test_compile_failure_populates_failure_kind_and_missing_packages(tmp_path: Path) -> None:
    """End-to-end: a deliberately-missing-package .tex must produce a
    CompileResult with `failure_kind="missing_package"` and the bare
    package name in `missing_packages`."""
    bad = tmp_path / "bad.tex"
    bad.write_text(
        textwrap.dedent(
            r"""
            \documentclass{article}
            \usepackage{thispackagedoesnotexist123}
            \begin{document}
            hello
            \end{document}
            """
        ).strip(),
        encoding="utf-8",
    )
    result = compile_cv(bad)
    assert result.status == "failed"
    assert result.failure_kind == "missing_package"
    assert "thispackagedoesnotexist123" in result.missing_packages


# --- Bundled-template compile (Sprint-7-c6) ------------------------------
#
# These two tests pin the user-found bugs from the first real run:
#   - As-shipped template must compile cleanly.
#   - Template with all OPTIONAL_BLOCKS uncommented (per the agent
#     contract documented in references/cv_optimization.md) must also
#     compile cleanly.
# Both skip when TeX is absent or required packages are missing — but
# crucially, they FAIL (not skip) on a structural template error,
# which is what we want to catch in CI.


def _required_packages_present_or_skip(result: CompileResult) -> None:
    """Skip the test if the failure is purely a missing-package issue
    (out of our control on minimal TeX installs); fail the test
    otherwise (a real template structural bug we want to catch)."""
    if result.status == "tex_not_installed":
        pytest.skip("TeX not installed")
    if result.status == "failed" and result.failure_kind == "missing_package":
        pytest.skip(f"required TeX packages missing: {result.missing_packages}")


@pytest.mark.skipif(not _has_tex(), reason="TeX (latexmk/pdflatex) not installed")
def test_bundled_template_compiles_as_shipped(tmp_path: Path) -> None:
    """The as-shipped template MUST compile to a valid PDF on a TeX
    install with the required packages. Sprint-7-c6 added this test
    after a real-user run hit three structural LaTeX bugs that didn't
    surface in c1's existence-only test."""
    cv = tmp_path / "cv.tex"
    cv.write_text(TEMPLATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    result = compile_cv(cv)
    _required_packages_present_or_skip(result)
    assert result.status == "ok", (
        "as-shipped template failed to compile (not a missing-package "
        f"issue): kind={result.failure_kind} excerpt={result.error_excerpt}"
    )
    assert result.pdf_path is not None
    assert result.pdf_path.exists()
    assert result.pdf_path.stat().st_size > 0


@pytest.mark.skipif(not _has_tex(), reason="TeX (latexmk/pdflatex) not installed")
def test_bundled_template_compiles_with_all_optional_blocks_enabled(
    tmp_path: Path,
) -> None:
    """Same as the as-shipped test, but with every OPTIONAL_BLOCK
    region uncommented per the agent contract (Coursework table +
    multi-affiliation extra emails). User-reported bug:
    `OPTIONAL_BLOCK: Relevant Coursework` triggered "missing \\item"
    when uncommented because the tabular fell into the itemize without
    a fresh \\item prefix. The c6 fix prepends `\\item[]` inside the
    block; this test pins it."""
    text = TEMPLATE_PATH.read_text(encoding="utf-8")
    enabled = uncomment_optional_blocks(text)
    cv = tmp_path / "cv_all_blocks.tex"
    cv.write_text(enabled, encoding="utf-8")
    result = compile_cv(cv)
    _required_packages_present_or_skip(result)
    assert result.status == "ok", (
        "all-optional-blocks template failed to compile (not a missing-"
        f"package issue): kind={result.failure_kind} "
        f"excerpt={result.error_excerpt}"
    )
    assert result.pdf_path is not None
    assert result.pdf_path.exists()


# --- Uncomment helper (Sprint-7-c6) --------------------------------------


def test_uncomment_optional_blocks_strips_leading_comment_prefix() -> None:
    text = (
        "% --- OPTIONAL_BLOCK_START: Test ---\n"
        "%    \\item[] hello\n"
        "%    \\textbf{world}\n"
        "% --- OPTIONAL_BLOCK_END: Test ---\n"
    )
    out = uncomment_optional_blocks(text)
    # Marker lines preserved verbatim
    assert "OPTIONAL_BLOCK_START: Test" in out
    assert "OPTIONAL_BLOCK_END: Test" in out
    # Inner lines lost their leading "% " (2 chars: percent + space).
    # Input "%    \item[] hello" (% + 4 spaces + content) becomes
    # "   \item[] hello" (3 spaces + content) — still indented, but
    # the comment prefix is gone.
    assert "   \\item[] hello" in out
    assert "   \\textbf{world}" in out
    # The "% " prefix should NOT remain on inner lines
    assert "% \\item[]" not in out
    assert "%    \\item[]" not in out


def test_uncomment_optional_blocks_leaves_outside_text_alone() -> None:
    """Lines outside any OPTIONAL_BLOCK pair must stay verbatim."""
    text = (
        "regular line 1\n"
        "% comment that stays\n"
        "% --- OPTIONAL_BLOCK_START: Foo ---\n"
        "% inner\n"
        "% --- OPTIONAL_BLOCK_END: Foo ---\n"
        "% comment that also stays\n"
        "regular line 2\n"
    )
    out = uncomment_optional_blocks(text)
    assert "regular line 1" in out
    assert "% comment that stays" in out
    assert "% comment that also stays" in out
    assert "regular line 2" in out
    # Inner block uncommented
    assert "\ninner\n" in out


def test_uncomment_optional_blocks_handles_naked_percent() -> None:
    """Blank-style separator lines like "%" (just the percent, no space)
    should also lose their prefix."""
    text = (
        "% --- OPTIONAL_BLOCK_START: X ---\n"
        "% line a\n"
        "%\n"  # naked percent, separator
        "% line b\n"
        "% --- OPTIONAL_BLOCK_END: X ---\n"
    )
    out = uncomment_optional_blocks(text)
    lines = out.splitlines()
    # Find the lines between markers
    inside = [
        line for line in lines
        if "OPTIONAL_BLOCK" not in line
    ]
    assert "line a" in inside
    assert "" in inside  # the bare-% separator turned into a blank line
    assert "line b" in inside


# --- CLI hint routing (Sprint-7-c6) --------------------------------------


@pytest.mark.skipif(not _has_tex(), reason="TeX (latexmk/pdflatex) not installed")
def test_cli_emits_targeted_tlmgr_hint_on_missing_package(tmp_path: Path) -> None:
    """End-to-end: CLI on a missing-package failure must print the
    specific `tlmgr install <pkg>` command, not the generic
    unescaped-chars hint."""
    bad = tmp_path / "bad.tex"
    bad.write_text(
        textwrap.dedent(
            r"""
            \documentclass{article}
            \usepackage{thispackagedoesnotexist123}
            \begin{document}
            hello
            \end{document}
            """
        ).strip(),
        encoding="utf-8",
    )
    result = _run_cli(str(bad))
    assert result.returncode == 1
    # Targeted: package name in the hint
    assert "thispackagedoesnotexist123" in result.stderr
    assert "tlmgr install" in result.stderr
    # Not the generic unescaped-chars message
    assert "unescaped LaTeX special" not in result.stderr


@pytest.mark.skipif(not _has_tex(), reason="TeX (latexmk/pdflatex) not installed")
def test_cli_emits_structure_hint_on_missing_item_failure(tmp_path: Path) -> None:
    bad = tmp_path / "bad.tex"
    bad.write_text(
        textwrap.dedent(
            r"""
            \documentclass{article}
            \usepackage{enumitem}
            \begin{document}
            \begin{itemize}[leftmargin=0.15in, label={}]
            \begin{itemize}
            \item nested without outer item
            \end{itemize}
            \end{itemize}
            \end{document}
            """
        ).strip(),
        encoding="utf-8",
    )
    result = _run_cli(str(bad))
    assert result.returncode == 1
    # Structure hint should fire, not unescaped-chars
    assert "itemize / list-environment structure" in result.stderr
    assert "unescaped LaTeX special" not in result.stderr


# --- Install-hint content (updated Sprint-7-c6) --------------------------


def test_install_hint_lists_fancyhdr() -> None:
    """fancyhdr was added to the required-extras list in c6 after a
    user run found tlmgr install titlesec enumitem alone wasn't
    enough on TinyTeX."""
    assert "fancyhdr" in INSTALL_HINT


def test_install_hint_mentions_historic_mirror_recovery() -> None:
    """TinyTeX users hit a TeX-Live-version mismatch where tlmgr
    refuses to install. The historic-mirror trick is non-obvious;
    the install hint should mention it."""
    assert "historic" in INSTALL_HINT.lower()
    assert "tlnet-final" in INSTALL_HINT


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
