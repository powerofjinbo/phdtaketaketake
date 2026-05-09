"""LaTeX compile pipeline for the CV sub-skill (Sprint-7-c2).

Picks the best available compiler (``latexmk`` preferred, ``pdflatex``
fallback), runs multi-pass when needed for cross-references, captures
the most-useful diagnostic lines on failure. Designed to be friendly
to agents — never silently succeeds with a broken PDF, never silently
fails with no diagnosis.

Behaviour summary:

- ``latexmk -pdf`` handles multi-pass internally → 1 invocation suffices.
- ``pdflatex`` fallback: run up to ``max_passes`` times; stop early
  when the log no longer says "Rerun to get cross-references right".
- Compile failure: extract ``! LaTeX Error:``, ``l.<num>``, "Undefined
  control sequence", "Missing X inserted", "Runaway argument",
  "Emergency stop" lines from the .log file. Discard the rest.
- TeX not installed: return a structured ``tex_not_installed`` status
  with install hints for macOS / Linux / Windows + Overleaf fallback.

The CLI wrapper (``phd_matcher/cv/cli/compile.py``) renders these
``CompileResult`` objects as user-friendly stdout messages with
appropriate exit codes.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

CompileStatus = Literal["ok", "failed", "tex_not_installed"]


@dataclass
class CompileResult:
    """Structured return value of :func:`compile_cv`.

    ``status``: tri-state. ``ok`` → ``pdf_path`` populated. ``failed``
    → ``error_excerpt`` populated (and ``full_log_path`` if the log
    was preserved). ``tex_not_installed`` → ``install_hint`` populated.
    """

    status: CompileStatus
    pdf_path: Path | None = None
    compiler: str | None = None  # "latexmk" or "pdflatex"
    passes: int = 0
    error_excerpt: list[str] = field(default_factory=list)
    full_log_path: Path | None = None
    install_hint: str | None = None


# -- Compiler discovery --------------------------------------------------------


def _find_compiler() -> tuple[str | None, str | None]:
    """Locate latexmk / pdflatex on ``PATH``.

    Returns ``(executable_path, compiler_name)`` or ``(None, None)``
    when neither is installed. ``latexmk`` is preferred because it
    handles multi-pass cross-reference resolution internally.
    """
    if (path := shutil.which("latexmk")) is not None:
        return path, "latexmk"
    if (path := shutil.which("pdflatex")) is not None:
        return path, "pdflatex"
    return None, None


INSTALL_HINT = (
    "TeX not installed. Install one of:\n"
    "  - macOS:    brew install --cask mactex            # full ~5GB\n"
    "          or  brew install --cask mactex-no-gui     # ~3GB\n"
    "          or  brew install --cask basictex          # ~100MB minimum\n"
    "  - Debian/Ubuntu: sudo apt install texlive-latex-extra latexmk\n"
    "  - Fedora/RHEL:   sudo dnf install texlive-latex texlive-latexmk\n"
    "  - Windows:       TeX Live (https://tug.org/texlive/) or MiKTeX\n"
    "\n"
    "Minimal installs (BasicTeX, TinyTeX) may also need:\n"
    "  tlmgr install titlesec enumitem\n"
    "(the bundled CV template uses these for section styling and "
    "list margins).\n"
    "\n"
    "Or, paste the .tex content into Overleaf (https://overleaf.com) — "
    "the bundled CV template is fully Overleaf-compatible."
)


# -- Log diagnostics -----------------------------------------------------------


# Regex patterns for the actionable lines in a TeX log. Each entry's
# ``re.search`` deciding whether to keep the line. Order matters only
# for documentation; matching is OR.
_INTERESTING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^!\s"),  # "! LaTeX Error:" / "! Undefined control sequence." / etc.
    re.compile(r"^l\.\d+"),  # "l.42 ..." line-number anchor
    re.compile(r"Undefined control sequence"),
    re.compile(r"Missing .+ inserted"),
    re.compile(r"Runaway argument"),
    re.compile(r"Emergency stop"),
    re.compile(r"LaTeX Error:"),
    re.compile(r"^\s*File .+ not found"),  # missing .sty / .cls / image
)


def extract_error_excerpt(log_text: str, max_lines: int = 30) -> list[str]:
    """Pull the most actionable diagnostic lines from a raw TeX log.

    TeX logs are noisy (200–1000+ lines for a typical compile). This
    function distills them to the lines an agent / human can actually
    act on. Capped at ``max_lines`` to keep stdout readable.
    """
    excerpt: list[str] = []
    for line in log_text.splitlines():
        if any(p.search(line) for p in _INTERESTING_PATTERNS):
            stripped = line.rstrip()
            if stripped:
                excerpt.append(stripped)
            if len(excerpt) >= max_lines:
                break
    return excerpt


# -- Main entry ---------------------------------------------------------------


def compile_cv(
    tex_path: Path | str,
    output_dir: Path | str | None = None,
    max_passes: int = 3,
) -> CompileResult:
    """Compile ``tex_path`` to PDF in ``output_dir`` (default: alongside the .tex).

    Strategy:

    1. Detect compiler. ``latexmk`` preferred (one invocation handles
       multi-pass). ``pdflatex`` fallback (we run it up to ``max_passes``
       times to settle cross-references).
    2. Run with ``-interaction=nonstopmode -halt-on-error``.
    3. On failure, read the ``.log`` file and extract diagnostic lines.

    Always returns a :class:`CompileResult`; never raises on compile
    failure. Raises ``FileNotFoundError`` only when ``tex_path`` itself
    doesn't exist (an input error, not a compile error).
    """
    tex_path = Path(tex_path).resolve()
    if not tex_path.exists():
        raise FileNotFoundError(f"CV LaTeX file not found: {tex_path}")

    output_dir = Path(output_dir).resolve() if output_dir else tex_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    compiler_path, compiler_name = _find_compiler()
    if compiler_path is None or compiler_name is None:
        return CompileResult(status="tex_not_installed", install_hint=INSTALL_HINT)

    log_path = output_dir / (tex_path.stem + ".log")
    pdf_path = output_dir / (tex_path.stem + ".pdf")

    if compiler_name == "latexmk":
        result = _run(
            [
                compiler_path,
                "-pdf",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={output_dir}",
                str(tex_path),
            ],
            cwd=tex_path.parent,
        )
        if result.returncode == 0 and pdf_path.exists():
            return CompileResult(
                status="ok",
                pdf_path=pdf_path,
                compiler="latexmk",
                passes=1,
            )
        log_text = _read_or_fallback(log_path, result)
        return CompileResult(
            status="failed",
            compiler="latexmk",
            passes=1,
            error_excerpt=extract_error_excerpt(log_text),
            full_log_path=log_path if log_path.exists() else None,
        )

    # pdflatex path: run up to max_passes times, stop early once the
    # log no longer says "Rerun to get cross-references right".
    log_text = ""
    last_returncode = 0
    last_attempt = 0
    for attempt in range(1, max_passes + 1):
        last_attempt = attempt
        result = _run(
            [
                compiler_path,
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={output_dir}",
                str(tex_path),
            ],
            cwd=tex_path.parent,
        )
        last_returncode = result.returncode
        log_text = _read_or_fallback(log_path, result)
        if result.returncode != 0:
            return CompileResult(
                status="failed",
                compiler="pdflatex",
                passes=attempt,
                error_excerpt=extract_error_excerpt(log_text),
                full_log_path=log_path if log_path.exists() else None,
            )
        # Successful run; check whether another pass is needed.
        if "Rerun" not in log_text:
            break

    if last_returncode == 0 and pdf_path.exists():
        return CompileResult(
            status="ok",
            pdf_path=pdf_path,
            compiler="pdflatex",
            passes=last_attempt,
        )
    # Edge case: pdflatex returned 0 but no PDF (extremely unusual).
    return CompileResult(
        status="failed",
        compiler="pdflatex",
        passes=last_attempt,
        error_excerpt=extract_error_excerpt(log_text)
        or ["pdflatex exited 0 but no PDF was produced"],
        full_log_path=log_path if log_path.exists() else None,
    )


# -- Internals ----------------------------------------------------------------


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a compile command; capture both streams as text.

    Wrapped so test code can monkeypatch a single seam. ``check=False``
    so we can introspect the return code and log file rather than
    raising on a non-zero exit.
    """
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=cwd,
        check=False,
    )


def _read_or_fallback(
    log_path: Path,
    result: subprocess.CompletedProcess[str],
) -> str:
    """Prefer the on-disk ``.log`` file (TeX writes it for any run that
    reached \\documentclass parsing); fall back to combined stdout +
    stderr only when the log is missing (e.g. compiler crashed before
    reaching a writeable state)."""
    if log_path.exists():
        return log_path.read_text(encoding="utf-8", errors="replace")
    return (result.stdout or "") + "\n" + (result.stderr or "")
