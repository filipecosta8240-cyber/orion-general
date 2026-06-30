"""
Advanced Checkpointing & State Persistence
==========================================
Provides durable execution and state persistence for multi-agent workflows.
Based on 2026 production patterns for fault tolerance and recovery.

Features:
- State serialization/deserialization
- Automatic checkpointing
- Recovery from failures
- Version control for states
- Distributed state management
"""

from __future__ import annotations

import json
import logging
import hashlib
import pickle
import zlib
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import threading

logger = logging.getLogger("orion.checkpointing")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_ROOT = _PROJECT_ROOT / "ORION_SYSTEM" / "CHECKPOINTS"


class CheckpointStatus(str, Enum):
    """Checkpoint status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERED = "recovered"
    ROLLED_BACK = "rolled_back"


class StateVersion(str, Enum):
    """State version strategies."""
    LATEST = "latest"
    ALL = "all"
    TAGGED = "tagged"


@dataclass
class StateSnapshot:
    """A snapshot of system state."""
    snapshot_id: str
    workflow_id: str
    agent_id: str
    state_data: Dict[str, Any]
    version: int
    checksum: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tags: List[str] = field(default_factory=list)
    parent_snapshot_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Checkpoint:
    """A checkpoint in workflow execution."""
    checkpoint_id: str
    workflow_id: str
    task_id: str
    status: str
    snapshots: List[StateSnapshot]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowState:
    """Persistent workflow state."""
    workflow_id: str
    current_step: int
    total_steps: int
    agent_states: Dict[str, Dict[str, Any]]
    metadata: Dict[str, Any]
    version: int = 1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CheckpointManager:
    """
    Advanced Checkpoint Manager
    
    Manages state persistence, recovery, and versioning for multi-agent workflows.
    Provides fault tolerance through automatic checkpointing and recovery.
    """
    
    def __init__(self, checkpoint_root: Optional[Path] = None):
        self._root = checkpoint_root or CHECKPOINT_ROOT
        self._root.mkdir(parents=True, exist_ok=True)
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._states: Dict[str, WorkflowState] = {}
        self._snapshots: Dict[str, StateSnapshot] = {}
        self._lock = threading.Lock()
        self._load_checkpoints()
        
    def _load_checkpoints(self) -> None:
        """Load checkpoints from disk."""
        checkpoint_file = self._root / "checkpoints.json"
        if checkpoint_file.exists():
            try:
                data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
                for cid, cdata in data.items():
                    self._checkpoints[cid] = Checkpoint(**cdata)
            except (json.JSONDecodeError, TypeError):
                pass
                
    def _save_checkpoints(self) -> None:
        """Save checkpoints to disk."""
        checkpoint_file = self._root / "checkpoints.json"
        data = {cid: c.to_dict() for cid, c in self._checkpoints.items()}
        checkpoint_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for state data."""
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
        
    def _compress_state(self, state_data: Dict[str, Any]) -> bytes:
        """Compress state data for storage."""
        serialized = pickle.dumps(state_data)
        return zlib.compress(serialized)
        
    def _decompress_state(self, compressed: bytes) -> Dict[str, Any]:
        """Decompress state data."""
        decompressed = zlib.decompress(compressed)
        return pickle.loads(decompressed)
        
    def create_snapshot(self, workflow_id: str, agent_id: str, 
                       state_data: Dict[str, Any], tags: Optional[List[str]] = None) -> StateSnapshot:
        """Create a state snapshot."""
        with self._lock:
            version = len([s for s in self._snapshots.values() 
                          if s.workflow_id == workflow_id]) + 1
            
            snapshot = StateSnapshot(
                snapshot_id=f"snap_{workflow_id}_{version}",
                workflow_id=workflow_id,
                agent_id=agent_id,
                state_data=state_data,
                version=version,
                checksum=self._calculate_checksum(state_data),
                tags=tags or []
            )
            
            self._snapshots[snapshot.snapshot_id] = snapshot
            logger.info(f"Snapshot created: {snapshot.snapshot_id}")
            return snapshot
    
    def save_workflow_state(self, state: WorkflowState) -> None:
        """Save workflow state to persistent storage."""
        with self._lock:
            state.version += 1
            state.updated_at = datetime.now(timezone.utc)
            self._states[state.workflow_id] = state
            
            state_file = self._root / f"state_{state.workflow_id}.json"
            state_file.write_text(json.dumps(state.to_dict(), indent=2, ensure_ascii=False), 
                                encoding="utf-8")
            logger.info(f"Workflow state saved: {state.workflow_id} v{state.version}")
    
    def load_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """Load workflow state from persistent storage."""
        state_file = self._root / f"state_{workflow_id}.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                return WorkflowState(**data)
            except (json.JSONDecodeError, TypeError):
                pass
        return None
    
    def create_checkpoint(self, workflow_id: str, task_id: str, 
                         snapshots: List[StateSnapshot]) -> Checkpoint:
        """Create a checkpoint with snapshots."""
        with self._lock:
            checkpoint = Checkpoint(
                checkpoint_id=f"cp_{workflow_id}_{task_id}",
                workflow_id=workflow_id,
                task_id=task_id,
                status=CheckpointStatus.COMPLETED,
                snapshots=snapshots,
                completed_at=datetime.now(timezone.utc)
            )
            
            self._checkpoints[checkpoint.checkpoint_id] = checkpoint
            self._save_checkpoints()
            logger.info(f"Checkpoint created: {checkpoint.checkpoint_id}")
            return checkpoint
    
    def recover_from_checkpoint(self, checkpoint_id: str) -> Optional[WorkflowState]:
        """Recover workflow state from a checkpoint."""
        checkpoint = self._checkpoints.get(checkpoint_id)
        if not checkpoint:
            logger.warning(f"Checkpoint not found: {checkpoint_id}")
            return None
            
        latest_snapshot = max(checkpoint.snapshots, key=lambda s: s.version, default=None)
        if latest_snapshot:
            state = WorkflowState(
                workflow_id=checkpoint.workflow_id,
                current_step=latest_snapshot.version,
                total_steps=0,
                agent_states={latest_snapshot.agent_id: latest_snapshot.state_data},
                metadata={"recovered_from": checkpoint_id},
                version=latest_snapshot.version
            )
            self.save_workflow_state(state)
            checkpoint.status = CheckpointStatus.RECOVERED
            self._save_checkpoints()
            logger.info(f"Recovered from checkpoint: {checkpoint_id}")
            return state
            
        return None
    
    def get_workflow_checkpoints(self, workflow_id: str) -> List[Checkpoint]:
        """Get all checkpoints for a workflow."""
        return [cp for cp in self._checkpoints.values() if cp.workflow_id == workflow_id]
    
    def get_checkpoint_status(self) -> Dict[str, Any]:
        """Get checkpoint manager status."""
        return {
            "total_checkpoints": len(self._checkpoints),
            "total_snapshots": len(self._snapshots),
            "total_states": len(self._states),
            "checkpoints": {cid: cp.to_dict() for cid, cp in self._checkpoints.items()}
        }
