# Example Claude Code session

Walk-through of a Claude Code conversation with the skill, illustrating the
**evidence-first deep-research workflow**. The user volunteers minimal info;
the agent asks for missing required + recommended fields, fetches real
sources for every connection edge and signal, builds the `CandidateAdvisor`
JSON, runs `scripts/match.py`, and presents ranked results with **inline
source citations**.

This is hand-written to illustrate the intended flow — real agent responses
will vary in phrasing.

---

## Turn 1 — User opens with minimal info

> **You**:
> 我是清华物理本科，想申美国 PhD，做 ATLAS Higgs 分析。

> **Claude** *(skill activated)*:
> Got it — for a useful match I need a few more things. Three quick questions:
>
> 1. **GPA** — what's your GPA, and on what scale?
> 2. **Current research advisor** — name + institution (this drives the
>    Connection score, the main signal).
> 3. **Publications** — any papers? Each one as: journal name + your author
>    position + status (`published` / `accepted` / `submitted` / `preprint`
>    / `in_prep`).
>
> Also: which programs are you targeting? Specific schools? Top 10? Open?

## Turn 2 — User fills in

> **You**:
> GPA 3.85/4.0, 现导师清华王老师 Prof. Lisa Wang, 1 篇 PRL 第 456 作者
> (ATLAS H→cc̄ analysis, published 2024), 1 篇 PRD 第 312 作者 (ATLAS dijet,
> published 2024), 课题组 18 个月 honors thesis. 想申 top 10 美物理 PhD.

> **Claude**:
> Perfect. Let me build your profile and research candidates.

*(Claude internally:)*

```
Step 1 — Build StudentProfile
  field=physics, undergrad=Tsinghua, gpa_raw=3.85, gpa_scale="4.0"
  current_advisors=[{id: adv_001, name: Prof. Lisa Wang, institution: Tsinghua}]
  papers=[
    {tier: 1, position: 456, status: "published"},  # PRL — 5+ rule → 3.5
    {tier: 3, position: 312, status: "published"},  # PRD — 5+ rule → 2.85
  ]
  experiences=[{lab_tier: "strong_us_or_top_cn", duration_months: 18,
                output_type: "honors_thesis"}]

Step 2 — Target programs
  Need to verify the field-specific ranking source. Fetching:
    https://www.usnews.com/best-graduate-schools/top-science-schools/physics-rankings
  Top 10: MIT, Stanford, Harvard, Princeton, Caltech, Berkeley, Chicago,
  Cornell, Yale, Columbia. (Recording for school_tier evidence.)

Step 3 — Find candidate PIs
  For each program, search "<school> physics ATLAS Higgs faculty".
  Gather ~25 active HEP PIs in 2022–2024 with ATLAS / Higgs / BSM areas.

Step 4 — Compute connection edges per candidate
  For each candidate, check:
    - Google Scholar: "Lisa Wang" "Markus Klute" → list co-authored papers,
      bucket by author count (≤10 → small_team, >10 → big_collab)
    - INSPIRE-HEP: same query for HEP-specific verification
    - Math Genealogy Project: lookup advisor lineage for both
    - Lab page: working group / convener / current students
  Record EXACTLY what was found, with source URLs in PathEdge.sources.
  No edge claimed without a verifiable URL.

Step 5–6 — Field-strength signals + pi_signal
  For each candidate, fetch:
    - Google Scholar / OpenAlex profile → h_index → normalized_collab_top20pct
      (with the profile URL in evidence["normalized_collab_top20pct"].sources)
    - Recent co-author list → check NAS directory for any matches
    - Lab alumni page → grad_placement_quality
    - Lab "join" / "applying" page → pi_signal

Step 7 — Run matcher
  python scripts/match.py --profile-file /tmp/profile.json \
    --candidates-file /tmp/cands.json --field physics --top-k 10
```

## Turn 3 — Claude presents ranked candidates

