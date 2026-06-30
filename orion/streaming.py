"""
Streaming Responses System
==========================
Provides real-time streaming capabilities for agent responses.
Based on 2026 patterns for streaming LLM outputs.

Features:
- Token-by-token streaming
- Chunk aggregation
- Stream buffering
- Event-based streaming
- Progress tracking
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, AsyncIterator
from collections import defaultdict
import threading
import queue

logger = logging.getLogger("orion.streaming")


class StreamStatus(str, Enum):
    """Stream status."""
    IDLE = "idle"
    STREAMING = "streaming"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


class EventType(str, Enum):
    """Stream event types."""
    TOKEN = "token"
    CHUNK = "chunk"
    MESSAGE = "message"
    ERROR = "error"
    COMPLETE = "complete"
    PROGRESS = "progress"
    TOOL_CALL = "tool_call"
    THINKING = "thinking"


@dataclass
class StreamEvent:
    """A single stream event."""
    event_type: str
    data: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_sse(self) -> str:
        """Convert to Server-Sent Events format."""
        return f"event: {self.event_type}\ndata: {json.dumps(self.data)}\n\n"


@dataclass
class StreamChunk:
    """A chunk of streamed content."""
    chunk_id: int
    content: str
    is_final: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StreamSession:
    """A streaming session."""
    session_id: str
    status: str
    events: List[StreamEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StreamBuffer:
    """Buffer for stream events."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._buffer: queue.Queue = queue.Queue(maxsize=max_size)
        self._flushed: List[StreamEvent] = []
    
    def put(self, event: StreamEvent) -> bool:
        """Add an event to the buffer."""
        try:
            self._buffer.put_nowait(event)
            return True
        except queue.Full:
            return False
    
    def get(self, timeout: float = 0.1) -> Optional[StreamEvent]:
        """Get an event from the buffer."""
        try:
            return self._buffer.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def flush(self) -> List[StreamEvent]:
        """Flush all events from buffer."""
        events = []
        while not self._buffer.empty():
            try:
                event = self._buffer.get_nowait()
                events.append(event)
                self._flushed.append(event)
            except queue.Empty:
                break
        return events
    
    def get_all(self) -> List[StreamEvent]:
        """Get all events including flushed."""
        return self._flushed + list(self._buffer.queue)
    
    def clear(self) -> None:
        """Clear the buffer."""
        while not self._buffer.empty():
            try:
                self._buffer.get_nowait()
            except queue.Empty:
                break
    
    @property
    def size(self) -> int:
        return self._buffer.qsize()


class StreamAggregator:
    """Aggregate stream chunks into complete messages."""
    
    def __init__(self):
        self._chunks: Dict[str, List[StreamChunk]] = defaultdict(list)
    
    def add_chunk(self, stream_id: str, chunk: StreamChunk) -> Optional[str]:
        """Add a chunk and return complete message if ready."""
        self._chunks[stream_id].append(chunk)
        
        if chunk.is_final:
            complete_message = self.get_complete(stream_id)
            self._chunks.pop(stream_id, None)
            return complete_message
        
        return None
    
    def get_complete(self, stream_id: str) -> str:
        """Get complete aggregated message."""
        chunks = self._chunks.get(stream_id, [])
        return "".join(chunk.content for chunk in sorted(chunks, key=lambda c: c.chunk_id))
    
    def get_progress(self, stream_id: str) -> float:
        """Get aggregation progress."""
        chunks = self._chunks.get(stream_id, [])
        if not chunks:
            return 0.0
        
        has_final = any(c.is_final for c in chunks)
        return 1.0 if has_final else len(chunks) / 100.0


