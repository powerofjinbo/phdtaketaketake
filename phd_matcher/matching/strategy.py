"""Strategy explainer (Sprint-2-c5 / Roadmap-#7).

Per-candidate `StrategyRecommendation` + portfolio-level
`StrategySummary` — purely derivative on top of scoring. Does NOT
modify `match_score`, `application_strength`, `risk_adjusted_strength`,
`difficulty_adjusted_strength`, or `research_fit_score`. Pinned by
`test_strategy_does_not_change_scores`.

Bucket precedence (hard-risk first; first match wins):

  drop → only_if_space → reach → target → priority

This means hard risks (not_recruiting, ≥3 unsourced claims, very low
fit) override high nominal scores. The strategy report is a decision
memo, not a "score → label" mapping.

> **Thresholds are v1 defaults; recalibrate after running real
> portfolios.** The bucket cutoffs and recommendation rules are
> educated guesses, not load-bearing magnitudes.
"""

from __future__ import annotations

from typing import Literal

from phd_matcher.models import (
    ApplyBucket,
    MatchResult,
    RecommendedAction,
    StrategyRecommendation,
    StrategySummary,
)

# ---- Bucket thresholds (v1 defaults) ------------------------------------

DROP_RISK_ADJUSTED_FLOOR = 1.50
DROP_UNSOURCED_THRESHOLD = 3
DROP_RESEARCH_FIT_FLOOR = 0.20

ONLY_IF_SPACE_RISK_ADJUSTED_CEIL = 2.00
ONLY_IF_SPACE_MISSING_CEIL = 5
ONLY_IF_SPACE_LOWER_BOUND_CEIL = 1.60

REACH_APPLICATION_STRENGTH_FLOOR = 2.40
REACH_RISK_ADJUSTED_CEIL = 2.40

TARGET_RISK_ADJUSTED_FLOOR = 2.30
TARGET_UNSOURCED_CEIL = 2

PRIORITY_RISK_ADJUSTED_FLOOR = 2.70
PRIORITY_LOWER_BOUND_FLOOR = 2.30
PRIORITY_UNSOURCED_REQUIREMENT = 0

STRONG_C_FLOOR = 3.7      # C bucket boundary for "strong connection"
STRONG_FIT_FLOOR = 0.65


# ---- Bucket assignment (first-match precedence) -------------------------

