# Enrich corpus subfolders with semantic INDEX.md files derived from the knowledge graph
from __future__ import annotations
from pathlib import Path
import datetime
import networkx as nx


def _group_nodes_by_folder(G: nx.Graph, corpus_path: Path) -> dict[Path, list[str]]:
    """Group node IDs by their immediate parent folder, excluding graphify-out/.

    Folder keys are always relative to corpus_path. Absolute source_file paths
    that fall under corpus_path are made relative; others are used as-is.
    """
    corpus_path = Path(corpus_path).resolve()
    groups: dict[Path, list[str]] = {}
    for node_id, data in G.nodes(data=True):
        src = data.get("source_file", "")
        if not src:
            continue
        p = Path(src)
        if not p.parts:
            continue
        # Normalise absolute paths to corpus-relative
        if p.is_absolute():
            try:
                p = p.relative_to(corpus_path)
            except ValueError:
                pass  # outside corpus — use as-is
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
    """Return edges from nodes in `folder` that cross into other folders.

    Each unique (source, target) pair is emitted at most once.
    """
    node_set = set(node_ids)
    seen: set[frozenset] = set()
    results = []
    for nid in node_ids:
        for neighbor in G.neighbors(nid):
            if neighbor in node_set:
                continue
            pair = frozenset((nid, neighbor))
            if pair in seen:
                continue
            seen.add(pair)
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


def _write_subfolder_index(
    folder: Path,
    data: dict,
    dry_run: bool = False,
) -> str | None:
    """Write enriched INDEX.md for a subfolder.

    Returns the content string when dry_run=True (no file written).
    Returns None after writing the file when dry_run=False.
    """
    folder_path = Path(data["folder"])
    now = datetime.date.today().isoformat()
    nodes = data["nodes"]
    cross_edges = data.get("cross_edges", [])
    summary = data.get("summary", "")

    docs = sorted({Path(n["source_file"]).name for n in nodes if n.get("source_file")})
    entities = [n["label"] for n in nodes if n.get("label")]
    # Quote each entity so the YAML list is valid when parsed programmatically
    entity_list = ", ".join(f'"{e}"' for e in entities[:10])

    connected: dict[str, str] = {}
    for e in cross_edges:
        tf = str(e["target_folder"])
        if tf not in connected:
            connected[tf] = e["relation"]

    lines = [
        "---",
        f'folder: "{folder_path}"',
        f'entities: [{entity_list}]',
        f'last_enriched: "{now}"',
        "---",
        "",
        f"# {folder_path.name.replace('-', ' ').replace('_', ' ').title()}",
        "",
    ]

    if summary:
        lines += ["## What's here", "", summary, ""]

    lines += ["## Documents", ""]
    for doc in docs:
        lines.append(f"- {doc}")
    lines.append("")

    if entities:
        lines += ["## Key entities", ""]
        for entity in entities[:20]:
            lines.append(f"- {entity}")
        lines.append("")

    if connected:
        lines += ["## Connected folders", ""]
        for tf, relation in connected.items():
            lines.append(f"- [[{tf}]] — `{relation}`")
        lines.append("")

    content = "\n".join(lines)

    if dry_run:
        return content

    index_path = folder / "INDEX.md"
    index_path.write_text(content, encoding="utf-8")
    return None


def _write_master_index(
    corpus_path: Path,
    folder_summaries: dict[Path, dict],
    dry_run: bool = False,
) -> str | None:
    """Write master INDEX.md at corpus root.

    Returns the content string when dry_run=True (no file written).
    Returns None after writing the file when dry_run=False.
    """
    now = datetime.date.today().isoformat()

    lines = [
        "---",
        f'last_enriched: "{now}"',
        f"total_folders: {len(folder_summaries)}",
        "---",
        "",
        "# Master Index",
        "",
        "## Folder map",
        "",
        "| Folder | What's there | Key entities |",
        "| --- | --- | --- |",
    ]

    for folder, data in sorted(folder_summaries.items()):
        summary = data.get("summary", "")
        entities = ", ".join(data.get("entities", [])[:5])
        lines.append(f"| {folder} | {summary} | {entities} |")

    lines += ["", "## Entity → Folder map", ""]

    entity_map: dict[str, list[str]] = {}
    for folder, data in folder_summaries.items():
        for entity in data.get("entities", []):
            entity_map.setdefault(entity, []).append(str(folder))

    lines += ["| Entity | Folder(s) |", "| --- | --- |"]
    for entity, folders in sorted(entity_map.items()):
        lines.append(f"| {entity} | {', '.join(folders)} |")

    lines.append("")
    content = "\n".join(lines)

    if dry_run:
        return content

    index_path = Path(corpus_path) / "INDEX.md"
    index_path.write_text(content, encoding="utf-8")
    return None
