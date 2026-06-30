"""
ORION Federated Memory
========================
Network-based memory sharing across ORION instances.

Features:
- P2P memory synchronization
- Conflict resolution
- Distributed memory search
- Instance discovery
- Memory replication
"""

import json
import time
import uuid
import threading
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
from pathlib import Path
import logging

logger = logging.getLogger("orion.federated_memory")


class SyncStrategy(str, Enum):
    PUSH = "push"       # Push changes to peers
    PULL = "pull"       # Pull changes from peers
    BIDIRECTIONAL = "bidirectional"  # Both directions


class ConflictResolution(str, Enum):
    LAST_WRITE_WINS = "last_write_wins"
    HIGHEST_CONFIDENCE = "highest_confidence"
    MANUAL = "manual"


@dataclass
class PeerInfo:
    """Information about a federated peer"""
    id: str = ""
    name: str = ""
    address: str = ""
    port: int = 0
    last_seen: float = field(default_factory=time.time)
    is_active: bool = True
    version: str = "1.0"
    capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "address": self.address,
            "port": self.port,
            "last_seen": self.last_seen,
            "is_active": self.is_active,
            "version": self.version,
            "capabilities": self.capabilities
        }


@dataclass
class MemoryReplica:
    """Replicated memory entry"""
    id: str = ""
    source_peer: str = ""
    content: str = ""
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    version: int = 1
    conflicts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_peer": self.source_peer,
            "content": self.content[:200],
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "version": this.version
        }


class FederatedMemoryNode:
    """
    Federated memory node for P2P synchronization.
    """
    
    def __init__(
        self,
        node_id: Optional[str] = None,
        node_name: str = "orion-node"
    ):
        self.node_id = node_id or str(uuid.uuid4())[:8]
        self.node_name = node_name
        self.peers: Dict[str, PeerInfo] = {}
        self.replicas: Dict[str, MemoryReplica] = {}
        self.local_storage: Dict[str, Dict] = {}
        self._lock = threading.RLock()
        
        self.sync_strategy = SyncStrategy.BIDIRECTIONAL
        self.conflict_resolution = ConflictResolution.LAST_WRITE_WINS
        self.sync_interval = 60  # seconds
        
        logger.info(f"Federated Memory Node '{node_name}' ({self.node_id}) initialized")
    
    def register_peer(
        self,
        peer_id: str,
        name: str,
        address: str = "localhost",
        port: int = 0,
        capabilities: Optional[List[str]] = None
    ) -> PeerInfo:
        """Register a peer for synchronization"""
        with self._lock:
            peer = PeerInfo(
                id=peer_id,
                name=name,
                address=address,
                port=port,
                last_seen=time.time(),
                capabilities=capabilities or []
            )
            self.peers[peer_id] = peer
            logger.info(f"Registered peer: {name} ({peer_id})")
            return peer
    
    def unregister_peer(self, peer_id: str) -> bool:
        """Unregister a peer"""
        with self._lock:
            if peer_id in self.peers:
                self.peers[peer_id].is_active = False
                logger.info(f"Unregistered peer: {peer_id}")
                return True
            return False
    
    def store_local(self, key: str, value: Dict) -> None:
        """Store local memory entry"""
        with self._lock:
            self.local_storage[key] = {
                "value": value,
                "timestamp": time.time(),
                "version": self.local_storage.get(key, {}).get("version", 0) + 1
            }
    
    def get_local(self, key: str) -> Optional[Dict]:
        """Get local memory entry"""
        with self._lock:
            entry = self.local_storage.get(key)
            return entry["value"] if entry else None
    
    def replicate(self, memory_id: str, content: str, confidence: float = 1.0) -> MemoryReplica:
        """Create a memory replica for distribution"""
        with self._lock:
            replica = MemoryReplica(
                id=memory_id,
                source_peer=self.node_id,
                content=content,
                confidence=confidence
            )
            self.replicas[memory_id] = replica
            return replica
    
    def receive_replica(self, replica: MemoryReplica) -> bool:
        """Receive a replica from a peer"""
        with self._lock:
            existing = self.replicas.get(replica.id)
            
            if existing and replica.version <= existing.version:
                return False  # Already have this version
            
            # Conflict resolution
            if existing and replica.timestamp > existing.timestamp + 1:
                if self.conflict_resolution == ConflictResolution.LAST_WRITE_WINS:
                    if replica.timestamp > existing.timestamp:
                        self.replicas[replica.id] = replica
                
                elif self.conflict_resolution == ConflictResolution.HIGHEST_CONFIDENCE:
                    if replica.confidence > existing.confidence:
                        self.replicas[replica.id] = replica
                
                elif self.conflict_resolution == ConflictResolution.MANUAL:
                    existing.conflicts.append(replica.source_peer)
                    return False
            else:
                self.replicas[replica.id] = replica
            
            return True
    
    def sync_with_peer(self, peer_id: str) -> Dict[str, Any]:
        """Synchronize memory with a peer"""
        peer = self.peers.get(peer_id)
        if not peer or not peer.is_active:
            return {"status": "peer_not_available", "synced": 0}
        
        synced_count = 0
        conflicts = 0
        
        # Push local replicas to peer
        for replica_id, replica in self.replicas.items():
            if replica.source_peer == self.node_id:
                try:
                    self._send_replica(peer, replica)
                    synced_count += 1
                except Exception:
                    conflicts += 1
        
        peer.last_seen = time.time()
        
        return {
            "status": "completed",
            "synced": synced_count,
            "conflicts": conflicts,
            "peer": peer_id
        }
    
    def _send_replica(self, peer: PeerInfo, replica: MemoryReplica) -> None:
        """Send replica to peer (simulated - in production use HTTP/gRPC)"""
        logger.debug(f"Syncing replica {replica.id} to {peer.name}")
        pass
    
    def search_across_peers(
        self,
        query: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Search memory across all known peers"""
        results = []
        
        # Search local first
        for key, entry in self.local_storage.items():
            if query.lower() in key.lower():
                results.append({
                    "key": key,
                    "value": entry["value"],
                    "source": "local",
                    "timestamp": entry["timestamp"]
                })
        
        # Search replicas
        for replica_id, replica in self.replicas.items():
            if query.lower() in replica.content.lower():
                results.append({
                    "id": replica_id,
                    "content": replica.content[:200],
                    "source": f"peer:{replica.source_peer}",
                    "confidence": replica.confidence,
                    "timestamp": replica.timestamp
                })
        
        results.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return results[:max_results]
    
    def get_active_peers(self) -> List[PeerInfo]:
        """Get list of active peers"""
        return [
            p for p in self.peers.values()
            if p.is_active and (time.time() - p.last_seen) < 300  # Active in last 5 min
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get federated memory statistics"""
        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "peers": len(self.peers),
            "active_peers": len(self.get_active_peers()),
            "local_entries": len(self.local_storage),
            "replicas": len(self.replicas),
            "sync_strategy": self.sync_strategy.value,
            "conflict_resolution": self.conflict_resolution.value
        }


# Global instance
_federated_memory: Optional[FederatedMemoryNode] = None

def get_federated_memory() -> FederatedMemoryNode:
    global _federated_memory
    if _federated_memory is None:
        _federated_memory = FederatedMemoryNode()
    return _federated_memory
