# Example Claude Code session

Walk-through of an end-to-end conversation with the skill. The user volunteers
minimal info; the skill follows the **ask-when-missing** workflow defined in
`SKILL.md`, then does **real-time web research** to find candidates and verify
connection edges, builds the profile + candidates JSON, runs the matcher, and
presents results conversationally.

This isn't a recorded transcript — it's a hand-written illustration of the
intended flow. Real agent responses will vary in phrasing.

---

## Turn 1 — User opens with minimal info

> **You**:
> 我是清华物理本科，想申美国 PhD，做 ATLAS Higgs 分析。

> **Claude** *(skill activated)*:
> Got it — for matching to be useful I need a few more things. Three quick questions:
>
> 1. **GPA** — what's your GPA, and on what scale? (4.0 / 4.3 / 100-point / …)
> 2. **Current research advisor** — name + institution (this drives the Connection score, the main IP of this matcher).
> 3. **Publications** — any papers? Each one as: journal name + your author position. ATLAS papers usually mean 100+, that's fine.
>
> Also: which programs do you have in mind? Specific schools? Top 10 physics? Anywhere?

## Turn 2 — User fills in

> **You**:
> GPA 3.85/4.0, 现导师清华王老师 Prof. Lisa Wang，1 篇 PRL 第 456 作者 (ATLAS Higgs charm coupling), 1 篇 PRD 第 312 作者 (ATLAS dijet search), 课题组待了 18 个月写了 honors thesis。想申 top 10 美国物理 PhD。

> **Claude**:
> Perfect. Building the profile and starting the candidate research…

*(Internal — the agent runs:)*

```
1. Build StudentProfile JSON
   - field=physics, undergrad=Tsinghua, gpa_raw=3.85, gpa_scale=4.0
   - current_advisors=[{id: adv_001, name: Prof. Lisa Wang, ...}]
   - papers: PRL pos=456 tier=1, PRD pos=312 tier=3
   - experiences: lab=Wang, tier=strong_us_or_top_cn, 18 mo, thesis

2. Identify top-10 US physics programs (US News): MIT, Stanford, Harvard,
   Princeton, Caltech, Berkeley, Chicago, Cornell, Yale, Columbia.

3. Web-search each program's faculty in HEP / ATLAS / Higgs:
   - "MIT physics ATLAS Higgs faculty"
   - "Stanford SLAC ATLAS faculty"
   - …
   → Gather ~25 candidates active on ATLAS / Higgs in last 3 yrs.

4. For each candidate, verify connection to Prof. Lisa Wang:
   - Google Scholar / OpenAlex: '"Lisa Wang Tsinghua" "<candidate name>"'
   - INSPIRE-HEP: search co-authored papers
   - Math Genealogy: check shared lineage
   → Find candidates with ≥1 ATLAS co-authorship; record paper counts.

5. Look up each candidate's lab page for current students / recruiting:
   → set pi_signal accordingly.

6. Build CandidateAdvisor[] JSON, write to /tmp/cands.json,
   call scripts/match.py.
```

## Turn 3 — Claude presents ranked candidates

> **Claude**:
>
> Top 10 matches at top-10 US physics programs:
>
> ```
> #1  Prof. Markus Klute — MIT                                    [Match]
>     Match: 3.71 / 4.0 · Admit: 3.31 / 4.0 (±0.3)
>     C: 4.00  P: 3.30  E: 3.25  G: 3.85
>     co-authored 6+ ATLAS papers with Prof. Wang in 2020–2024 (per
>     Google Scholar) · same ATLAS-Tsinghua working group on Higgs
>     boson coupling measurements · CV3 lab page lists 3 recent PhD
>     admits → strong recruiting
>
> #2  Prof. Aram Apyan — Princeton                                [Match]
>     Match: 3.56 / 4.0 · Admit: 3.16 / 4.0 (±0.3)
>     C: 3.70  P: 3.30  E: 3.25  G: 3.85
>     co-authored 3 ATLAS papers with Prof. Wang in 2021–2023 ·
>     ATLAS Higgs cross-section group overlap ~5 yr · lab page
>     lists 2 recent PhDs → normal recruiting
>
> #3  Prof. Jeffrey Berryhill — Stanford                          [Match]
>     Match: 3.43 / 4.0 · Admit: 3.03 / 4.0 (±0.5)
>     C: 3.30  P: 3.30  E: 3.25  G: 3.85
>     no direct co-authorship found · Math Genealogy: candidate's
>     PhD advisor (Y. Tu) was a postdoc with Wang's PhD advisor
>     (X. Liu) at SLAC in late 90s → "uncle_nephew" genealogy edge ·
>     recruiting status: missing data, defaulted
>
> #4  Prof. Maria Chen — Stanford                                 [Reach]
>     Match: 2.86 / 4.0 · Admit: 2.46 / 4.0 (±0.5)
>     C: 2.30  P: 3.30  E: 3.25  G: 3.85
>     no direct path to Prof. Wang found · pure theory PI (EFT,
>     not detector physics) — research-direction match weak ·
>     normalized_collab=0.7 (NAS member, h=89)
>
> ... (6 more)
> ```
>
> Estimates use only public academic-network signals I gathered via web
> search. Does not include SOP / recommendation letters / interviews.
> Real admission decisions depend on factors beyond what this tool models.
>
> Want to drill into anyone? See more candidates at top-30 schools? Try
> a different field?

