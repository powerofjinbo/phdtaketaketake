# phdtaketaketake

> **PhD advisor matching and application triage assistant.** Connection-first, evidence-first. Packaged as a **Claude Code skill** — also works on **QClaw**, Codex CLI, Cursor, and any LLM agent that can read SKILL.md.
> Find the right advisor by network strength, not h-index.

[中文](README.zh.md) · English

> ⚠️ **Product boundary.** This is a **4.0-scale relative application-strength index, not an admission probability**. Missing or blocked sources widen the confidence band instead of being guessed.
>
> phdtaketaketake is an **expert-designed heuristic decision-support system**, **not** an empirically calibrated admission probability predictor. All thresholds (CAPEG weights, recency multipliers, program-difficulty components, strategy bucket cutoffs, etc.) are v1/v2 defaults — they should be recalibrated against real portfolios over time. See [`docs/DESIGN.md`](docs/DESIGN.md) §11 for the design boundaries and §"Frozen scope" for what this skill explicitly will not do.

## Install

```bash
git clone https://github.com/powerofjinbo/phdtaketaketake.git \
  ~/.claude/skills/phdtaketaketake

cd ~/.claude/skills/phdtaketaketake
pip install -e .
```

After install, seven CLIs are on `$PATH`:

```bash
# Workflow A — advisor matching / triage
phdtaketaketake-discovery-plan   # per-field PI-search recipe
phdtaketaketake-collect-evidence # auto-fill evidence from OpenAlex / PubMed / DBLP / Semantic Scholar
phdtaketaketake-audit            # report evidence repair queue
phdtaketaketake-match            # rank candidates given profile + JSON
phdtaketaketake-export-schemas   # write Pydantic models out to JSON Schema (Draft 2020-12)

# Workflow B — CV optimization
phdtaketaketake-cv-template      # print the bundled LaTeX CV template (path or contents)
phdtaketaketake-cv-compile       # compile a CV .tex to PDF via latexmk / pdflatex
```

You can also invoke them via `python scripts/<name>.py …` from a checkout (without install).

