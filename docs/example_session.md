# Example Claude Code session

End-to-end illustration of the **evidence-first deep-research workflow**.

> ⚠️ **All professor names below are FICTIONAL** (invented for this
> illustration). Per the cardinal rule, the real skill never asserts facts
> about specific real PIs without citing primary sources. This document
> shows the *shape* of agent output, not actual ranking claims.

---

## Turn 1 — Minimal info

> **You**:
> 我是清华物理本科，想申美国 PhD，做 ATLAS Higgs 分析。

> **Claude** *(skill activated)*:
>
> Got it. For a useful match I need a few more things:
>
> 1. **GPA** — value + scale.
> 2. **Current research advisor** — name + institution (drives the
>    Connection score, the main signal).
> 3. **Publications** — each one as: journal name + your author position
>    + status (`published` / `accepted` / `submitted` / `preprint` /
>    `in_prep`).
> 4. **Targets** — specific schools? a tier? open?

## Turn 2 — User fills in

> **You**:
> GPA 3.85/4.0. 现导师清华王老师 Prof. Lisa Wang. 1 篇 PRL 第 456 作者
> (ATLAS H→cc̄, published 2024), 1 篇 PRD 第 312 作者 (ATLAS dijet,
> published 2024). 课题组 18 个月 honors thesis. 想申 top 10 美物理 PhD.

> **Claude**:
>
> Building profile and starting candidate research.

*(Internally, the agent does:)*

```
Step 1 — StudentProfile
  field=physics, undergrad=Tsinghua, gpa_raw=3.85, gpa_scale="4.0"
  current_advisors=[{id: adv_001, name: Prof. Lisa Wang, ...}]
  papers=[
    {journal_tier: 1, author_position: 456, status: "published"},
    {journal_tier: 3, author_position: 312, status: "published"},
  ]
  experiences=[{lab_tier: "strong_us_or_top_cn", duration_months: 18,
                output_type: "honors_thesis"}]

Step 2 — Target programs (with fetched ranking source)
  Fetched: https://www.usnews.com/best-graduate-schools/...physics-rankings
  Top 10: MIT, Stanford, Harvard, Princeton, Caltech, Berkeley,
          Chicago, Cornell, Yale, Columbia
  Will record this URL in evidence["school_tier"] for every candidate.

Step 3 — Find candidate PIs
  For each program, search "<school> physics ATLAS Higgs faculty".
  Capture: id, name, institution, school_tier, field, research_areas.

Step 4 — Compute connection edges per candidate
  For each, search:
    Google Scholar: "Lisa Wang" "<candidate name>" → bucket by author count
    INSPIRE-HEP: same query for HEP-specific verification
    Math Genealogy Project: lookup advisor lineage for both
    ATLAS Glance: subgroup / convener overlap
    Lab page: current students / recruiting status
  Record each edge with PathEdge.items[supports_fields=[<field_name>]].

Step 5–6 — Field-strength + pi_signal (with claim-level evidence)
  Each non-default field gets evidence[<field>].items entries.

Step 7 — Run matcher (strict mode for real decisions)
  python scripts/match.py --profile-file /tmp/profile.json \
    --candidates-file /tmp/cands.json --field physics --top-k 10 \
    --strict-evidence
```

## Turn 3 — Strict mode runs cleanly; results presented

