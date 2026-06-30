"""
ORION Workflow Engine
======================
DAG-based workflow engine inspired by LangGraph.

Features:
- Directed Acyclic Graph (DAG) workflow definition
- Node types: task, decision, parallel, sub-workflow
- State management across workflow execution
- Conditional branching
- Parallel execution
- Human-in-the-loop checkpoints
- Retry and error handling
"""

import time
import uuid
import json
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger("orion.workflow")


class NodeType(str, Enum):
    TASK = "task"
    DECISION = "decision"
    PARALLEL = "parallel"
    SUB_WORKFLOW = "sub_workflow"
    START = "start"
    END = "end"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


@dataclass
class WorkflowNode:
    """A node in the workflow DAG"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    node_type: NodeType = NodeType.TASK
    handler: Optional[Callable] = None
    config: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 300
    requires_approval: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "config": self.config,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "requires_approval": self.requires_approval
        }


@dataclass
class WorkflowEdge:
    """Edge connecting nodes in the workflow DAG"""
    source_id: str = ""
    target_id: str = ""
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    label: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "label": self.label
        }


@dataclass
class WorkflowDefinition:
    """Definition of a workflow"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    nodes: Dict[str, WorkflowNode] = field(default_factory=dict)
    edges: List[WorkflowEdge] = field(default_factory=list)
    start_node_id: str = ""
    end_node_ids: List[str] = field(default_factory=list)
    version: str = "1.0"
    
    def add_node(self, node: WorkflowNode) -> "WorkflowDefinition":
        self.nodes[node.id] = node
        return self
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        condition: Optional[Callable] = None,
        label: str = ""
    ) -> "WorkflowDefinition":
        self.edges.append(WorkflowEdge(
            source_id=source_id,
            target_id=target_id,
            condition=condition,
            label=label
        ))
        return self
    
    def validate(self) -> Tuple[bool, str]:
        """Validate workflow definition"""
        if not self.nodes:
            return False, "No nodes defined"
        if not self.start_node_id:
            return False, "No start node defined"
        if self.start_node_id not in self.nodes:
            return False, "Start node not found"
        
        # Check all edges reference valid nodes
        for edge in self.edges:
            if edge.source_id not in self.nodes:
                return False, f"Edge source {edge.source_id} not found"
            if edge.target_id not in self.nodes:
                return False, f"Edge target {edge.target_id} not found"
        
        return True, "Valid"