def _assign_bucket(result: MatchResult) -> tuple[ApplyBucket, list[str]]:
    """Return ``(bucket, reasons)``. First-matching rule wins."""
    reasons: list[str] = []
    cand = result.candidate

    # 1. drop — hard risks
    eff_pi = (
        cand.opportunity_signal.pi_signal
        if cand.opportunity_signal is not None
        and cand.opportunity_signal.pi_signal != "missing"
        else cand.pi_signal
    )
    if eff_pi == "not_recruiting":
        return "drop", ["pi_signal=not_recruiting (lab is not accepting students)"]
    if result.unsourced_signals >= DROP_UNSOURCED_THRESHOLD:
        return "drop", [
            f"{result.unsourced_signals} unsourced claims (≥{DROP_UNSOURCED_THRESHOLD})"
            f" — hallucination risk too high to trust the ranking"
        ]
    if (
        result.research_fit_score is not None
        and result.research_fit_score < DROP_RESEARCH_FIT_FLOOR
    ):
        return "drop", [
            f"research_fit_score={result.research_fit_score:.2f} < "
            f"{DROP_RESEARCH_FIT_FLOOR} — fundamental topical mismatch"
        ]
    if result.risk_adjusted_strength < DROP_RISK_ADJUSTED_FLOOR:
        return "drop", [
            f"risk_adjusted_strength={result.risk_adjusted_strength:.2f} < "
            f"{DROP_RISK_ADJUSTED_FLOOR} (Far Reach territory)"
        ]

    # 2. only_if_space — marginal
    no_path = (
        not cand.paths_to_advisors
        or all(
            not edge.has_any_edge
            for edge in cand.paths_to_advisors.values()
        )
    )
    no_strong_fit = (
        result.research_fit_score is None
        or result.research_fit_score < STRONG_FIT_FLOOR
    )
    if result.risk_adjusted_strength < ONLY_IF_SPACE_RISK_ADJUSTED_CEIL:
        return "only_if_space", [
            f"risk_adjusted_strength={result.risk_adjusted_strength:.2f} < "
            f"{ONLY_IF_SPACE_RISK_ADJUSTED_CEIL} (Reach territory)"
        ]
    if result.missing_signals >= ONLY_IF_SPACE_MISSING_CEIL:
        return "only_if_space", [
            f"{result.missing_signals} missing signals (≥{ONLY_IF_SPACE_MISSING_CEIL}) "
            f"— too many information gaps to commit"
        ]
    if result.lower_bound < ONLY_IF_SPACE_LOWER_BOUND_CEIL:
        return "only_if_space", [
            f"lower_bound={result.lower_bound:.2f} < "
            f"{ONLY_IF_SPACE_LOWER_BOUND_CEIL} — wide downside if signals are wrong"
        ]
    if no_path and no_strong_fit:
        return "only_if_space", [
            "no verified connection path AND no strong research fit — "
            "thin reasons to apply"
        ]

    # 3. reach — high difficulty / decent profile
    if (
        result.application_strength >= REACH_APPLICATION_STRENGTH_FLOOR
        and result.risk_adjusted_strength < REACH_RISK_ADJUSTED_CEIL
    ):
        reasons.append(
            f"application_strength={result.application_strength:.2f} ≥ "
            f"{REACH_APPLICATION_STRENGTH_FLOOR} but risk-adjusted "
            f"{result.risk_adjusted_strength:.2f} < {REACH_RISK_ADJUSTED_CEIL} "
            f"— wide confidence band"
        )
        return "reach", reasons

    # 4. priority — clean evidence + strong signal
    has_strong_c = result.c_score >= STRONG_C_FLOOR
    has_strong_fit = (
        result.research_fit_score is not None
        and result.research_fit_score >= STRONG_FIT_FLOOR
    )
    if (
        result.risk_adjusted_strength >= PRIORITY_RISK_ADJUSTED_FLOOR
        and result.unsourced_signals == PRIORITY_UNSOURCED_REQUIREMENT
        and result.lower_bound >= PRIORITY_LOWER_BOUND_FLOOR
        and (has_strong_c or has_strong_fit)
    ):
        if has_strong_c:
            reasons.append(f"strong connection (C={result.c_score:.2f})")
        if has_strong_fit:
            reasons.append(
                f"strong research fit ({result.research_fit_score:.2f})"
            )
        reasons.extend([
            f"risk_adjusted_strength={result.risk_adjusted_strength:.2f} ≥ "
            f"{PRIORITY_RISK_ADJUSTED_FLOOR}",
            f"lower_bound={result.lower_bound:.2f} ≥ {PRIORITY_LOWER_BOUND_FLOOR}",
            "0 unsourced claims (clean evidence)",
        ])
        return "priority", reasons

    # 5. target — solid match without all priority criteria
    if (
        result.risk_adjusted_strength >= TARGET_RISK_ADJUSTED_FLOOR
        and result.unsourced_signals <= TARGET_UNSOURCED_CEIL
        and (has_strong_c or has_strong_fit or result.a_score >= 3.3)
    ):
        reasons.append(
            f"risk_adjusted_strength={result.risk_adjusted_strength:.2f} ≥ "
            f"{TARGET_RISK_ADJUSTED_FLOOR}"
        )
        if has_strong_c:
            reasons.append(f"strong connection (C={result.c_score:.2f})")
        elif has_strong_fit:
            reasons.append(
                f"strong research fit ({result.research_fit_score:.2f})"
            )
        elif result.a_score >= 3.3:
            reasons.append(f"strong advisor influence (A={result.a_score:.2f})")
        return "target", reasons

    # Fallback — usually reach territory
    reasons.append(
        f"risk_adjusted_strength={result.risk_adjusted_strength:.2f} "
        f"doesn't meet target/priority floors but isn't drop/only_if_space"
    )
    return "reach", reasons


# ---- Action mapping ------------------------------------------------------

