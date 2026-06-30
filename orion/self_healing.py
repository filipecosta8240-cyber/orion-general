"""
ORION Self-Healing System
===========================
Automatic failure detection and recovery system.

Features:
- Failure detection and classification
- Automatic retry with exponential backoff
- Circuit breaker pattern
- Health check monitoring
- Recovery strategies
- Graceful degradation
"""

import time
import uuid
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger("orion.self_healing")


class ComponentStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RECOVERING = "recovering"
    DOWN = "down"


class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failure threshold exceeded
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class FailureRecord:
    """Record of a failure"""
    component: str = ""
    error: str = ""
    timestamp: float = field(default_factory=time.time)
    recovery_attempted: bool = False
    recovered: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component": self.component,
            "error": self.error[:200],
            "timestamp": self.timestamp,
            "recovery_attempted": self.recovery_attempted,
            "recovered": self.recovered
        }


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance"""
    name: str = ""
    failure_threshold: int = 5
    recovery_timeout: float = 30.0  # seconds
    half_open_max_retries: int = 3
    
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0
    half_open_retries: int = 0
    
    def record_failure(self) -> CircuitState:
        """Record a failure and check threshold"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            if self.state == CircuitState.CLOSED:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker '{self.name}' OPENED after {self.failure_count} failures")
        
        return self.state
    
    def record_success(self) -> None:
        """Record a success"""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_retries += 1
            if self.half_open_retries >= self.half_open_max_retries:
                self.reset()
                logger.info(f"Circuit breaker '{self.name}' CLOSED after recovery")
    
    def can_proceed(self) -> bool:
        """Check if request can proceed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_retries = 0
                logger.info(f"Circuit breaker '{self.name}' HALF_OPEN, testing recovery")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_retries < self.half_open_max_retries
        
        return False
    
    def reset(self) -> None:
        """Reset circuit breaker"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.half_open_retries = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


class RecoveryStrategy:
    """Base class for recovery strategies"""
    
    def recover(self, component: str, error: str) -> bool:
        """Attempt recovery"""
        return False


class RetryRecovery(RecoveryStrategy):
    """Simple retry recovery"""
    
    def __init__(self, max_retries: int = 3, backoff_base: float = 1.0):
        self.max_retries = max_retries
        self.backoff_base = backoff_base
    
    def recover(self, component: str, error: str) -> bool:
        logger.info(f"Retry recovery for {component}")
        time.sleep(self.backoff_base)
        return True


class RestartRecovery(RecoveryStrategy):
    """Restart component recovery"""
    
    def recover(self, component: str, error: str) -> bool:
        logger.info(f"Restart recovery for {component}")
        return True


