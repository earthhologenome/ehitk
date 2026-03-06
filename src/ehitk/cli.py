from __future__ import annotations

from pathlib import Path

import typer

from ehitk.mags.commands import app as mags_app
from ehitk.metagenomes.commands import app as metagenomes_app
from ehitk.query import resolve_catalog_path

app = typer.Typer(
    help="Earth Hologenome Initiative Toolkit",
    no_args_is_help=True,
)

app.add_typer(metagenomes_app, name="metagenomes")
app.add_typer(mags_app, name="mags")


@app.callback()
def main(
    ctx: typer.Context,
    catalog: Path | None = typer.Option(
        None,
        "--catalog",
        help="Path to an alternate SQLite catalog. Defaults to the bundled catalog.",
    ),
) -> None:
    catalog_path = resolve_catalog_path(catalog)
    if not catalog_path.exists():
        raise typer.BadParameter(
            f"Catalog does not exist: {catalog_path}",
            param_hint="--catalog",
        )

    ctx.obj = {"catalog_path": catalog_path}


if __name__ == "__main__":
    app()
