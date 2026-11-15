"""Tests for ATG Builder module."""

from src.module1_semantic.atg_builder import ATGNode, ATGEdge, ATG


def test_atg_node_creation():
    node = ATGNode(
        node_id="lock_pool",
        node_type="contract",
        chain="source",
        address="0xABC",
    )
    assert node.node_id == "lock_pool"
    assert node.chain == "source"


def test_atg_edge_creation():
    edge = ATGEdge(
        src="user_A",
        dst="lock_pool",
        label="lock",
        conditions=["amount > 0"],
    )
    assert edge.label == "lock"


def test_atg_structure():
    atg = ATG()
    atg.nodes.append(ATGNode("user_A", "user", "source"))
    atg.edges.append(ATGEdge("user_A", "lock_pool", "lock"))
    assert len(atg.nodes) == 1
    assert len(atg.edges) == 1


def test_build_coerces_null_edge_fields_to_strings():
    # The LLM may emit explicit nulls; the Rust AtgEdge requires strings.
    from src.module1_semantic.atg_builder import ATGBuilder

    ab = ATGBuilder()
    atg = ab.build({
        "entities": [], "functions": [], "guards": [],
        "asset_flows": [{"src": None, "dst": "bridge", "label": "lock",
                         "token": None, "function_signature": None, "conditions": []}],
    })
    edge = ab.to_json(atg)["edges"][0]
    for key in ("edge_id", "src", "dst", "label", "token", "function_signature"):
        assert isinstance(edge[key], str), key
    assert edge["token"] == "UNKNOWN"


def test_from_json_coerces_null_edge_fields():
    from src.module1_semantic.atg_builder import ATGBuilder

    atg = ATGBuilder().from_json({"nodes": [], "edges": [{
        "edge_id": "e1", "src": "a", "dst": "b", "label": None,
        "token": None, "function_signature": None, "conditions": []}]})
    edge = atg.edges[0]
    assert (edge.label, edge.token, edge.function_signature) == ("verify", "UNKNOWN", "")
