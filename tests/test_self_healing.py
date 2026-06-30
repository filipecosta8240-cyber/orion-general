"""Tests for self-healing system"""
import pytest
from orion.self_healing import SelfHealingEngine, ComponentStatus, CircuitState


def test_component_registration():
    engine = SelfHealingEngine()
    breaker = engine.register_component("test_comp")
    assert breaker is not None
    assert breaker.name == "test_comp"


def test_failure_recording():
    engine = SelfHealingEngine()
    engine.register_component("test_comp", failure_threshold=2)
    
    engine.record_failure("test_comp", "error 1")
    status = engine.get_status("test_comp")
    assert status == ComponentStatus.UNHEALTHY or status == ComponentStatus.HEALTHY
    
    state = engine.can_proceed("test_comp")
    assert state is True  # Still under threshold


def test_circuit_breaker():
    engine = SelfHealingEngine()
    engine.register_component("circuit_test", failure_threshold=3, recovery_timeout=1)
    
    for i in range(3):
        engine.record_failure("circuit_test", f"error {i}")
    
    state = engine.can_proceed("circuit_test")
    assert state is False  # Circuit should be open


def test_get_statistics():
    engine = SelfHealingEngine()
    engine.register_component("comp1")
    engine.register_component("comp2")
    stats = engine.get_statistics()
    assert stats["total_components"] == 2
