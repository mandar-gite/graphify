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