class StreamingSystem:
    """
    Streaming Responses System
    
    Provides real-time streaming capabilities for agent responses.
    Supports token-by-token streaming and event-based communication.
    """
    
    def __init__(self):
        self._sessions: Dict[str, StreamSession] = {}
        self._buffers: Dict[str, StreamBuffer] = {}
        self._aggregator = StreamAggregator()
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def create_session(self, session_id: str) -> StreamSession:
        """Create a new streaming session."""
        with self._lock:
            session = StreamSession(
                session_id=session_id,
                status=StreamStatus.IDLE
            )
            self._sessions[session_id] = session
            self._buffers[session_id] = StreamBuffer()
            logger.info(f"Stream session created: {session_id}")
            return session
    
    def start_streaming(self, session_id: str) -> None:
        """Start streaming for a session."""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].status = StreamStatus.STREAMING
    
    def stop_streaming(self, session_id: str) -> None:
        """Stop streaming for a session."""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].status = StreamStatus.COMPLETED
                self._sessions[session_id].completed_at = datetime.now(timezone.utc)
    
    def emit_token(self, session_id: str, token: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Emit a token event."""
        event = StreamEvent(
            event_type=EventType.TOKEN,
            data={"token": token},
            metadata=metadata or {}
        )
        self._emit_event(session_id, event)
    
    def emit_chunk(self, session_id: str, chunk: StreamChunk) -> None:
        """Emit a chunk event."""
        event = StreamEvent(
            event_type=EventType.CHUNK,
            data=chunk.to_dict(),
            metadata={"chunk_id": chunk.chunk_id}
        )
        self._emit_event(session_id, event)
        
        complete = self._aggregator.add_chunk(session_id, chunk)
        if complete:
            self.emit_complete(session_id, complete)
    
    def emit_message(self, session_id: str, message: str, 
                    metadata: Optional[Dict[str, Any]] = None) -> None:
        """Emit a complete message event."""
        event = StreamEvent(
            event_type=EventType.MESSAGE,
            data={"message": message},
            metadata=metadata or {}
        )
        self._emit_event(session_id, event)
    
    def emit_error(self, session_id: str, error: str) -> None:
        """Emit an error event."""
        event = StreamEvent(
            event_type=EventType.ERROR,
            data={"error": error}
        )
        self._emit_event(session_id, event)
    
    def emit_complete(self, session_id: str, result: str) -> None:
        """Emit a completion event."""
        event = StreamEvent(
            event_type=EventType.COMPLETE,
            data={"result": result}
        )
        self._emit_event(session_id, event)
        self.stop_streaming(session_id)
    
    def emit_progress(self, session_id: str, progress: float, 
                     message: str = "") -> None:
        """Emit a progress event."""
        event = StreamEvent(
            event_type=EventType.PROGRESS,
            data={"progress": progress, "message": message}
        )
        self._emit_event(session_id, event)
    
    def emit_thinking(self, session_id: str, thought: str) -> None:
        """Emit a thinking event."""
        event = StreamEvent(
            event_type=EventType.THINKING,
            data={"thought": thought}
        )
        self._emit_event(session_id, event)
    
    def _emit_event(self, session_id: str, event: StreamEvent) -> None:
        """Emit an event to a session."""
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].events.append(event)
            
            if session_id in self._buffers:
                self._buffers[session_id].put(event)
        
        for callback in self._callbacks.get(session_id, []):
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Stream callback error: {e}")
    
    def subscribe(self, session_id: str, callback: Callable[[StreamEvent], None]) -> None:
        """Subscribe to stream events."""
        self._callbacks[session_id].append(callback)
    
    def unsubscribe(self, session_id: str, callback: Callable) -> None:
        """Unsubscribe from stream events."""
        if session_id in self._callbacks:
            self._callbacks[session_id] = [c for c in self._callbacks[session_id] if c != callback]
    
    def get_events(self, session_id: str, since: Optional[datetime] = None) -> List[StreamEvent]:
        """Get events for a session."""
        if session_id not in self._sessions:
            return []
        
        events = self._sessions[session_id].events
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        return events
    
    def get_session(self, session_id: str) -> Optional[StreamSession]:
        """Get a streaming session."""
        return self._sessions.get(session_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get streaming statistics."""
        total_sessions = len(self._sessions)
        active = sum(1 for s in self._sessions.values() if s.status == StreamStatus.STREAMING)
        completed = sum(1 for s in self._sessions.values() if s.status == StreamStatus.COMPLETED)
        total_events = sum(len(s.events) for s in self._sessions.values())
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": active,
            "completed_sessions": completed,
            "total_events": total_events,
            "avg_events_per_session": total_events / total_sessions if total_sessions > 0 else 0
        }
