"""CLI: ``phdtaketaketake-cv-compile``.

Compiles a CV ``.tex`` file to PDF using the bundled compile pipeline
(:func:`phd_matcher.cv.compile.compile_cv`). Surfaces friendly output
to stdout — success path prints the PDF path, failure path prints the
extracted diagnostic lines + recovery hints.

Exit codes:

- 0  success (PDF produced)
- 1  compile failed (TeX install OK; .tex has an error)
- 2  TeX not installed (no ``latexmk`` / ``pdflatex`` on ``PATH``)
- 3  input error (file not found, etc.)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from phd_matcher.cv.compile import compile_cv


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="phdtaketaketake-cv-compile",
        description=(
            "Compile a CV LaTeX file to PDF. Tries latexmk first "
            "(handles multi-pass cross-reference resolution internally); "
            "falls back to pdflatex (run up to --max-passes times). On "
            "failure, surfaces the most actionable diagnostic lines from "
            "the .log file. On no-TeX-installed, prints install hints "
            "for macOS / Linux / Windows + the Overleaf fallback."
        ),
    )
    ap.add_argument(
        "tex_path",
        type=Path,
        help="Path to the CV .tex file to compile.",
    )
    ap.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Directory to write the .pdf and intermediate .aux / .log "
            "files. Default: alongside the input .tex."
        ),
    )
    ap.add_argument(
        "--max-passes",
        type=int,
        default=3,
        help=(
            "Maximum number of pdflatex passes (only used when latexmk "
            "is unavailable). Default: 3 — typical CVs settle in 2."
        ),
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the PDF path on success; suppress the success banner.",
    )
    return ap


def main() -> int:
    args = build_parser().parse_args()

    try:
        result = compile_cv(
            args.tex_path,
            output_dir=args.output_dir,
            max_passes=args.max_passes,
        )
    except FileNotFoundError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 3

    if result.status == "ok":
        if args.quiet:
            print(result.pdf_path)
        else:
            print(
                f"✓ Compiled {args.tex_path.name} with {result.compiler} "
                f"({result.passes} pass{'es' if result.passes != 1 else ''})."
            )
            print(f"  → {result.pdf_path}")
        return 0

    if result.status == "tex_not_installed":
        print("✗ TeX not installed.", file=sys.stderr)
        print(file=sys.stderr)
        print(result.install_hint, file=sys.stderr)
        return 2

    # status == "failed"
    print(
        f"✗ Compile failed ({result.compiler}, {result.passes} "
        f"pass{'es' if result.passes != 1 else ''}).",
        file=sys.stderr,
    )
    if result.error_excerpt:
        print(file=sys.stderr)
        print("  Most-relevant log lines:", file=sys.stderr)
        for line in result.error_excerpt:
            print(f"    {line}", file=sys.stderr)
    if result.full_log_path:
        print(file=sys.stderr)
        print(f"  Full log: {result.full_log_path}", file=sys.stderr)
    print(file=sys.stderr)
    print(_hint_for_failure(result), file=sys.stderr)
    return 1


# -- Hint routing (Sprint-7-c6) -------------------------------------------
#
# Pre-c6 the CLI printed a single static "unescaped chars" hint regardless
# of failure kind, which was wrong about 75% of the time. c6 added
# `failure_kind` classification on `CompileResult`; this function picks
# the matching recovery hint per kind. Always end with the Overleaf
# fallback so users with a stuck local TeX always have an out.


_OVERLEAF_FALLBACK = (
    "  If the error is unclear or you can't fix it locally, paste the .tex\n"
    "  into Overleaf (https://overleaf.com) — it has a more forgiving\n"
    "  error UI and the bundled CV template is fully Overleaf-compatible."
)


def _hint_for_failure(result: "object") -> str:  # noqa: UP037 — forward ref OK
    """Return the recovery hint for a failed-compile result.

    Branches on ``result.failure_kind`` (set by
    :func:`phd_matcher.cv.compile.classify_failure`); falls back to a
    generic catch-all when classification produced ``unknown``.
    """
    kind = getattr(result, "failure_kind", None)
    missing = getattr(result, "missing_packages", []) or []

    if kind == "missing_package":
        pkg_args = " ".join(missing) if missing else "<package>"
        body = (
            "  Hint: a required TeX package is missing. Install it with:\n"
            f"    tlmgr install {pkg_args}\n"
            "  (or `sudo apt install texlive-latex-extra` on Debian/Ubuntu).\n"
            "\n"
            "  If `tlmgr install` rejects with a TeX-Live-version mismatch\n"
            "  (e.g. local 2025 vs remote 2026), point tlmgr at the\n"
            "  historic mirror first:\n"
            "    tlmgr option repository \\\n"
            "      https://ftp.math.utah.edu/pub/tex/historic/systems/texlive/<YEAR>/tlnet-final\n"
            "  then re-run the install."
        )
        return body + "\n\n" + _OVERLEAF_FALLBACK

    if kind == "structure":
        body = (
            "  Hint: itemize / list-environment structure error. Common causes:\n"
            "    - Bare text or \\vspace before the first \\item in an itemize\n"
            "    - Two nested \\begin{itemize} without an \\item between them\n"
            "    - Tabular / non-list content in an itemize without a leading\n"
            "      \\item (e.g. add `\\item[]` before `\\noindent ... \\begin{tabular}`)\n"
            "  If you edited the bundled template, check the section around\n"
            "  the line number reported above against the as-shipped version:\n"
            "    phdtaketaketake-cv-template --print | diff - your-cv.tex"
        )
        return body + "\n\n" + _OVERLEAF_FALLBACK

    if kind == "undefined_command":
        body = (
            "  Hint: a LaTeX command in the document is not defined. Causes:\n"
            "    - Typo in a command name (e.g. \\notarealcmd)\n"
            "    - Package providing the command was not loaded — check the\n"
            "      \\usepackage list in the preamble"
        )
        return body + "\n\n" + _OVERLEAF_FALLBACK

    if kind == "unescaped_chars":
        body = (
            "  Hint: most CV compile failures are unescaped LaTeX special\n"
            "  characters in user-supplied text (&, %, _, #, $, {, }). Each\n"
            "  needs a backslash, e.g. \\& \\% \\_ \\# \\$."
        )
        return body + "\n\n" + _OVERLEAF_FALLBACK

    # kind == "unknown" or None
    body = (
        "  Hint: the failure pattern doesn't match a common case. Read the\n"
        "  diagnostic lines above carefully — the line number (l.<N>) and\n"
        "  any `! LaTeX Error:` text usually point at the offending line\n"
        "  in your .tex."
    )
    return body + "\n\n" + _OVERLEAF_FALLBACK


if __name__ == "__main__":
    raise SystemExit(main())
