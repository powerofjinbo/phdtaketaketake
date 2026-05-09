# phdtaketaketake — agent instructions

This file is the entry point that OpenAI Codex (and other agents that
discover persistent instructions via `AGENTS.md` per the Codex
convention) uses to find this skill. **It is intentionally a short
pointer, not a copy of `SKILL.md`.** Maintaining two copies of the
skill contract creates drift; the canonical contract lives in
[`SKILL.md`](SKILL.md), and Cursor / Codex / any future host reads
that file or gets a generated short-pointer like this one.

## Use

When the user asks about PhD advisor matching, application triage,
PI ranking, connection-first evaluation, evidence-backed application
strategy, or PhD-application CV optimization, follow the workflow
defined in **[`SKILL.md`](SKILL.md)**:

- **Workflow A** (advisor matching): Steps 1–8.5 — gather profile,
  generate discovery plan, find candidates, compute connection edges,
  score with the 5-layer pipeline (CAPEG → application_strength →
  risk_adjusted → difficulty_adjusted → strategy bucket), present
  cards.
- **Workflow B** (CV optimization): Steps CV-1–CV-6 — read the
  bundled LaTeX template, fill from user-typed input, optionally
  reorder for a target PI from `match.json`, compile.

## Hard rules (non-negotiable for both workflows)

1. **Connection-first** — `w_C > w_A` in every tier. Verified academic
   network beats h-index.
2. **Evidence-first** — every claim traces to a real source the agent
   actually fetched. Four-state semantics: Verified / Verified-empty
   / Missing / Blocked. Strict mode rejects unsourced claims.
3. **No invention** — never fabricate candidate facts, advisor
   connections, publication records, GPA conversions, opportunity
   signals, CV experiences, papers, or skills.
4. **CV source-of-truth** — every fact in the rendered `cv.tex` traces
   to something the user explicitly provided in conversation. Target
   PIs from `match.json` drive ordering decisions; their names never
   appear in the CV body.
5. **Output is a relative-fit index, not an admission probability.**
   Surface what's strong, what's weak, what's uncertain — never claim
   a numeric admit chance.

The full data-integrity contract, scoring formulas, source-of-truth
allowed/forbidden table, blocked-source four-state policy, and
per-section CV editing conventions are all in [`SKILL.md`](SKILL.md)
and [`references/`](references/). Read those before acting.

## Installed CLIs (after `pip install -e .`)

```
phdtaketaketake-discovery-plan      # per-field PI search recipe
phdtaketaketake-collect-evidence    # auto-fill via OpenAlex / PubMed / DBLP / SS
phdtaketaketake-audit               # evidence repair queue
phdtaketaketake-match               # rank candidates
phdtaketaketake-export-schemas      # Pydantic → JSON Schema
phdtaketaketake-cv-template         # bundled LaTeX template (path or contents)
phdtaketaketake-cv-compile          # latexmk / pdflatex compile pipeline
```
