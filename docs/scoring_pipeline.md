# Scoring pipeline diagram

The matcher's deterministic scoring is a **5-layered pipeline**, each
layer composing the layers below. Inputs are filled by the agent
(directly or via `phdtaketaketake-collect-evidence` automation); outputs
are pure functions of inputs — no LLM-in-the-loop scoring.

```mermaid
flowchart TD
    %% =========================================================
    %% Inputs
    %% =========================================================
    subgraph Inputs ["Inputs (agent-filled, evidence-backed)"]
        SP[StudentProfile<br/>field · GPA · advisors · papers · experiences]
        CA[CandidateAdvisor<br/>school_tier · paths_to_advisors · recent_papers<br/>· research_areas · A signals · ResearchFit]
        OS[OpportunitySignal<br/>pi_signal · funding · capacity · accessibility]
        PP[ProgramProfile<br/>cohort · admission · funding · faculty count]
        FP[FieldProfile YAML<br/>per-discipline calibration]
    end

    %% =========================================================
    %% Layer 1 — CAPEG match_score
    %% =========================================================
    subgraph L1 ["Layer 1 · CAPEG match_score"]
        C[Connection C<br/>v2: strongest + 0.10·second<br/>× recency multiplier]
        A[Advisor influence A<br/>0.40·influence + 0.30·elite + 0.30·placement<br/>reputation only post-#6a]
        P[Publication P<br/>tier × position × status × recency<br/>+ contribution_bonus<br/>+ big-collab guardrail]
        E[Experience E<br/>0.20·lab + 0.30·duration + 0.50·output]
        G[GPA G<br/>4.0 / 4.3 / 4.5 / 100 / UK normalized]
        MS[match_score<br/>= w_C·C + w_A·A + w_P·P + w_E·E + w_G·G<br/>tier-adaptive weights]
    end

    SP --> C
    CA --> C
    CA --> A
    SP --> P
    FP --> P
    SP --> E
    SP --> G
    C --> MS
    A --> MS
    P --> MS
    E --> MS
    G --> MS

    %% =========================================================
    %% Layer 2 — application_strength
    %% =========================================================
    subgraph L2 ["Layer 2 · application_strength"]
        OA[opportunity_adj<br/>O ≥ 0.70 → +0.2<br/>O ≥ 0.50 →  0.0<br/>O ≥ 0.30 → −0.2<br/>O <  0.30 → −0.4<br/>not_recruiting → 0]
        AS[application_strength<br/>= clip\(match + opportunity_adj, 0, 4.0\)]
    end

    OS --> OA
    MS --> AS
    OA --> AS

    %% =========================================================
    %% Layer 3 — risk-adjusted
    %% =========================================================
    subgraph L3 ["Layer 3 · risk-adjusted"]
        CB[confidence_band<br/>0 / 1-2 / 3-4 / 5+ unverified<br/>→ ±0.2 / 0.4 / 0.6 / 0.8]
        RA[risk_adjusted_strength<br/>= application_strength − band/2]
        LB[lower_bound<br/>= application_strength − band]
    end

    AS --> RA
    AS --> LB
    CB --> RA
    CB --> LB

    %% =========================================================
    %% Layer 4 — difficulty-adjusted (primary sort key)
    %% =========================================================
    subgraph L4 ["Layer 4 · difficulty-adjusted (PRIMARY SORT KEY)"]
        PD[program_difficulty_penalty<br/>school_tier_factor + cohort + admission<br/>+ funding + area + intl friendliness<br/>clipped 0 – 0.8]
        DA[difficulty_adjusted_strength<br/>= max\(0, risk_adjusted − program_penalty\)]
        LBL[strength_label<br/>≥3.5 Safe · ≥3.0 Match · ≥2.5 Target<br/>≥2.0 Reach · <2.0 Far Reach]
    end

    PP --> PD
    CA --> PD
    RA --> DA
    PD --> DA
    DA --> LBL

    %% =========================================================
    %% Layer 5 — strategy bucket
    %% =========================================================
    subgraph L5 ["Layer 5 · strategy bucket (decision memo)"]
        RF[research_fit_score<br/>0.30·topic + 0.20·method + 0.15·system<br/>+ 0.15·temporal + 0.10·grant + 0.10·background<br/>tie-breaker only]
        SB[apply_bucket<br/>drop → only_if_space → reach<br/>→ target → priority<br/>first match wins]
        AC[recommended_action<br/>skip · contact_first · investigate_evidence<br/>· deprioritize · apply]
        OUT[outreach_angle + main_risks<br/>+ evidence_to_fix + next_steps]
    end

    CA --> RF
    DA --> SB
    RF --> SB
    SB --> AC
    SB --> OUT

    %% =========================================================
    %% Sort key
    %% =========================================================
    DA -.primary sort key.-> SORT[rank_advisors output<br/>tie-break ladder:<br/>diff_adj > risk_adj > research_fit<br/>> direction_relevance > app_strength > lower_bound]
    RA -.tie-break.-> SORT
    RF -.tie-break.-> SORT

    classDef inputs fill:#eef,stroke:#558
    classDef capeg fill:#efe,stroke:#585
    classDef adj fill:#fee,stroke:#855
    classDef strategy fill:#fef,stroke:#858
    class SP,CA,OS,PP,FP inputs
    class C,A,P,E,G,MS capeg
    class OA,AS,CB,RA,LB,PD,DA,LBL adj
    class RF,SB,AC,OUT,SORT strategy
```

