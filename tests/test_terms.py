from __future__ import annotations

from rich.console import Console

from ehitk import terms


def test_terms_prompt_renders_boxed_message(monkeypatch) -> None:
    console = Console(record=True, width=90)
    monkeypatch.setattr(terms.Confirm, "ask", lambda *args, **kwargs: True)

    terms.ensure_terms_accepted(console, accept_terms=False)

    rendered = console.export_text()
    normalized_rendered = " ".join(rendered.split())
    assert "Data Usage Terms" in rendered
    assert "Under our Terms of Use" in rendered
    assert "ehi@sund.ku.dk" in rendered
    assert "--accept-terms" in normalized_rendered
    assert "suppress this" in normalized_rendered
    assert "prompt." in normalized_rendered
