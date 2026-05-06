# phdtaketaketake

> **Connection-first PhD advisor matcher** — find the right advisor by network strength, not h-index.
>
> Packaged as a **Claude Code skill** so you can use it in plain English (or Chinese).

[中文](README.zh.md) · English

![demo](docs/demo.png)

---

## Install (as a Claude Code skill)

```bash
git clone https://github.com/powerofjinbo/phdtaketaketake.git \
  ~/.claude/skills/phdtaketaketake

cd ~/.claude/skills/phdtaketaketake
pip install -e .
```

Claude Code auto-discovers the skill on next session start.

> **Don't have Claude Code?** Install at [claude.com/code](https://claude.com/code).
> See [Alternative ways to use](#alternative-ways-to-use) below for CLI / Streamlit options.

## Use it

In any Claude Code session, just describe what you want:

> *"I'm applying to Physics PhDs this fall — here's my CV [paste]. Find advisors that match."*

> *"我是 SJTU 材料系本科，研究方向 2D 材料的 photodetector，GPA 88/100，求美国 PhD 申请定位。"*

> *"Score these 3 papers I have for grad school applications: [list]"*

Claude reads your CV, builds a profile, runs the matcher (`scripts/match.py`),
and presents ranked candidates with per-dimension breakdown and connection-path
explanations.

## What you get back

For each ranked candidate:

- **Match score** (0–4.0) — weighted across 4 dimensions
- **Admit likelihood** (0–4.0) with confidence band ±0.3 / 0.5 / 0.7
- **5-tier label**: Reach · Target · Match · Safe · Far Reach
- **Per-dimension breakdown**: Connection / Publication / Experience / GPA
- **Why matched**: connection-path explanation
  (e.g., *"co-authored 4 papers with your advisor; same academic genealogy line"*)

## How it differs from existing tools

|                         | CSrankings        | h-index ranking | **phdtaketaketake**                       |
| ----------------------- | ----------------- | --------------- | ----------------------------------------- |
| Data                    | conf. paper count | citations       | co-author + genealogy + multi-dim         |
| Personalized            | ❌                | ❌              | ✅ student profile → candidate matching   |
| Connection-first        | ❌                | ❌              | ✅ #1 ranking signal                      |
| Multi-STEM              | ❌ CS only        | partial         | ✅ (HEP/Physics + MSE in v0.1)            |
| Big-collab paper aware  | ❌                | ❌              | ✅ ATLAS/CMS-style 5+ author rule         |
| Conversational interface| ❌                | ❌              | ✅ via Claude Code (this is the skill)    |

## Scoring philosophy

All four dimensions on a 4.0 scale (matching GPA), then weighted-combined:

- **Connection (C)** — paths between candidate ↔ your current advisor (co-author / academic genealogy / joint collaborations / committee co-membership)
- **Publication (P)** — journal tier × author position decay; 5+ author papers handled specially for big-collaboration physics
- **Experience (E)** — lab × duration × output, output-weighted (50%)
- **GPA (G)** — direct on 4.0; percentage / 4.3 / 4.5 / UK honours all normalized

Weights are **tier-adaptive**: Top 10 schools weight Connection more (0.45),
Top 60+ weight GPA more (0.30).

`admit_likelihood = match_score + tier_adjustment + pi_recruiting_signal`,
clipped to [0, 4.0].

Full formulas: [docs/scoring.md](docs/scoring.md).
Skill instructions for Claude: [SKILL.md](SKILL.md).
Profile schema: [references/profile_schema.md](references/profile_schema.md).

## Coverage (v0.1)

- 🔭 **High Energy Physics / Physics**
- 🧱 **Materials Science & Engineering (MSE)**

Top 30 US PhD programs in each field.

Adding a new field is a YAML + a cache build script — see
[`scripts/build_advisors_cache.py`](scripts/build_advisors_cache.py) (WIP).
PRs welcome.

## Alternative ways to use

The matcher also ships as a standalone Python package, no Claude Code needed:

```bash
# CLI
phd-matcher match --profile data/samples/sample_student_physics.json \
  --field physics --top-k 10

# Streamlit demo
streamlit run phd_matcher/app.py

# Python API
python -c "from phd_matcher import rank_advisors; ..."

# Direct script (what the skill calls under the hood)
python scripts/match.py --profile-file profile.json --field physics --top-k 10
```

## Mock data disclaimer

The bundled `data/advisors/mock_advisors.json` is **synthetic mock data**, not
real faculty profiles. It exists so the skill / CLI / demo runs out of the box
without scraping anything. Real OpenAlex-backed cache is roadmap
(`scripts/build_advisors_cache.py`).

## Roadmap

- [ ] Real OpenAlex-backed advisor cache (replacing mock)
- [ ] Embedding-based research-direction matching (sentence-transformers / Voyage AI)
- [ ] Live LLM-generated explanations (currently template-based)
- [ ] Chemistry, Biology, CS coverage (community PRs welcome)
- [ ] Plugin marketplace listing

## License

MIT — see [LICENSE](LICENSE).
