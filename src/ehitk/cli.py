from __future__ import annotations

from pathlib import Path

import typer

from ehitk import __version__
from ehitk.mags.commands import app as mags_app
from ehitk.metagenomes.commands import app as metagenomes_app
from ehitk.specimens.commands import app as specimens_app
from ehitk.query import resolve_catalog_path

app = typer.Typer(
    help="Earth Hologenome Initiative Toolkit",
    no_args_is_help=True,
    add_completion=False,
)

app.add_typer(metagenomes_app, name="metagenomes")
app.add_typer(mags_app, name="mags")
app.add_typer(specimens_app, name="specimens")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show EHItk version and exit.",
    ),
    db: Path | None = typer.Option(
        None,
        "--db",
        help="Path to an alternate SQLite database. Defaults to the bundled database.",
    ),
) -> None:
    catalog_path = resolve_catalog_path(db)
    if not catalog_path.exists():
        raise typer.BadParameter(
            f"Database does not exist: {catalog_path}",
            param_hint="--db",
        )

    ctx.obj = {"catalog_path": catalog_path}


if __name__ == "__main__":
    app()
