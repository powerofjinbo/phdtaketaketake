# phdtaketaketake

> **Connection-first PhD advisor matcher**, packaged as a **Claude Code skill**.
> Find the right advisor by network strength, not h-index.

[中文](README.zh.md) · English

## Install

```bash
git clone https://github.com/powerofjinbo/phdtaketaketake.git \
  ~/.claude/skills/phdtaketaketake

cd ~/.claude/skills/phdtaketaketake
pip install -e .
```

Claude Code auto-discovers the skill on next session start.

> Don't have Claude Code? Install at [claude.com/code](https://claude.com/code).

## Use

In any Claude Code session, describe what you want in plain English (or Chinese):

> *"I'm applying for Physics PhDs this fall — here's my CV [paste]. Find advisors that match."*

> *"我是 SJTU 材料系本科，研究方向 2D 材料 photodetector，GPA 88/100，求美国 PhD 申请定位。"*

Claude will:

1. Read your CV (or ask brief targeted questions if info is missing)
2. Build a profile JSON
3. Run `scripts/match.py` to compute scores
4. Return ranked candidates with per-dimension breakdown + connection-path explanation

### Output per candidate

- **Match score** (0–4.0) + **admit likelihood** (0–4.0) with ±confidence band
- **5-tier label**: Reach · Target · Match · Safe · Far Reach
- **Per-dimension**: Connection / Publication / Experience / GPA
- **Why matched** — e.g., *"co-authored 4 papers with your advisor; same academic genealogy line"*

## How it differs

|                        | CSrankings        | h-index ranking | **phdtaketaketake**                       |
| ---------------------- | ----------------- | --------------- | ----------------------------------------- |
| Data                   | conf. paper count | citations       | co-author + genealogy + multi-dim         |
| Personalized           | ❌                | ❌              | ✅ student profile → candidate matching   |
| Connection-first       | ❌                | ❌              | ✅ #1 ranking signal                      |
| Big-collab paper aware | ❌                | ❌              | ✅ ATLAS/CMS-style 5+ author rule         |
| Multi-STEM             | ❌ CS only        | partial         | ✅ HEP/Physics + MSE                      |

## Scoring philosophy

All four dimensions on 4.0 scale (matching GPA), tier-adaptively weighted by school competitiveness:

- **Connection (C)** — paths between candidate ↔ your current advisor (co-author / genealogy / joint collaborations / committee)
- **Publication (P)** — journal tier × author position decay; 5+ author papers handled specially for big-collaboration physics
- **Experience (E)** — lab × duration × output, output-weighted (50%)
- **GPA (G)** — direct on 4.0; percentage / 4.3 / 4.5 / UK honours all normalized

`admit_likelihood = match_score + tier_adjustment + pi_recruiting_signal`, clipped to [0, 4.0].

Full formulas: [docs/scoring.md](docs/scoring.md) · Skill instructions: [SKILL.md](SKILL.md) · Profile schema: [references/profile_schema.md](references/profile_schema.md).

## Coverage — works for ANY STEM field

The deterministic scoring engine (Connection / Publication / Experience / GPA on 4.0 scale) is **field-agnostic** — same math runs for any STEM discipline.

Two paths depending on whether a verified candidate cache is bundled:

| Path | Fields | How |
|------|--------|-----|
| 🟢 **Bundled cache** (best confidence) | `physics`, `mse` | `scripts/match.py` loads candidates from `data/advisors/`. |
| 🟡 **Generated candidates** (lower confidence) | Any other STEM (chem · biology · CS · math · EE · ChemE · earth science · …) | Claude generates plausible candidate advisors from training knowledge for the user's specific research direction, then runs them through the same scoring engine. |

Adding a verified cache for a new field: see [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome.

## Mock data disclaimer

The bundled `data/advisors/mock_advisors.json` is **synthetic mock data**, not real faculty profiles. It's there so the skill runs out-of-the-box. Real OpenAlex-backed cache is roadmap.

## License

MIT — see [LICENSE](LICENSE).
