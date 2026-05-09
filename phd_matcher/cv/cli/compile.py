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
    print(
        "  Hint: most CV compile failures are unescaped LaTeX special\n"
        "  characters in user-supplied text (&, %, _, #, $, {, }). Each\n"
        "  needs a backslash, e.g. \\& \\% \\_ \\# \\$.\n"
        "  If the error is unclear, paste the .tex into Overleaf\n"
        "  (https://overleaf.com) — it has a more forgiving error UI.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