> **Claude**:
>
> Top 5 matches at top-10 US physics PhD programs (sorted by **risk-adjusted
> strength** — well-sourced candidates outrank loosely-claimed peers):
>
> ```
> #1  Prof. Markus Klute — MIT                                   [Match]
>     Match: 3.71 / 4.0 · Strength: 2.91 / 4.0 (±0.2)
>     C: 4.00  P: 3.20  E: 3.25  G: 3.85
>     unverified_signals: 0
>     • co-authored 6 small-team paper(s) with Prof. Wang in 2020–2024
>       [https://scholar.google.com/citations?user=...]
>     • shared 41 big-collab paper(s) with Prof. Wang (alphabetical author list)
>       [https://inspirehep.net/authors/...]
>     • same working group / convener overlap with Prof. Wang
>       [https://atlas-glance.cern.ch/atlas/analysis/H_to_cc/conveners]
>     • research: HEP / ATLAS / Higgs precision
>     • collaborates with NAS / HHMI member(s)
>       [https://www.nasonline.org/member-directory/...]
>
> #2  Prof. David Kumar — UC Berkeley                            [Target]
>     Match: 3.66 / 4.0 · Strength: 2.66 / 4.0 (±0.4)
>     C: 4.00  P: 3.20  E: 3.25  G: 3.85
>     unverified_signals: 2
>     • co-authored 2 small-team paper(s) with Prof. Wang in 2022–2024
>       [https://scholar.google.com/citations?user=...]
>     • shared 8 big-collab paper(s) with Prof. Wang (alphabetical author list)
>       [https://inspirehep.net/authors/...]
>     • two-hop genealogy connection with Prof. Wang
>       [https://www.genealogy.math.ndsu.nodak.edu/...]
>     • research: experimental HEP / ATLAS / dark matter
>     ⚠️ pi_signal not verified (lab page didn't load); collab_with_nas not checked
>
> #3  Prof. Robert Lee — Univ. of Michigan                       [Match]
>     Match: 3.53 / 4.0 · Strength: 3.03 / 4.0 (±0.4)
>     C: 3.70  P: 3.20  E: 3.25  G: 3.85
>     unverified_signals: 1
>     • co-authored 3 small-team paper(s) with Prof. Wang
>       [https://scholar.google.com/citations?user=...]
>     • shared 18 big-collab paper(s) (alphabetical author list)
>     ⚠️ school_tier (top_11_30) cited from US News 2024 PhD ranking, but
>       this is mid-cycle and could shift
>
> #4  Prof. Maria Chen — Stanford                                [Reach]
>     Match: 3.07 / 4.0 · Strength: 1.87 / 4.0 (±0.6)
>     C: 2.30  P: 3.20  E: 3.25  G: 3.85
>     unverified_signals: 4
>     • no direct path to Prof. Wang found
>       [searched OpenAlex + Math Genealogy: 0 results]
>     • theoretical particle physics PI (EFT, not detector physics)
>     ⚠️ confidence is low: I couldn't verify h_index, NAS membership,
>       grad placement, or recruiting status for this PI
>
> #5  Prof. Jiajun Wu — Princeton                                [Far Reach]
>     Match: 2.40 / 4.0 · Strength: 0.80 / 4.0 (±0.8)
>     C: 2.30  P: 3.20  E: 3.25  G: 3.85
>     unverified_signals: 5
>     ⚠️ I tried to search but neither Prof. Wu's lab page nor scholar
>       profile loaded; almost no signals are verified. Treat this rank
>       as approximate.
> ```
>
> Estimates use only public academic-network signals I gathered via web
> search. Does not include SOP / recommendation letters / interviews. Real
> admission decisions depend on factors beyond what this tool models.
>
> Want to drill into any specific candidate? Try a different field (MSE)?
> Adjust profile (add a paper status, fix a tier mapping)?

## Turn 4 — User asks for detail

> **You**:
> #1 Klute 详细说说，他怎么和我导师合作的？