## Turn 4 — User asks for detail

> **You**:
> #1 Klute 详细说说，他怎么和我导师合作的？

> **Claude**:
> Prof. Markus Klute (MIT) is a senior experimental HEP PI working on:
> - ATLAS Higgs precision measurements (cross-section, couplings)
> - Future detector R&D
>
> His connection to Prof. Lisa Wang:
>
> Per a Google Scholar search of `"Lisa Wang" "Markus Klute"` filtered to
> 2020–2024: **6 ATLAS papers** with both as authors, including:
> - Phys. Rev. Lett. 130 (2023) — H → cc̄ coupling (your paper)
> - JHEP 06 (2022) — Higgs differential cross-sections
> - 4 more in PRD / PRL / Eur Phys J C
>
> They're both members of the ATLAS Higgs sub-group on bosonic decays;
> Klute is a former physics convener of that group, Wang is a coordinator
> on the Tsinghua side of the H → cc̄ analysis.
>
> Why this matters: a recommendation letter from Wang to Klute is *known
> recommender, known calibration*. He's read her papers, supervised
> analyses she co-led, and trusts her assessment. That's the entire
> connection-first thesis the matcher embodies.
>
> Score breakdown for him:
> - C = 4.00 (max — direct coauthorship density 6+ in 5 yr saturates the
>   `coauthor_papers_5y/5` formula at 1.0; field strength bumps with NAS
>   collaboration)
> - P = 3.30 (your two ATLAS papers, 5+ author rule → both 3.5; aggregated
>   `0.7·3.5 + 0.3·3.5 = 3.5`, but tier-3 PRD blends down)
> - E = 3.25 (Wang lab tier 3.5, 18 mo → 3.5, honors_thesis output → 3.0)
> - G = 3.85 (direct 4.0 GPA → 3.85)
> - match = 0.45·4.0 + 0.30·3.30 + 0.15·3.25 + 0.10·3.85 = 3.71
> - admit_likelihood = 3.71 + (top_10 = -0.4) + (strong recruiting = +0.0
>   — actually it was already pi_signal=normal, +0.0) = 3.31
>
> Caveat: this is one paper-author combination away from the actual
> ATLAS-Tsinghua-MIT working group dynamic. The score reflects what
> public co-authorship records show, not internal lab politics or
> Klute's actual admissions decisions.

## Turn 5 — User wants to compare to MSE

> **You**:
> 那如果我想试试材料 PhD 怎么办？

> **Claude**:
> Sure — for materials, two things change:
>
> 1. Your ATLAS papers don't help much (they're physics-domain). Pub score
>    will recompute lower for materials matching.
> 2. I'll need to research candidates in materials science / condensed
>    matter, not HEP. Different US News ranking too — top-10 MSE programs
>    are MIT, Northwestern, Stanford, Berkeley, Georgia Tech, UCSB,
>    Michigan, Cornell, UIUC, Caltech.
>
> Want me to run that, or refine the angle (e.g., "MSE with computational
> physics flavor" — 2D materials, condensed matter theory, etc.)?

---

## Notes on the flow

1. The skill asked for **3 specific things** in turn 1 — not a generic
   "tell me everything about you" prompt.
2. The agent did **live web research** rather than consulting a static
   cache. Citations like "per Google Scholar" / "per Math Genealogy" are
   surfaced in explanations.
3. Confidence band reflects what was verifiable (±0.3 for #1 with verified
   coauthorship + lab page check, ±0.5 for #3 where genealogy was inferred
   indirectly).
4. The user could naturally drill in or pivot to a different field — the
   skill doesn't have a fixed coverage, it researches whatever the user asks
   about.

For an uncovered field (say chemistry or biology), the same flow runs — only
the journal tier reference (`references/journal_tiers.md`) and the agent's
domain knowledge differ.
