# Example Claude Code session

A walk-through of what an end-to-end conversation with the skill looks like.
The user volunteers minimal information; the skill follows the
**ask-when-missing** workflow defined in `SKILL.md`, builds a profile JSON,
runs the matcher, and presents results conversationally.

This isn't a recorded transcript — it's a hand-written illustration of the
intended flow. Real Claude responses will vary in phrasing.

---

## Turn 1 — User opens with minimal info

> **You**:
> 我是清华物理本科，想申美国 PhD，做 ATLAS Higgs 分析。

The skill triggers from "PhD" + "Physics" + research-direction context.

> **Claude** *(skill activated)*:
> Got it — for matching to be useful I need a few more things. Three quick questions:
>
> 1. **GPA** — what's your GPA, and on what scale? (4.0 / 4.3 / 100-point / …)
> 2. **Current research advisor** — name + institution (this drives the
>    Connection score, which is the main IP of this matcher).
> 3. **Publications** — any papers? If yes, list each as: journal name + your author position. ATLAS papers usually mean position 100+, that's fine.
>
> Once I have these I'll rank advisors at top US programs.

## Turn 2 — User fills in

> **You**:
> GPA 3.85/4.0, 现导师是清华王老师 (Prof. Lisa Wang)，发了 1 篇 PRL 第 456 作者 (ATLAS Higgs charm coupling) 和 1 篇 PRD 第 312 作者 (ATLAS dijet search)。课题组待了 18 个月，写了 honors thesis。

> **Claude**:
> Perfect — that's enough. Building the profile and running the match…

*(Claude constructs the profile JSON internally, then runs:)*

```bash
python scripts/match.py --profile-json '<JSON>' --field physics --top-k 10
```

## Turn 3 — Claude presents ranked candidates

> **Claude**:
> Top 10 matches for physics PhDs at US programs:
>
> ```
> #1  Prof. James Anderson — MIT                                   [Match]
>     Match: 3.66 / 4.0 · Admit: 3.26 / 4.0 (±0.3)
>     C: 4.00  P: 3.30  E: 3.25  G: 3.85
>     co-authored 4 paper(s) with Prof. Lisa Wang in last 5 years ·
>     shared collaboration membership for ~8 years (ATLAS) ·
>     research: HEP / ATLAS / BSM / Higgs · collaborates with NAS
>
> #2  Prof. David Kumar — UC Berkeley                              [Match]
>     Match: 3.66 / 4.0 · Admit: 3.26 / 4.0 (±0.3)
>     C: 4.00  P: 3.30  E: 3.25  G: 3.85
>     co-authored 2 papers with Prof. Lisa Wang ·
>     two-hop genealogy connection · ATLAS overlap ~6 yrs ·
>     research: experimental HEP / ATLAS / dark matter
>
> #3  Prof. Robert Lee — Univ. of Michigan                         [Match]
>     Match: 3.53 / 4.0 · Admit: 3.33 / 4.0 (±0.3)
>     C: 3.70  P: 3.30  E: 3.25  G: 3.85
>     co-authored 3 papers with Prof. Lisa Wang · ATLAS overlap 7 yrs
>
> #4  Prof. Maria Chen — Stanford                                  [Match]
>     Match: 3.36 / 4.0 · Admit: 3.16 / 4.0 (±0.5)
>     C: 3.30  P: 3.30  E: 3.25  G: 3.85
>     no direct path to your advisor; field-strength only ·
>     research: theoretical particle physics, Higgs, EFT ·
>     PI is recruiting strong (≥2 PhDs/yr)
>
> ... (6 more)
> ```
>
> Estimates use public academic-network signals only — does not include
> SOP / recommendation letters / interviews.
>
> Want to drill into any specific candidate? See more? Try a different
> field?

## Turn 4 — User asks for detail

> **You**:
> #1 (James Anderson MIT) 详细说说，他怎么和我导师合作的？

> **Claude** *(reads `data/advisors/mock_advisors.json` for the candidate, or
> consults its own knowledge for the real cache):*
>
> Prof. James Anderson at MIT works on:
> - High energy physics (ATLAS detector)
> - BSM searches
> - Higgs measurements
>
> His connection to Prof. Lisa Wang (your advisor):
> - **Co-authored 4 papers in the last 5 years** — most likely all ATLAS
>   collaboration papers given the field overlap
> - Both have been ATLAS members for 8+ years
> - The Connection score caps at 4.0 because direct co-authorship at this
>   density is the strongest signal type
>
> Why this matters for admission: a recommendation letter from Lisa Wang to
> James Anderson is a *known recommender*, not a cold one. Anderson will
> have read Wang's papers, may have collaborated on analyses, and trusts
> the calibration of her assessment. That's the connection-first thesis
> the entire scoring system embodies.
>
> Caveats:
> - This advisor cache currently uses **synthetic mock data** for
>   demonstration. The real OpenAlex-backed cache (now built into
>   `data/advisors/physics_cache.json`) ships with empty
>   `paths_to_advisors` — those edges need to be computed at query time
>   based on your actual advisor's co-authorship graph.
> - The 5+ author rule means your ATLAS papers (positions 312 and 456)
>   each scored 3.5 (the big-collab credit floor), then aggregated to
>   P = 3.5 × 0.7 + 3.5 × 0.3 = 3.5 (top 2 papers, both at the floor).

## Notes on the flow

1. The skill asked for **3 specific things** in turn 1 — not a generic
   "tell me everything about you" prompt.
2. Once enough info was given, it built the profile **without asking
   confirmation** for unambiguous fields (GPA, papers) but would have asked
   for confirmation if it had to make judgment calls (e.g., uncertain
   `journal_tier` or `lab_tier`).
3. The result presentation was conversational, not a JSON dump.
4. The user could naturally drill in by name; the skill responded with
   contextual interpretation, not just data lookup.

For an uncovered field (e.g., chemistry), turn 2 would also include:

> *(Claude internally generates ~15 candidate chemistry advisors at top US
> chem programs matching the user's research direction, then passes them
> via `--candidates-json`.)*

And turn 3 would surface the caveat:

> The candidates above were generated from my general knowledge of
> chemistry, not a verified cache — treat the absolute scores as rough,
> the relative ranking is more reliable. To upgrade, see CONTRIBUTING.md
> for adding a verified chemistry advisor cache.
