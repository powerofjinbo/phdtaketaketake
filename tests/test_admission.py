"""Tests for the admission-probability estimator (phd_matcher.admission)."""

from __future__ import annotations

import json
import math
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from phd_matcher.admission import (
    AdmissionApplicant,
    AdmissionTarget,
    estimate_admission,
    estimate_portfolio,
)
from phd_matcher.admission.api import estimate_admission_json
from phd_matcher.admission.calibrate import Outcome, calibrate
from phd_matcher.admission.estimator import (
    WEIGHTS,
    Draws,
    _mean,
    prepare,
    simulate,
)
from phd_matcher.admission.features import Feature
from phd_matcher.admission.transcript import coursework_signals, grade_points

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "examples" / "admission_demo"
N = 1500


def _applicant(**over) -> AdmissionApplicant:
    base = json.loads((DEMO / "applicant.json").read_text())
    base.update(over)
    return AdmissionApplicant(**base)


def _targets() -> list[dict]:
    return json.loads((DEMO / "targets.json").read_text())


def _pi_target(**over) -> AdmissionTarget:
    raw = _targets()[0]
    raw.update(over)
    return AdmissionTarget(**raw)


def _program_target(tier="top_11_30", **over) -> AdmissionTarget:
    raw = {"id": "prog", "institution": "Some University", "school_tier": tier}
    raw.update(over)
    return AdmissionTarget(**raw)


def _p(app, tgt, **kw):
    return estimate_admission(app, tgt, samples=N, with_levers=False, **kw)


# ---------------------------------------------------------------------------
# Required inputs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("missing", [
    "gpa_raw", "transcript", "publications", "research_interests", "application_direction",
])
def test_required_inputs(missing):
    raw = json.loads((DEMO / "applicant.json").read_text())
    raw.pop(missing)
    with pytest.raises(ValidationError):
        AdmissionApplicant(**raw)


def test_blank_direction_rejected():
    with pytest.raises(ValidationError):
        _applicant(application_direction="   ")


def test_empty_transcript_rejected():
    with pytest.raises(ValidationError):
        _applicant(transcript={"courses": []})


def test_gre_is_optional_and_no_publications_is_a_valid_answer():
    app = _applicant(gre_subject=None, gre_general=None, publications=[])
    est = _p(app, _program_target())
    assert 0.0 < est.probability < 1.0


def test_target_needs_tier_or_pi():
    with pytest.raises(ValidationError):
        AdmissionTarget(id="x", institution="Somewhere")


def test_api_reports_readable_validation_errors():
    raw = json.loads((DEMO / "applicant.json").read_text())
    raw.pop("transcript")
    out = json.loads(estimate_admission_json(json.dumps(raw), json.dumps(_targets())))
    assert out["error"] == "invalid input"
    assert any("transcript" in d for d in out["details"])


# ---------------------------------------------------------------------------
# Calibration: an applicant we know nothing about gets the base rate
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("tier", ["top_10", "top_11_30", "top_31_60", "top_60_plus"])
def test_unknown_applicant_reproduces_base_rate(tier):
    prep = prepare(_applicant(is_international=None), _program_target(tier))
    blank = [Feature(f.key, f.label, f.label_zh, "missing", loading=f.loading)
             for f in prep.features]
    prep = replace(prep, features=blank, bonus=[], funding={"direct": 0.0, "committee": 0.0})
    offers, _ = simulate(prep, Draws(20000, seed=3))
    assert _mean(offers) == pytest.approx(prep.base_rate, abs=0.012)


def test_weights_sum_to_one_and_connection_leads_direct_admit():
    for model, w in WEIGHTS.items():
        assert sum(w.values()) == pytest.approx(1.0), model
    direct = WEIGHTS["direct"]
    assert direct["connection"] == max(direct.values())


# ---------------------------------------------------------------------------
# Monotonicity and bounds
# ---------------------------------------------------------------------------

