"""
ORION Reasoning Engine
======================
Advanced reasoning patterns: ReAct, Reflexion, Plan-and-Execute, Tree of Thoughts.

Baseado em pesquisas de 2026:
- ReAct (Yao et al., 2022): Reason + Act loop
- Reflexion (Shinn et al., 2023): Self-reflection with memory
- Plan-and-Execute: Hierarchical decomposition
- Tree of Thoughts: Parallel exploration of reasoning paths
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from collections import deque


class ReasoningPattern(str, Enum):
    REACT = "react"
    REFLEXION = "reflexion"
    PLAN_EXECUTE = "plan_execute"
    TREE_OF_THOUGHTS = "tree_of_thoughts"


class StepStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Thought:
    content: str
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class Action:
    tool_name: str
    parameters: Dict[str, Any]
    thought: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class Observation:
    content: str
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class ReasoningStep:
    step_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    thought: Optional[Thought] = None
    action: Optional[Action] = None
    observation: Optional[Observation] = None
    status: StepStatus = StepStatus.PENDING
    duration_ms: float = 0.0
    tokens_used: int = 0


@dataclass
class Plan:
    plan_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal: str = ""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    status: str = "pending"
    created_at: float = field(default_factory=time.time)


@dataclass
class ThoughtBranch:
    branch_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    thought: str = ""
    score: float = 0.0
    depth: int = 0
    children: List['ThoughtBranch'] = field(default_factory=list)
    parent_id: Optional[str] = None
    is_leaf: bool = True


@dataclass
class ReasoningResult:
    pattern: ReasoningPattern
    answer: str
    steps: List[ReasoningStep]
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReActReasoner:
    """ReAct (Reason + Act) reasoning pattern"""
    
    def __init__(self, max_steps: int = 10, llm_fn: Optional[Callable] = None):
        self.max_steps = max_steps
        self.llm_fn = llm_fn
        self.steps: List[ReasoningStep] = []
    
    def reason(self, task: str, tools: Dict[str, Callable]) -> ReasoningResult:
        start_time = time.time()
        messages = [{"role": "user", "content": task}]
        
        for step_num in range(self.max_steps):
            step = ReasoningStep()
            step.status = StepStatus.IN_PROGRESS
            step_start = time.time()
            
            thought = self._think(task, messages, step_num)
            step.thought = thought
            
            if self._is_final_answer(thought.content):
                step.status = StepStatus.COMPLETED
                step.duration_ms = (time.time() - step_start) * 1000
                self.steps.append(step)
                break
            
            action = self._plan_action(thought.content, tools)
            step.action = action
            
            observation = self._execute_action(action, tools)
            step.observation = observation
            
            messages.append({"role": "assistant", "content": thought.content})
            messages.append({"role": "user", "content": f"Observation: {observation.content}"})
            
            step.status = StepStatus.COMPLETED
            step.duration_ms = (time.time() - step_start) * 1000
            self.steps.append(step)
        
        total_duration = (time.time() - start_time) * 1000
        answer = self._extract_answer(messages)
        
        return ReasoningResult(
            pattern=ReasoningPattern.REACT,
            answer=answer,
            steps=self.steps.copy(),
            total_duration_ms=total_duration,
            confidence=self._calculate_confidence()
        )
    
    def _think(self, task: str, messages: List[Dict], step: int) -> Thought:
        prompt = f"""Task: {task}
Step {step + 1} of {self.max_steps}

Analyze the current situation and decide what to do next.
If you have enough information to answer, start with "Final Answer:"
Otherwise, describe your next thought and what action to take."""
        
        response = self._call_llm(prompt)
        return Thought(content=response, confidence=0.8)
    
    def _is_final_answer(self, thought: str) -> bool:
        return thought.strip().startswith("Final Answer:")
    
    def _plan_action(self, thought: str, tools: Dict[str, Callable]) -> Action:
        tool_names = list(tools.keys())
        prompt = f"""Based on this thought: {thought}

Available tools: {tool_names}