def _recommend_action(
    result: MatchResult, bucket: ApplyBucket,
) -> RecommendedAction:
    """Map (bucket, signal mix) to a recommended action.

    Priority (post-Sprint-2-c5 spec):
      1. drop → skip (never contact)
      2. strong C (verified direct connection) → contact_first regardless
         of bucket (even only_if_space) — a real connection is the
         load-bearing reason to apply
      3. unsourced claims (without strong C) → investigate_evidence
      4. only_if_space (no strong C, no unsourced override) → deprioritize
      5. priority/target with strong fit → contact_first
      6. else → apply
    """
    if bucket == "drop":
        return "skip"

    has_strong_c = result.c_score >= STRONG_C_FLOOR
    has_strong_fit = (
        result.research_fit_score is not None
        and result.research_fit_score >= STRONG_FIT_FLOOR
    )

    # Verified strong connection trumps bucket boundaries — the user
    # should reach out personally even if the rest of the picture is
    # uncertain (only_if_space) or has gaps. The connection itself is
    # already sourced; that's enough to warrant a personal email.
    if has_strong_c:
        return "contact_first"

    # Without strong C: unsourced claims block apply — fix evidence first.
    if result.unsourced_signals >= 1:
        return "investigate_evidence"

    if bucket == "only_if_space":
        return "deprioritize"
    if bucket in ("priority", "target") and has_strong_fit:
        return "contact_first"

    return "apply"


# ---- Outreach angle ------------------------------------------------------

def _outreach_angle(result: MatchResult) -> str | None:
    """Produce a restrained, evidence-backed outreach angle.

    Rules:
      - Only use sourced material (verified path, sourced research_fit
        summary, sourced recruiting note).
      - If no clean evidence: return None (caller's `next_steps` should
        say "Read two recent papers before contacting.")
      - Do not invent personalized claims.
    """
    cand = result.candidate

    # Find a sourced path (small_team_coauthor / co_mentored / shared_grant
    # / working_group / analysis_contact / genealogy)
    sourced_path: str | None = None
    for adv_id, edge in cand.paths_to_advisors.items():
        if not edge.has_any_edge:
            continue
        # Has at least some edge data — assume sourced for outreach purposes
        # (strict-mode evidence enforcement happens elsewhere).
        if edge.small_team_coauthor_5y and edge.small_team_coauthor_5y >= 2:
            sourced_path = (
                f"shared small-team coauthorship with {adv_id} "
                f"({edge.small_team_coauthor_5y} papers)"
            )
            break
        if (
            edge.co_mentored_student_count
            and edge.co_mentored_student_count >= 1
        ):
            sourced_path = (
                f"co-mentored student(s) with {adv_id}"
            )
            break
        if (
            edge.shared_grant_count_5y
            and edge.shared_grant_count_5y >= 1
        ):
            sourced_path = f"shared grant(s) with {adv_id}"
            break
        if edge.same_working_group:
            sourced_path = f"same working group as {adv_id}"
            break
        if edge.analysis_contact_overlap:
            sourced_path = f"analysis-contact overlap with {adv_id}"
            break
        if edge.genealogy_relation == "same_advisor":
            sourced_path = f"academic-sibling relation through {adv_id}"
            break

    if sourced_path:
        return f"Lead with the {sourced_path} as the connection."

    # No connection path — fall back to research_fit summary if it's
    # set AND at least moderately strong.
    if (
        cand.research_fit_summary
        and result.research_fit_score is not None
        and result.research_fit_score >= 0.50
    ):
        return (
            f"Lead with research overlap; do not claim a personal "
            f"connection because no advisor path was verified. Summary: "
            f"{cand.research_fit_summary}"
        )

    return None


# ---- Evidence-to-fix and risk extraction ---------------------------------

def _evidence_to_fix(result: MatchResult) -> list[str]:
    """Prioritize unsourced (high) over missing (medium). One entry per
    signal — each entry is the signal name (caller can pair with the
    repair_hint_for() lookup if it wants the full hint string)."""
    out: list[str] = []
    out.extend(result.unsourced_signal_names)
    out.extend(result.missing_signal_names)
    return out


def _main_risks(result: MatchResult, bucket: ApplyBucket) -> list[str]:
    """Surface the top 1–3 risks the user should know about."""
    risks: list[str] = []
    if result.unsourced_signals > 0:
        risks.append(
            f"{result.unsourced_signals} unsourced claim(s) — "
            f"the band is wider than it looks"
        )
    if result.confidence_band >= 0.6:
        risks.append(
            f"wide confidence band (±{result.confidence_band:.1f}) — "
            f"true strength may be {result.lower_bound:.2f}–"
            f"{result.application_strength + result.confidence_band:.2f}"
        )
    if result.program_difficulty_penalty >= 0.5:
        risks.append(
            f"program difficulty penalty {result.program_difficulty_penalty:.2f} "
            f"(top-tier admit pressure / small cohort / tight funding)"
        )
    if (
        result.research_fit_score is not None
        and result.research_fit_score < 0.50
    ):
        risks.append(
            f"research fit only {result.research_fit_score:.2f} — "
            f"may be a topical stretch"
        )
    return risks[:3]