def test_higher_gpa_never_lowers_probability():
    tgt = _program_target()
    probs = [_p(_applicant(gpa_raw=g), tgt).probability for g in (3.0, 3.4, 3.7, 3.95)]
    assert probs == sorted(probs)
    assert probs[-1] > probs[0]


def test_first_author_paper_raises_probability():
    tgt = _program_target()
    paper = {"title": "t", "journal": "PRL", "journal_tier": 1, "author_position": 1,
             "status": "published", "year": 2025}
    base = _applicant()
    better = _applicant(publications=[*json.loads((DEMO / "applicant.json").read_text())
                                      ["publications"], paper])
    assert _p(better, tgt).probability > _p(base, tgt).probability


def test_positive_contact_with_pi_helps():
    app = _applicant()
    cold = _p(app, _pi_target(contact_status="none")).probability
    warm = _p(app, _pi_target(contact_status="meeting_held")).probability
    assert warm > cold


def test_international_status_lowers_odds():
    tgt = _program_target()
    assert _p(_applicant(is_international=True), tgt).probability < \
        _p(_applicant(is_international=False), tgt).probability


def test_probability_capped_below_certainty():
    star = _applicant(
        gpa_raw=4.0, undergrad_tier="elite",
        letters=[{"name": "A", "prominence": "field_leader", "is_research_supervisor": True},
                 {"name": "B", "prominence": "field_leader", "is_research_supervisor": True}],
        publications=[{"title": f"p{i}", "journal": "Nature", "journal_tier": "S",
                       "author_position": 1, "status": "published", "year": 2025}
                      for i in range(3)],
        external_fellowship="secured", is_international=False,
    )
    est = _p(star, _program_target("top_60_plus"))
    assert est.probability <= 0.95
    assert est.interval_80[1] <= 0.95
    assert est.verdict == "strong"


def test_interview_stage_raises_probability():
    app = _applicant()
    pre = _p(app, _program_target("top_10")).probability
    post = _p(app, _program_target("top_10", stage="interview")).probability
    assert post > pre


# ---------------------------------------------------------------------------
# PI-specific behaviour
# ---------------------------------------------------------------------------

def _pp(model: str) -> dict:
    return {"admission_model": model}


def test_not_recruiting_pi_closes_direct_admit_route():
    pi = _targets()[0]["pi"]
    pi = {**pi, "pi_signal": "not_recruiting"}
    est = _p(_applicant(), _pi_target(pi=pi, program_profile=_pp("direct_admit")))
    assert est.probability_with_pi is not None and est.probability_with_pi < 0.02


def test_not_recruiting_pi_in_committee_program_keeps_the_offer_but_not_the_lab():
    pi = {**_targets()[0]["pi"], "pi_signal": "not_recruiting"}
    open_pi = {**_targets()[0]["pi"], "pi_signal": "normal"}
    closed = _p(_applicant(), _pi_target(pi=pi, program_profile=_pp("centralized")))
    opened = _p(_applicant(), _pi_target(pi=open_pi, program_profile=_pp("centralized")))
    assert closed.probability > 0.05
    assert closed.probability_with_pi < 0.25 * closed.probability
    assert opened.probability_with_pi > closed.probability_with_pi


def test_with_pi_never_exceeds_offer_probability():
    est = _p(_applicant(), _pi_target(program_profile=_pp("rotation")))
    assert est.probability_with_pi <= est.probability + 1e-9


# ---------------------------------------------------------------------------
# Uncertainty
# ---------------------------------------------------------------------------

def test_verified_program_stat_narrows_interval():
    app = _applicant()
    prior = _p(app, _program_target())
    evidence = {"items": [{"url": "https://example.edu/admissions-stats", "source_type": "other",
                           "claim": "95 offers / 820 applicants",
                           "supports_fields": ["admission:admit_rate"]}]}
    stat = _p(app, _program_target(stats={"applicants": 820, "offers": 123,
                                          "evidence": evidence}))
    assert stat.base_rate_source == "verified_program_stat"
    assert _logit_width(stat) < _logit_width(prior)


