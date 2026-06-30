"""
ORION Advanced Observability
============================
OpenTelemetry-compatible tracing, metrics, and logging for AI agents.

Inspired by: Langfuse, Arize Phoenix, OpenLLMetry (2026)
Features:
- Distributed tracing with spans
- Token usage and cost tracking
- Agent execution visibility
- Structured logging
- Performance metrics
"""

import time
import uuid
import json
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict
from contextlib import contextmanager


class SpanStatus(str, Enum):
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


class SpanKind(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    AGENT = "agent"
    CHAIN = "chain"
    RETRIEVAL = "retrieval"
    EMBEDDING = "embedding"


@dataclass
class SpanEvent:
    name: str
    timestamp: float = field(default_factory=time.time)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanLink:
    trace_id: str
    span_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Span:
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    trace_id: str = ""
    parent_id: Optional[str] = None
    name: str = ""
    kind: SpanKind = SpanKind.AGENT
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[SpanEvent] = field(default_factory=list)
    links: List[SpanLink] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0
    
    def set_status(self, status: SpanStatus, message: str = ""):
        self.status = status
        if message:
            self.attributes["status_message"] = message
    
    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.events.append(SpanEvent(name=name, attributes=attributes or {}))
    
    def finish(self):
        self.end_time = time.time()


@dataclass
class Trace:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:16])
    spans: List[Span] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0
    
    @property
    def total_spans(self) -> int:
        return len(self.spans)
    
    @property
    def error_count(self) -> int:
        return sum(1 for s in self.spans if s.status == SpanStatus.ERROR)
    
    def get_span_by_id(self, span_id: str) -> Optional[Span]:
        for span in self.spans:
            if span.span_id == span_id:
                return span
        return None
    
    def get_root_spans(self) -> List[Span]:
        return [s for s in self.spans if s.parent_id is None]
    
    def get_child_spans(self, parent_id: str) -> List[Span]:
        return [s for s in self.spans if s.parent_id == parent_id]


@dataclass
class MetricPoint:
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LogEntry:
    level: str
    message: str
    timestamp: float = field(default_factory=time.time)
    attributes: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


