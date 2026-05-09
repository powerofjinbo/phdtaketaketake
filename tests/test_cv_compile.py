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
    compile_cv,
    extract_error_excerpt,
)

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


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
