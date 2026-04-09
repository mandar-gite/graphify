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
