import networkx as nx
from pathlib import Path
from graphify.enrich import _group_nodes_by_folder


def _make_graph():
    G = nx.Graph()
    G.add_node("a", label="DocA", source_file="clients/bridgestone/brief.md", file_type="document")
    G.add_node("b", label="DocB", source_file="clients/bridgestone/contract.md", file_type="document")
    G.add_node("c", label="DocC", source_file="finance/invoice.md", file_type="document")
    G.add_node("d", label="DocD", source_file="graphify-out/graph.json", file_type="code")
    return G


def test_group_nodes_by_folder_basic():
    G = _make_graph()
    groups = _group_nodes_by_folder(G, Path("."))
    assert Path("clients/bridgestone") in groups
    assert Path("finance") in groups
    assert len(groups[Path("clients/bridgestone")]) == 2
    assert len(groups[Path("finance")]) == 1


def test_group_nodes_excludes_graphify_out():
    G = _make_graph()
    groups = _group_nodes_by_folder(G, Path("."))
    for folder in groups:
        assert "graphify-out" not in str(folder)


def test_group_nodes_excludes_nodes_without_source_file():
    G = nx.Graph()
    G.add_node("x", label="X", source_file="", file_type="document")
    G.add_node("y", label="Y", file_type="document")
    groups = _group_nodes_by_folder(G, Path("."))
    assert len(groups) == 0


# ---------------------------------------------------------------------------
# Task 2: _cross_folder_edges
# ---------------------------------------------------------------------------
from graphify.enrich import _cross_folder_edges


def test_cross_folder_edges_finds_edges():
    G = nx.Graph()
    G.add_node("a", label="A", source_file="clients/bridgestone/brief.md", file_type="document")
    G.add_node("b", label="B", source_file="finance/invoice.md", file_type="document")
    G.add_edge("a", "b", relation="references", confidence="EXTRACTED", _src="a", _tgt="b")
    edges = _cross_folder_edges(Path("clients/bridgestone"), ["a"], G)
    assert len(edges) == 1
    assert edges[0]["target_folder"] == Path("finance")
    assert edges[0]["relation"] == "references"


def test_cross_folder_edges_ignores_same_folder():
    G = nx.Graph()
    G.add_node("a", label="A", source_file="clients/bridgestone/brief.md", file_type="document")
    G.add_node("b", label="B", source_file="clients/bridgestone/contract.md", file_type="document")
    G.add_edge("a", "b", relation="references", confidence="EXTRACTED", _src="a", _tgt="b")
    edges = _cross_folder_edges(Path("clients/bridgestone"), ["a", "b"], G)
    assert len(edges) == 0


# ---------------------------------------------------------------------------
# Task 3: _write_subfolder_index
# ---------------------------------------------------------------------------
from graphify.enrich import _write_subfolder_index


def _make_folder_data():
    return {
        "folder": Path("clients/bridgestone"),
        "node_ids": ["a", "b"],
        "nodes": [
            {"id": "a", "label": "Contract Renewal", "source_file": "clients/bridgestone/contract.md", "file_type": "document"},
            {"id": "b", "label": "Q2 Review", "source_file": "clients/bridgestone/q2.md", "file_type": "document"},
        ],
        "cross_edges": [
            {"target_folder": Path("finance"), "relation": "references", "confidence": "EXTRACTED"},
        ],
        "summary": "Bridgestone engagement covering contract renewal and Q2 review.",
    }


def test_write_subfolder_index_dry_run(tmp_path):
    data = _make_folder_data()
    written = _write_subfolder_index(tmp_path / "clients/bridgestone", data, dry_run=True)
    assert isinstance(written, str)
    assert "Contract Renewal" in written
    assert not (tmp_path / "clients/bridgestone/INDEX.md").exists()


def test_write_subfolder_index_creates_file(tmp_path):
    folder = tmp_path / "clients/bridgestone"
    folder.mkdir(parents=True)
    data = _make_folder_data()
    _write_subfolder_index(folder, data, dry_run=False)
    content = (folder / "INDEX.md").read_text()
    assert "Contract Renewal" in content
    assert "Q2 Review" in content
    assert "finance" in content
    assert "last_enriched" in content


def test_write_subfolder_index_lists_documents(tmp_path):
    folder = tmp_path / "clients/bridgestone"
    folder.mkdir(parents=True)
    data = _make_folder_data()
    _write_subfolder_index(folder, data, dry_run=False)
    content = (folder / "INDEX.md").read_text()
    assert "contract.md" in content
    assert "q2.md" in content


# ---------------------------------------------------------------------------
# Task 4: _write_master_index
# ---------------------------------------------------------------------------
from graphify.enrich import _write_master_index


