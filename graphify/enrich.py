from __future__ import annotations
from pathlib import Path
import networkx as nx


def _group_nodes_by_folder(G: nx.Graph, corpus_path: Path) -> dict[Path, list[str]]:
    """Group node IDs by their immediate parent folder, excluding graphify-out/."""
    groups: dict[Path, list[str]] = {}
    for node_id, data in G.nodes(data=True):
        src = data.get("source_file", "")
        if not src:
            continue
        p = Path(src)
        if not p.parts:
            continue
        folder = p.parent
        if not folder.parts:
            continue
        if "graphify-out" in folder.parts:
            continue
        groups.setdefault(folder, []).append(node_id)
    return groups
