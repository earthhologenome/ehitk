from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
import typer

TERMS_MESSAGE = (
    "Under our Terms of Use, researchers seeking to use EHI datasets to address "
    "ecological or evolutionary questions involving animal hosts or associated "
    "microbial communities should contact ehi@sund.ku.dk. This helps avoid "
    "duplication of ongoing analyses and fosters collaborative research. The EHI "
    "management team will facilitate communication between interested users and "
    "the researchers who generated the data in order to coordinate research "
    "efforts, ensure appropriate recognition of the substantial work involved in "
    "sample collection, data generation, and initial analyses, and promote the "
    "collaborative use of these datasets.\n\n"
    "If you agree, you may use the --accept-terms flag in the future to suppress "
    "this prompt."
)


def ensure_terms_accepted(console: Console, *, accept_terms: bool) -> None:
    if accept_terms:
        return

    console.print(
        Panel(
            TERMS_MESSAGE,
            title="Data Usage Terms",
            border_style="yellow",
        )
    )
    try:
        accepted = Confirm.ask(
            "Do you confirm that you have read and accept these terms?",
            console=console,
            default=False,
        )
    except EOFError:
        console.print(
            "No interactive input is available. Re-run this command with "
            "--accept-terms if you have already read and accepted these terms."
        )
        raise typer.Exit(code=1) from None
    if not accepted:
        raise typer.Exit(code=1)