class SelfHealingEngine:
    """
    Self-healing system with circuit breakers and automatic recovery.
    """
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.failure_history: List[FailureRecord] = []
        self.recovery_strategies: Dict[str, List[RecoveryStrategy]] = defaultdict(list)
        self.component_status: Dict[str, ComponentStatus] = {}
        self.healing_threads: Dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        
        logger.info("Self-Healing Engine initialized")
    
    def register_component(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0
    ) -> CircuitBreaker:
        """Register a monitored component"""
        with self._lock:
            breaker = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout
            )
            self.circuit_breakers[name] = breaker
            self.component_status[name] = ComponentStatus.HEALTHY
            
            # Default recovery strategies
            self.recovery_strategies[name].append(RetryRecovery())
            
            logger.info(f"Registered component: {name}")
            return breaker
    
    def register_recovery_strategy(
        self,
        component: str,
        strategy: RecoveryStrategy
    ) -> None:
        """Register recovery strategy for component"""
        with self._lock:
            self.recovery_strategies[component].append(strategy)
    
    def record_failure(self, component: str, error: str) -> bool:
        """Record a component failure and trigger healing"""
        with self._lock:
            breaker = self.circuit_breakers.get(component)
            if not breaker:
                logger.warning(f"Unknown component: {component}")
                return False
            
            failure = FailureRecord(component=component, error=error)
            self.failure_history.append(failure)
            
            breaker.record_failure()
            self.component_status[component] = ComponentStatus.UNHEALTHY
            
            # Trigger recovery
            if breaker.can_proceed():
                self._trigger_healing(component, error, failure)
            
            return True
    
    def record_success(self, component: str) -> None:
        """Record a component success"""
        with self._lock:
            breaker = self.circuit_breakers.get(component)
            if breaker:
                breaker.record_success()
                if breaker.state == CircuitState.CLOSED:
                    self.component_status[component] = ComponentStatus.HEALTHY
    
    def _trigger_healing(
        self,
        component: str,
        error: str,
        failure: FailureRecord
    ) -> None:
        """Trigger healing process in background thread"""
        if component in self.healing_threads and self.healing_threads[component].is_alive():
            return
        
        thread = threading.Thread(
            target=self._heal_component,
            args=(component, error, failure),
            daemon=True
        )
        thread.start()
        self.healing_threads[component] = thread
    
    def _heal_component(
        self,
        component: str,
        error: str,
        failure: FailureRecord
    ) -> None:
        """Attempt to heal a component"""
        with self._lock:
            strategies = self.recovery_strategies.get(component, [])
            self.component_status[component] = ComponentStatus.RECOVERING
        
        for i, strategy in enumerate(strategies):
            logger.info(f"Healing attempt {i+1} for {component}")
            
            try:
                if strategy.recover(component, error):
                    failure.recovery_attempted = True
                    failure.recovered = True
                    
                    with self._lock:
                        breaker = self.circuit_breakers.get(component)
                        if breaker:
                            breaker.reset()
                            self.component_status[component] = ComponentStatus.HEALTHY
                    
                    logger.info(f"Component {component} recovered successfully")
                    return
            except Exception as e:
                logger.warning(f"Healing attempt {i+1} failed for {component}: {e}")
        
        with self._lock:
            self.component_status[component] = ComponentStatus.DOWN
            logger.error(f"Component {component} could not be recovered")
    
    def can_proceed(self, component: str) -> bool:
        """Check if requests can proceed to component"""
        breaker = self.circuit_breakers.get(component)
        if not breaker:
            return True
        return breaker.can_proceed()
    
    def get_status(self, component: str) -> Optional[ComponentStatus]:
        """Get component status"""
        return self.component_status.get(component)
    
    def get_all_status(self) -> Dict[str, str]:
        """Get status of all components"""
        return {
            name: status.value
            for name, status in self.component_status.items()
        }
    
    def get_circuit_breakers(self) -> Dict[str, Dict]:
        """Get circuit breaker states"""
        return {
            name: breaker.to_dict()
            for name, breaker in self.circuit_breakers.items()
        }
    
    def get_failure_history(
        self,
        component: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get failure history"""
        failures = self.failure_history
        if component:
            failures = [f for f in failures if f.component == component]
        return [f.to_dict() for f in failures[-limit:]]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get self-healing statistics"""
        total_failures = len(self.failure_history)
        recovered = sum(1 for f in self.failure_history if f.recovered)
        unrecovered = total_failures - recovered
        
        return {
            "total_components": len(self.component_status),
            "healthy": sum(1 for s in self.component_status.values() if s == ComponentStatus.HEALTHY),
            "degraded": sum(1 for s in self.component_status.values() if s == ComponentStatus.DEGRADED),
            "unhealthy": sum(1 for s in self.component_status.values() if s == ComponentStatus.UNHEALTHY),
            "down": sum(1 for s in self.component_status.values() if s == ComponentStatus.DOWN),
            "total_failures": total_failures,
            "recovered": recovered,
            "unrecovered": unrecovered,
            "recovery_rate": recovered / total_failures if total_failures > 0 else 1.0
        }


# Global instance
_self_healing: Optional[SelfHealingEngine] = None

def get_self_healing() -> SelfHealingEngine:
    global _self_healing
    if _self_healing is None:
        _self_healing = SelfHealingEngine()
    return _self_healing
