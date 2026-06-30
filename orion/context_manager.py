"""
ORION Context Manager
=====================
Advanced context management for AI agents.

Inspired by: Anthropic Context Engineering, Manus, AgentSwing (2026)
Features:
- Context compression and summarization
- Token-aware window management
- Lazy loading of skills and tools
- Semantic relevance scoring
- Context isolation for parallel tasks
"""

import time
import json
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import deque


class CompressionStrategy(str, Enum):
    NONE = "none"
    TRUNCATE = "truncate"
    SUMMARIZE = "summarize"
    SLIDING_WINDOW = "sliding_window"
    IMPORTANCE_BASED = "importance_based"


class TokenType(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    CONTEXT = "context"


@dataclass
class TokenEstimate:
    text: str
    token_count: int
    token_type: TokenType
    importance: float = 0.5
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContextWindow:
    max_tokens: int = 128000
    reserved_output: int = 4096
    system_prompt_tokens: int = 0
    history_tokens: int = 0
    context_tokens: int = 0
    
    @property
    def available_tokens(self) -> int:
        return self.max_tokens - self.reserved_output - self.system_prompt_tokens - self.history_tokens - self.context_tokens
    
    @property
    def usage_ratio(self) -> float:
        used = self.system_prompt_tokens + self.history_tokens + self.context_tokens
        return used / self.max_tokens if self.max_tokens > 0 else 1.0
    
    @property
    def needs_compression(self) -> bool:
        return self.usage_ratio > 0.75


@dataclass
class CompressedContext:
    original_tokens: int
    compressed_tokens: int
    strategy: CompressionStrategy
    summary: str = ""
    kept_messages: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def compression_ratio(self) -> float:
        if self.original_tokens == 0:
            return 1.0
        return self.compressed_tokens / self.original_tokens


class TokenCounter:
    """Estimates token counts for text"""
    
    CHARS_PER_TOKEN = 4
    
    def count(self, text: str) -> int:
        return max(1, len(text) // self.CHARS_PER_TOKEN)
    
    def count_messages(self, messages: List[Dict[str, Any]]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += self.count(content)
            total += 4
        return total


class ImportanceScorer:
    """Scores message importance for selective retention"""
    
    RECENT_DECAY = 0.95
    
    def score(self, message: Dict[str, Any], position: int, total: int) -> float:
        score = 0.5
        
        role = message.get("role", "")
        if role == "system":
            score = 1.0
        elif role == "user":
            score = 0.7
        elif role == "assistant":
            content = message.get("content", "")
            if any(kw in content.lower() for kw in ["error", "important", "critical", "key"]):
                score = 0.8
        
        recency = (position / total) if total > 0 else 0.5
        score *= (0.5 + 0.5 * recency)
        
        content = message.get("content", "")
        if len(content) > 500:
            score *= 1.2
        if "?" in content:
            score *= 1.1
        
        return min(1.0, score)


class ContextCompressor:
    """Compresses context using various strategies"""
    
    def __init__(self, llm_fn: Optional[Callable] = None):
        self.llm_fn = llm_fn
        self.counter = TokenCounter()
        self.scorer = ImportanceScorer()
    
    def compress(self, messages: List[Dict[str, Any]], target_ratio: float = 0.3,
                 strategy: CompressionStrategy = CompressionStrategy.IMPORTANCE_BASED) -> CompressedContext:
        original_tokens = self.counter.count_messages(messages)
        
        if strategy == CompressionStrategy.NONE:
            return CompressedContext(
                original_tokens=original_tokens,
                compressed_tokens=original_tokens,
                strategy=strategy,
                kept_messages=messages
            )
        
        if strategy == CompressionStrategy.TRUNCATE:
            return self._truncate(messages, original_tokens, target_ratio)
        elif strategy == CompressionStrategy.SLIDING_WINDOW:
            return self._sliding_window(messages, original_tokens, target_ratio)
        elif strategy == CompressionStrategy.IMPORTANCE_BASED:
            return self._importance_based(messages, original_tokens, target_ratio)
        elif strategy == CompressionStrategy.SUMMARIZE:
            return self._summarize(messages, original_tokens, target_ratio)
        else:
            return self._importance_based(messages, original_tokens, target_ratio)
    
    def _truncate(self, messages: List[Dict[str, Any]], original_tokens: int,
                  target_ratio: float) -> CompressedContext:
        target_tokens = int(original_tokens * target_ratio)
        kept = []
        current_tokens = 0
        
        for msg in messages:
            msg_tokens = self.counter.count(msg.get("content", ""))
            if current_tokens + msg_tokens <= target_tokens:
                kept.append(msg)
                current_tokens += msg_tokens
        
        return CompressedContext(
            original_tokens=original_tokens,
            compressed_tokens=current_tokens,
            strategy=CompressionStrategy.TRUNCATE,
            kept_messages=kept
        )
    
    def _sliding_window(self, messages: List[Dict[str, Any]], original_tokens: int,
                        target_ratio: float) -> CompressedContext:
        target_tokens = int(original_tokens * target_ratio)
        window_size = max(5, len(messages) // 4)
        
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]
        
        recent = other_msgs[-window_size:] if len(other_msgs) > window_size else other_msgs
        kept = system_msgs + recent
        
        kept_tokens = self.counter.count_messages(kept)
        
        return CompressedContext(
            original_tokens=original_tokens,
            compressed_tokens=kept_tokens,
            strategy=CompressionStrategy.SLIDING_WINDOW,
            kept_messages=kept
        )
    
    def _importance_based(self, messages: List[Dict[str, Any]], original_tokens: int,
                          target_ratio: float) -> CompressedContext:
        target_tokens = int(original_tokens * target_ratio)
        
        scored = []
        for i, msg in enumerate(messages):
            score = self.scorer.score(msg, i, len(messages))
            scored.append((score, i, msg))
        
        scored.sort(key=lambda x: x[0], reverse=True)
        
        kept = []
        current_tokens = 0
        for score, idx, msg in scored:
            msg_tokens = self.counter.count(msg.get("content", ""))
            if current_tokens + msg_tokens <= target_tokens:
                kept.append((idx, msg))
                current_tokens += msg_tokens
        
        kept.sort(key=lambda x: x[0])
        kept_messages = [msg for _, msg in kept]
        
        return CompressedContext(
            original_tokens=original_tokens,
            compressed_tokens=current_tokens,
            strategy=CompressionStrategy.IMPORTANCE_BASED,
            kept_messages=kept_messages
        )
    
    def _summarize(self, messages: List[Dict[str, Any]], original_tokens: int,
                   target_ratio: float) -> CompressedContext:
        old_messages = messages[:len(messages)//2]
        recent_messages = messages[len(messages)//2:]
        
        summary = self._generate_summary(old_messages)
        summary_tokens = self.counter.count(summary)
        recent_tokens = self.counter.count_messages(recent_messages)
        
        kept = [{"role": "system", "content": f"Previous context summary: {summary}"}]
        kept.extend(recent_messages)
        
        return CompressedContext(
            original_tokens=original_tokens,
            compressed_tokens=summary_tokens + recent_tokens,
            strategy=CompressionStrategy.SUMMARIZE,
            summary=summary,
            kept_messages=kept
        )
    
    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        if self.llm_fn:
            content = "\n".join(f"{m.get('role', 'unknown')}: {m.get('content', '')[:200]}" for m in messages[-5:])
            return self.llm_fn(f"Summarize this conversation briefly:\n{content}")
        
        topics = set()
        for msg in messages:
            content = msg.get("content", "").lower()
            for word in ["error", "question", "answer", "code", "file", "test"]:
                if word in content:
                    topics.add(word)
        
        return f"Conversation covered: {', '.join(topics) if topics else 'general discussion'}"


class SkillLoader:
    """Lazy loading of skills and tools"""
    
    def __init__(self):
        self.registered_skills: Dict[str, Dict[str, Any]] = {}
        self.loaded_skills: Dict[str, Any] = {}
        self.load_counts: Dict[str, int] = {}
    
    def register(self, skill_name: str, loader: Callable, metadata: Optional[Dict[str, Any]] = None):
        self.registered_skills[skill_name] = {
            "loader": loader,
            "metadata": metadata or {},
            "loaded": False
        }
    
    def load(self, skill_name: str) -> Any:
        if skill_name in self.loaded_skills:
            self.load_counts[skill_name] = self.load_counts.get(skill_name, 0) + 1
            return self.loaded_skills[skill_name]
        
        if skill_name not in self.registered_skills:
            raise KeyError(f"Skill not registered: {skill_name}")
        
        skill_info = self.registered_skills[skill_name]
        skill = skill_info["loader"]()
        self.loaded_skills[skill_name] = skill
        skill_info["loaded"] = True
        self.load_counts[skill_name] = 1
        
        return skill
    
    def unload(self, skill_name: str):
        if skill_name in self.loaded_skills:
            del self.loaded_skills[skill_name]
            self.registered_skills[skill_name]["loaded"] = False
    
    def get_most_used(self, count: int = 5) -> List[Tuple[str, int]]:
        return sorted(self.load_counts.items(), key=lambda x: x[1], reverse=True)[:count]
    
    def get_token_estimate(self) -> int:
        total = 0
        for name, skill in self.loaded_skills.items():
            if hasattr(skill, '__doc__') and skill.__doc__:
                total += len(skill.__doc__) // 4
            total += 100
        return total


class ContextIsolator:
    """Isolates context for parallel tasks"""
    
    def __init__(self):
        self.contexts: Dict[str, Dict[str, Any]] = {}
    
    def create_context(self, context_id: str, base_context: Optional[Dict[str, Any]] = None):
        self.contexts[context_id] = {
            "messages": base_context.get("messages", [])[:] if base_context else [],
            "metadata": base_context.get("metadata", {}).copy() if base_context else {},
            "created_at": time.time()
        }
    
    def add_message(self, context_id: str, message: Dict[str, Any]):
        if context_id in self.contexts:
            self.contexts[context_id]["messages"].append(message)
    
    def get_messages(self, context_id: str) -> List[Dict[str, Any]]:
        if context_id in self.contexts:
            return self.contexts[context_id]["messages"]
        return []
    
    def merge(self, target_id: str, source_id: str, strategy: str = "append"):
        if target_id not in self.contexts or source_id not in self.contexts:
            return
        
        source = self.contexts[source_id]
        target = self.contexts[target_id]
        
        if strategy == "append":
            target["messages"].extend(source["messages"])
        elif strategy == "interleave":
            merged = []
            t_msgs = target["messages"]
            s_msgs = source["messages"]
            for i in range(max(len(t_msgs), len(s_msgs))):
                if i < len(t_msgs):
                    merged.append(t_msgs[i])
                if i < len(s_msgs):
                    merged.append(s_msgs[i])
            target["messages"] = merged
    
    def remove_context(self, context_id: str):
        if context_id in self.contexts:
            del self.contexts[context_id]


class ContextManager:
    """Main context management system"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        
        self.window = ContextWindow(
            max_tokens=config.get("max_tokens", 128000),
            reserved_output=config.get("reserved_output", 4096)
        )
        self.compressor = ContextCompressor(llm_fn=config.get("llm_fn"))
        self.skill_loader = SkillLoader()
        self.isolator = ContextIsolator()
        self.counter = TokenCounter()
        
        self.messages: List[Dict[str, Any]] = []
        self.compression_history: List[CompressedContext] = []
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        message = {"role": role, "content": content}
        if metadata:
            message["metadata"] = metadata
        
        self.messages.append(message)
        self._update_token_counts()
        
        if self.window.needs_compression:
            self.compress_context()
    
    def add_system_prompt(self, prompt: str):
        self.messages.insert(0, {"role": "system", "content": prompt})
        self._update_token_counts()
    
    def get_messages(self) -> List[Dict[str, Any]]:
        return self.messages.copy()
    
    def compress_context(self, strategy: CompressionStrategy = CompressionStrategy.IMPORTANCE_BASED,
                        target_ratio: float = 0.3):
        result = self.compressor.compress(self.messages, target_ratio, strategy)
        self.compression_history.append(result)
        
        self.messages = result.kept_messages
        self._update_token_counts()
        
        return result
    
    def _update_token_counts(self):
        total_tokens = 0
        for msg in self.messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            msg_tokens = self.counter.count(content)
            
            if role == "system":
                self.window.system_prompt_tokens = msg_tokens
            else:
                total_tokens += msg_tokens
        
        if self.messages and self.messages[0].get("role") == "system":
            self.window.system_prompt_tokens = self.counter.count(self.messages[0].get("content", ""))
            self.window.history_tokens = sum(
                self.counter.count(m.get("content", "")) for m in self.messages[1:]
            )
        else:
            self.window.history_tokens = total_tokens
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_messages": len(self.messages),
            "window": {
                "max_tokens": self.window.max_tokens,
                "used_tokens": self.window.system_prompt_tokens + self.window.history_tokens,
                "usage_ratio": round(self.window.usage_ratio, 3),
                "needs_compression": self.window.needs_compression,
            },
            "compressions": len(self.compression_history),
            "skills_loaded": len(self.skill_loader.loaded_skills),
            "isolated_contexts": len(self.isolator.contexts),
        }