Claude Code auto-discovers the skill on next session. For other agents, see [Use with non-Claude agents](#use-with-non-claude-agents) below.

> Don't have Claude Code? Install at [claude.com/code](https://claude.com/code).

## Use

In any Claude Code / QClaw / Codex session, describe what you want in plain English (or Chinese) — you do **not** need to write JSON yourself:

> *"I'm applying for Physics PhDs this fall — ATLAS Higgs / detector ML, UCI undergrad GPA 3.85/4.0, two ATLAS big-collab papers, advisor Prof. X. Find me top 10–30 matching PIs and rank them by phdtaketaketake's evidence-first rules."*

> *"我是 SJTU 材料系本科，研究方向 2D 材料 photodetector，GPA 88/100，导师是 Prof. Y，求美国 top-30 PhD 申请定位。"*

The agent will:

1. Build your profile (asks for any missing key info)
2. Web-research candidate advisors at your target schools matching your research direction
3. Verify connection edges to your current advisor (co-author papers, academic genealogy, joint collaborations)
4. Run `scripts/match.py` for deterministic 4.0-scale scoring
5. Present ranked candidates with per-dimension breakdown and cited sources

### What you need to give the agent

**Required for a useful run** (the agent will ask if you don't volunteer them):

- **Field / subfield** — `physics / HEP`, `cs / NLP`, `bio / immunology`, …
- **Undergrad institution + GPA** (with scale: `4.0` / `4.3` / `4.5` / `100` / UK honours)
- **Research direction** — 1–2 sentences
- **Current advisor(s)** — name + institution. Without this, connection-first matching loses its anchor; the matcher prints a stderr warning and the C pillar floors.
- **Target school tier or list** — `top_10` / `top_11_30` / `top_31_60` / `top_60_plus`, or specific schools

**Optional but improves output quality**: papers (title / venue / status / author position / total authors), prior research experiences, specific candidate PIs you already have in mind, theory ↔ experiment crossover preferences, international friendliness needs.

The matcher is **evidence-first**: missing optional fields *widen the confidence band* — they don't crash and they don't get filled with guesses.

### Parallel workflow: CV optimization

Once the matcher has surfaced your top candidates, the same skill can help you produce a **LaTeX-formatted PhD-application CV**, optionally tailored for the top targets:

> *"Now help me make a CV for these top 3 PIs."*
> *"用上面的 match.json 帮我做一份针对 Hartman 的 tailored CV。"*

Two CLIs back this:

```bash
phdtaketaketake-cv-template --print > cv.tex   # bundled LaTeX template
phdtaketaketake-cv-compile cv.tex              # → cv.pdf via latexmk / pdflatex
```

The template ships with all sections present by default (Education, Research Experience, Publications & Presentations, Technical Skills, Teaching, Leadership, Honors); the agent fills it from your conversational input and, given a `match.json`, reorders the existing content + prunes weakly-relevant entries (with your confirmation before any deletion). **Tailoring is reordering and user-approved pruning — never invention** (no fabricated experiences, papers, or skills). PDF compile requires a TeX install (MacTeX / TeX Live / MiKTeX); minimal installs may need `tlmgr install titlesec enumitem`. Falls back cleanly to "paste into Overleaf" when local TeX is unavailable. Full agent contract in [`SKILL.md`](SKILL.md) §"CV optimization (parallel workflow)" and [`references/cv_optimization.md`](references/cv_optimization.md).

### Output per candidate

- **`match_score`** (0–4.0) — CAPEG composite
- **`application_strength`** (0–4.0, **not** a probability) — `match + opportunity_adj`
- **`risk_adjusted_strength`** = `application_strength − band/2`
- **`difficulty_adjusted_strength`** = `max(0, risk_adjusted − program_penalty)` — **primary sort key (post-#5)**
- **`lower_bound`** = `application_strength − band` — conservative reading
- **5-tier label** (on `difficulty_adjusted_strength`): Far Reach · Reach · Target · Match · Safe
- **Per-pillar**: `c_score` / `a_score` / `p_score` / `e_score` / `g_score`
- **Per-feature**: `o_score` (opportunity) · `program_difficulty_penalty` + `difficulty_reasons` · `research_fit_score` + axes
- **Evidence breakdown**: `total_signals` / `verified` / `missing` / `unsourced` (with names of which signals fall in each)
- **Strategy** (post-#7): `apply_bucket` (priority / target / reach / only_if_space / drop) + `recommended_action` (apply / contact_first / investigate_evidence / deprioritize / skip) + `outreach_angle` (only if sourced material exists) + `evidence_to_fix` queue
- **Why matched** — cited from real searches: e.g., *"co-authored 4 small-team papers with Prof. Wang in 2022–2024 (Google Scholar) · same ATLAS H→cc̄ working group (ATLAS Glance)"*

Top-level CLI output also includes a **`strategy_summary`** rolling up the full portfolio (priority/target/reach/only_if_space/drop candidate IDs + evidence_fix_queue + portfolio_notes).

## Architecture: no static cache, real data only

There is **no bundled cache** of advisors. PhD-advisor data is too dynamic and too vast for static datasets to be useful. Instead:

| Component | Role |
|-----------|------|
| The agent (Claude / Codex / Cursor / …) | Deep research: find candidates, verify connections, estimate signals — **all from real web sources, never fabricated** |
| `scripts/match.py` | Pure-Python deterministic scoring — takes the agent's findings and applies the 4.0-scale formulas |
| `data/journals/<field>.yaml`, `references/*.md`, `docs/scoring.md` | Authoritative project opinions on tiers / formulas / schema |

### Cardinal rule: real data only

Every connection edge, every candidate fact must trace back to a real source the agent actually fetched (Google Scholar / OpenAlex / INSPIRE-HEP / PubMed / Math Genealogy / faculty pages / etc.). **Fabrication is strictly forbidden** — students use these rankings for real decisions, and made-up data is worse than no data. Missing signals are honest; the matcher widens its confidence band accordingly.

Allowed sources + forbidden behaviors are enumerated in [`references/data_integrity.md`](references/data_integrity.md).

## Design charter

The full design goals — what this skill is for, what it explicitly is not,
and the roadmap — live in [`docs/DESIGN.md`](docs/DESIGN.md). One-line
mission:

> **Generate auditable, discipline-calibrated, connection-first US PhD
> advisor / program rankings for STEM applicants — to support school and
> advisor selection, without pretending to be an admission-probability
> predictor.**

## Coverage

The scoring engine itself is field-agnostic, but the **calibration** is best-supported for fields the project was designed against.

| | Coverage |
|--|----------|
| 🟢 **Best-supported** | physics / HEP, materials science (MSE) — bundled `data/journals/<field>.yaml` tier files; the scoring system was originally calibrated against these subcultures |
| 🟡 **Extensible** | chemistry, biology, CS, math, EE, chemical engineering, earth science — the agent uses [`references/journal_tiers.md`](references/journal_tiers.md) cross-field guidance + its training knowledge; the confidence band is wider |
| ⚠️ **Field-specific caveats** | CS is conference-first (different venue hierarchy); biology has co-first authorship conventions; math has a slower publication pace; clinical fields use multi-center RCT-driven prestige | see `references/journal_tiers.md` for guidance |

Quality of agent retrieval scales the result quality — and data is always fresh, since nothing is cached.

Adding a tier YAML for a new field: see [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome.

## How it differs

|                        | CSrankings        | h-index ranking | **phdtaketaketake**                                |
| ---------------------- | ----------------- | --------------- | -------------------------------------------------- |
| Data freshness         | static            | static          | ✅ real-time agent retrieval                       |
| Personalized           | ❌                | ❌              | ✅ student profile → candidate matching            |
| Connection-first       | ❌                | ❌              | ✅ #1 ranking signal                               |
| Big-collab paper aware | ❌                | ❌              | ✅ ATLAS/CMS-style 5+ author rule                  |
| Multi-STEM             | ❌ CS only        | partial         | ✅ universal (any field)                           |

## Scoring philosophy

The matcher uses a **5-layered scoring pipeline** — each layer is deterministic Python, every score traceable back to cited evidence:

```
match_score          = w_C·C + w_A·A + w_P·P + w_E·E + w_G·G        # CAPEG, tier-adaptive weights
application_strength = clip(match_score + opportunity_adj, 0, 4.0)   # adds admit-cycle availability
risk_adjusted        = application_strength − band/2                 # widens band → lower rank
difficulty_adjusted  = max(0, risk_adjusted − program_penalty)       # ← primary sort key
strategy             = bucket(difficulty_adjusted, evidence, …)      # → priority/target/reach/only_if_space/drop
```

Five **CAPEG** pillars on a 4.0 scale, tier-adaptively weighted by school competitiveness:

- **Connection (C)** — paths between candidate ↔ your current advisor: co-author (small-team vs big-collab differentiated), academic genealogy, shared grants, co-mentored students, working-group / analysis-contact overlap, committee/exam, same center, prior-institution overlap, conference sessions. v2 aggregation: `strongest + 0.10·second_strongest`, capped at 1.0, scaled by recency.
- **Advisor influence (A)** — reputation only (post-#6a refactor): h-index proxy + elite status + grad placement quality. Funding and recruiting moved to **Opportunity (O)**.
- **Publication (P)** — field-aware tier × author-role × status × recency × contribution-bonus, with big-collab and consortium guardrails. Top-3 weighted aggregate.
- **Experience (E)** — `0.20·lab_prestige + 0.30·duration + 0.50·output`, strongest single experience.
- **GPA (G)** — direct on 4.0; 4.3 / 4.5 / 100 / UK honours normalized.

Three **non-CAPEG** dimensions:

- **Opportunity (O)** — admit-cycle availability: recruiting health + funding + lab capacity + accessibility. Drives `opportunity_adj` (replaces v1 `pi_adj`); `not_recruiting` forces `application_strength=0`.
- **Program difficulty (D)** — per-program penalty 0–0.8 from school-tier admit rate + cohort size + admission model + funding structure + faculty count + international friendliness. Subtracted to form `difficulty_adjusted_strength` (the **primary sort key**).
- **Research fit (R)** — structured 6-axis tie-breaker: `0.30·topic + 0.20·method + 0.15·system + 0.15·temporal + 0.10·grant + 0.10·background`. Never a 6th pillar; sorts ties only.

5-tier label (applied to `difficulty_adjusted_strength`): **Far Reach · Reach · Target · Match · Safe**.

Full formulas: [docs/scoring.md](docs/scoring.md) · Pipeline diagram: [docs/scoring_pipeline.md](docs/scoring_pipeline.md) · Skill instructions: [SKILL.md](SKILL.md) · Profile + CandidateAdvisor schema: [references/profile_schema.md](references/profile_schema.md).

## Use with non-Claude agents

The skill is designed Claude-Code-native but the underlying matcher is plain Python and the workflow instructions in `SKILL.md` are framework-agnostic. To use with another agent:

- **Codex CLI / OpenCode**: drop a symlink at the repo root: `ln -s SKILL.md AGENTS.md`. Codex auto-reads `AGENTS.md`.
- **Cursor**: copy `SKILL.md` content into `.cursorrules` at your project root.
- **Other**: tell the agent "follow the workflow in `SKILL.md`" — most modern coding agents read it and execute the deep-research + `scripts/match.py` flow correctly.

## Example session

See [`docs/example_session.md`](docs/example_session.md) for a walk-through.

## License

MIT — see [LICENSE](LICENSE).
