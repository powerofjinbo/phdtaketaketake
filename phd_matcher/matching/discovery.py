"""Per-field candidate discovery plan generator (Sprint-2-c4).

Given a target field and a list of schools, produces a structured search
plan: per-field query recipes (Google Scholar / DBLP / INSPIRE / PubMed
/ etc.), required source list, and exclusion rules.

The agent uses the plan as a checklist when gathering candidate PIs —
ensures consistent coverage across fields and prevents the "I forgot
to search OpenReview for ML papers" failure mode.

> **Thresholds and recipes are v2 defaults; recalibrate after running
> real portfolios.**
"""

from __future__ import annotations

from typing import TypedDict

from phd_matcher.models import FieldProfile


class QueryRecipe(TypedDict):
    """A single search query the agent should run."""

    engine: str
    query: str
    purpose: str


# Per-field query templates. Format placeholders: {school}, {keywords}.
# Each entry is (engine_id, query_template, purpose_template).
_FIELD_QUERIES: dict[str, list[tuple[str, str, str]]] = {
    "physics": [
        ("google_scholar",
         '"{school}" "{keywords}" site:scholar.google.com',
         "Find scholars at {school} working on {keywords}"),
        ("inspire",
         '{keywords} site:inspirehep.net',
         "HEP-specific paper / institution search"),
        ("arxiv",
         '{keywords} {school} site:arxiv.org',
         "Recent preprints"),
        ("faculty_page",
         "{school} physics department faculty {keywords}",
         "Department directory"),
        ("atlas_glance",
         '{keywords} site:atlas-glance.cern.ch',
         "ATLAS / CMS subgroup membership and conveners (HEP-specific)"),
    ],
    "cs": [
        ("dblp",
         '{school} {keywords} site:dblp.org',
         "CS publication graph"),
        ("openreview",
         '"{keywords}" "{school}" site:openreview.net',
         "OpenReview profiles + reviewer history (NeurIPS/ICML/ICLR)"),
        ("semantic_scholar",
         '"{keywords}" "{school}" site:semanticscholar.org',
         "Citation graph + author profiles"),
        ("csrankings",
         '{keywords} site:csrankings.org',
         "Subfield-specific faculty ranking"),
        ("faculty_page",
         "{school} CS OR CSAIL OR EECS faculty {keywords}",
         "Department directory"),
        ("arxiv",
         '{keywords} {school} site:arxiv.org/abs/cs',
         "cs.* preprints"),
    ],
    "biology": [
        ("pubmed",
         '{keywords} {school}[affiliation] site:pubmed.ncbi.nlm.nih.gov',
         "Biomedical literature with affiliation filter"),
        ("biorxiv",
         '{keywords} {school} site:biorxiv.org',
         "Recent preprints"),
        ("nih_reporter",
         '{keywords} {school} site:reporter.nih.gov',
         "Active R01 / NIH grants"),
        ("hhmi",
         '{school} HHMI investigator site:hhmi.org',
         "HHMI directory"),
        ("faculty_page",
         "{school} biology OR molecular biology OR genetics OR neuroscience faculty {keywords}",
         "Department directory"),
        ("europe_pmc",
         '{keywords} {school} site:europepmc.org',
         "European biomedical literature mirror"),
    ],
    "chemistry": [
        ("google_scholar",
         '"{school}" "{keywords}" chemistry site:scholar.google.com',
         "Scholar with chemistry filter"),
        ("acs",
         '{keywords} {school} site:pubs.acs.org',
         "ACS publications (JACS, JOC, Angew. Chem., etc.)"),
        ("rsc",
         '{keywords} {school} site:pubs.rsc.org',
         "RSC publications"),
        ("nih_reporter",
         '{keywords} {school} site:reporter.nih.gov',
         "Chem-bio grant overlap"),
        ("faculty_page",
         "{school} chemistry department faculty {keywords}",
         "Department directory"),
    ],
    "mse": [
        ("google_scholar",
         '"{school}" "{keywords}" materials science site:scholar.google.com',
         "Scholar with MSE filter"),
        ("nature_materials",
         '{keywords} site:nature.com',
         "Nature Materials, Nature Nanotechnology, etc."),
        ("nsf_award",
         '{keywords} {school} site:nsf.gov/awardsearch',
         "NSF MSE grants"),
        ("faculty_page",
         "{school} materials science engineering faculty {keywords}",
         "Department directory"),
        ("doe",
         '{keywords} {school} site:energy.gov OR site:science.energy.gov',
         "DOE Office of Science (BES, etc.)"),
    ],
    "math": [
        ("arxiv",
         '{keywords} {school} site:arxiv.org/abs/math',
         "Math arXiv (math.AG / math.NT / math.GT / etc.)"),
        ("math_genealogy",
         '{school} {keywords} site:genealogy.math.ndsu.nodak.edu',
         "Mathematics Genealogy Project (advisor lineage)"),
        ("mathscinet",
         '{keywords} {school}',
         "MathSciNet (institutional access required)"),
        ("zbmath",
         '{keywords} {school} site:zbmath.org',
         "zbMATH (open-access math review)"),
        ("faculty_page",
         "{school} mathematics department faculty {keywords}",
         "Department directory"),
    ],
}