class Tracer:
    """Distributed tracer for AI agent operations"""
    
    def __init__(self, service_name: str = "orion"):
        self.service_name = service_name
        self.traces: Dict[str, Trace] = {}
        self._local = threading.local()
    
    def start_trace(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Trace:
        trace = Trace(metadata=metadata or {})
        self.traces[trace.trace_id] = trace
        
        root_span = Span(trace_id=trace.trace_id, name=name, kind=SpanKind.AGENT)
        root_span.set_attribute("service.name", self.service_name)
        trace.spans.append(root_span)
        
        self._local.current_trace_id = trace.trace_id
        self._local.current_span_id = root_span.span_id
        
        return trace
    
    def start_span(self, name: str, kind: SpanKind = SpanKind.AGENT,
                   attributes: Optional[Dict[str, Any]] = None) -> Span:
        trace_id = getattr(self._local, 'current_trace_id', None)
        parent_id = getattr(self._local, 'current_span_id', None)
        
        if not trace_id:
            trace = self.start_trace(name)
            trace_id = trace.trace_id
        
        span = Span(trace_id=trace_id, parent_id=parent_id, name=name, kind=kind)
        if attributes:
            span.attributes.update(attributes)
        
        trace = self.traces.get(trace_id)
        if trace:
            trace.spans.append(span)
        
        self._local.current_span_id = span.span_id
        return span
    
    @contextmanager
    def span(self, name: str, kind: SpanKind = SpanKind.AGENT, **attributes):
        span = self.start_span(name, kind, attributes)
        try:
            yield span
            span.set_status(SpanStatus.OK)
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            raise
        finally:
            span.finish()
    
    def finish_span(self):
        span_id = getattr(self._local, 'current_span_id', None)
        if span_id:
            trace_id = getattr(self._local, 'current_trace_id', None)
            if trace_id:
                trace = self.traces.get(trace_id)
                if trace:
                    span = trace.get_span_by_id(span_id)
                    if span:
                        span.finish()
    
    def finish_trace(self):
        trace_id = getattr(self._local, 'current_trace_id', None)
        if trace_id:
            trace = self.traces.get(trace_id)
            if trace:
                trace.end_time = time.time()
        
        self._local.current_trace_id = None
        self._local.current_span_id = None
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        return self.traces.get(trace_id)
    
    def get_recent_traces(self, count: int = 10) -> List[Trace]:
        traces = sorted(self.traces.values(), key=lambda t: t.start_time, reverse=True)
        return traces[:count]


class MetricsCollector:
    """Collects and aggregates metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.counters: Dict[str, int] = defaultdict(int)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
    
    def record(self, name: str, value: float, attributes: Optional[Dict[str, Any]] = None):
        point = MetricPoint(name=name, value=value, attributes=attributes or {})
        self.metrics[name].append(point)
    
    def increment(self, name: str, value: int = 1):
        self.counters[name] += value
    
    def gauge(self, name: str, value: float):
        self.gauges[name] = value
    
    def histogram(self, name: str, value: float):
        self.histograms[name].append(value)
    
    def get_counter(self, name: str) -> int:
        return self.counters.get(name, 0)
    
    def get_gauge(self, name: str) -> float:
        return self.gauges.get(name, 0.0)
    
    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        values = self.histograms.get(name, [])
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        
        sorted_vals = sorted(values)
        count = len(sorted_vals)
        
        return {
            "count": count,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "avg": sum(sorted_vals) / count,
            "p50": sorted_vals[count // 2],
            "p95": sorted_vals[int(count * 0.95)] if count > 20 else sorted_vals[-1],
            "p99": sorted_vals[int(count * 0.99)] if count > 100 else sorted_vals[-1],
        }
    
    def get_all_metrics(self) -> Dict[str, Any]:
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "histograms": {name: self.get_histogram_stats(name) for name in self.histograms},
            "time_series_count": len(self.metrics)
        }


class StructuredLogger:
    """Structured logging with trace context"""
    
    def __init__(self):
        self.entries: List[LogEntry] = []
        self._local = threading.local()
    
    def set_context(self, trace_id: str, span_id: Optional[str] = None):
        self._local.trace_id = trace_id
        self._local.span_id = span_id
    
    def log(self, level: str, message: str, attributes: Optional[Dict[str, Any]] = None):
        entry = LogEntry(
            level=level,
            message=message,
            attributes=attributes or {},
            trace_id=getattr(self._local, 'trace_id', None),
            span_id=getattr(self._local, 'span_id', None)
        )
        self.entries.append(entry)
        return entry
    
    def info(self, message: str, **attributes):
        return self.log("INFO", message, attributes)
    
    def warning(self, message: str, **attributes):
        return self.log("WARNING", message, attributes)
    
    def error(self, message: str, **attributes):
        return self.log("ERROR", message, attributes)
    
    def debug(self, message: str, **attributes):
        return self.log("DEBUG", message, attributes)
    
    def get_recent(self, count: int = 100, level: Optional[str] = None) -> List[LogEntry]:
        entries = self.entries
        if level:
            entries = [e for e in entries if e.level == level]
        return entries[-count:]


class TokenTracker:
    """Tracks token usage and costs"""
    
    def __init__(self):
        self.records: List[Dict[str, Any]] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
    
    def record(self, model: str, input_tokens: int, output_tokens: int,
               input_cost_per_token: float = 0.0, output_cost_per_token: float = 0.0):
        cost = (input_tokens * input_cost_per_token + output_tokens * output_cost_per_token)
        
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        
        self.records.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "timestamp": time.time()
        })
    
    def get_by_model(self) -> Dict[str, Dict[str, Any]]:
        by_model = defaultdict(lambda: {"input": 0, "output": 0, "cost": 0.0, "calls": 0})
        for record in self.records:
            m = record["model"]
            by_model[m]["input"] += record["input_tokens"]
            by_model[m]["output"] += record["output_tokens"]
            by_model[m]["cost"] += record["cost"]
            by_model[m]["calls"] += 1
        return dict(by_model)
    
    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost": round(self.total_cost, 6),
            "total_calls": len(self.records),
            "by_model": self.get_by_model()
        }


class ObservabilitySystem:
    """Main observability system combining all components"""
    
    def __init__(self, service_name: str = "orion"):
        self.tracer = Tracer(service_name)
        self.metrics = MetricsCollector()
        self.logger = StructuredLogger()
        self.token_tracker = TokenTracker()
        
        self.service_name = service_name
    
    def start_trace(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> Trace:
        trace = self.tracer.start_trace(name, metadata)
        self.logger.set_context(trace.trace_id)
        self.metrics.increment("traces_started")
        return trace
    
    @contextmanager
    def span(self, name: str, kind: SpanKind = SpanKind.AGENT, **attributes):
        with self.tracer.span(name, kind, **attributes) as s:
            self.logger.set_context(s.trace_id, s.span_id)
            yield s
    
    def record_llm_call(self, model: str, input_tokens: int, output_tokens: int,
                        input_cost: float = 0.0, output_cost: float = 0.0,
                        duration_ms: float = 0.0):
        self.token_tracker.record(model, input_tokens, output_tokens, input_cost, output_cost)
        self.metrics.record("llm.duration_ms", duration_ms, {"model": model})
        self.metrics.record("llm.tokens.input", input_tokens, {"model": model})
        self.metrics.record("llm.tokens.output", output_tokens, {"model": model})
        self.metrics.increment("llm.calls", 1)
    
    def record_tool_call(self, tool_name: str, duration_ms: float, success: bool):
        self.metrics.record("tool.duration_ms", duration_ms, {"tool": tool_name})
        self.metrics.increment("tool.calls")
        if success:
            self.metrics.increment("tool.success")
        else:
            self.metrics.increment("tool.errors")
    
    def record_agent_step(self, agent_name: str, step_type: str, duration_ms: float):
        self.metrics.record("agent.step_duration_ms", duration_ms, {"agent": agent_name, "type": step_type})
        self.metrics.increment("agent.steps")
    
    def get_trace_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        trace = self.tracer.get_trace(trace_id)
        if not trace:
            return None
        
        return {
            "trace_id": trace.trace_id,
            "duration_ms": trace.duration_ms,
            "total_spans": trace.total_spans,
            "error_count": trace.error_count,
            "spans": [
                {
                    "span_id": s.span_id,
                    "name": s.name,
                    "kind": s.kind.value,
                    "duration_ms": s.duration_ms,
                    "status": s.status.value,
                }
                for s in trace.spans
            ]
        }
    
    def get_dashboard(self) -> Dict[str, Any]:
        return {
            "service": self.service_name,
            "traces": {
                "total": len(self.tracer.traces),
                "recent": len(self.tracer.get_recent_traces(10)),
            },
            "metrics": self.metrics.get_all_metrics(),
            "tokens": self.token_tracker.get_summary(),
            "logs": {
                "total": len(self.logger.entries),
                "errors": len(self.logger.get_recent(1000, "ERROR")),
                "warnings": len(self.logger.get_recent(1000, "WARNING")),
            }
        }