def _logit_width(e) -> float:
    lo, hi = e.interval_80
    return math.log(hi / (1 - hi)) - math.log(lo / (1 - lo))


def test_missing_inputs_widen_interval():
    # Compare in log-odds: an absolute width also shrinks when the point
    # estimate drops, which would hide the extra uncertainty.
    full = _p(_applicant(), _program_target())
    sparse = _p(_applicant(letters=[], experiences=[], undergrad_tier="unknown"),
                _program_target())
    assert _logit_width(sparse) > _logit_width(full)
    assert any("letter" in m.lower() for m in sparse.missing_inputs)


def test_deterministic():
    a = _p(_applicant(), _pi_target())
    b = _p(_applicant(), _pi_target())
    assert a.model_dump() == b.model_dump()


def test_portfolio_accounts_for_correlation():
    app = _applicant()
    targets = [AdmissionTarget(**t) for t in _targets()]
    port = estimate_portfolio(app, targets, samples=N, with_levers=False)
    assert len(port.estimates) == len(targets)
    assert port.p_at_least_one <= port.p_at_least_one_if_independent + 1e-9
    assert port.p_at_least_one >= max(e.probability for e in port.estimates)


def test_levers_are_positive_what_ifs():
    est = estimate_admission(_applicant(external_fellowship="none"),
                             _pi_target(contact_status="none"), samples=N)
    keys = {lv.key for lv in est.levers}
    assert "fellowship" in keys and "contact_pi" in keys
    assert all(lv.delta_pp > 0 for lv in est.levers)


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------

def test_grade_points_formats():
    assert grade_points("A-", None) == pytest.approx(3.7)
    assert grade_points("93", None) == pytest.approx(4.0)
    assert grade_points("良好", None) == pytest.approx(3.3)
    assert grade_points("P", None) is None
    assert grade_points(3.9, "4.3") <= 4.0


def test_coursework_signals_core_and_trend():
    from phd_matcher.admission.models import Transcript

    t = Transcript(courses=[
        {"name": "Calculus", "grade": "B", "year": 1},
        {"name": "Writing", "grade": "B", "year": 2},
        {"name": "量子力学", "grade": "A", "year": 3},
        {"name": "Electrodynamics", "grade": "A", "year": 3},
        {"name": "Quantum Field Theory", "grade": "A-", "year": 4, "level": "graduate"},
    ])
    cw = coursework_signals(t, ["quantum", "electrodynamics", "量子"])
    assert cw.n_core == 3
    assert cw.core_gpa == pytest.approx((4.0 + 4.0 + 3.7) / 3)
    assert cw.n_graduate_good == 1
    assert cw.trend is not None and cw.trend > 0


# ---------------------------------------------------------------------------
# Calibration fit + CLI
# ---------------------------------------------------------------------------

def test_calibrate_moves_toward_observed_rate():
    app = _applicant()
    tgt = _program_target("top_31_60")
    # Everyone admitted → estimates were too pessimistic → shift goes up.
    outcomes = [Outcome(applicant=app, target=tgt, admitted=True) for _ in range(40)]
    res = calibrate(outcomes)
    assert res["fitted_relative"]["intercept_shift"] > 0
    assert res["log_loss"]["after"] < res["log_loss"]["before"]


def test_cli_end_to_end():
    out = subprocess.run(
        [sys.executable, "-m", "phd_matcher.cli.admission",
         "--applicant-file", str(DEMO / "applicant.json"),
         "--targets-file", str(DEMO / "targets.json"),
         "--samples", "400", "--no-levers"],
        capture_output=True, text=True, check=True, cwd=ROOT,
    )
    data = json.loads(out.stdout)
    assert len(data["estimates"]) == len(_targets())
    assert 0 < data["p_at_least_one"] < 1
