# CV optimization reference

The phdtaketaketake CV sub-skill (Sprint-7) renders a LaTeX-formatted
PhD-application CV from agent-collected user info, with optional
tailoring for a target advisor list (typically from a prior
`match.json` run).

This document is the agent's structural reference: template layout,
edit conventions, what to keep vs delete, and the tailoring playbook.
SKILL.md §"CV optimization (parallel workflow)" is the user-flow
contract; this file is the per-section detail.

## Module layout

```
phd_matcher/cv/
  __init__.py                # exports TEMPLATE_PATH
  templates/
    default.tex              # the bundled template
  cli/
    template.py              # phdtaketaketake-cv-template
    compile.py               # phdtaketaketake-cv-compile (Sprint-7-c2)
```

The template path is also importable:

```python
from phd_matcher.cv import TEMPLATE_PATH
text = TEMPLATE_PATH.read_text(encoding="utf-8")
```

## Template structure

The bundled template has these top-level blocks, in fixed order:

| # | Block | Required | Notes |
|---|---|---|---|
| 1 | Preamble | yes | `\documentclass`, `\usepackage`, layout tweaks, custom resume commands. **Never edit.** Marked with a `% DO NOT EDIT` guard. |
| 2 | Header (name + emails + website) | yes | Wraps an optional multi-affiliation extra-emails block. |
| 3 | `\section{Education}` | yes | At least 1 institution. Wraps an optional Relevant Coursework table. |
| 4 | `\section{Research Experience}` | yes | N entries via `\resumeSubheading{...}` + bullets. |
| 5 | `\section{Publications & Presentations}` | conditional | 3 sub-categories: SELECTED PAPERS / WORK IN PROGRESS / POSTERS & TALKS. Delete sub-categories you don't have; delete the whole section if none apply. |
| 6 | `\section{Technical Skills}` | yes | Typically 3 categorized lines. |
| 7 | `\section{Teaching Experience}` | optional | Delete if N/A. |
| 8 | `\section{Leadership Experience}` | optional | Delete if N/A. |
| 9 | `\section{Honors and Awards}` | optional | Delete if N/A; keep if you have any. |

Sections that should **never** be deleted (always relevant for a PhD
application): Education, Research Experience, Technical Skills.

## Placeholder convention

The template uses **angle-bracketed placeholders**: `<Your Full Name>`,
`<primary@example.edu>`, `<Research Project Title>`, etc. These are
LaTeX-safe (`<` and `>` are ordinary characters in text mode) and
visually distinct, so the agent can find/replace them by string match.

The as-shipped template **compiles to a placeholder demo CV** — every
`<placeholder>` renders as its angle-bracketed text. Running the
compile pipeline immediately after fetching the template:

```bash
phdtaketaketake-cv-template --print > cv.tex
phdtaketaketake-cv-compile cv.tex
```

…produces a valid 1-page PDF with placeholder content, confirming the
LaTeX install + custom commands + structure all work end-to-end before
the user spends time personalizing.

## OPTIONAL_BLOCK convention

Field-conditional content (Coursework table is useful for physics /
theory CS, less so for wet-lab bio) is wrapped:

```
% --- OPTIONAL_BLOCK_START: <name> ---
% <description of when to enable>
%
% <every line of the optional block prefixed with `% `>
% --- OPTIONAL_BLOCK_END: <name> ---
```

To enable, remove the `% ` prefix from each content line between
START and END. **Keep the START / END marker comments themselves**
so future edits know it's an optional block (recoverable).

Currently shipped optional blocks:

| Name | Default | Enable when |
|---|---|---|
| `Relevant Coursework` | off | Physics / applied math / theory CS PhDs (programs that explicitly weigh coursework) |
| `Multi-affiliation extra emails` | off | User has REU host / summer-program / dual-affiliated lab emails alongside their primary |

## Section-deletion convention

If an entire section doesn't apply to the user (no teaching experience,
no leadership roles), **delete the entire block** including:

1. The `\section{...}` line
2. The `\resumeSubHeadingListStart` / `End` wrapper
3. All `\resumeSubheading{...}` + `\resumeItemListStart` / `End`
   sub-blocks
4. Any `\vspace{...}` immediately above and the trailing comment if
   present (e.g. `% Delete the entire Teaching Experience section ...`)

Empty section headers (a `\section{}` followed by nothing) look worse
than a missing section. Don't leave them.

## Tailoring playbook (when match.json is available)

**Tailoring is reordering and pruning. It is never invention.**

### Step T-1: Identify target PIs

From `match.json`, take candidates ranked in `priority_candidates` +
`target_candidates` (the top two strategy buckets). For each, read:

- `candidate.research_areas` — list of subfield strings
- `c_score` + active path edges (which connection edges are non-empty)
- `research_fit_axes` if computed

