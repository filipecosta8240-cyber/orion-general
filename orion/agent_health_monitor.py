"""
Agent Health Monitoring & Diagnostics
=====================================
Continuous health monitoring for all agents with automatic detection of
failures, performance degradation, and recovery tracking.

Health Status: HEALTHY, WARNING, CRITICAL
Recovery mechanisms: Auto-restart, fallback, manual intervention
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable
from datetime import datetime
import logging
import threading
from collections import deque

logger = logging.getLogger("orion.agent_health_monitor")


class HealthStatus(str, Enum):
    """Health status of an agent."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthMetrics:
    """Current health metrics for an agent."""
    agent_id: str
    is_alive: bool = True
    last_heartbeat: datetime = field(default_factory=datetime.now)
    cpu_usage: float = 0.0  # Percentage
    memory_usage: float = 0.0  # Percentage
    avg_response_time: float = 0.0  # Milliseconds
    error_rate: float = 0.0  # Percentage
    error_categories: Dict[str, int] = field(default_factory=dict)
    recovery_attempts: int = 0
    total_restarts: int = 0
    uptime: float = 0.0  # Seconds
    status: HealthStatus = HealthStatus.UNKNOWN
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class HealthAlert:
    """Alert generated when health issues detected."""
    agent_id: str
    alert_type: str  # "HIGH_ERROR_RATE", "NO_HEARTBEAT", "HIGH_LATENCY", "RESOURCE_DEPLETION"
    severity: str  # "WARNING", "CRITICAL"
    message: str
    timestamp: datetime
    suggested_action: Optional[str] = None


class AgentHealthMonitor:
    """
    Monitors health of individual agents.
    
    Features:
    - Heartbeat detection
    - Performance tracking
    - Error rate monitoring
    - Resource usage tracking
    - Recovery attempt logging
    - Health history
    """
    
    def __init__(self, agent_id: str, heartbeat_timeout: float = 30.0):
        """
        Initialize health monitor for an agent.
        
        Args:
            agent_id: Agent identifier
            heartbeat_timeout: Seconds before heartbeat considered missing
        """
        self.agent_id = agent_id
        self.heartbeat_timeout = heartbeat_timeout
        self.metrics = HealthMetrics(agent_id=agent_id)
        self.lock = threading.RLock()
        
        # History tracking
        self.metrics_history: deque = deque(maxlen=100)  # Last 100 measurements
        self.error_history: deque = deque(maxlen=50)
        self.heartbeat_history: deque = deque(maxlen=100)
        
        # Callbacks
        self.on_health_change: List[Callable[[HealthAlert], None]] = []
    
    def record_heartbeat(self):
        """Record that agent is alive."""
        with self.lock:
            now = datetime.now()
            self.metrics.is_alive = True
            self.metrics.last_heartbeat = now
            self.heartbeat_history.append(now)
    
    def record_error(self, error_type: str, error_message: str):
        """Record an error from the agent."""
        with self.lock:
            if error_type not in self.metrics.error_categories:
                self.metrics.error_categories[error_type] = 0
            self.metrics.error_categories[error_type] += 1
            self.error_history.append((error_type, datetime.now()))
            
            # Recalculate error rate
            if self.error_history:
                self.metrics.error_rate = len(self.error_history) / 50  # As percentage of history
    
    def record_metrics(self, cpu_usage: float, memory_usage: float, avg_response_time: float):
        """Record resource metrics."""
        with self.lock:
            self.metrics.cpu_usage = cpu_usage
            self.metrics.memory_usage = memory_usage
            self.metrics.avg_response_time = avg_response_time
            self.metrics.timestamp = datetime.now()
            self.metrics_history.append(self.metrics)
    
    def check_health(self) -> HealthStatus:
        """
        Evaluate current health status based on metrics.
        
        Returns:
            Current health status
        """
        with self.lock:
            alerts = []
            
            # Check heartbeat
            if self.metrics.is_alive:
                time_since_heartbeat = (datetime.now() - self.metrics.last_heartbeat).total_seconds()
                if time_since_heartbeat > self.heartbeat_timeout:
                    self.metrics.is_alive = False
                    alerts.append(HealthAlert(
                        agent_id=self.agent_id,
                        alert_type="NO_HEARTBEAT",
                        severity="CRITICAL",
                        message=f"No heartbeat for {time_since_heartbeat:.1f}s",
                        timestamp=datetime.now(),
                        suggested_action="Check agent process or restart"
                    ))
            
            # Check error rate
            if self.metrics.error_rate > 30:  # >30% errors
                alerts.append(HealthAlert(
                    agent_id=self.agent_id,
                    alert_type="HIGH_ERROR_RATE",
                    severity="CRITICAL",
                    message=f"Error rate: {self.metrics.error_rate:.1f}%",
                    timestamp=datetime.now(),
                    suggested_action="Review error logs and restart if needed"
                ))
            elif self.metrics.error_rate > 10:  # >10% errors
                alerts.append(HealthAlert(
                    agent_id=self.agent_id,
                    alert_type="HIGH_ERROR_RATE",
                    severity="WARNING",
                    message=f"Elevated error rate: {self.metrics.error_rate:.1f}%",
                    timestamp=datetime.now()
                ))
            
            # Check response time
            if self.metrics.avg_response_time > 5000:  # >5 seconds
                alerts.append(HealthAlert(
                    agent_id=self.agent_id,
                    alert_type="HIGH_LATENCY",
                    severity="WARNING",
                    message=f"High response time: {self.metrics.avg_response_time:.0f}ms",
                    timestamp=datetime.now()
                ))
            
            # Check resource usage
            if self.metrics.cpu_usage > 90:
                alerts.append(HealthAlert(
                    agent_id=self.agent_id,
                    alert_type="RESOURCE_DEPLETION",
                    severity="CRITICAL",
                    message=f"CPU usage: {self.metrics.cpu_usage:.1f}%",
                    timestamp=datetime.now()
                ))
            elif self.metrics.memory_usage > 90:
                alerts.append(HealthAlert(
                    agent_id=self.agent_id,
                    alert_type="RESOURCE_DEPLETION",
                    severity="CRITICAL",
                    message=f"Memory usage: {self.metrics.memory_usage:.1f}%",
                    timestamp=datetime.now()
                ))
            
            # Determine overall status
            if any(a.severity == "CRITICAL" for a in alerts):
                self.metrics.status = HealthStatus.CRITICAL
            elif alerts:
                self.metrics.status = HealthStatus.WARNING
            elif self.metrics.is_alive:
                self.metrics.status = HealthStatus.HEALTHY
            
            # Trigger callbacks for new alerts
            for alert in alerts:
                for callback in self.on_health_change:
                    try:
                        callback(alert)
                    except Exception:
                        logger.warning("Erro em callback on_health_change", exc_info=True)
            
            return self.metrics.status
    
    def record_recovery_attempt(self):
        """Record recovery attempt."""
        with self.lock:
            self.metrics.recovery_attempts += 1
    
    def record_restart(self):
        """Record agent restart."""
        with self.lock:
            self.metrics.total_restarts += 1
            self.metrics.uptime = 0
    
    def get_metrics_summary(self) -> Dict:
        """Get current metrics summary."""
        with self.lock:
            return {
                "agent_id": self.agent_id,
                "is_alive": self.metrics.is_alive,
                "status": self.metrics.status.value,
                "last_heartbeat": self.metrics.last_heartbeat.isoformat(),
                "cpu_usage": self.metrics.cpu_usage,
                "memory_usage": self.metrics.memory_usage,
                "avg_response_time": self.metrics.avg_response_time,
                "error_rate": self.metrics.error_rate,
                "error_categories": dict(self.metrics.error_categories),
                "recovery_attempts": self.metrics.recovery_attempts,
                "total_restarts": self.metrics.total_restarts
            }