Choose a tool and parameters. Format as JSON:
{{"tool": "tool_name", "parameters": {{...}}}}"""
        
        response = self._call_llm(prompt)
        try:
            data = json.loads(response)
            return Action(tool_name=data.get("tool", ""), parameters=data.get("parameters", {}))
        except json.JSONDecodeError:
            return Action(tool_name=tool_names[0] if tool_names else "", parameters={})
    
    def _execute_action(self, action: Action, tools: Dict[str, Callable]) -> Observation:
        if action.tool_name not in tools:
            return Observation(content=f"Tool not found: {action.tool_name}", success=False)
        
        try:
            result = tools[action.tool_name](**action.parameters)
            return Observation(content=str(result), success=True)
        except Exception as e:
            return Observation(content=f"Error: {str(e)}", success=False)
    
    def _extract_answer(self, messages: List[Dict]) -> str:
        for msg in reversed(messages):
            if msg["role"] == "assistant" and "Final Answer:" in msg["content"]:
                return msg["content"].split("Final Answer:", 1)[1].strip()
        return messages[-1]["content"] if messages else ""
    
    def _calculate_confidence(self) -> float:
        if not self.steps:
            return 0.0
        successful = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        return successful / len(self.steps)
    
    def _call_llm(self, prompt: str) -> str:
        if self.llm_fn:
            return self.llm_fn(prompt)
        return f"[Simulated LLM response for: {prompt[:50]}...]"


class ReflexionReasoner:
    """Reflexion pattern with self-reflection and memory"""
    
    def __init__(self, max_reflections: int = 3, llm_fn: Optional[Callable] = None):
        self.max_reflections = max_reflections
        self.llm_fn = llm_fn
        self.reflection_memory: List[str] = []
        self.attempts: List[ReasoningResult] = []
    
    def reason(self, task: str, tools: Dict[str, Callable], verifier: Optional[Callable] = None) -> ReasoningResult:
        best_result = None
        best_score = -1
        
        for reflection_num in range(self.max_reflections):
            react = ReActReasoner(max_steps=10, llm_fn=self.llm_fn)
            result = react.reason(task, tools)
            
            score = self._evaluate(result, verifier)
            
            if score > best_score:
                best_score = score
                best_result = result
            
            if score >= 0.9:
                break
            
            reflection = self._reflect(task, result, score)
            self.reflection_memory.append(reflection)
            
            task_with_reflection = f"""{task}

Previous attempt failed with score {score}.
Reflection: {reflection}
Please try again with these insights."""
            task = task_with_reflection
        
        if best_result:
            best_result.metadata["reflections"] = len(self.reflection_memory)
            best_result.metadata["final_score"] = best_score
        
        return best_result or ReasoningResult(
            pattern=ReasoningPattern.REFLEXION,
            answer="Failed to find solution",
            steps=[]
        )
    
    def _evaluate(self, result: ReasoningResult, verifier: Optional[Callable]) -> float:
        if verifier:
            return verifier(result.answer)
        return result.confidence
    
    def _reflect(self, task: str, result: ReasoningResult, score: float) -> str:
        prompt = f"""Task: {task}
Result: {result.answer}
Score: {score}

Reflect on why this attempt didn't succeed.
What should be done differently next time?"""
        
        return self._call_llm(prompt)
    
    def _call_llm(self, prompt: str) -> str:
        if self.llm_fn:
            return self.llm_fn(prompt)
        return f"[Simulated reflection for: {prompt[:50]}...]"


class PlanExecuteReasoner:
    """Plan-and-Execute pattern with hierarchical decomposition"""
    
    def __init__(self, llm_fn: Optional[Callable] = None):
        self.llm_fn = llm_fn
        self.plans: List[Plan] = []
    
    def reason(self, goal: str, tools: Dict[str, Callable]) -> ReasoningResult:
        start_time = time.time()
        all_steps: List[ReasoningStep] = []
        
        plan = self._create_plan(goal)
        self.plans.append(plan)
        
        while plan.current_step < len(plan.steps):
            step_info = plan.steps[plan.current_step]
            step = ReasoningStep()
            step.status = StepStatus.IN_PROGRESS
            step_start = time.time()
            
            try:
                result = self._execute_step(step_info, tools)
                step.observation = Observation(content=str(result), success=True)
                step.status = StepStatus.COMPLETED
                plan.current_step += 1
            except Exception as e:
                step.observation = Observation(content=f"Error: {str(e)}", success=False)
                step.status = StepStatus.FAILED
                
                if self._should_replan(plan, step_info, str(e)):
                    new_plan = self._replan(goal, plan, str(e))
                    self.plans.append(new_plan)
                    plan = new_plan
                    continue
                else:
                    plan.current_step += 1
            
            step.duration_ms = (time.time() - step_start) * 1000
            all_steps.append(step)
        
        plan.status = "completed"
        total_duration = (time.time() - start_time) * 1000
        
        answer = self._synthesize_answer(goal, all_steps)
        
        return ReasoningResult(
            pattern=ReasoningPattern.PLAN_EXECUTE,
            answer=answer,
            steps=all_steps,
            total_duration_ms=total_duration,
            confidence=self._calculate_confidence(all_steps),
            metadata={"plans_created": len(self.plans)}
        )
    
    def _create_plan(self, goal: str) -> Plan:
        prompt = f"""Goal: {goal}

