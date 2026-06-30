"""
ORION Model Router
==================
Dynamic model selection based on task complexity, cost, and performance.

Inspired by: RouteLLM, Martian, Not Diamond, OpenRouter (2026)
Features:
- Task complexity classification
- Cost-aware routing
- Fallback chains
- Performance tracking
- A/B testing support
"""

import time
import uuid
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import defaultdict


class TaskComplexity(str, Enum):
    SIMPLE = "simple"          # Text ops, formatting, Q&A
    STANDARD = "standard"      # Coding, writing, analysis
    COMPLEX = "complex"        # Architecture, debugging, reasoning
    REASONING = "reasoning"    # Math, multi-step logic, novel problems


class ModelTier(str, Enum):
    NANO = "nano"              # $0.01-0.30/M tokens
    MID = "mid"                # $0.50-3.00/M tokens
    FRONTIER = "frontier"      # $3.00-15.00/M tokens
    REASONING = "reasoning"    # $6.00-60.00/M tokens


@dataclass
class ModelConfig:
    model_id: str
    name: str
    tier: ModelTier
    provider: str
    input_cost_per_mtok: float
    output_cost_per_mtok: float
    max_tokens: int = 4096
    supports_tools: bool = True
    supports_vision: bool = False
    latency_ms: float = 1000.0
    quality_score: float = 0.8
    enabled: bool = True


@dataclass
class RoutingDecision:
    model_id: str
    reason: str
    complexity: TaskComplexity
    estimated_cost: float
    alternatives: List[str]
    confidence: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class RoutingStats:
    total_requests: int = 0
    by_model: Dict[str, int] = field(default_factory=dict)
    by_complexity: Dict[str, int] = field(default_factory=dict)
    total_cost: float = 0.0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0


class TaskClassifier:
    """Classifies task complexity based on content analysis"""
    
    COMPLEXITY_KEYWORDS = {
        TaskComplexity.SIMPLE: [
            "format", "convert", "list", "simple", "quick", "basic",
            "what is", "define", "explain briefly", "summary"
        ],
        TaskComplexity.STANDARD: [
            "write", "create", "implement", "code", "function", "class",
            "analyze", "review", "refactor", "test"
        ],
        TaskComplexity.COMPLEX: [
            "architect", "design", "debug", "optimize", "performance",
            "security", "scale", "distributed", "complex", "multi-step"
        ],
        TaskComplexity.REASONING: [
            "prove", "math", "logic", "reason", "deduce", "calculate",
            "algorithm", "proof", "theorem", "novel", "creative"
        ]
    }
    
    def classify(self, task: str) -> Tuple[TaskComplexity, float]:
        task_lower = task.lower()
        scores = {complexity: 0 for complexity in TaskComplexity}
        
        for complexity, keywords in self.COMPLEXITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in task_lower:
                    scores[complexity] += 1
        
        task_length = len(task.split())
        if task_length > 100:
            scores[TaskComplexity.COMPLEX] += 2
        elif task_length > 50:
            scores[TaskComplexity.STANDARD] += 1
        
        if "?" in task:
            scores[TaskComplexity.SIMPLE] += 1
        
        max_score = max(scores.values())
        if max_score == 0:
            return TaskComplexity.STANDARD, 0.5
        
        best_complexity = max(scores, key=scores.get)
        total = sum(scores.values())
        confidence = scores[best_complexity] / total if total > 0 else 0.5
        
        return best_complexity, confidence