class SystemHealthMonitor:
    """
    Manages health monitoring for all agents in the system.
    
    Features:
    - Centralized health tracking
    - System-wide alerts
    - Automatic recovery triggering
    - Performance trends
    """
    
    def __init__(self, event_bus=None):
        self.agents: Dict[str, AgentHealthMonitor] = {}
        self.lock = threading.RLock()
        self.event_bus = event_bus
        self.alerts_history: List[HealthAlert] = []
    
    def register_agent(self, agent_id: str) -> AgentHealthMonitor:
        """Register agent for health monitoring."""
        with self.lock:
            if agent_id not in self.agents:
                monitor = AgentHealthMonitor(agent_id)
                self.agents[agent_id] = monitor
                
                # Add callback to alert history
                monitor.on_health_change.append(self._on_health_alert)
                
                return monitor
            return self.agents[agent_id]
    
    def _on_health_alert(self, alert: HealthAlert):
        """Internal callback for health alerts."""
        with self.lock:
            self.alerts_history.append(alert)
            
            if self.event_bus:
                try:
                    from .events import Event, EventType
                    ev = Event(
                        type=EventType.AGENT_HEALTH_ALERT,
                        source="HealthMonitor",
                        payload={
                            "agent_id": alert.agent_id,
                            "alert_type": alert.alert_type,
                            "severity": alert.severity,
                            "message": alert.message
                        }
                    )
                    self.event_bus.publish(ev)
                except Exception:
                    logger.warning("Erro ao publicar alerta de saúde", exc_info=True)
    
    def check_all_health(self) -> Dict[str, HealthStatus]:
        """Check health of all agents."""
        with self.lock:
            statuses = {}
            for agent_id, monitor in self.agents.items():
                statuses[agent_id] = monitor.check_health()
            return statuses
    
    def get_system_health_summary(self) -> Dict:
        """Get overview of system health."""
        with self.lock:
            statuses = self.check_all_health()
            
            healthy = sum(1 for s in statuses.values() if s == HealthStatus.HEALTHY)
            warning = sum(1 for s in statuses.values() if s == HealthStatus.WARNING)
            critical = sum(1 for s in statuses.values() if s == HealthStatus.CRITICAL)
            
            return {
                "timestamp": datetime.now().isoformat(),
                "total_agents": len(self.agents),
                "healthy": healthy,
                "warning": warning,
                "critical": critical,
                "agents": {agent_id: monitor.get_metrics_summary() 
                          for agent_id, monitor in self.agents.items()},
                "recent_alerts": [
                    {
                        "agent_id": a.agent_id,
                        "alert_type": a.alert_type,
                        "severity": a.severity,
                        "timestamp": a.timestamp.isoformat()
                    }
                    for a in self.alerts_history[-20:]  # Last 20 alerts
                ]
            }
