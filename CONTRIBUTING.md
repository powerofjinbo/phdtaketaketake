# Contributing

Thanks for considering a contribution. The most useful kinds:

## Add or refine journal tier mappings

The bundled YAMLs at `data/journals/<field>.yaml` are the project's
authoritative opinion on what counts as tier 1 vs 2 vs 3 within a field.
Currently bundled: physics, mse. Add a new field by:

1. Build the YAML mirroring `data/journals/physics.yaml`. Cover the top
   30–50 journals across tiers S / 1 / 2 / 3 / 4.
2. Cite at least one impact-factor / reputational source per non-obvious
   placement so the change can be reviewed.
3. Open a PR.

The cross-field digest at [`references/journal_tiers.md`](references/journal_tiers.md)
should be updated in lock-step.

## Add or refine lab tier criteria

Edit [`references/lab_tiers.md`](references/lab_tiers.md). The 6-tier scheme
(`world_class` / `top_us` / `strong_us_or_top_cn` / `good_us_or_985` /
`211_or_overseas` / `other`) is intentionally fixed; criteria refinements
and edge cases (national labs, international universities, etc.) are
welcome.

## Refine the SKILL.md deep-research workflow

`SKILL.md` is the agent-facing instructions for how to find candidates and
verify connection edges. Improvements that are valuable:

- Better search query templates for specific fields / databases (Google
  Scholar / OpenAlex / PubMed / INSPIRE-HEP / etc.)
- More-reliable signals for `pi_signal` extraction from lab pages
- Better heuristics for `normalized_collab_top20pct` / `grad_placement_quality`
  estimation

## Modify scoring rules

The scoring formulas (weights, decays, tier baselines, 5+ author rule) are
intentionally fixed — they're the IP of this skill's connection-first
thesis. **Open an issue first to discuss** before touching the formulas.
Code: see `phd_matcher/scoring/`.

## Code standards

- 119 unit tests live in `tests/`. Run `pytest`. Don't drop coverage.
- Lint with `ruff` (config in `pyproject.toml`).
- Pure stdlib + `pydantic` + `pyyaml`. Don't add deps casually.

## Re-enable GitHub Actions CI

The bundled CI config is staged at `.github_workflows/ci.yml` (note the
underscore). The repo doesn't yet have `.github/workflows/ci.yml` because
the OAuth token used to create the initial repo lacked the `workflow`
scope.

To enable (one-time, needs a quick browser auth):

```bash
gh auth refresh -s workflow                       # browser one-tap
mkdir -p ~/.claude/skills/phdtaketaketake/.github/workflows
cp ~/.claude/skills/phdtaketaketake/.github_workflows/ci.yml \
   ~/.claude/skills/phdtaketaketake/.github/workflows/ci.yml
cd ~/.claude/skills/phdtaketaketake
git add .github/workflows/ci.yml
git commit -m "Enable GitHub Actions CI"
git push
```

After that, every push runs `pytest` + `ruff check` on Python 3.11 + 3.12.

## Bugs / discussion

Open a GitHub issue at
<https://github.com/powerofjinbo/phdtaketaketake/issues>.
