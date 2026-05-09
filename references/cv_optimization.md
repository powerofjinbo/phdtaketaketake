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
  compile.py                 # core compile pipeline (compile_cv → CompileResult)
  cli/
    template.py              # phdtaketaketake-cv-template
    compile.py               # phdtaketaketake-cv-compile
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

## Worked example — end-to-end tailoring

Concrete walkthrough using the bundled `examples/physics_hep_audit_demo`
data. The "user" is the demo's profile (Tsinghua undergrad, ATLAS
Higgs precision focus, 18 months in Prof. Wang's lab, two ATLAS
big-collab papers). They've already run the matching pipeline; the
result is `examples/physics_hep_audit_demo/match.json`.

### Step T-0: Read the match output

The top three from `match.json` (excerpted):

| Rank | Name | Institution | Strategy | research_areas | outreach_angle |
|------|------|-------------|----------|----------------|----------------|
| 1 | Prof. Alex Hartman | MIT | **target / contact_first** | Higgs boson, ATLAS, particle physics, collider physics | "Lead with the shared small-team coauthorship with adv_001 (3 papers) as the connection." |
| 2 | Prof. Riley Chen | UC Berkeley | reach / investigate_evidence | ATLAS, particle physics, dark matter, BSM searches | (none — investigate first) |
| 3 | Prof. Casey Lin | Stanford | only_if_space / investigate_evidence | effective field theory, Standard Model, theoretical particle physics | (none) |

Only `target_candidates` get a `contact_first` outreach angle, so we
**tailor for Hartman first** — that's the highest-confidence apply.
For the others, generic CV is fine until the user gathers more
evidence.

### Step T-1: Pull the target's signal vector

Hartman's relevant fields:

- `research_areas`: Higgs boson, ATLAS, particle physics, collider physics
- `c_score`: 3.7 (top of the field — driven by 3 small-team coauthored papers with the user's advisor Prof. Wang)
- `outreach_angle`: lead with the small-team coauthorship

So the CV should:

1. Surface the **ATLAS Higgs** content first (topic match)
2. Surface the **Prof. Wang collaboration** indirectly via the same papers (the connection narrative gets reinforced by the small-team coauthorship being prominent)
3. Keep but de-emphasize work outside the topic (BSM, dark matter, theory) since this user happens to also have a BSM-flavoured time-dependent-DM project — useful breadth, but not the lead

### Step T-2: Reorder Research Experience

Suppose the user's CV (post-Step CV-3 fill) has these research
experiences in the order they wrote them in:

1. ✅ ATLAS H→cc̄ analysis with Prof. Wang at Tsinghua (18 months)
2. ⚠ Time-dependent BSM signatures with Prof. Whiteson at UCI (CATHODE method)
3. ⚠ Photometric high-z galaxy survey with Prof. Cooray at UCI
4. ⚠ Nanophotonic ENZ materials with Prof. Lee at UCI

**Tailoring decisions:**

- **#1 stays #1.** Strong overlap (ATLAS Higgs is the literal topic of Hartman's research areas). This is the user's anchor experience and Hartman's outreach_angle explicitly references the connection through Wang.
- **#2 moves to #2.** Moderate overlap (LHC + ML on dark matter — the LHC + ML half overlaps "particle physics, collider physics" + the detector-ML angle Hartman cares about; the dark matter half is closer to Chen than Hartman, but the methodology is shared).
- **#3 stays in middle / moves down.** Weak overlap (astrophysics — not collider, not particle physics). Could justify keeping for breadth narrative ("computational physics across scales") but should not be earlier than the on-topic items.
- **#4 stays last.** Almost no overlap with Hartman (nanophotonic materials is a different field). Don't delete though — > 2 years old and it's a real published paper, so keep at the bottom for completeness.

In LaTeX terms: this is just reordering the four `\resumeSubheading{...}{...}{...}{}` + `\resumeItemListStart` / `End` blocks. No content edits.

### Step T-3: Reorder bullets within the lead experience

Within the ATLAS H→cc̄ experience, the user might have written bullets
in chronological order. Hartman cares about detector ML — so the
detector-ML / classifier bullet should lead, not "implemented
preselection cuts" (which is generic ATLAS work).

Original order:

1. Implemented preselection cuts and event filtering on H→cc̄ candidates
2. Built a CNN-based jet-flavour tagger improving signal efficiency by 12%
3. Co-author on PRD precision measurement paper (alphabetical author list)

Tailored order:

1. **Built a CNN-based jet-flavour tagger improving signal efficiency by 12%** ← detector-ML, target topic
2. Implemented preselection cuts and event filtering on H→cc̄ candidates
3. Co-author on PRD precision measurement paper

Same content, different lead. The first bullet now matches Hartman's
`research_areas` ∩ "detector ML" sweet spot.

### Step T-4: Reorder Publications

Same logic. Suppose user's Selected Papers has:

- ATLAS Collaboration. ``Measurement of H→cc̄ ...'' Phys. Rev. D (2024).
- ATLAS Collaboration. ``Search for BSM dark matter ...'' JHEP (2023).

Hartman's areas favour the first; reorder accordingly. Within Work in
Progress, lead with anything mentioning `H→cc̄` / `Higgs precision` /
`detector ML`. **Do not change** the citations themselves, the author
order, or the paper status.

### Step T-5: Reorder Technical Skills

Suppose the original "Physics Software" line is:

```latex
\textbf{Physics Software}: MadGraph5, Pythia8, Delphes, Geant4, FastJet
```

Hartman's group works heavily with the ATLAS detector simulation +
analysis stack. Reorder to put detector-relevant tools first:

```latex
\textbf{Physics Software}: Geant4, FastJet, Delphes, MadGraph5, Pythia8
```

Same six items, different order. The first three are the ones an ATLAS
detector / Higgs analysis person scans for.

### Step T-6: Surface what changed to the user

Before saving the tailored `cv.tex`, tell the user what you did. The
canonical form (from SKILL.md Step CV-6):

> Tailored for **Prof. Alex Hartman (MIT, ATLAS Higgs / detector ML)**:
>
> - Kept the ATLAS H→cc̄ project at top of Research Experience —
>   strongest overlap with Hartman's research areas + reinforces the
>   connection through Prof. Wang noted in the matcher's
>   `outreach_angle`.
> - Moved the time-dependent BSM project (Whiteson) to #2 — shares
>   LHC + ML methodology even though the physics target differs.
> - Within the ATLAS experience, led with the CNN jet-flavour tagger
>   bullet (detector-ML angle Hartman emphasizes).
> - Reordered the "Physics Software" line to lead with Geant4, FastJet,
>   Delphes — the ATLAS analysis stack.
> - Did NOT change any paper citations, author orders, or content.
>   No experience was deleted (the photometric and nanophotonic projects
>   stay for breadth, just lower in the section).
>
> If you want to tailor a separate version for **Prof. Riley Chen
> (Berkeley, BSM / dark matter)**, the time-dependent DM project would
> swap to #1 and the ATLAS Higgs work to #2 — reach out and I'll
> generate it.

The user can push back on any of these. Tailoring is a starting point,
not the final answer.

### What did NOT change in this example

- ❌ Hartman's connection edges (the matcher's job, not the CV's)
- ❌ Any author lists, paper venues, or paper statuses
- ❌ GPA, dates, institution names
- ❌ Any factual content — the user's experiences are exactly as they
  reported them, just in a different order

This is the entire tailoring contract: **reorder, prune (with user
consent), surface the lead. Never invent.**

## What this skill does NOT do

- ❌ **Write or revise SoPs / personal statements / cover letters.** Frozen scope (DESIGN.md §13).
- ❌ **Invent experiences, skills, papers, or awards.** Every line in the output must trace to user-provided info or template structure.
- ❌ **Contact PIs on the user's behalf.** The skill produces documents; it does not send messages.
- ❌ **Optimize for ATS / industry resumes.** The template is academic / PhD-application style. Industry CV is a different genre with different conventions.
- ❌ **Assess content quality.** Whether an experiment is "good" or a paper is "important" is the user's (and their letter-writers') judgment, not the skill's.

