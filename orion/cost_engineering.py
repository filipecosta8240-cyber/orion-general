"""
Cost Engineering & Token Optimization
=====================================
Manages token usage, cost tracking, and optimization for LLM-based agents.
Based on 2026 production patterns for cost-effective multi-agent systems.

Features:
- Token usage tracking per agent
- Cost modeling and budgeting
- Model tiering (cheap → expensive)
- Token optimization strategies
- Cost alerts and limits
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import threading

logger = logging.getLogger("orion.cost_engineering")


class ModelTier(str, Enum):
    """Model cost tiers."""
    FREE = "free"
    BUDGET = "budget"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class CostAlertType(str, Enum):
    """Types of cost alerts."""
    BUDGET_THRESHOLD = "budget_threshold"
    DAILY_LIMIT = "daily_limit"
    MONTHLY_LIMIT = "monthly_limit"
    ANOMALY = "anomaly"


@dataclass
class ModelPricing:
    """Pricing information for a model."""
    model_name: str
    tier: str
    input_cost_per_1k: float  # Cost per 1000 input tokens
    output_cost_per_1k: float  # Cost per 1000 output tokens
    max_context: int
    capabilities: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TokenUsage:
    """Token usage record."""
    agent_id: str
    model_name: str
    input_tokens: int
    output_tokens: int
    task_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CostRecord:
    """Cost record for tracking."""
    record_id: str
    agent_id: str
    model_name: str
    input_cost: float
    output_cost: float
    total_cost: float
    tokens_used: int
    task_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Budget:
    """Budget configuration."""
    budget_id: str
    name: str
    daily_limit: float
    monthly_limit: float
    alert_threshold: float = 0.8  # 80% threshold
    current_daily: float = 0.0
    current_monthly: float = 0.0
    last_reset: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CostEngineeringManager:
    """
    Cost Engineering & Token Optimization Manager
    
    Manages token usage, cost tracking, and optimization for LLM-based agents.
    Helps optimize costs while maintaining performance.
    """
    
    def __init__(self):
        self._model_pricing: Dict[str, ModelPricing] = {}
        self._token_usage: List[TokenUsage] = []
        self._cost_records: List[CostRecord] = []
        self._budgets: Dict[str, Budget] = {}
        self._agent_costs: Dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()
        self._init_default_pricing()
        
    def _init_default_pricing(self) -> None:
        """Initialize default model pricing."""
        default_models = [
            ModelPricing("gpt-4o", ModelTier.PREMIUM, 0.005, 0.015, 128000, ["reasoning", "code"]),
            ModelPricing("gpt-4o-mini", ModelTier.STANDARD, 0.00015, 0.0006, 128000, ["general"]),
            ModelPricing("claude-3-opus", ModelTier.ENTERPRISE, 0.015, 0.075, 200000, ["reasoning", "analysis"]),
            ModelPricing("claude-3-sonnet", ModelTier.PREMIUM, 0.003, 0.015, 200000, ["general", "code"]),
            ModelPricing("claude-3-haiku", ModelTier.BUDGET, 0.00025, 0.00125, 200000, ["fast"]),
            ModelPricing("local-llama", ModelTier.FREE, 0.0, 0.0, 8192, ["local"]),
        ]
        
        for model in default_models:
            self._model_pricing[model.model_name] = model
    
    def register_model(self, pricing: ModelPricing) -> None:
        """Register a model with pricing information."""
        self._model_pricing[pricing.model_name] = pricing
        logger.info(f"Model registered: {pricing.model_name} ({pricing.tier})")
    
    def record_token_usage(self, usage: TokenUsage) -> CostRecord:
        """Record token usage and calculate cost."""
        with self._lock:
            pricing = self._model_pricing.get(usage.model_name)
            if not pricing:
                pricing = ModelPricing(usage.model_name, ModelTier.STANDARD, 0.001, 0.002, 100000)
            
            input_cost = (usage.input_tokens / 1000) * pricing.input_cost_per_1k
            output_cost = (usage.output_tokens / 1000) * pricing.output_cost_per_1k
            total_cost = input_cost + output_cost
            
            record = CostRecord(
                record_id=f"cost_{len(self._cost_records)}",
                agent_id=usage.agent_id,
                model_name=usage.model_name,
                input_cost=input_cost,
                output_cost=output_cost,
                total_cost=total_cost,
                tokens_used=usage.total_tokens,
                task_id=usage.task_id
            )
            
            self._cost_records.append(record)
            self._agent_costs[usage.agent_id] += total_cost
            self._token_usage.append(usage)
            
            self._check_budget_alerts(usage.agent_id, total_cost)
            
            return record
    
    def _check_budget_alerts(self, agent_id: str, cost: float) -> None:
        """Check and trigger budget alerts."""
        for budget in self._budgets.values():
            budget.current_daily += cost
            budget.current_monthly += cost
            
            if budget.current_daily >= budget.daily_limit * budget.alert_threshold:
                logger.warning(f"Budget alert: {budget.name} daily limit {budget.alert_threshold*100}% reached")
            
            if budget.current_daily >= budget.daily_limit:
                logger.error(f"Budget exceeded: {budget.name} daily limit reached")
    
    def get_optimal_model(self, task_type: str, max_cost: Optional[float] = None) -> Optional[ModelPricing]:
        """Get the optimal model for a task type based on cost and capabilities."""
        suitable_models = []
        
        for pricing in self._model_pricing.values():
            if task_type in pricing.capabilities or "general" in pricing.capabilities:
                if max_cost is None or pricing.input_cost_per_1k <= max_cost:
                    suitable_models.append(pricing)
        
        if not suitable_models:
            return None
            
        suitable_models.sort(key=lambda m: (m.input_cost_per_1k + m.output_cost_per_1k))
        return suitable_models[0]
    
    def get_agent_cost_summary(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
        """Get cost summary for an agent."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        agent_records = [
            r for r in self._cost_records 
            if r.agent_id == agent_id and r.timestamp >= cutoff
        ]
        
        total_cost = sum(r.total_cost for r in agent_records)
        total_tokens = sum(r.tokens_used for r in agent_records)
        
        model_usage = defaultdict(lambda: {"cost": 0.0, "tokens": 0})
        for record in agent_records:
            model_usage[record.model_name]["cost"] += record.total_cost
            model_usage[record.model_name]["tokens"] += record.tokens_used
        
        return {
            "agent_id": agent_id,
            "period_days": days,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "avg_cost_per_task": total_cost / len(agent_records) if agent_records else 0,
            "model_breakdown": dict(model_usage)
        }
    
    def get_system_cost_summary(self, days: int = 30) -> Dict[str, Any]:
        """Get system-wide cost summary."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent_records = [
            r for r in self._cost_records if r.timestamp >= cutoff
        ]
        
        total_cost = sum(r.total_cost for r in recent_records)
        total_tokens = sum(r.tokens_used for r in recent_records)
        
        agent_costs = defaultdict(float)
        for record in recent_records:
            agent_costs[record.agent_id] += record.total_cost
        
        return {
            "period_days": days,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "total_requests": len(recent_records),
            "agent_costs": dict(agent_costs),
            "avg_cost_per_request": total_cost / len(recent_records) if recent_records else 0
        }
    
    def create_budget(self, budget: Budget) -> None:
        """Create a new budget."""
        self._budgets[budget.budget_id] = budget
        logger.info(f"Budget created: {budget.name}")
    
    def get_cost_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommendations for cost optimization."""
        recommendations = []
        
        agent_summary = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "requests": 0})
        for record in self._cost_records[-100:]:  # Last 100 requests
            agent_summary[record.agent_id]["cost"] += record.total_cost
            agent_summary[record.agent_id]["tokens"] += record.tokens_used
            agent_summary[record.agent_id]["requests"] += 1
        
        for agent_id, data in agent_summary.items():
            if data["requests"] > 10:
                avg_cost = data["cost"] / data["requests"]
                if avg_cost > 0.01:  # High cost per request
                    recommendations.append({
                        "agent_id": agent_id,
                        "type": "model_downgrade",
                        "current_avg_cost": avg_cost,
                        "recommendation": "Consider using a cheaper model for routine tasks"
                    })
        
        return recommendations