## Layer-by-layer

### Layer 1 — CAPEG match_score
Five pillars on a 4.0 scale, tier-adaptively weighted by school
competitiveness. **Connection-first invariant**: `w_C > w_A` in every
tier (pinned by `test_a_does_not_outrank_c_in_any_tier`). Per-pillar
formulas live in `phd_matcher.scoring.{connection,advisor,pub,
experience,gpa}` modules.

### Layer 2 — application_strength
Adds the **time-sensitive admit-cycle availability** signal via
`opportunity_adj`, derived from `OpportunitySignal` (recruiting
health · funding · capacity · accessibility). `not_recruiting` is a
hard short-circuit: `application_strength = 0`.

For pure-legacy candidates without an `opportunity_signal`, the
matcher falls back to the v1 PI_ADJ table verbatim — preserving
exact old behavior. See `references/opportunity.md`.

### Layer 3 — risk-adjusted
The **band** is driven by `unverified_signals` count. Wider band →
larger discount via `band/2`. **The agent literally cannot get a top
rank by writing nice numbers without sources** — the band would
widen and `risk_adjusted_strength` would drop.

`lower_bound = application_strength − band` is shown alongside as a
"conservative reading at the wide edge of uncertainty".

### Layer 4 — difficulty-adjusted (PRIMARY SORT KEY)
`program_difficulty_penalty` (0–0.8) refines what the v1 `tier_adj`
did. It composes 6 components: school-tier admit-rate factor (the
biggest contribution), cohort size, admission model (direct admit vs
rotation), funding structure, faculty count in subfield,
international friendliness.

The 5-tier `strength_label` (Safe / Match / Target / Reach / Far Reach)
is applied to `difficulty_adjusted_strength`, **not** raw
`application_strength` — so a perfect 4.0 candidate at a tiny
direct-admit small-subfield top-10 program can legitimately show as
`Match` rather than `Safe`. See `references/program_profile.md`.

### Layer 5 — strategy bucket
The **decision memo**. Bucket precedence is hard-risk-first:

```
drop → only_if_space → reach → target → priority
```

First match wins. Hard risks (not_recruiting, ≥3 unsourced claims,
research_fit < 0.20, risk_adj < 1.50) override high nominal scores —
the strategy report is about how the user should triage their own
application time, **not** about admit odds.

Strong-C-overrides-bucket: a verified `c_score ≥ 3.7` upgrades
`recommended_action` to `contact_first` even from `only_if_space`.

`research_fit_score` enters here only as a sort tie-breaker (rank #3
in the descending sort key ladder, never overrides
`difficulty_adjusted` or `risk_adjusted`). See
`references/strategy.md` and `references/research_fit_v2.md`.

## Hard architectural invariants

These are pinned by the test suite (each invariant has at least one
named test enforcing it; running `python -m pytest -q` from the repo
root exercises the full set):

1. **Strategy is purely derivative.** The strategy layer never modifies
   any scoring field. `test_strategy_does_not_change_scores` pins this.
2. **Source adapters never compute scores.** They produce evidence + raw
   facts only. `test_collect_evidence_does_not_modify_scores` pins this.
3. **Connection-first.** `w_C > w_A` in every tier.
4. **Strong C beats strong A or O alone.** A verified path outranks a
   no-path candidate even when A and O are maxed.
5. **Research fit is a tie-breaker only.** Cannot move
   `risk_adjusted_strength` or `difficulty_adjusted_strength`. Null fits
   are excluded from coverage so a missing fit cannot widen the band.
6. **Strict mode rejects unsourced claims.** Missing data is allowed
   (honest "I couldn't verify" state); claims-without-proof are not.

## Calibration status

> Every threshold in the pipeline (CAPEG weights, recency multipliers,
> program difficulty components, strategy bucket cutoffs, opportunity
> adjustment ladder) is a **v1 / v2 default** — expert-designed
> heuristic, not empirically calibrated against admission outcomes.
> Recalibrate against real portfolios over time. The output is a
> 4.0-scale relative-fit / application-strength index, **not** an
> admission probability. See `docs/DESIGN.md` §11.
