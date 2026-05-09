"""CV optimization sub-skill (Sprint-7).

Provides a LaTeX template + thin Python tooling for users to render
and compile a PhD-application CV. The template ships with placeholder
content so the as-shipped file compiles to a "demo CV" — confirming
the pipeline works end-to-end before personalization.

Architecture: agent-led, Python-thin. The Python here only:

1. Exposes the bundled template path (so the agent can read it via
   ``phdtaketaketake-cv-template``).
2. Compiles a filled ``.tex`` to PDF (``phdtaketaketake-cv-compile``,
   added in Sprint-7-c2).

Filling the template, tailoring it to a target PI list, and any
content judgement is the agent's job. See SKILL.md
§"CV optimization workflow" for the agent contract and
``references/cv_optimization.md`` for the per-section editing rules
and tailoring playbook.
"""

from pathlib import Path

TEMPLATE_PATH: Path = Path(__file__).parent / "templates" / "default.tex"

__all__ = ["TEMPLATE_PATH"]
