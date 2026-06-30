"""Tests for federated memory"""
import pytest
from orion.federated_memory import FederatedMemoryNode


def test_node_initialization():
    node = FederatedMemoryNode(node_id="test", node_name="test-node")
    assert node.node_id == "test"
    assert node.node_name == "test-node"


def test_store_and_get_local():
    node = FederatedMemoryNode()
    node.store_local("key1", {"data": "hello"})
    value = node.get_local("key1")
    assert value == {"data": "hello"}


def test_peer_registration():
    node = FederatedMemoryNode()
    peer = node.register_peer("peer1", "Peer 1")
    assert peer.id == "peer1"
    assert len(node.peers) == 1


def test_get_statistics():
    node = FederatedMemoryNode()
    node.register_peer("peer1", "Peer 1")
    stats = node.get_statistics()
    assert stats["peers"] == 1
    assert stats["node_id"] is not None