> **Claude**:
>
> Top 5 matches at top-10 US physics PhD programs (sorted by
> `risk_adjusted_strength`, strict mode):
>
> ```
> #1  Prof. Alex Hartman — MIT                                   [Match]
>     Strength: 2.91 / 4.0 (±0.2) · risk-adjusted: 2.81 · lower bound: 2.71
>     C: 4.00  P: 3.20  E: 3.25  G: 3.85
>     Evidence coverage: 7/7 verified ✓
>     • co-authored 6 small-team paper(s) with Prof. Wang in last 5y
>       [https://scholar.google.com/citations?user=...&q=Wang+Hartman ·
>        google_scholar]
>     • shared 41 big-collab paper(s) with Prof. Wang (alphabetical author
>       list) [https://inspirehep.net/authors/... · inspire]
>     • same working group / convener overlap with Prof. Wang
>       [https://atlas-glance.cern.ch/.../H_to_cc/conveners · lab_page]
>     • research: HEP / ATLAS / Higgs precision
>       [https://physics.mit.edu/people/... · faculty_page]
>     • collaborates with NAS / HHMI member(s)
>       [https://www.nasonline.org/member-directory/... · nas]
>
> #2  Prof. Riley Chen — UC Berkeley                             [Target]
>     Strength: 2.66 / 4.0 (±0.4) · risk-adjusted: 2.46 · lower bound: 2.26
>     C: 4.00  P: 3.20  E: 3.25  G: 3.85
>     Evidence coverage: 5/7 verified · 2 missing (collab_with_nas, grad_placement_quality)
>     • co-authored 2 small-team paper(s) with Prof. Wang in 2022–2024
>       [https://scholar.google.com/... · google_scholar]
>     • shared 8 big-collab paper(s) (alphabetical author list)
>       [https://inspirehep.net/... · inspire]
>     • two-hop genealogy connection with Prof. Wang
>       [https://www.genealogy.math.ndsu.nodak.edu/... · genealogy]
>     • research: experimental HEP / ATLAS / dark matter
>       [https://physics.berkeley.edu/people/... · faculty_page]
>     ⚠️ Missing: I couldn't verify NAS membership of any recent
>        co-author, and the lab's alumni page didn't load. Two signals
>        absent → wider band.
>
> #3  Prof. Morgan Patel — Princeton                             [Match]
>     Strength: 3.03 / 4.0 (±0.4) · risk-adjusted: 2.83 · lower bound: 2.63
>     C: 3.70  P: 3.20  E: 3.25  G: 3.85
>     Evidence coverage: 6/7 verified · 1 missing (collab_with_nas)
>     • co-authored 3 small-team paper(s) with Prof. Wang
>       [https://scholar.google.com/... · google_scholar]
>     • shared 18 big-collab paper(s) (alphabetical author list)
>       [https://inspirehep.net/... · inspire]
>     • same working group / convener overlap with Prof. Wang
>       [https://atlas-glance.cern.ch/... · lab_page]
>     • research: ATLAS / Higgs precision / SUSY
>       [https://www.princeton.edu/... · faculty_page]
>
> #4  Prof. Casey Lin — Stanford                                 [Reach]
>     Strength: 1.87 / 4.0 (±0.4) · risk-adjusted: 1.67 · lower bound: 1.47
>     C: 2.30  P: 3.20  E: 3.25  G: 3.85
>     Evidence coverage: 6/7 verified · 1 missing (path:adv_001)
>     • no co-authorship found between Prof. Wang and Prof. Lin
>       (searched Google Scholar 2020–2024, INSPIRE-HEP, Math Genealogy)
>       [https://scholar.example/search?q=Wang+Lin · google_scholar]
>     • theoretical particle physics PI (EFT, not detector physics)
>       [https://physics.stanford.edu/... · faculty_page]
>
> ⚠️ One candidate dropped from this list: **Prof. Sam Kuznetsov** (MIT)
>    failed strict-evidence — I couldn't verify
>    `evidence["pi_signal"].items` (lab page returned 404). I can either
>    re-run after I find the recruiting page, or fall back to default
>    mode and rank with confidence band ±0.6 — your call.
> ```
>
> Estimates use only public academic-network signals I gathered via web
> search. Does not include SOP / recommendation letters / interviews.
>
> Want to drill into any candidate? Try a different field?

## Turn 4 — Drill into #1

> **You**:
> #1 Hartman 详细说说，他怎么和我导师合作的？

> **Claude**:
>
> Prof. Alex Hartman (MIT) — based on what I fetched:
>
> **Co-authorship** (Google Scholar 2020–2024, structured items in
> `paths_to_advisors["adv_001"].items`):
>
> - 6 papers with **≤10 authors** (small team) including both Hartman and
>   Wang — these are real working-relationship signals, not bulk
>   collaboration credit.
> - 41 papers with **>10 authors** (ATLAS bulk publications) — these
>   count as `big_collab_papers_5y` and contribute much less per the
>   `min(0.4, n/25)` strength curve.
>
> **Working group** (ATLAS Glance conveners page):
> - Both listed as co-conveners of the H→cc̄ subgroup, 2021–2023. This
>   is the strongest big-collab evidence — `analysis_contact_overlap`
>   would be even stronger if I'd found a paper-specific contact list.
>
> **Score breakdown**:
>
> | Component | Value | How it was computed |
> |-----------|-------|---------------------|
> | C (Connection) | **4.00** | path: small_team_coauthor_5y=6 → strength `min(1.0, 6/5) = 1.0`; same_working_group=true → 0.7; max wins → c_path = 1.0. Field strength: 0.4·0.85 (h_index proxy) + 0.3·1 (NAS) + 0.3·0.8 (placement) = 0.88. c_raw = 0.6·1.0 + 0.4·0.88 = 0.952 → bucket maps to 4.0 |
> | P (Publication) | **3.20** | PRL pos 456 → 5+ rule: `min(3.5, 4.0−0.45)=3.5`; PRD pos 312 → 5+ rule: `min(3.5, 3.3−0.45)=2.85`. Aggregate top-2: `0.7·3.5 + 0.3·2.85 = 3.305`. Both `published`, weight 1.0 → P = 3.20 (rounded display) |
> | E (Experience) | **3.25** | lab=strong_us_or_top_cn (3.5)·0.20 + duration=18mo (3.5)·0.30 + output=honors_thesis (3.0)·0.50 = 0.7+1.05+1.5 = 3.25 |
> | G (GPA) | **3.85** | 3.85/4.0, direct |
> | match_score | **3.71** | top_10 weights: 0.45·4.0 + 0.30·3.20 + 0.15·3.25 + 0.10·3.85 = 1.80+0.96+0.4875+0.385 = 3.6325 → rounded 3.71 (with the rounding applied per-component first) |
> | tier_adj | **−1.0** | top_10 — competitive |
> | pi_adj | **0.0** | normal recruiting (lab page lists 1.7 PhDs/yr) |
> | application_strength | **2.71** | `clip(3.71 − 1.0 + 0.0, 0, 4.0) = 2.71` |
> | risk-adjusted | **2.81** *(but only because)* | wait — risk-adjusted = strength − band/2 = 2.71 − 0.1 = 2.61. The 2.81 in the card was higher because I rounded for display; let me recheck below. |
> | confidence_band | **±0.2** | 0 unverified (everything sourced) |
> | lower_bound | **2.51** | strength − band = 2.71 − 0.2 = 2.51 |
>
> *Apologies — the card I showed in Turn 3 had a rounding error. The
> matcher's actual numbers are above. The skill labels this `Match` (≥3.0
> would be `Match`, < 3.0 is `Target`) — actually `Target` since 2.71 is
> in [2.5, 3.0). Let me re-rank the list with the corrected numbers if
> you want.*
>
> *(In a real session, the matcher would surface the right numbers
> directly; this turn-4 dialogue exists to illustrate that the agent
> should be willing to admit display-rounding mistakes and re-show.)*
>
> **Why this matters for admission**: Hartman knows Wang's work directly
> (analysis-level overlap, not just collaboration co-membership). A
> recommendation letter from Wang to Hartman is *known recommender,
> calibrated opinion*. That's the connection-first thesis the score
> reflects.
>
> **Caveats**:
> - All 7 signals were verified via structured items with
>   `supports_fields` tags. confidence_band = ±0.2.
> - `application_strength` is **not a probability**. Top-10 PhD programs
>   reject ~90% of applicants regardless of how strong the profile looks.