Create a step-by-step plan to achieve this goal.
Return as JSON array of steps:
[{{"description": "...", "tool": "...", "params": {{...}}}}]"""
        
        response = self._call_llm(prompt)
        try:
            steps = json.loads(response)
        except json.JSONDecodeError:
            steps = [{"description": "Execute goal", "tool": "default", "params": {}}]
        
        return Plan(goal=goal, steps=steps)
    
    def _execute_step(self, step_info: Dict, tools: Dict[str, Callable]) -> Any:
        tool_name = step_info.get("tool", "")
        params = step_info.get("params", {})
        
        if tool_name in tools:
            return tools[tool_name](**params)
        return f"Executed: {step_info.get('description', 'unknown')}"
    
    def _should_replan(self, plan: Plan, failed_step: Dict, error: str) -> bool:
        return "critical" in failed_step.get("description", "").lower()
    
    def _replan(self, goal: str, old_plan: Plan, error: str) -> Plan:
        prompt = f"""Goal: {goal}
Previous plan failed at step {old_plan.current_step}: {error}

Create a new plan avoiding the failed approach."""
        
        return self._create_plan(prompt)
    
    def _synthesize_answer(self, goal: str, steps: List[ReasoningStep]) -> str:
        completed = [s for s in steps if s.status == StepStatus.COMPLETED]
        return f"Goal '{goal}' completed with {len(completed)}/{len(steps)} steps successful"
    
    def _calculate_confidence(self, steps: List[ReasoningStep]) -> float:
        if not steps:
            return 0.0
        successful = sum(1 for s in steps if s.status == StepStatus.COMPLETED)
        return successful / len(steps)
    
    def _call_llm(self, prompt: str) -> str:
        if self.llm_fn:
            return self.llm_fn(prompt)
        return '[{"description": "Simulated step", "tool": "default", "params": {}}]'


class TreeOfThoughtsReasoner:
    """Tree of Thoughts pattern with parallel exploration"""
    
    def __init__(self, max_depth: int = 3, branch_factor: int = 3, llm_fn: Optional[Callable] = None):
        self.max_depth = max_depth
        self.branch_factor = branch_factor
        self.llm_fn = llm_fn
    
    def reason(self, task: str, tools: Dict[str, Callable]) -> ReasoningResult:
        start_time = time.time()
        all_steps: List[ReasoningStep] = []
        
        root = ThoughtBranch(thought=task, depth=0)
        best_leaf = self._search(root, task, tools, all_steps)
        
        total_duration = (time.time() - start_time) * 1000
        
        return ReasoningResult(
            pattern=ReasoningPattern.TREE_OF_THOUGHTS,
            answer=best_leaf.thought if best_leaf else "No solution found",
            steps=all_steps,
            total_duration_ms=total_duration,
            confidence=best_leaf.score if best_leaf else 0.0,
            metadata={"branches_explored": self._count_branches(root)}
        )
    
    def _search(self, node: ThoughtBranch, task: str, tools: Dict[str, Callable], steps: List[ReasoningStep]) -> Optional[ThoughtBranch]:
        if node.depth >= self.max_depth:
            node.score = self._evaluate(node.thought, task)
            return node
        
        children = self._generate_children(node, task)
        node.children = children
        node.is_leaf = False
        
        step = ReasoningStep()
        step.status = StepStatus.IN_PROGRESS
        step_start = time.time()
        
        scored_children = []
        for child in children:
            child.score = self._evaluate(child.thought, task)
            scored_children.append(child)
        
        scored_children.sort(key=lambda x: x.score, reverse=True)
        top_children = scored_children[:self.branch_factor]
        
        best_leaf = None
        best_score = -1
        
        for child in top_children:
            leaf = self._search(child, task, tools, steps)
            if leaf and leaf.score > best_score:
                best_score = leaf.score
                best_leaf = leaf
        
        step.status = StepStatus.COMPLETED
        step.duration_ms = (time.time() - step_start) * 1000
        step.thought = Thought(content=f"Evaluated {len(children)} branches, best score: {best_score:.2f}")
        steps.append(step)
        
        return best_leaf
    
    def _generate_children(self, node: ThoughtBranch, task: str) -> List[ThoughtBranch]:
        prompt = f"""Task: {task}
