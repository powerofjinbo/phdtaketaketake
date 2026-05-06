# phdtaketaketake

> **Connection-first PhD advisor matcher**, packaged as a **Claude Code skill** (also works with Codex CLI / Cursor / any LLM coding agent that can read SKILL.md).
> Find the right advisor by network strength, not h-index.

[中文](README.zh.md) · English

## Install

```bash
git clone https://github.com/powerofjinbo/phdtaketaketake.git \
  ~/.claude/skills/phdtaketaketake

cd ~/.claude/skills/phdtaketaketake
pip install -e .
```

Claude Code auto-discovers the skill on next session. For other agents, see [Use with non-Claude agents](#use-with-non-claude-agents) below.

> Don't have Claude Code? Install at [claude.com/code](https://claude.com/code).

## Use

In any Claude Code session, describe what you want in plain English (or Chinese):

> *"I'm applying for Physics PhDs this fall — here's my CV [paste]. Find advisors that match."*

> *"我是 SJTU 材料系本科，研究方向 2D 材料 photodetector，GPA 88/100，求美国 PhD 申请定位。"*

The agent will:

1. Build your profile (asks for any missing key info)
2. Web-research candidate advisors at your target schools matching your research direction
3. Verify connection edges to your current advisor (co-author papers, academic genealogy, joint collaborations)
4. Run `scripts/match.py` for deterministic 4.0-scale scoring
5. Present ranked candidates with per-dimension breakdown and cited sources

### Output per candidate

- **Match score** (0–4.0) + **admit likelihood** (0–4.0) with ±confidence band
- **5-tier label**: Reach · Target · Match · Safe · Far Reach
- **Per-dimension**: Connection / Publication / Experience / GPA
- **Why matched** — cited from real searches: e.g., *"co-authored 4 papers with Prof. Wang in 2022–2024 (per Google Scholar) · same ATLAS collaboration since 2017"*

## Architecture: no static cache

There is **no bundled cache** of advisors. PhD-advisor data is too dynamic and too vast for static datasets to be useful. Instead:

| Component | Role |
|-----------|------|
| The agent (Claude / Codex / Cursor / …) | Deep research: find candidates, verify connections, estimate signals |
| `scripts/match.py` | Pure-Python deterministic scoring — takes the agent's findings and applies the 4.0-scale formulas |
| `data/journals/<field>.yaml`, `references/*.md`, `docs/scoring.md` | Authoritative project opinions on tiers / formulas / schema |

This works for any STEM field, any subdiscipline, any school — quality scales with the agent's retrieval quality, and data is always fresh.

## How it differs

|                        | CSrankings        | h-index ranking | **phdtaketaketake**                                |
| ---------------------- | ----------------- | --------------- | -------------------------------------------------- |
| Data freshness         | static            | static          | ✅ real-time agent retrieval                       |
| Personalized           | ❌                | ❌              | ✅ student profile → candidate matching            |
| Connection-first       | ❌                | ❌              | ✅ #1 ranking signal                               |
| Big-collab paper aware | ❌                | ❌              | ✅ ATLAS/CMS-style 5+ author rule                  |
| Multi-STEM             | ❌ CS only        | partial         | ✅ universal (any field)                           |

## Scoring philosophy

Four dimensions, all on a 4.0 scale (matching GPA), tier-adaptively weighted by school competitiveness:

- **Connection (C)** — paths between candidate ↔ your current advisor (co-author / genealogy / joint collaborations / committee)
- **Publication (P)** — journal tier × author position decay; 5+ author papers handled specially for big-collaboration physics
- **Experience (E)** — lab × duration × output, output-weighted (50%)
- **GPA (G)** — direct on 4.0; percentage / 4.3 / 4.5 / UK honours all normalized

`admit_likelihood = match_score + tier_adjustment + pi_recruiting_signal`, clipped to [0, 4.0].

Full formulas: [docs/scoring.md](docs/scoring.md) · Skill instructions: [SKILL.md](SKILL.md) · Profile + CandidateAdvisor schema: [references/profile_schema.md](references/profile_schema.md).

## Use with non-Claude agents

The skill is designed Claude-Code-native but the underlying matcher is plain Python and the workflow instructions in `SKILL.md` are framework-agnostic. To use with another agent:

- **Codex CLI / OpenCode**: drop a symlink at the repo root: `ln -s SKILL.md AGENTS.md`. Codex auto-reads `AGENTS.md`.
- **Cursor**: copy `SKILL.md` content into `.cursorrules` at your project root.
- **Other**: tell the agent "follow the workflow in `SKILL.md`" — most modern coding agents read it and execute the deep-research + `scripts/match.py` flow correctly.

## Example session

See [`docs/example_session.md`](docs/example_session.md) for a walk-through.

## License

MIT — see [LICENSE](LICENSE).