## Compile failure recovery

The compile pipeline (``phd_matcher.cv.compile.compile_cv``) returns a
structured ``CompileResult`` with one of three statuses:

| status | What it means | Agent should |
|---|---|---|
| ``ok`` | PDF was produced. | Hand user the ``pdf_path``. |
| ``failed`` | TeX is installed but the ``.tex`` has an error. ``error_excerpt`` lists the actionable lines (``! LaTeX Error:``, ``l.<num>``, "Undefined control sequence", "Missing X inserted", "Runaway argument", "Emergency stop", missing-file lines). | Surface ``error_excerpt`` verbatim. **Never guess at LaTeX fixes.** Identify the most likely cause (usually an unescaped special char) and ask the user to paste the offending source line back. Offer Overleaf as a fallback for unclear errors. |
| ``tex_not_installed`` | Neither ``latexmk`` nor ``pdflatex`` was found on ``PATH``. ``install_hint`` is populated. | Surface ``install_hint`` (covers macOS / Debian / Fedora / Windows and the minimal-TeX gotcha — TinyTeX / BasicTeX users may need ``tlmgr install titlesec enumitem``). Always offer Overleaf as the universal fallback. |

The CLI ``phdtaketaketake-cv-compile`` maps these statuses to exit
codes 0 / 1 / 2; exit code 3 is reserved for input errors (file not
found etc.) and is raised as ``FileNotFoundError`` by the Python
function rather than returned in ``CompileResult``.

### Most common compile failures (and how to fix them)

| Symptom in error_excerpt | Likely cause | Agent fix |
|---|---|---|
| ``Undefined control sequence`` near user-supplied text | Unescaped LaTeX special char (``&``, ``%``, ``_``, ``#``, ``$``, ``{``, ``}``) | Re-escape per Step CV-3's table; re-run |
| ``File 'X.sty' not found`` | Minimal TeX install missing a package | Suggest ``tlmgr install <package>`` (macOS/TinyTeX) or ``apt install texlive-latex-extra`` (Debian) |
| ``Runaway argument`` | Missing closing brace ``}`` somewhere | Read the ``l.<num>`` line; user pasted text with mismatched braces |
| ``Missing $ inserted`` | Math-mode special char (``^``, ``_``, ``$``) outside math | Wrap in ``\$`` or ``$...$`` as appropriate |

## Boundaries with advisor matching

CV optimization is a **parallel workflow** to advisor matching, not a
sub-step. The two share install + repo, but trigger independently:

- "find me advisors" → matching workflow (Steps 1–8.5)
- "make me a CV" → CV workflow (Steps CV-1–CV-6)
- "make me a CV tailored for the matches you found" → matching first, then CV with `match.json` as input

The connection between the two is one-way: CV optimization can *consume*
a `match.json` for tailoring, but matching never depends on the CV.