class CostTracker:
    """Tracks costs across models and tasks"""
    
    def __init__(self):
        self.records: List[Dict[str, Any]] = []
        self.budget_limit: float = float('inf')
        self.current_spend: float = 0.0
    
    def record(self, model_id: str, input_tokens: int, output_tokens: int,
               model_config: ModelConfig) -> float:
        cost = (input_tokens * model_config.input_cost_per_mtok / 1_000_000 +
                output_tokens * model_config.output_cost_per_mtok / 1_000_000)
        
        self.current_spend += cost
        
        self.records.append({
            "model_id": model_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost,
            "timestamp": time.time()
        })
        
        return cost
    
    def get_cost_by_model(self) -> Dict[str, float]:
        costs = defaultdict(float)
        for record in self.records:
            costs[record["model_id"]] += record["cost"]
        return dict(costs)
    
    def get_daily_cost(self, date: Optional[str] = None) -> float:
        today = date or time.strftime("%Y-%m-%d")
        return sum(
            r["cost"] for r in self.records
            if time.strftime("%Y-%m-%d", time.localtime(r["timestamp"])) == today
        )
    
    def is_over_budget(self) -> bool:
        return self.current_spend >= self.budget_limit
    
    def set_budget(self, limit: float):
        self.budget_limit = limit


