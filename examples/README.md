# Examples

End-to-end demos of the matcher pipeline. Each example is fully
reproducible: inputs are checked in and the bundled fixtures replace
live API calls so runs are deterministic + offline.

## Available examples

| Path | Field | What it shows |
|---|---|---|
| [`physics_hep_audit_demo/`](physics_hep_audit_demo/) | physics / HEP | Full 4-stage pipeline (discovery_plan → collect_evidence → audit → match) on a Tsinghua undergrad applying to top-10 US physics PhDs with ATLAS / Higgs background. 3 candidates differentiated to land in `target` / `reach` / `only_if_space` strategy buckets. Runs in **default mode** (no `--strict-evidence`) so the audit's repair queue is exercised — see the demo's README for the strict-mode + live-API caveats. |

Run any example:

```bash
# from the repo root, after `pip install -e .`:
bash examples/physics_hep_audit_demo/run_example.sh
```

Each example's `README.md` walks through the inputs, the per-stage
output, and what the resulting ranking + strategy means.

## Adding a new example

1. Create `examples/<your_field>_<scenario>/`
2. Write `profile.json` + `candidates_raw.json`
3. Add `fixtures/<adapter>/{find_author,recent_works,coauthored}/*.json`
   — see [`references/evidence_collection.md`](../references/evidence_collection.md)
   for the layout
4. Write `run_example.sh` (copy from physics_hep_audit_demo, adjust args)
5. Run it once, commit the generated outputs alongside
6. Write `README.md` walking through the demo
7. PR
