"""Streamlit demo. Run: `streamlit run phd_matcher/app.py`"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from phd_matcher.data.loaders import load_advisors
from phd_matcher.matching.ranker import rank_advisors
from phd_matcher.models import StudentProfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


st.set_page_config(page_title="phdtaketaketake", page_icon="🎓", layout="wide")
st.title("🎓 phdtaketaketake")
st.caption(
    "Connection-first PhD advisor matcher · "
    "不靠 h-index，靠 connection 找 PhD 导师"
)


# ---- Sidebar: profile selection ----
with st.sidebar:
    st.header("Profile")

    field = st.selectbox(
        "Field",
        options=["physics", "mse"],
        format_func=lambda f: {"physics": "Physics / HEP", "mse": "Materials Science (MSE)"}[f],
    )

    sample_path = DATA_DIR / "samples" / f"sample_student_{field}.json"
    use_sample = st.toggle("Use sample profile", value=True)

    student: StudentProfile | None = None

    if use_sample and sample_path.exists():
        with open(sample_path) as f:
            sample = json.load(f)
        student = StudentProfile(**sample)
        with st.expander("Sample profile (JSON)", expanded=False):
            st.json(sample)
    else:
        st.info("Upload your own profile JSON.")
        uploaded = st.file_uploader("Profile JSON", type=["json"])
        if uploaded:
            try:
                student = StudentProfile(**json.loads(uploaded.read()))
            except Exception as e:
                st.error(f"Invalid profile: {e}")

    top_k = st.slider("Top K candidates", 1, 30, 10)

    st.divider()
    st.caption(
        "All advisor data in this demo is **synthetic mock**. "
        "Real OpenAlex-backed cache is roadmap."
    )


# ---- Main panel ----
if student is None:
    st.info("👈 Pick a field and (optionally) upload a profile, then click **Find advisors**.")
    st.markdown(
        """
### How it works

This tool ranks PhD advisors for you by **connection strength** — co-author graph,
academic genealogy, joint collaborations between candidate ↔ your current advisor.
Not h-index, not paper count.

All four dimensions on a 4.0 scale (matching GPA):

- **Connection (C)** — paths between candidate and your current advisor(s)
- **Publication (P)** — journal tier × author position decay; big-collab papers handled
- **Experience (E)** — lab × duration × output (output-weighted)
- **GPA (G)** — direct, with multi-system normalization

Weights are tier-adaptive — top-10 schools weight Connection more, top-60+ weight GPA more.

See [docs/scoring.md](https://github.com/powerofjinbo/phdtaketaketake/blob/main/docs/scoring.md) for full formulas.
"""
    )
    st.stop()


go = st.button("Find advisors", type="primary", use_container_width=True)
if not go:
    st.markdown("Profile loaded. Click **Find advisors** above to rank candidates.")
    st.stop()


with st.spinner("Ranking candidates..."):
    candidates = load_advisors(DATA_DIR, field)
    if not candidates:
        st.error(f"No candidate advisors found for field={field}. Build the cache first.")
        st.stop()
    results = rank_advisors(student, candidates, top_k=top_k)


st.success(f"Ranked {len(results)} of {len(candidates)} candidates")

for i, r in enumerate(results, 1):
    with st.container(border=True):
        top_cols = st.columns([4, 1, 1, 1])
        areas = " · ".join(r.candidate.research_areas[:3]) if r.candidate.research_areas else ""
        top_cols[0].markdown(
            f"**#{i} · {r.candidate.name}** — {r.candidate.institution}  \n"
            f"<span style='color:#888'>{r.candidate.school_tier} · {areas}</span>",
            unsafe_allow_html=True,
        )
        top_cols[1].metric("Match", f"{r.match_score:.2f}")
        top_cols[2].metric(
            "Admit", f"{r.admit_likelihood:.2f}",
            delta=f"±{r.confidence_band:.1f}",
            delta_color="off",
        )
        top_cols[3].markdown(f"### `{r.likelihood_label}`")

        with st.expander("Score breakdown · why matched"):
            bcols = st.columns(4)
            bcols[0].metric("Connection (C)", f"{r.c_score:.2f}")
            bcols[1].metric("Publication (P)", f"{r.p_score:.2f}")
            bcols[2].metric("Experience (E)", f"{r.e_score:.2f}")
            bcols[3].metric("GPA (G)", f"{r.g_score:.2f}")

            st.markdown(f"**Why matched:** {r.explanation}")

            if r.candidate.recent_phd_count is not None:
                st.markdown(
                    f"**PI signal:** `{r.candidate.pi_signal}` · "
                    f"{r.candidate.recent_phd_count} new PhDs in last 3 years"
                )

st.caption(
    "⚠️ Estimates based on public academic-network signals only. "
    "Does not include SOP / recommendation letters / interview factors."
)
