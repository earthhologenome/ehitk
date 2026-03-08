"""Render a simple EHItk architecture diagram with mingrammer/diagrams.

Requirements:
    pip install diagrams
    Graphviz `dot` executable available on PATH

Usage:
    python3 docs/ehitk_architecture.py

Output:
    docs/ehitk_architecture.png
"""

from __future__ import annotations

from pathlib import Path
from shutil import which

OUTPUT_STEM = Path(__file__).with_name("ehitk_architecture")


def main() -> None:
    try:
        from diagrams import Cluster, Diagram, Edge
        from diagrams.onprem.client import User
        from diagrams.onprem.network import Internet
        from diagrams.programming.flowchart import Database, Document, InputOutput
        from diagrams.programming.language import Python
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing diagram dependencies. Install `diagrams` separately with "
            "`pip install diagrams` and rerun."
        ) from exc

    if which("dot") is None:
        raise SystemExit(
            "Graphviz `dot` was not found on PATH. Install Graphviz and rerun "
            "`python3 docs/ehitk_architecture.py`."
        )

    graph_attr = {
        "pad": "0.35",
        "nodesep": "0.9",
        "ranksep": "1.0",
        "splines": "ortho",
    }
    node_attr = {
        "fontsize": "12",
    }

    with Diagram(
        "EHItk Architecture",
        filename=str(OUTPUT_STEM),
        outformat="png",
        show=False,
        direction="LR",
        graph_attr=graph_attr,
        node_attr=node_attr,
    ):
        user = User("Researcher")
        catalog = Database("SQLite catalog\nehitk.sqlite")
        results = InputOutput("Results\nterminal + CSV/TSV")
        manifest = Document("manifest.jsonl\ndownload log")
        archives = Internet("Remote archives\nFTP + HTTP(S)")

        with Cluster("Earth Hologenome Initiative ToolKit"):
            cli = Python("ehitk CLI\nspecimens | metagenomes | mags")
            metadata = Python("Metadata layer\nquery + stats")
            fetch = Python("Download layer\nfetch")

            cli >> Edge(label="query / stats") >> metadata
            cli >> Edge(label="fetch") >> fetch

        user >> Edge(label="runs") >> cli
        metadata >> Edge(label="reads metadata") >> catalog
        metadata >> Edge(label="shows or exports") >> results
        fetch >> Edge(label="resolves URLs") >> catalog
        fetch >> Edge(label="downloads files") >> archives
        fetch >> Edge(label="records status") >> manifest


if __name__ == "__main__":
    main()