Current thought: {node.thought}
Depth: {node.depth}

Generate {self.branch_factor} different next thoughts or approaches.
Each should be a distinct direction to explore."""
        
        response = self._call_llm(prompt)
        
        children = []
        for i in range(self.branch_factor):
            child = ThoughtBranch(
                thought=f"{node.thought} -> Option {i+1}: {response[:100]}",
                depth=node.depth + 1,
                parent_id=node.branch_id
            )
            children.append(child)
        
        return children
    
    def _evaluate(self, thought: str, task: str) -> float:
        prompt = f"""Task: {task}
Proposed thought: {thought}

Rate how promising this thought is from 0.0 to 1.0.
Return only the number."""
        
        response = self._call_llm(prompt)
        try:
            return float(response.strip())
        except ValueError:
            return 0.5
    
    def _count_branches(self, node: ThoughtBranch) -> int:
        count = 1
        for child in node.children:
            count += self._count_branches(child)
        return count
    
    def _call_llm(self, prompt: str) -> str:
        if self.llm_fn:
            return self.llm_fn(prompt)
        return "Alternative approach 1; Alternative approach 2; Alternative approach 3"


class ReasoningEngine:
    """Main reasoning engine that orchestrates different patterns"""
    
    def __init__(self, llm_fn: Optional[Callable] = None):
        self.llm_fn = llm_fn
        self.reasoners = {
            ReasoningPattern.REACT: ReActReasoner(llm_fn=llm_fn),
            ReasoningPattern.REFLEXION: ReflexionReasoner(llm_fn=llm_fn),
            ReasoningPattern.PLAN_EXECUTE: PlanExecuteReasoner(llm_fn=llm_fn),
            ReasoningPattern.TREE_OF_THOUGHTS: TreeOfThoughtsReasoner(llm_fn=llm_fn),
        }
        self.history: List[ReasoningResult] = []
    
    def reason(self, task: str, pattern: ReasoningPattern = ReasoningPattern.REACT,
               tools: Optional[Dict[str, Callable]] = None, **kwargs) -> ReasoningResult:
        tools = tools or {}
        reasoner = self.reasoners.get(pattern)
        
        if not reasoner:
            raise ValueError(f"Unknown reasoning pattern: {pattern}")
        
        if pattern == ReasoningPattern.REACT:
            result = reasoner.reason(task, tools)
        elif pattern == ReasoningPattern.REFLEXION:
            result = reasoner.reason(task, tools, kwargs.get("verifier"))
        elif pattern == ReasoningPattern.PLAN_EXECUTE:
            result = reasoner.reason(task, tools)
        elif pattern == ReasoningPattern.TREE_OF_THOUGHTS:
            result = reasoner.reason(task, tools)
        else:
            result = reasoner.reason(task, tools)
        
        self.history.append(result)
        return result
    
    def auto_select_pattern(self, task: str) -> ReasoningPattern:
        task_lower = task.lower()
        
        if any(word in task_lower for word in ["complex", "multi-step", "plan", "workflow"]):
            return ReasoningPattern.PLAN_EXECUTE
        elif any(word in task_lower for word in ["creative", "explore", "alternatives", "options"]):
            return ReasoningPattern.TREE_OF_THOUGHTS
        elif any(word in task_lower for word in ["improve", "retry", "learn", "reflect"]):
            return ReasoningPattern.REFLEXION
        else:
            return ReasoningPattern.REACT
    
    def get_stats(self) -> Dict[str, Any]:
        if not self.history:
            return {"total": 0}
        
        pattern_counts = {}
        for result in self.history:
            p = result.pattern.value
            pattern_counts[p] = pattern_counts.get(p, 0) + 1
        
        avg_confidence = sum(r.confidence for r in self.history) / len(self.history)
        avg_duration = sum(r.total_duration_ms for r in self.history) / len(self.history)
        
        return {
            "total": len(self.history),
            "patterns": pattern_counts,
            "avg_confidence": round(avg_confidence, 3),
            "avg_duration_ms": round(avg_duration, 2)
        }
