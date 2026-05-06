"""CLI: `phd-matcher match --profile foo.json --field physics --top-k 10`"""

from __future__ import annotations

import json
from pathlib import Path

import click

from phd_matcher.data.loaders import load_advisors
from phd_matcher.matching.ranker import rank_advisors
from phd_matcher.models import StudentProfile


@click.group()
@click.version_option()
def cli():
    """phdtaketaketake — connection-first PhD advisor matcher."""


@cli.command()
@click.option(
    "--profile",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to student profile JSON",
)
@click.option(
    "--field",
    type=click.Choice(["physics", "mse"]),
    required=True,
    help="Target field",
)
@click.option("--top-k", type=int, default=20, help="Number of candidates to return")
@click.option(
    "--data-dir",
    type=click.Path(exists=True, file_okay=False),
    default=str(Path(__file__).resolve().parents[1] / "data"),
    help="Path to bundled data directory",
)
def match(profile: str, field: str, top_k: int, data_dir: str):
    """Run advisor matching for a student profile."""
    with open(profile) as f:
        student = StudentProfile(**json.load(f))

    candidates = load_advisors(data_dir, field)
    if not candidates:
        click.echo(f"No candidates loaded for field={field}.", err=True)
        return

    results = rank_advisors(student, candidates, top_k=top_k)

    click.echo()
    click.echo(f"Top {len(results)} of {len(candidates)} candidates ({field}):")
    click.echo()
    click.echo(
        f"{'#':<3} {'Advisor':<28} {'Institution':<26} {'C':>5} {'P':>5} {'E':>5} {'G':>5} {'Match':>7} {'Admit':>7}  Label"
    )
    click.echo("-" * 110)
    for i, r in enumerate(results, 1):
        click.echo(
            f"{i:<3} {r.candidate.name[:26]:<28} {r.candidate.institution[:24]:<26} "
            f"{r.c_score:>5.2f} {r.p_score:>5.2f} {r.e_score:>5.2f} {r.g_score:>5.2f} "
            f"{r.match_score:>7.2f} {r.admit_likelihood:>7.2f}  {r.likelihood_label}"
        )
    click.echo()


if __name__ == "__main__":
    cli()
