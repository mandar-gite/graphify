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


def _cross_folder_edges(
    folder: Path,
    node_ids: list[str],
    G: nx.Graph,
) -> list[dict]:
    """Return edges from nodes in `folder` that cross into other folders."""
    node_set = set(node_ids)
    results = []
    for nid in node_ids:
        for neighbor in G.neighbors(nid):
            if neighbor in node_set:
                continue
            n_src = G.nodes[neighbor].get("source_file", "")
            if not n_src:
                continue
            target_folder = Path(n_src).parent
            if not target_folder.parts:
                continue
            edata = G.edges[nid, neighbor]
            results.append({
                "source_node": nid,
                "target_node": neighbor,
                "target_folder": target_folder,
                "relation": edata.get("relation", ""),
                "confidence": edata.get("confidence", "EXTRACTED"),
            })
    return results