@dataclass
class NodeExecution:
    """Execution state of a node"""
    node_id: str = ""
    status: NodeStatus = NodeStatus.PENDING
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    attempts: int = 0
    
    @property
    def duration_ms(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return 0.0


@dataclass
class WorkflowExecution:
    """Execution state of a workflow"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    workflow_id: str = ""
    status: WorkflowStatus = WorkflowStatus.PENDING
    node_executions: Dict[str, NodeExecution] = field(default_factory=dict)
    shared_state: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status.value,
            "node_count": len(self.node_executions),
            "completed_nodes": sum(1 for n in self.node_executions.values() if n.status == NodeStatus.COMPLETED),
            "failed_nodes": sum(1 for n in self.node_executions.values() if n.status == NodeStatus.FAILED),
            "duration_ms": self.duration_ms,
            "error": self.error
        }


class WorkflowEngine:
    """
    DAG-based workflow execution engine.
    
    Supports:
    - Sequential task execution
    - Conditional branching (if/else)
    - Parallel execution
    - Sub-workflows
    - Human-in-the-loop checkpoints
    - Retry with backoff
    """
    
    def __init__(self):
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self._lock = threading.RLock()
        logger.info("Workflow Engine initialized")
    
    def register_workflow(self, workflow: WorkflowDefinition) -> str:
        """Register a workflow definition"""
        valid, msg = workflow.validate()
        if not valid:
            raise ValueError(f"Invalid workflow: {msg}")
        
        with self._lock:
            self.workflows[workflow.id] = workflow
            logger.info(f"Registered workflow: {workflow.name} ({workflow.id})")
            return workflow.id
    
    def execute(
        self,
        workflow_id: str,
        initial_state: Optional[Dict[str, Any]] = None
    ) -> str:
        """Execute a workflow"""
        with self._lock:
            workflow = self.workflows.get(workflow_id)
            if not workflow:
                raise ValueError(f"Workflow not found: {workflow_id}")
        
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            shared_state=initial_state or {},
            started_at=time.time()
        )
        
        with self._lock:
            self.executions[execution.id] = execution
        
        # Start execution in thread
        thread = threading.Thread(
            target=self._execute_workflow,
            args=(execution.id, workflow),
            daemon=True
        )
        thread.start()
        
        return execution.id
    
    def _execute_workflow(
        self,
        execution_id: str,
        workflow: WorkflowDefinition
    ) -> None:
        """Execute workflow in thread"""
        execution = self.executions.get(execution_id)
        if not execution:
            return
        
        try:
            execution.status = WorkflowStatus.RUNNING
            
            # Start from start node
            current_id = workflow.start_node_id
            visited = set()
            
            while current_id and current_id not in workflow.end_node_ids:
                if current_id in visited:
                    execution.error = f"Cycle detected at node {current_id}"
                    execution.status = WorkflowStatus.FAILED
                    return
                
                visited.add(current_id)
                current_id = self._execute_node(
                    execution_id, workflow, current_id
                )
            
            execution.status = WorkflowStatus.COMPLETED
            
        except Exception as e:
            execution.status = WorkflowStatus.FAILED
            execution.error = str(e)
            logger.error(f"Workflow {execution_id} failed: {e}")
        finally:
            execution.completed_at = time.time()
    
    def _execute_node(
        self,
        execution_id: str,
        workflow: WorkflowDefinition,
        node_id: str
    ) -> Optional[str]:
        """Execute a single node and return next node ID"""
        execution = self.executions.get(execution_id)
        node = workflow.nodes.get(node_id)
        
        if not execution or not node:
            return None
        
        node_exec = NodeExecution(node_id=node_id, started_at=time.time())
        execution.node_executions[node_id] = node_exec
        
        try:
            node_exec.status = NodeStatus.RUNNING
            
            if node.node_type == NodeType.START:
                node_exec.status = NodeStatus.COMPLETED
                return self._get_next_node(workflow, node_id, execution.shared_state)
            
            elif node.node_type == NodeType.TASK:
                if node.requires_approval:
                    node_exec.status = NodeStatus.BLOCKED
                    return None  # Wait for approval
                
                node_exec.attempts += 1
                if node.handler:
                    result = node.handler(execution.shared_state)
                    if isinstance(result, dict):
                        execution.shared_state.update(result)
                    node_exec.output_data = result or {}
                
                node_exec.status = NodeStatus.COMPLETED
                return self._get_next_node(workflow, node_id, execution.shared_state)
            
            elif node.node_type == NodeType.DECISION:
                next_id = self._evaluate_decision(
                    workflow, node_id, execution.shared_state
                )
                node_exec.status = NodeStatus.COMPLETED
                return next_id
            
            elif node.node_type == NodeType.PARALLEL:
                self._execute_parallel(
                    execution_id, workflow, node, execution.shared_state
                )
                node_exec.status = NodeStatus.COMPLETED
                return self._get_next_node(workflow, node_id, execution.shared_state)
            
            elif node.node_type == NodeType.END:
                node_exec.status = NodeStatus.COMPLETED
                return None
            
        except Exception as e:
            node_exec.status = NodeStatus.FAILED
            node_exec.error = str(e)
            
            if node_exec.attempts < node.max_retries:
                node_exec.attempts += 1
                logger.info(f"Retrying node {node_id} (attempt {node_exec.attempts})")
                return node_id  # Retry same node
            
            execution.status = WorkflowStatus.FAILED
            execution.error = f"Node {node_id} failed: {e}"
            
        finally:
            node_exec.completed_at = time.time()
        
        return None
    
    def _get_next_node(
        self,
        workflow: WorkflowDefinition,
        current_id: str,
        state: Dict[str, Any]
    ) -> Optional[str]:
        """Get next node based on edges"""
        outgoing = [e for e in workflow.edges if e.source_id == current_id]
        
        if not outgoing:
            return None
        
        # Check conditional edges first
        for edge in outgoing:
            if edge.condition:
                if edge.condition(state):
                    return edge.target_id
        
        # Default to unconditional edge
        unconditional = [e for e in outgoing if not e.condition]
        if unconditional:
            return unconditional[0].target_id
        
        # If all edges have conditions and none matched, return None
        return None
    
    def _evaluate_decision(
        self,
        workflow: WorkflowDefinition,
        node_id: str,
        state: Dict[str, Any]
    ) -> Optional[str]:
        """Evaluate decision node and return next node"""
        return self._get_next_node(workflow, node_id, state)
    
    def _execute_parallel(
        self,
        execution_id: str,
        workflow: WorkflowDefinition,
        parallel_node: WorkflowNode,
        state: Dict[str, Any]
    ) -> None:
        """Execute parallel branches"""
        threads = []
        
        # Find branches (nodes that connect from parallel node)
        branch_starts = [
            e.target_id for e in workflow.edges
            if e.source_id == parallel_node.id
        ]
        
        for branch_id in branch_starts:
            thread = threading.Thread(
                target=self._execute_branch,
                args=(execution_id, workflow, branch_id),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        
        for thread in threads:
            thread.join()
    
    def _execute_branch(
        self,
        execution_id: str,
        workflow: WorkflowDefinition,
        start_id: str
    ) -> None:
        """Execute a branch of parallel nodes"""
        current_id = start_id
        while current_id:
            current_id = self._execute_node(
                execution_id, workflow, current_id
            )
    
    def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution status"""
        return self.executions.get(execution_id)
    
    def get_workflow_status(self, execution_id: str) -> Optional[str]:
        """Get execution status"""
        execution = self.executions.get(execution_id)
        return execution.status.value if execution else None
    
    def approve_node(self, execution_id: str, node_id: str) -> bool:
        """Approve a blocked node (HITL)"""
        execution = self.executions.get(execution_id)
        if not execution:
            return False
        
        node_exec = execution.node_executions.get(node_id)
        if not node_exec or node_exec.status != NodeStatus.BLOCKED:
            return False
        
        # Resume execution
        node_exec.status = NodeStatus.PENDING
        workflow = self.workflows.get(execution.workflow_id)
        if workflow:
            thread = threading.Thread(
                target=self._execute_node,
                args=(execution_id, workflow, node_id),
                daemon=True
            )
            thread.start()
        
        return True
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List registered workflows"""
        return [
            {
                "id": w.id,
                "name": w.name,
                "description": w.description,
                "nodes": len(w.nodes),
                "edges": len(w.edges),
                "version": w.version
            }
            for w in self.workflows.values()
        ]
    
    def list_executions(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List workflow executions"""
        executions = self.executions.values()
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        
        return [
            {
                "id": e.id,
                "workflow_id": e.workflow_id,
                "status": e.status.value,
                "duration_ms": e.duration_ms,
                "completed_at": e.completed_at
            }
            for e in sorted(executions, key=lambda x: x.started_at or 0, reverse=True)
        ]


# Global instance
_workflow_engine: Optional[WorkflowEngine] = None

def get_workflow_engine() -> WorkflowEngine:
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
