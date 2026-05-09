"""CLI: ``phdtaketaketake-cv-template``.

Default behaviour: print the absolute path of the bundled CV template
(useful when you want to ``Read`` / ``Edit`` it via tooling that takes
a path).

With ``--print``: print the template contents to stdout. Useful as the
first step of the agent's CV workflow:

    phdtaketaketake-cv-template --print > cv.tex

The template is a LaTeX file that compiles as-is to a placeholder
"demo CV" — agents and users can verify the LaTeX install + template
integrity before personalizing.
"""

from __future__ import annotations

import argparse
import sys

from phd_matcher.cv import TEMPLATE_PATH


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="phdtaketaketake-cv-template",
        description=(
            "Print the path (default) or contents (--print) of the bundled "
            "CV LaTeX template. Pipe the contents to a fresh file to start a "
            "new CV: `phdtaketaketake-cv-template --print > cv.tex`. "
            "The template compiles to a placeholder demo CV as-shipped, so "
            "you can verify your LaTeX install before personalizing."
        ),
    )
    ap.add_argument(
        "--print",
        dest="print_contents",
        action="store_true",
        help="Print the template contents to stdout instead of the path.",
    )
    return ap


def main() -> int:
    args = build_parser().parse_args()
    if args.print_contents:
        sys.stdout.write(TEMPLATE_PATH.read_text(encoding="utf-8"))
    else:
        print(TEMPLATE_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
