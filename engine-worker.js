/* Pyodide Web Worker — runs the exact phd_matcher scoring engine in-browser.
 *
 * Messages in:  {id, type: "rank", profile, candidates, topK, strict}
 *               {id, type: "validate-profile", profile}
 * Messages out: {id, ok, result} | {id, ok: false, error}
 *               {type: "status", note}  (loading progress, no id)
 */

// Module worker. Self-hosted Pyodide (same origin) — no third-party CDN at
// runtime, so the app works on restricted networks too.
//
// IMPORTANT: self.onmessage is assigned synchronously at module top level
// (bottom of this file) with NO top-level await before it — module workers
// drop messages that arrive before the handler exists.
const BASE = self.location.pathname.replace(/\/engine-worker\.js$/, "");

let enginePromise = null;

function status(note) {
  self.postMessage({ type: "status", note });
}

async function initEngine() {
  status("Downloading Python runtime (~13 MB, cached after first visit)…");
  const { loadPyodide } = await import(
    `${self.location.origin}${BASE}/pyodide/pyodide.mjs`
  );
  const pyodide = await loadPyodide({
    indexURL: `${self.location.origin}${BASE}/pyodide/`,
  });
  status("Loading pydantic + pyyaml…");
  await pyodide.loadPackage(["pydantic", "pyyaml"]);
  status("Mounting the phd_matcher scoring engine…");
  const resp = await fetch(`${BASE}/engine/bundle.json`);
  if (!resp.ok) throw new Error(`engine bundle fetch failed: ${resp.status}`);
  const bundle = await resp.json();
  for (const [rel, text] of Object.entries(bundle.files)) {
    const path = `/eng/${rel}`;
    pyodide.FS.mkdirTree(path.slice(0, path.lastIndexOf("/")));
    pyodide.FS.writeFile(path, text);
  }
  await pyodide.runPythonAsync(`
import sys, json
sys.path.insert(0, "/eng")
from phd_matcher.models import StudentProfile, CandidateAdvisor
from phd_matcher.matching.ranker import rank_advisors, strict_validate
from phd_matcher.matching.strategy import recommend_strategy, summarize_portfolio
from phd_matcher.data.loaders import load_field_profile

def _rank(profile_json, candidates_json, top_k, strict):
    profile = json.loads(profile_json)
    raw_candidates = json.loads(candidates_json)
    student = StudentProfile(**profile)
    field_profile = load_field_profile("/eng/data", student.field)
    if field_profile and student.field != field_profile.id:
        student.field = field_profile.id
    candidates, dropped = [], []
    for raw in raw_candidates:
        if not isinstance(raw, dict):
            dropped.append(f"{raw!r}: not a JSON object")
            continue
        try:
            cand = CandidateAdvisor(**raw)
            if field_profile and cand.field != field_profile.id:
                cfp = load_field_profile("/eng/data", cand.field)
                if cfp and cfp.id == field_profile.id:
                    cand.field = field_profile.id
            candidates.append(cand)
        except Exception as e:
            name = raw.get("name") or raw.get("id") or "?"
            dropped.append(f"{name}: {e}")
    strict_errors = []
    if strict:
        for cand in candidates:
            strict_errors += strict_validate(student, cand)
        # Match errors to known ids by prefix (ids may contain spaces, so
        # splitting on whitespace is wrong — iterate the real ids instead).
        bad = {c.id for c in candidates
               if any(err.startswith(f"candidate={c.id} ") for err in strict_errors)}
        candidates = [c for c in candidates if c.id not in bad]
    # rank_advisors defaults to field_filter=True and silently drops any
    # candidate whose field != student.field — surface that as a diagnostic
    # so a 0-result run explains itself instead of looking empty-for-no-reason.
    field_mismatched = [c.name for c in candidates if c.field != student.field]
    if not candidates:
        return json.dumps({"error": "no valid candidates survived validation",
                           "dropped": dropped[:8], "strict_errors": strict_errors[:8]})
    results = rank_advisors(student, candidates, top_k=top_k, field_profile=field_profile)
    if not results and field_mismatched:
        return json.dumps({
            "error": (f"all {len(field_mismatched)} candidates were filtered out for a "
                      f"field mismatch (expected '{student.field}'). Mismatched: "
                      + ", ".join(field_mismatched[:8])),
            "dropped": dropped[:8], "strict_errors": strict_errors[:8]})
    for r in results:
        if r.strategy is None:
            r.strategy = recommend_strategy(r)
    summary = summarize_portfolio(results)
    notes = " ".join(summary.portfolio_notes) if summary.portfolio_notes else ""
    if dropped:
        notes += f" ({len(dropped)} discovered candidates dropped for schema errors.)"
    if strict_errors:
        notes += f" ({len(strict_errors)} unsourced claims rejected by strict mode.)"
    return json.dumps({
        "results": [json.loads(r.model_dump_json()) for r in results],
        "portfolio_summary": notes,
        "field_caveats": list(field_profile.caveats) if field_profile and getattr(field_profile, "caveats", None) else [],
    })

def _validate_profile(profile_json):
    try:
        StudentProfile(**json.loads(profile_json))
        return json.dumps({"ok": True})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})
`);
  status("Engine ready.");
  return pyodide;
}

function getEngine() {
  if (!enginePromise) {
    enginePromise = initEngine().catch((e) => {
      enginePromise = null; // allow retry on next call
      throw e;
    });
  }
  return enginePromise;
}

self.onmessage = async (ev) => {
  const { id, type } = ev.data;
  try {
    const pyodide = await getEngine();
    if (type === "rank") {
      const { profile, candidates, topK, strict } = ev.data;
      const fn = pyodide.globals.get("_rank");
      const out = fn(
        JSON.stringify(profile),
        JSON.stringify(candidates),
        topK,
        strict
      );
      fn.destroy();
      self.postMessage({ id, ok: true, result: JSON.parse(out) });
    } else if (type === "validate-profile") {
      const fn = pyodide.globals.get("_validate_profile");
      const out = fn(JSON.stringify(ev.data.profile));
      fn.destroy();
      self.postMessage({ id, ok: true, result: JSON.parse(out) });
    } else if (type === "warmup") {
      self.postMessage({ id, ok: true, result: { ready: true } });
    } else {
      self.postMessage({ id, ok: false, error: `unknown message type ${type}` });
    }
  } catch (e) {
    self.postMessage({ id, ok: false, error: String(e && e.message ? e.message : e) });
  }
};