def _next_steps(
    result: MatchResult,
    bucket: ApplyBucket,
    action: RecommendedAction,
    has_outreach: bool,
) -> list[str]:
    """Concrete actions the user should take next."""
    steps: list[str] = []
    if action == "investigate_evidence":
        steps.append(
            "Fix unsourced claims (highest priority): "
            f"{', '.join(result.unsourced_signal_names[:3])}"
        )
    if action == "contact_first":
        if has_outreach:
            steps.append("Email the PI; mention the sourced connection above.")
        else:
            steps.append("Email the PI; lead with sourced research overlap.")
    if action == "apply":
        steps.append("Submit the application; cite the connection in SOP.")
    if action == "deprioritize":
        steps.append(
            "Hold this candidate; revisit only if portfolio has slack."
        )
    if action == "skip":
        steps.append("Do not apply this cycle.")
    if not has_outreach and action in ("apply", "contact_first"):
        steps.append("Read 2 recent papers before contacting.")
    if result.missing_signals >= 3:
        steps.append(
            f"Optionally tighten {result.missing_signals} missing "
            f"signal(s) for a narrower band."
        )
    return steps


# ---- Public entry points -------------------------------------------------

def recommend_strategy(result: MatchResult) -> StrategyRecommendation:
    """Produce a `StrategyRecommendation` for one match result.

    Pure derivative — does NOT modify the underlying scores. The result
    captures bucket, action, why, risks, evidence-to-fix, outreach
    angle, and next steps.
    """
    bucket, why = _assign_bucket(result)
    action = _recommend_action(result, bucket)
    outreach = _outreach_angle(result)
    risks = _main_risks(result, bucket)
    evidence_fixes = _evidence_to_fix(result)
    next_steps = _next_steps(result, bucket, action, has_outreach=outreach is not None)

    return StrategyRecommendation(
        apply_bucket=bucket,
        recommended_action=action,
        why_this_rank=why,
        main_risks=risks,
        evidence_to_fix=evidence_fixes,
        outreach_angle=outreach,
        next_steps=next_steps,
    )


def summarize_portfolio(results: list[MatchResult]) -> StrategySummary:
    """Roll up per-candidate strategies into a portfolio-level summary."""
    summary = StrategySummary()

    for r in results:
        if r.strategy is None:
            continue
        cid = r.candidate.id
        bucket = r.strategy.apply_bucket
        if bucket == "priority":
            summary.priority_candidates.append(cid)
        elif bucket == "target":
            summary.target_candidates.append(cid)
        elif bucket == "reach":
            summary.reach_candidates.append(cid)
        elif bucket == "only_if_space":
            summary.only_if_space_candidates.append(cid)
        elif bucket == "drop":
            summary.drop_candidates.append(cid)

        # Evidence fix queue: unsourced first (high severity), then missing.
        for sig in r.strategy.evidence_to_fix:
            severity: Literal["high", "medium"] = (
                "high" if sig in r.unsourced_signal_names else "medium"
            )
            summary.evidence_fix_queue.append({
                "candidate_id": cid,
                "signal": sig,
                "severity": severity,
            })

    # Sort fix queue: high severity first, then by candidate.
    summary.evidence_fix_queue.sort(
        key=lambda e: (0 if e["severity"] == "high" else 1, e["candidate_id"]),
    )

    # Portfolio notes — short narrative.
    n_total = len(results)
    n_priority = len(summary.priority_candidates)
    n_target = len(summary.target_candidates)
    n_reach = len(summary.reach_candidates)
    n_space = len(summary.only_if_space_candidates)
    n_drop = len(summary.drop_candidates)
    summary.portfolio_notes.append(
        f"{n_total} candidates: {n_priority} priority · {n_target} target "
        f"· {n_reach} reach · {n_space} only_if_space · {n_drop} drop"
    )
    if n_priority == 0 and n_target == 0:
        summary.portfolio_notes.append(
            "No priority or target candidates — the matcher has no "
            "high-confidence applies. Fix evidence or expand the school list."
        )
    if n_drop > n_total / 3:
        summary.portfolio_notes.append(
            f"{n_drop}/{n_total} drops — many candidates triggered hard "
            f"risks (not_recruiting / unsourced ≥3 / fundamental mismatch)."
        )
    return summary