def test_write_master_index_creates_file(tmp_path):
    folder_summaries = {
        Path("clients/bridgestone"): {
            "summary": "Bridgestone engagement.",
            "entities": ["Contract Renewal", "Tanaka-san"],
        },
        Path("finance"): {
            "summary": "Finance and invoices.",
            "entities": ["payment terms", "Q2 budget"],
        },
    }
    _write_master_index(tmp_path, folder_summaries, dry_run=False)
    content = (tmp_path / "INDEX.md").read_text()
    assert "clients/bridgestone" in content
    assert "Contract Renewal" in content
    assert "finance" in content
    assert "last_enriched" in content


def test_write_master_index_entity_folder_map(tmp_path):
    folder_summaries = {
        Path("clients/bridgestone"): {
            "summary": "Bridgestone.",
            "entities": ["contract renewal"],
        },
        Path("finance"): {
            "summary": "Finance.",
            "entities": ["contract renewal", "invoice"],
        },
    }
    _write_master_index(tmp_path, folder_summaries, dry_run=False)
    content = (tmp_path / "INDEX.md").read_text()
    # contract renewal appears in two folders
    assert content.count("contract renewal") >= 2


def test_write_master_index_dry_run(tmp_path):
    result = _write_master_index(tmp_path, {}, dry_run=True)
    assert not (tmp_path / "INDEX.md").exists()
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Task 5: enrich() orchestrator
# ---------------------------------------------------------------------------
import json
from graphify.enrich import enrich
from graphify.export import to_json
from graphify.build import build_from_json
from graphify.cluster import cluster


def _make_graph_json(tmp_path):
    extraction = {
        "nodes": [
            {"id": "a", "label": "Contract", "source_file": str(tmp_path / "clients/brief.md"), "file_type": "document"},
            {"id": "b", "label": "Invoice", "source_file": str(tmp_path / "finance/inv.md"), "file_type": "document"},
        ],
        "edges": [
            {"source": "a", "target": "b", "relation": "references", "confidence": "EXTRACTED",
             "source_file": str(tmp_path / "clients/brief.md"), "weight": 1.0},
        ],
    }
    G = build_from_json(extraction)
    communities = cluster(G)
    out = tmp_path / "graphify-out"
    out.mkdir()
    to_json(G, communities, str(out / "graph.json"))
    return out / "graph.json"


def test_enrich_creates_subfolder_indexes(tmp_path):
    (tmp_path / "clients").mkdir()
    (tmp_path / "finance").mkdir()
    graph_json = _make_graph_json(tmp_path)
    enrich(tmp_path, graph_json_path=graph_json, watch=False, dry_run=False)
    assert (tmp_path / "clients" / "INDEX.md").exists()
    assert (tmp_path / "finance" / "INDEX.md").exists()


def test_enrich_creates_master_index(tmp_path):
    (tmp_path / "clients").mkdir()
    graph_json = _make_graph_json(tmp_path)
    enrich(tmp_path, graph_json_path=graph_json, watch=False, dry_run=False)
    assert (tmp_path / "INDEX.md").exists()


def test_enrich_dry_run_no_writes(tmp_path):
    (tmp_path / "clients").mkdir()
    graph_json = _make_graph_json(tmp_path)
    enrich(tmp_path, graph_json_path=graph_json, watch=False, dry_run=True)
    assert not (tmp_path / "clients" / "INDEX.md").exists()
    assert not (tmp_path / "INDEX.md").exists()


def test_enrich_master_only(tmp_path):
    (tmp_path / "clients").mkdir()
    graph_json = _make_graph_json(tmp_path)
    enrich(tmp_path, graph_json_path=graph_json, watch=False, dry_run=False, master_only=True)
    assert (tmp_path / "INDEX.md").exists()
    assert not (tmp_path / "clients" / "INDEX.md").exists()


# ---------------------------------------------------------------------------
# Task 6: _watch_and_enrich
# ---------------------------------------------------------------------------
import time
import threading
from graphify.enrich import _watch_and_enrich


def test_watch_and_enrich_triggers_on_change(tmp_path):
    (tmp_path / "clients").mkdir()
    graph_json = _make_graph_json(tmp_path)

    triggered = []

    def fake_enrich(corpus_path, graph_json_path, master_only):
        triggered.append(1)

    stop = threading.Event()

    def run():
        _watch_and_enrich(
            tmp_path,
            graph_json,
            master_only=False,
            _enrich_fn=fake_enrich,
            _stop_event=stop,
            _poll_interval=0.1,
        )

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.2)
    graph_json.touch()  # simulate graph.json update
    time.sleep(0.5)
    stop.set()
    t.join(timeout=2)

    assert len(triggered) >= 1