class ModelRouter:
    """Main model router with dynamic selection"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        
        self.models: Dict[str, ModelConfig] = {}
        self.classifier = TaskClassifier()
        self.cost_tracker = CostTracker()
        self.stats = RoutingStats()
        self.routing_history: List[RoutingDecision] = []
        
        self._init_default_models()
        
        if "budget_limit" in config:
            self.cost_tracker.set_budget(config["budget_limit"])
    
    def _init_default_models(self):
        defaults = [
            ModelConfig(
                model_id="gpt-4o-mini",
                name="GPT-4o Mini",
                tier=ModelTier.NANO,
                provider="openai",
                input_cost_per_mtok=0.15,
                output_cost_per_mtok=0.60,
                latency_ms=500,
                quality_score=0.7
            ),
            ModelConfig(
                model_id="claude-haiku",
                name="Claude Haiku",
                tier=ModelTier.NANO,
                provider="anthropic",
                input_cost_per_mtok=0.25,
                output_cost_per_mtok=1.25,
                latency_ms=400,
                quality_score=0.75
            ),
            ModelConfig(
                model_id="gpt-4o",
                name="GPT-4o",
                tier=ModelTier.MID,
                provider="openai",
                input_cost_per_mtok=2.50,
                output_cost_per_mtok=10.00,
                latency_ms=1000,
                quality_score=0.85
            ),
            ModelConfig(
                model_id="claude-sonnet",
                name="Claude Sonnet",
                tier=ModelTier.MID,
                provider="anthropic",
                input_cost_per_mtok=3.00,
                output_cost_per_mtok=15.00,
                latency_ms=1200,
                quality_score=0.88
            ),
            ModelConfig(
                model_id="claude-opus",
                name="Claude Opus",
                tier=ModelTier.FRONTIER,
                provider="anthropic",
                input_cost_per_mtok=15.00,
                output_cost_per_mtok=75.00,
                latency_ms=2000,
                quality_score=0.95
            ),
            ModelConfig(
                model_id="gpt-5",
                name="GPT-5",
                tier=ModelTier.FRONTIER,
                provider="openai",
                input_cost_per_mtok=10.00,
                output_cost_per_mtok=30.00,
                latency_ms=1500,
                quality_score=0.93
            ),
        ]
        
        for model in defaults:
            self.models[model.model_id] = model
    
    def add_model(self, model: ModelConfig):
        self.models[model.model_id] = model
    
    def remove_model(self, model_id: str):
        if model_id in self.models:
            del self.models[model_id]
    
    def route(self, task: str, **kwargs) -> RoutingDecision:
        complexity, confidence = self.classifier.classify(task)
        
        preferred_provider = kwargs.get("provider")
        require_tools = kwargs.get("require_tools", False)
        require_vision = kwargs.get("require_vision", False)
        max_cost = kwargs.get("max_cost")
        
        candidates = self._get_candidates(
            complexity, preferred_provider, require_tools, require_vision
        )
        
        if max_cost:
            candidates = [m for m in candidates if m.input_cost_per_mtok <= max_cost]
        
        if not candidates:
            candidates = [m for m in self.models.values() if m.enabled]
        
        if not candidates:
            raise ValueError("No available models for routing")
        
        selected = self._select_best(candidates, complexity)
        
        estimated_tokens = len(task.split()) * 2
        estimated_cost = (estimated_tokens * selected.input_cost_per_mtok / 1_000_000 +
                         estimated_tokens * 0.5 * selected.output_cost_per_mtok / 1_000_000)
        
        alternatives = [m.model_id for m in candidates if m.model_id != selected.model_id][:3]
        
        decision = RoutingDecision(
            model_id=selected.model_id,
            reason=f"Routed {complexity.value} task to {selected.name}",
            complexity=complexity,
            estimated_cost=estimated_cost,
            alternatives=alternatives,
            confidence=confidence
        )
        
        self.routing_history.append(decision)
        self.stats.total_requests += 1
        self.stats.by_model[selected.model_id] = self.stats.by_model.get(selected.model_id, 0) + 1
        self.stats.by_complexity[complexity.value] = self.stats.by_complexity.get(complexity.value, 0) + 1
        
        return decision
    
    def _get_candidates(self, complexity: TaskComplexity, preferred_provider: Optional[str],
                       require_tools: bool, require_vision: bool) -> List[ModelConfig]:
        candidates = []
        
        for model in self.models.values():
            if not model.enabled:
                continue
            if preferred_provider and model.provider != preferred_provider:
                continue
            if require_tools and not model.supports_tools:
                continue
            if require_vision and not model.supports_vision:
                continue
            candidates.append(model)
        
        return candidates
    
    def _select_best(self, candidates: List[ModelConfig], complexity: TaskComplexity) -> ModelConfig:
        tier_preferences = {
            TaskComplexity.SIMPLE: [ModelTier.NANO, ModelTier.MID],
            TaskComplexity.STANDARD: [ModelTier.MID, ModelTier.NANO],
            TaskComplexity.COMPLEX: [ModelTier.MID, ModelTier.FRONTIER],
            TaskComplexity.REASONING: [ModelTier.REASONING, ModelTier.FRONTIER],
        }
        
        preferred_tiers = tier_preferences.get(complexity, [ModelTier.MID])
        
        for tier in preferred_tiers:
            tier_models = [m for m in candidates if m.tier == tier]
            if tier_models:
                return min(tier_models, key=lambda m: m.input_cost_per_mtok)
        
        return min(candidates, key=lambda m: m.input_cost_per_mtok)
    
    def record_usage(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        model = self.models.get(model_id)
        if not model:
            return 0.0
        
        cost = self.cost_tracker.record(model_id, input_tokens, output_tokens, model)
        self.stats.total_cost += cost
        return cost
    
    def get_fallback_chain(self, primary_model: str) -> List[str]:
        primary = self.models.get(primary_model)
        if not primary:
            return list(self.models.keys())[:3]
        
        chain = []
        for model in self.models.values():
            if model.model_id == primary_model:
                continue
            if model.tier.value <= primary.tier.value:
                chain.append(model.model_id)
        
        chain.sort(key=lambda mid: self.models[mid].input_cost_per_mtok)
        return chain[:3]
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self.stats.total_requests,
            "by_model": self.stats.by_model,
            "by_complexity": self.stats.by_complexity,
            "total_cost": round(self.stats.total_cost, 6),
            "daily_cost": round(self.cost_tracker.get_daily_cost(), 6),
            "budget_remaining": round(self.cost_tracker.budget_limit - self.cost_tracker.current_spend, 6),
            "available_models": len([m for m in self.models.values() if m.enabled])
        }
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        model = self.models.get(model_id)
        if not model:
            return None
        
        return {
            "model_id": model.model_id,
            "name": model.name,
            "tier": model.tier.value,
            "provider": model.provider,
            "input_cost_per_mtok": model.input_cost_per_mtok,
            "output_cost_per_mtok": model.output_cost_per_mtok,
            "quality_score": model.quality_score,
            "enabled": model.enabled
        }
