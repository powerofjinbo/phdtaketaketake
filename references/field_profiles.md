# FieldProfile catalog

Per-discipline calibration. Each profile lives in
`data/field_profiles/<id>.yaml` and is loaded by `load_field_profile()`.

The deterministic scoring engine itself is **field-agnostic** — same math
across all fields. FieldProfile is metadata that the agent consults to:

- bucket papers correctly (small-team vs big-collab threshold per field)
- search the right primary databases (INSPIRE-HEP for HEP, DBLP for CS, …)
- understand author-position semantics (e.g., senior = last in chemistry)
- apply correct ranking sources (US News for physics, CSRankings for CS)
- surface field-specific caveats in result presentation

## Bundled profiles (v0.1)

| id | venue_system | big_collab | co_first | senior_pos | notable databases |
|----|--------------|------------|----------|------------|-------------------|
| `physics` | journal_first | 10 | ❌ | n/a | INSPIRE-HEP, arXiv, OpenAlex |
| `mse` | journal_first | 8 | ❌ | last | Web of Science, Scholar |
| `cs` | **conference_first** | 8 | ✅ | last | DBLP, Semantic Scholar, OpenReview, CSRankings |
| `biology` | journal_first | 6 | ✅ | last | PubMed, Europe PMC, bioRxiv, NIH RePORTER |
| `chemistry` | journal_first | 6 | ❌ | last | Web of Science, Scholar |
| `math` | **preprint_first** | 4 | ❌ | n/a | arXiv, MathSciNet, Math Genealogy |

## Schema

See `phd_matcher/models.py` for the Pydantic source. Key fields:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | canonical field identifier |
| `aliases` | list of string | additional names that resolve to this profile |
| `venue_system` | enum | `journal_first` / `conference_first` / `preprint_first` / `trial_first` / `mixed` |
| `big_collab_threshold` | int ≥ 2 | author-count above which a paper is big collab |
| `co_first_supported` | bool | whether shared first authorship is a recognized convention |
| `senior_author_position` | enum | `last` / `first` / `n/a` |
| `primary_databases` | list of string | per-field web sources, in priority order |
| `ranking_source_url_template` | string \| null | per-field PhD-ranking URL |
| `genealogy_resources` | list of string | how to verify academic lineage in this field |
| `advisor_influence_signals` | list of string | what to look for to assess PI standing |
| `paper_status_weight_overrides` | dict of string → float | per-field paper-status weight overrides (e.g., math sets `preprint=0.9`) |
| `scoring_weight_overrides` | dict of string → dict | reserved — future per-school-tier C/A/P/E/G weight overrides |
| `research_fit_axes` | list of string | per-discipline axes the agent scores when computing `research_fit_score` (see [`research_fit.md`](research_fit.md)) |
| `caveats` | list of string | field-specific rules surfaced to the user |

`extra="forbid"` — unknown keys raise at YAML load.

## Adding a new profile

1. Copy an existing YAML in `data/field_profiles/` as a template.
2. Fill in `id`, `aliases`, `venue_system`, and other field-specific
   rules. Set `big_collab_threshold` honestly — physics big-collab papers
   regularly cross 1000 authors; CS systems papers rarely cross 8;
   biology consortium papers can cross 100.
3. Add caveats — anything an out-of-discipline reader would miss. Examples:
   - "co-first authorship is common — treat shared first as 1st"
   - "Last author = corresponding PI; mid-author = student/postdoc"
   - "Top conferences are equivalent to top journals — don't apply
     tier 4 default to a NeurIPS paper"
4. Add a regression test to `tests/test_field_profile.py` (alias check
   + spot-check on key fields).
5. PR.

## Active overrides (post-roadmap-#3 / #4)

- **Paper-status weights** — `paper_status_weight_overrides` is live.
  Math activates `preprint=0.9` (vs the cross-field default of 0.7),
  reflecting that arXiv preprints often *are* the canonical record in
  math. Other fields can opt in similarly.
- **Advisor influence as standalone A pillar** — extracted in roadmap
  #3 (commit `f80c4d9`). C is now path-only; the candidate's intrinsic
  prestige (h-index proxy / NAS / placement / funding / recruiting
  health) lives in A, with bounded tier weights so A never outranks C.
  See [`scoring_reference.md`](scoring_reference.md).
- **Research-fit axes** — `research_fit_axes` is live (roadmap #4,
  commit `a24d9ab`). Per-field axis lists drive the tie-breaker score;
  see [`research_fit.md`](research_fit.md).

## Out of scope (for now)

- **Per-field tier weights** — `match_score` weights are currently
  uniform across fields (only school-tier-adaptive).
  `scoring_weight_overrides` is reserved on the FieldProfile schema for
  future activation.
- **Per-field experience / GPA weights** — same.
