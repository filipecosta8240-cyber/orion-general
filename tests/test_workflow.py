"""Tests for workflow engine"""
import pytest
from orion.workflow_engine import WorkflowEngine, WorkflowDefinition, WorkflowNode, NodeType, WorkflowStatus


def test_workflow_registration():
    engine = WorkflowEngine()
    wf = WorkflowDefinition(name="test", start_node_id="start")
    wf.add_node(WorkflowNode(id="start", name="start", node_type=NodeType.START))
    wf.add_node(WorkflowNode(id="end", name="end", node_type=NodeType.END))
    wf.add_edge("start", "end")
    wf_id = engine.register_workflow(wf)
    assert wf_id is not None


def test_workflow_execution():
    engine = WorkflowEngine()
    
    def test_handler(state):
        state["executed"] = True
        return {"result": "done"}
    
    wf = WorkflowDefinition(name="exec_test", start_node_id="start")
    wf.add_node(WorkflowNode(id="start", name="start", node_type=NodeType.START))
    wf.add_node(WorkflowNode(id="task1", name="task1", node_type=NodeType.TASK, handler=test_handler))
    wf.add_node(WorkflowNode(id="end", name="end", node_type=NodeType.END))
    wf.add_edge("start", "task1")
    wf.add_edge("task1", "end")
    
    wf_id = engine.register_workflow(wf)
    exec_id = engine.execute(wf_id)
    
    import time
    time.sleep(0.5)
    
    status = engine.get_workflow_status(exec_id)
    assert status is not None


def test_invalid_workflow():
    engine = WorkflowEngine()
    wf = WorkflowDefinition(name="invalid")
    with pytest.raises(ValueError):
        engine.register_workflow(wf)