# Universal exclusion rules — applied across fields. Each rule is a
# concrete check the agent should perform when filtering candidates.
EXCLUSION_RULES: list[str] = [
    "no matching paper in last 3 years (the candidate has pivoted away or stopped publishing)",
    "emeritus / dean / chair-only / full admin role (not actively running a lab)",
    "fully pivoted to industry (no current academic affiliation)",
    "no PhD students currently in the lab (check the 'people' / 'group' page)",
    "explicitly 'not recruiting' on the lab / faculty page",
    "lab page returned 404 / no group page exists (cannot verify recruiting)",
]


def _generic_field_queries(
    field_id: str, school: str, keywords: str,
) -> list[QueryRecipe]:
    """Fallback for fields without a per-field template — generic
    Google Scholar + faculty-page recipes."""
    return [
        QueryRecipe(
            engine="google_scholar",
            query=f'"{school}" "{keywords}" site:scholar.google.com',
            purpose=f"Find {field_id} scholars at {school} working on {keywords}",
        ),
        QueryRecipe(
            engine="faculty_page",
            query=f"{school} {field_id} department faculty {keywords}",
            purpose="Department directory",
        ),
    ]


def build_discovery_plan(
    field: str,
    schools: list[str],
    keywords: str,
    field_profile: FieldProfile | None = None,
) -> dict:
    """Build a per-school discovery plan for the given field + keywords.

    `field_profile`, when provided, supplies the canonical primary
    databases, ranking source URL, and field caveats. Without a profile
    the script falls back to generic Scholar + faculty-page queries.
    """
    field_id = field_profile.id if field_profile is not None else field

    queries: list[QueryRecipe] = []
    for school in schools:
        templates = _FIELD_QUERIES.get(field_id)
        if templates is None:
            queries.extend(_generic_field_queries(field_id, school, keywords))
            continue
        for engine, q_tmpl, p_tmpl in templates:
            queries.append(QueryRecipe(
                engine=engine,
                query=q_tmpl.format(school=school, keywords=keywords),
                purpose=p_tmpl.format(school=school, keywords=keywords),
            ))

    primary_databases = (
        list(field_profile.primary_databases)
        if field_profile is not None
        else []
    )
    ranking_source_url = (
        field_profile.ranking_source_url_template
        if field_profile is not None
        else None
    )
    caveats = (
        list(field_profile.caveats)
        if field_profile is not None
        else []
    )

    return {
        "field_profile_id": field_id,
        "field_display_name": (
            field_profile.display_name if field_profile is not None else field
        ),
        "schools": schools,
        "keywords": keywords,
        "queries": queries,
        "primary_databases": primary_databases,
        "ranking_source_url": ranking_source_url,
        "field_caveats": caveats,
        "exclusion_rules": EXCLUSION_RULES,
        "field_profile_loaded": field_profile is not None,
    }
