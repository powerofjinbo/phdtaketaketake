"""Build advisors cache from OpenAlex (WIP).

The current repo uses bundled mock advisor data
(`data/advisors/mock_advisors.json`). This script will eventually replace
that with real OpenAlex-backed records.

Planned flow:
  1. Read schools list from data/schools/us_news_rank.yaml
  2. For each (school, field), query OpenAlex for active PIs
  3. Pull recent papers (5y), co-author graph, institutional affiliation
  4. Build paths_to_advisors via genealogy + co-author + collaboration matching
  5. Optionally scrape lab pages with LLM to estimate pi_signal (recent PhD count)
  6. Write to data/advisors/<field>_cache.json (or .sqlite)

Run: python scripts/build_advisors_cache.py --field physics --limit 100
"""

import click


@click.command()
@click.option("--field", type=click.Choice(["physics", "mse"]), required=True)
@click.option("--limit", type=int, default=None, help="Cap number of PIs (for dev)")
def build(field: str, limit):
    raise NotImplementedError(
        "Advisor cache builder is not yet implemented. "
        "Use bundled mock data: data/advisors/mock_advisors.json"
    )


if __name__ == "__main__":
    build()