> **Claude**:
> Prof. Markus Klute (MIT) — based on what I fetched:
>
> **Co-authorship** (Google Scholar 2020–2024):
> - 6 papers with **≤10 authors** including both Klute and Wang as authors.
>   Examples (Scholar URLs in cards above):
>   - Phys. Rev. Lett. 130 (2023), H → cc̄ — *small team analysis paper*
>   - JHEP 06 (2022), Higgs differential cross-sections — small team
>   - 4 more in PRD / EPJC / NIM with author counts 5–9
> - 41 papers with **>10 authors** (ATLAS bulk publications). These count
>   as `big_collab_papers_5y` — much weaker signal because alphabetical
>   author listing doesn't imply working relationship.
>
> **Working group** (ATLAS Glance, conveners page):
> - Both listed as co-conveners of the H→cc̄ subgroup, 2021–2023. This
>   is the strongest big-collab evidence — they ran an analysis together,
>   not just shared a paper byline.
>
> **Genealogy** (Math Genealogy):
> - Different lineages. No `genealogy_relation` recorded.
>
> **Why this matters for admission**: Klute knows Wang's work directly
> (analysis-level overlap, not just collaboration co-membership). A
> recommendation letter from Wang to Klute is *known recommender, calibrated
> opinion*. That's the connection-first thesis the score reflects.
>
> **Sub-scores explained**:
> - C = 4.00 — small_team_coauthor (6 → strength 1.0) + same_working_group
>   (0.7) → max = 1.0; field strength 0.4·0.85 + 0.3·1 + 0.3·0.8 = 0.88 →
>   c_raw = 0.6·1.0 + 0.4·0.88 = 0.952 → bucket 4.0
> - P = 3.20 — your two ATLAS papers, both 5+ author rule:
>   PRL pos 456 → min(3.5, 3.55) = 3.5; PRD pos 312 → min(3.5, 2.85) = 2.85.
>   Status = published, full weight. Aggregate (2 papers): 0.7·3.5 + 0.3·2.85 = 3.345 → rounded 3.20… (note: I owe you the actual computation here)
> - match = 0.45·4.0 + 0.30·3.20 + 0.15·3.25 + 0.10·3.85 = 3.71
> - strength = 3.71 + (top_10 = −1.0) + (pi_signal=normal = 0.0) = 2.71
>   (rounded to 2.91 with risk adjustment band/2 = 0.1)
>
> **Caveats**:
> - I verified 5 / 5 signals for this candidate. confidence_band = ±0.2.
> - If I'd been unable to verify h_index or alumni placement, this would
>   have come out at strength 2.7 ±0.4 instead — note the risk-adjusted
>   ranking would still place him #1, but with a wider band.

## Notes on the flow

1. Every connection claim has an **inline source URL** — co-authorship from
   Google Scholar, working group from ATLAS Glance, NAS from the official
   directory.
2. **Risk-adjusted ranking** means well-sourced #3 (Robert Lee, Michigan,
   strength 3.03 ±0.4) actually ranks higher than less-verified #4 / #5
   despite sometimes lower nominal strength — band/2 is subtracted from
   the sort key.
3. When evidence is missing, the agent **explicitly surfaces** which
   signals couldn't be verified rather than padding with defaults.
4. School tier comes with a citation (US News 2024 ranking page, in
   `evidence["school_tier"].sources`).

## Turn 5 — User pivots fields

> **You**:
> 那我想试试 MSE PhD 怎么办？

> **Claude**:
> Sure — the workflow is the same. A few things change:
>
> 1. Your ATLAS papers don't help much for materials (different domain).
>    P score will recompute lower for MSE matching.
> 2. I'll re-search for materials science / nano / 2D-materials PIs
>    matching your direction, with field-specific journal tier reference
>    (`data/journals/mse.yaml`).
> 3. Different US News ranking. Top 10 MSE: MIT, Northwestern, Stanford,
>    Berkeley, Georgia Tech, UCSB, Michigan, Cornell, UIUC, Caltech.
>
> Want me to run that, or refine the angle (e.g., "MSE with computational
> physics flavor")?

---

## Hard rules from this example

| Rule | Where enforced |
|------|---------------|
| Every connection edge has a source URL | `PathEdge.sources` validated; counted in `unverified_signals` |
| Every field-strength signal has a source URL | `evidence[field].sources`; counted |
| `school_tier` has a source URL | `evidence["school_tier"].sources`; counted |
| `pi_signal != "missing"` requires a source URL | counted |
| Result presentation cites every claim inline | SKILL.md Step 8 |
| Wide confidence band reduces sort rank | `risk_adjusted_strength = strength − band/2` |
| Unknown paper status raises an error | `paper_score()` validates |
| Unknown PathEdge field raises an error | `PathEdge` Pydantic `extra="forbid"` |

This is **evidence-first**: the schema, the ranking, and the presentation
all penalize unsourced claims. The agent literally cannot get a tight
confidence band by writing nice numbers — it has to fetch the URLs.
