# Contributing

Thanks for considering a contribution. The most useful kinds:

## Add a verified candidate cache for a new STEM field

The skill works for any STEM discipline by having Claude generate candidates
on the fly, but a **verified cache** lifts confidence. To add one for, say,
chemistry:

1. **Build the candidate list** — the schema is in
   [`references/profile_schema.md`](references/profile_schema.md) under
   *CandidateAdvisor*. Aim for 50+ candidates spanning top-10 / top-11–30 /
   top-31–60 / top-60+ schools, all active PIs.
2. Save as `data/advisors/<field>_cache.json` *or* append to
   `data/advisors/mock_advisors.json` (and tag each entry with
   `"field": "<field>"`).
3. **Add a journal tier YAML** at `data/journals/<field>.yaml`. Mirror the
   structure of `data/journals/physics.yaml`. Cover the top 30–50 journals
   in that field across tiers S / 1 / 2 / 3 / 4.
4. **Add school rankings** — append a `<field>` section to
   `data/schools/us_news_rank.yaml`.
5. **(Optional) Add a sample profile** at
   `data/samples/sample_student_<field>.json` for documentation.
6. Open a PR.

## Add or correct journal tier mappings

The bundled YAMLs at `data/journals/<field>.yaml` are the source of truth for
covered fields. For uncovered fields, the cross-field digest is in
[`references/journal_tiers.md`](references/journal_tiers.md). PRs welcome
for either — please cite at least one impact-factor / reputational source
in the PR description so the change can be reviewed objectively.

## Add or correct lab tier criteria

Edit [`references/lab_tiers.md`](references/lab_tiers.md). The 6-tier scheme
is intentionally fixed; criteria refinements are welcome. Edge cases (e.g.,
"how do I tier a national lab in country X?") are good to surface.

## Modify scoring rules

The scoring formulas (weights, decays, tier baselines, 5+ author rule) are
intentionally fixed — they're the IP of this skill's connection-first thesis.
**Open an issue first to discuss** before touching the formulas. Code: see
`phd_matcher/scoring/`.

## Code standards

- 75 unit tests live in `tests/`. Run `pytest`. Don't drop coverage.
- Lint with `ruff` (config in `pyproject.toml`).
- Pure stdlib + `pydantic` + `pyyaml`. Don't add deps casually.

## Bugs / discussion

Open a GitHub issue at
<https://github.com/powerofjinbo/phdtaketaketake/issues>.
