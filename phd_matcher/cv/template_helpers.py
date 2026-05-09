"""Helpers for working with the bundled CV LaTeX template.

Currently a single helper: :func:`uncomment_optional_blocks`, which
implements the ``OPTIONAL_BLOCK_START`` / ``OPTIONAL_BLOCK_END``
contract documented in ``references/cv_optimization.md``. The agent
edits the template by hand in normal use; this helper exists for
test code (Sprint-7-c6 added a CI test that uncomments every
optional block and compiles the result, so a future regression in
the optional-block markup gets caught).
"""

from __future__ import annotations

OPTIONAL_BLOCK_START_MARKER = "OPTIONAL_BLOCK_START:"
OPTIONAL_BLOCK_END_MARKER = "OPTIONAL_BLOCK_END:"


def uncomment_optional_blocks(text: str) -> str:
    """Return ``text`` with every line between ``OPTIONAL_BLOCK_START:`` and
    ``OPTIONAL_BLOCK_END:`` markers stripped of its leading ``% `` (or ``%``)
    comment prefix.

    The START / END marker lines themselves are preserved verbatim — they
    are LaTeX comments (``% --- OPTIONAL_BLOCK_START: ... ---``) so leaving
    them in place doesn't affect compilation, and leaving them in place
    keeps the structure recoverable for future edits.

    The optional-block contract (per ``references/cv_optimization.md``) is
    that descriptive prose explaining *when* to enable a block lives
    *outside* the START / END markers; the markers wrap only LaTeX code,
    each line prefixed with ``% `` (or ``%`` for blank-style separator
    lines). So uncommenting line-by-line yields valid LaTeX without
    leaking description text into the document body.
    """
    out: list[str] = []
    in_block = False
    for line in text.splitlines():
        if OPTIONAL_BLOCK_START_MARKER in line:
            in_block = True
            out.append(line)
        elif OPTIONAL_BLOCK_END_MARKER in line:
            in_block = False
            out.append(line)
        elif in_block:
            # Strip the leading "% " (with trailing space) when present;
            # otherwise strip a bare "%" (handles blank-comment separator
            # lines like "%" between paragraphs).
            if line.startswith("% "):
                out.append(line[2:])
            elif line.startswith("%"):
                out.append(line[1:])
            else:
                # Already uncommented (e.g. user already enabled this
                # block manually); pass through unchanged.
                out.append(line)
        else:
            out.append(line)
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")