## Turn 5 — Strict failure mode

> **You**:
> 那 Stanford 的 Casey Lin 你说 path 找不到，那我把所有顶校列出来（前 30）你帮我看看？

> **Claude**:
>
> OK — re-running with top-30 US physics programs. Strict mode flagged
> two candidates I couldn't verify:
>
> ```
> ❌ strict-evidence: unsourced claims detected
>    candidate=cand_017 unsourced claim: pi_signal — evidence['pi_signal'].items
>      must include an EvidenceSource citing the lab's current-students or
>      recruiting page (the candidate's lab page returned 404)
>    candidate=cand_023 unsourced claim: research_areas — evidence['research_areas'].items
>      must include an EvidenceSource with supports_fields containing 'research_areas'
>      (faculty page didn't list current research focus)
> ```
>
> Two options:
>
> 1. **I dig more** — try Wayback Machine for cand_017's lab page;
>    look at recent papers' acknowledgments for cand_023's research
>    direction. ~5 minutes.
>
> 2. **You skip strict** — re-rank in default mode. The two candidates
>    will appear with confidence band ±0.4 or wider; I'll flag them in
>    the explanation as "research_areas/pi_signal not verified, lower
>    confidence". Faster but less reliable for final decisions.
>
> Which?

---

## Notes on the flow

1. Every claim in the explanation is bound to a URL via the `items`
   structured form, with `source_type` annotated and `supports_fields`
   restricting which claim that URL backs.
2. **Risk-adjusted ranking** subtracts `band/2` from the sort key, so
   well-evidenced candidates outrank loosely-claimed peers.
3. **Strict mode** rejects unsourced claims with a structured error
   message pointing the agent at the right field to fix. Use this for
   real application decisions; use default mode only for early drafts.
4. When the agent is uncertain, it surfaces missing/unsourced signals
   explicitly rather than padding with defaults.

## Hard rules from this example

| Rule | Where enforced |
|------|----------------|
| Every claim has an `items` source whose `supports_fields` matches | `evidence_coverage()` per-claim check |
| Bare `sources: list[str]` accepted in default mode only (legacy) | `EvidenceEntry.has_evidence_for(strict=True)` rejects |
| Verified-empty path requires `supports_fields=["path:<id>"]` | `_path_edge_verified()` strict branch |
| `school_tier` requires citation to a ranking source | `evidence_coverage()` — strict_validate flags |
| Wide confidence band reduces sort rank | `risk_adjusted_strength = strength − band/2` |
| Unknown paper status raises | `paper_score()` validates |
| Unknown PathEdge field raises | `PathEdge` Pydantic `extra="forbid"` |
| Unknown EvidenceSource source_type raises | `EvidenceSource.source_type: Literal[...]` |

This is **evidence-first**: the schema, the ranking, and the presentation
all penalize unsourced claims. The agent literally cannot get a tight
confidence band by writing nice numbers — it has to fetch the URLs and
bind them to the right fields.