These three fields tell you what overlaps to surface in the CV.

### Step T-2: Reorder Research Experience

For each of the user's experiences, judge overlap with the *union* of
target PIs' `research_areas`:

| Overlap level | Action |
|---|---|
| **Strong** — project topic / system explicitly appears in target PI's `research_areas` | Move to top of section |
| **Moderate** — shared methods / instrument / dataset / framework | Keep in middle |
| **Weak / none, ≤ 2 years old** | Keep at bottom |
| **Weak / none, > 2 years old** | Consider deleting; **ask the user first** with a one-line note explaining the choice |

Heuristic for "shared methods" (physics example): both use Geant4 →
moderate; both use MadGraph5 + Pythia8 → moderate; both work on Higgs
precision but with different detectors → moderate; one is detector
ML and the other is theory EFT → weak.

### Step T-3: Reorder bullets within each kept experience

Within an experience block, lead with the bullet whose methods or
findings overlap the target. Example mappings:

- Target uses Geant4 → bullet about Geant4 simulation goes first
- Target works on Higgs / W / Z precision → bullet about that channel first
- Target focuses on SUSY / DM / BSM → bullet about BSM physics first
- Target is detector hardware → bullet about detector design / calibration first
- Target is heavy ML user → bullet about CATHODE / classifier / training pipeline first

### Step T-4: Reorder Publications

Same treatment as Research Experience. Lead with the paper whose
**author list, venue, or subject** most overlaps the target's recent
work.

Don't reformat the citation. Don't reorder authors within a citation.
Don't change paper status (`In Preparation` stays `In Preparation`).

### Step T-5: Reorder Technical Skills

Within each `\textbf{Category}: <list>` line, reorder the comma-separated
list to put target-relevant tools first. Example:

```latex
% Generic order:
\textbf{Physics Software}: MadGraph5, Pythia8, Delphes, Geant4
% After tailoring for a Geant4-heavy LDMX-style target:
\textbf{Physics Software}: Geant4, MadGraph5, Pythia8, Delphes
```

The list contents stay the same — only the order changes.

### Step T-6: Tell the user what changed

After tailoring, surface a 2–3 line summary of the moves you made:

> Tailored for **Prof. Hartman (MIT, ATLAS Higgs / detector ML)**:
>
> - Moved the time-dependent DM project (Whiteson) to top of Research
>   Experience — strongest LHC + ML overlap with Hartman's recent papers.
> - Moved the Caltech SURF Geant4 work above the FCC-ee work in
>   POSTERS & TALKS — more on-topic for Hartman's detector-ML angle.
> - Reordered Technical Skills "Physics Software" line to lead with
>   Geant4.

The user can push back on any of these. **Tailoring is a starting
point, not the final answer.**

## What this skill does NOT do

- ❌ **Write or revise SoPs / personal statements / cover letters.** Frozen scope (DESIGN.md §13).
- ❌ **Invent experiences, skills, papers, or awards.** Every line in the output must trace to user-provided info or template structure.
- ❌ **Contact PIs on the user's behalf.** The skill produces documents; it does not send messages.
- ❌ **Optimize for ATS / industry resumes.** The template is academic / PhD-application style. Industry CV is a different genre with different conventions.
- ❌ **Assess content quality.** Whether an experiment is "good" or a paper is "important" is the user's (and their letter-writers') judgment, not the skill's.

## Compile failure recovery

When the LaTeX compile fails (Sprint-7-c2 handles this), the agent
should **not** try to "fix" the LaTeX by guessing. Instead:

1. Surface the relevant error lines (`! LaTeX Error:`, `l.<num>`)
2. Identify the most likely cause (most common: an unescaped special
   char in user-supplied text — `&`, `%`, `_`, `#`, `$`)
3. Offer the user two recovery options:
   - Paste the offending line back, the agent escapes it, and re-run
   - Hand the user the raw `cv.tex` for [Overleaf](https://www.overleaf.com/) — Overleaf has a more forgiving error UI

If TeX is not installed at all, the compile CLI prints an install
hint and the agent should suggest:

- macOS: `brew install --cask mactex` (or `mactex-no-gui` for a smaller install)
- Linux: `sudo apt install texlive-latex-extra` (Debian/Ubuntu)
- Windows: TeX Live or MiKTeX

…or, fallback path: Overleaf with the raw `.tex`.

## Boundaries with advisor matching

CV optimization is a **parallel workflow** to advisor matching, not a
sub-step. The two share install + repo, but trigger independently:

- "find me advisors" → matching workflow (Steps 1–8.5)
- "make me a CV" → CV workflow (Steps CV-1–CV-6)
- "make me a CV tailored for the matches you found" → matching first, then CV with `match.json` as input

The connection between the two is one-way: CV optimization can *consume*
a `match.json` for tailoring, but matching never depends on the CV.
