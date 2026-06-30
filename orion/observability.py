"""
Advanced Tracing & Observability
================================
Provides comprehensive tracing, logging, and monitoring for multi-agent systems.
Based on 2026 production observability patterns.

Features:
- Distributed tracing across agents
- Performance metrics collection
- Error tracking and analysis
- Real-time monitoring dashboard data
- Alerting and anomaly detection
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict
import threading

logger = logging.getLogger("orion.observability")


class SpanStatus(str, Enum):
    """Trace span status."""
    OK = "ok"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class MetricType(str, Enum):
    """Metric types."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class TraceSpan:
    """A single trace span."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    operation: str
    agent_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = SpanStatus.OK
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0
    
    def finish(self, status: str = SpanStatus.OK) -> None:
        self.end_time = datetime.now(timezone.utc)
        self.status = status
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        self.events.append({
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": attributes or {}
        })
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Metric:
    """A collected metric."""
    name: str
    metric_type: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Alert:
    """An observability alert."""
    alert_id: str
    alert_type: str
    severity: str
    message: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TracingManager:
    """Distributed tracing manager."""
    
    def __init__(self):
        self._traces: Dict[str, List[TraceSpan]] = defaultdict(list)
        self._active_spans: Dict[str, TraceSpan] = {}
        self._lock = threading.Lock()
    
    def start_trace(self, operation: str, agent_id: str, 
                   attributes: Optional[Dict[str, Any]] = None) -> str:
        """Start a new trace."""
        trace_id = str(uuid.uuid4())
        span = TraceSpan(
            span_id=str(uuid.uuid4()),
            trace_id=trace_id,
            parent_span_id=None,
            operation=operation,
            agent_id=agent_id,
            start_time=datetime.now(timezone.utc),
            attributes=attributes or {}
        )
        
        with self._lock:
            self._traces[trace_id].append(span)
            self._active_spans[span.span_id] = span
        
        return trace_id
    
    def start_span(self, trace_id: str, operation: str, agent_id: str,
                  parent_span_id: Optional[str] = None,
                  attributes: Optional[Dict[str, Any]] = None) -> str:
        """Start a child span."""
        span = TraceSpan(
            span_id=str(uuid.uuid4()),
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            operation=operation,
            agent_id=agent_id,
            start_time=datetime.now(timezone.utc),
            attributes=attributes or {}
        )
        
        with self._lock:
            self._traces[trace_id].append(span)
            self._active_spans[span.span_id] = span
        
        return span.span_id
    
    def finish_span(self, span_id: str, status: str = SpanStatus.OK) -> None:
        """Finish a span."""
        with self._lock:
            if span_id in self._active_spans:
                self._active_spans[span_id].finish(status)
                del self._active_spans[span_id]
    
    def get_trace(self, trace_id: str) -> List[TraceSpan]:
        """Get all spans for a trace."""
        return self._traces.get(trace_id, [])
    
    def get_agent_traces(self, agent_id: str, limit: int = 100) -> List[TraceSpan]:
        """Get recent traces for an agent."""
        agent_spans = []
        for spans in self._traces.values():
            for span in spans:
                if span.agent_id == agent_id:
                    agent_spans.append(span)
        
        agent_spans.sort(key=lambda s: s.start_time, reverse=True)
        return agent_spans[:limit]
    
    def get_trace_statistics(self) -> Dict[str, Any]:
        """Get trace statistics."""
        total_traces = len(self._traces)
        total_spans = sum(len(spans) for spans in self._traces.values())
        
        agent_stats = defaultdict(lambda: {"traces": 0, "spans": 0, "errors": 0})
        for spans in self._traces.values():
            for span in spans:
                agent_stats[span.agent_id]["spans"] += 1
                if span.status == SpanStatus.ERROR:
                    agent_stats[span.agent_id]["errors"] += 1
        
        for trace_id in self._traces:
            agents = set(s.agent_id for s in self._traces[trace_id])
            for agent_id in agents:
                agent_stats[agent_id]["traces"] += 1
        
        return {
            "total_traces": total_traces,
            "total_spans": total_spans,
            "agent_statistics": dict(agent_stats)
        }


class MetricsCollector:
    """Metrics collection and aggregation."""
    
    def __init__(self):
        self._metrics: List[Metric] = []
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def increment_counter(self, name: str, value: float = 1.0, 
                         labels: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
            self._counters[key] += value
            self._metrics.append(Metric(name, MetricType.COUNTER, value, labels or {}))
    
    def set_gauge(self, name: str, value: float,
                 labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric."""
        with self._lock:
            key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
            self._gauges[key] = value
            self._metrics.append(Metric(name, MetricType.GAUGE, value, labels or {}))
    
    def record_histogram(self, name: str, value: float,
                        labels: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram value."""
        with self._lock:
            key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
            self._histograms[key].append(value)
            self._metrics.append(Metric(name, MetricType.HISTOGRAM, value, labels or {}))
    
    def get_counter(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get counter value."""
        key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
        return self._counters.get(key, 0.0)
    
    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge value."""
        key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
        return self._gauges.get(key, 0.0)
    
    def get_histogram_stats(self, name: str, 
                           labels: Optional[Dict[str, str]] = None) -> Dict[str, float]:
        """Get histogram statistics."""
        key = f"{name}_{json.dumps(labels or {}, sort_keys=True)}"
        values = self._histograms.get(key, [])
        
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_values = sorted(values)
        count = len(sorted_values)
        
        return {
            "count": count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "avg": sum(sorted_values) / count,
            "p50": sorted_values[count // 2],
            "p95": sorted_values[int(count * 0.95)],
            "p99": sorted_values[int(count * 0.99)]
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return {
            "total_metrics": len(self._metrics),
            "counters": len(self._counters),
            "gauges": len(self._gauges),
            "histograms": len(self._histograms)
        }


class AlertManager:
    """Alert management and notification."""
    
    def __init__(self):
        self._alerts: List[Alert] = []
        self._alert_rules: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
    
    def create_alert(self, alert_type: str, severity: str, 
                    message: str, source: str) -> Alert:
        """Create a new alert."""
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            alert_type=alert_type,
            severity=severity,
            message=message,
            source=source
        )
        
        with self._lock:
            self._alerts.append(alert)
            logger.warning(f"Alert created: {severity} - {message}")
        
        return alert
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        with self._lock:
            for alert in self._alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all unacknowledged alerts."""
        return [a for a in self._alerts if not a.acknowledged]
    
    def add_alert_rule(self, rule: Dict[str, Any]) -> None:
        """Add an alert rule."""
        self._alert_rules.append(rule)
    
    def evaluate_rules(self, metrics: MetricsCollector) -> List[Alert]:
        """Evaluate alert rules against metrics."""
        new_alerts = []
        
        for rule in self._alert_rules:
            metric_name = rule.get("metric")
            threshold = rule.get("threshold")
            condition = rule.get("condition", "gt")
            
            if metric_name and threshold is not None:
                value = metrics.get_gauge(metric_name)
                
                triggered = False
                if condition == "gt" and value > threshold:
                    triggered = True
                elif condition == "lt" and value < threshold:
                    triggered = True
                elif condition == "eq" and value == threshold:
                    triggered = True
                
                if triggered:
                    alert = self.create_alert(
                        alert_type="rule_triggered",
                        severity=rule.get("severity", "warning"),
                        message=f"Rule triggered: {metric_name} {condition} {threshold}",
                        source="alert_manager"
                    )
                    new_alerts.append(alert)
        
        return new_alerts


class ObservabilityManager:
    """
    Unified Observability Manager
    
    Combines tracing, metrics, and alerting for comprehensive observability.
    """
    
    def __init__(self):
        self.tracing = TracingManager()
        self.metrics = MetricsCollector()
        self.alerts = AlertManager()
        self._start_time = datetime.now(timezone.utc)
    
    def record_agent_operation(self, agent_id: str, operation: str,
                              duration_ms: float, success: bool,
                              attributes: Optional[Dict[str, Any]] = None) -> None:
        """Record an agent operation."""
        self.metrics.increment_counter(
            "agent_operations_total",
            labels={"agent": agent_id, "operation": operation, "success": str(success)}
        )
        
        self.metrics.record_histogram(
            "agent_operation_duration_ms",
            duration_ms,
            labels={"agent": agent_id, "operation": operation}
        )
        
        if not success:
            self.metrics.increment_counter(
                "agent_errors_total",
                labels={"agent": agent_id, "operation": operation}
            )
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status."""
        uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()
        
        return {
            "uptime_seconds": uptime,
            "tracing": self.tracing.get_trace_statistics(),
            "metrics": self.metrics.get_metrics_summary(),
            "active_alerts": len(self.alerts.get_active_alerts()),
            "start_time": self._start_time.isoformat()
        }
