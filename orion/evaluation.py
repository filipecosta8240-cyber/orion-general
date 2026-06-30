"""
ORION Evaluation Framework
============================
Benchmarking and evaluation system for AI agents.

Features:
- Agent performance benchmarking
- Task completion evaluation
- Accuracy and quality metrics
- Latency and cost tracking
- Custom test suites
- Report generation
"""

import time
import json
import uuid
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict
from pathlib import Path
import logging

logger = logging.getLogger("orion.evaluation")


class MetricType(str, Enum):
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1_score"
    LATENCY = "latency_ms"
    COST = "cost"
    TOKENS = "tokens"
    COMPLETION = "completion_rate"
    CONFIDENCE = "confidence"


@dataclass
class TestCase:
    """Individual test case"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    input_data: Dict[str, Any] = field(default_factory=dict)
    expected_output: Any = None
    tags: List[str] = field(default_factory=list)
    weight: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "input_data": self.input_data,
            "expected_output": str(self.expected_output)[:200],
            "tags": self.tags,
            "weight": self.weight
        }


@dataclass
class TestSuite:
    """Collection of test cases"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    description: str = ""
    tests: List[TestCase] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    def add_test(self, test: TestCase) -> "TestSuite":
        self.tests.append(test)
        return self
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "test_count": len(self.tests),
            "tags": self.tags
        }


@dataclass
class TestResult:
    """Result of a single test execution"""
    test_id: str = ""
    passed: bool = False
    score: float = 0.0
    output: Any = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "passed": self.passed,
            "score": self.score,
            "error": self.error,
            "latency_ms": self.latency_ms
        }


@dataclass
class SuiteResult:
    """Result of a test suite execution"""
    suite_id: str = ""
    suite_name: str = ""
    results: List[TestResult] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    @property
    def duration_ms(self) -> float:
        if self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return (time.time() - self.started_at) * 1000
    
    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for r in self.results if r.passed) / len(self.results)
    
    @property
    def average_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.score for r in self.results) / len(self.results)
    
    @property
    def average_latency(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.latency_ms for r in self.results) / len(self.results)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "suite_name": self.suite_name,
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "pass_rate": self.pass_rate,
            "average_score": self.average_score,
            "average_latency_ms": self.average_latency,
            "duration_ms": self.duration_ms,
            "results": [r.to_dict() for r in self.results]
        }


class MetricCalculator:
    """Calculate evaluation metrics"""
    
    @staticmethod
    def accuracy(correct: int, total: int) -> float:
        return correct / total if total > 0 else 0.0
    
    @staticmethod
    def precision(true_pos: int, false_pos: int) -> float:
        return true_pos / (true_pos + false_pos) if (true_pos + false_pos) > 0 else 0.0
    
    @staticmethod
    def recall(true_pos: int, false_neg: int) -> float:
        return true_pos / (true_pos + false_neg) if (true_pos + false_neg) > 0 else 0.0
    
    @staticmethod
    def f1_score(precision: float, recall: float) -> float:
        return 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    @staticmethod
    def exact_match(output: Any, expected: Any) -> bool:
        return str(output).strip().lower() == str(expected).strip().lower()
    
    @staticmethod
    def partial_match(output: Any, expected: Any) -> float:
        """Calculate partial match score (0-1)"""
        out_str = str(output).lower().strip()
        exp_str = str(expected).lower().strip()
        
        if not exp_str:
            return 0.0
        
        # Check what percentage of expected is in output
        exp_words = set(exp_str.split())
        out_words = set(out_str.split())
        
        if not exp_words:
            return 0.0
        
        intersection = exp_words & out_words
        return len(intersection) / len(exp_words)


class Evaluator:
    """
    Evaluation framework for benchmarking agents and systems.
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("orion_eval")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.suites: Dict[str, TestSuite] = {}
        self.results: Dict[str, SuiteResult] = {}
        self.history: List[Dict[str, Any]] = []
        
        self._load_history()
        
        logger.info("Evaluator initialized")
    
    def _load_history(self) -> None:
        """Load evaluation history"""
        try:
            history_file = self.storage_path / "eval_history.json"
            if history_file.exists():
                self.history = json.loads(history_file.read_text(encoding="utf-8"))
        except Exception:
            self.history = []
    
    def _save_history(self) -> None:
        """Save evaluation history"""
        try:
            history_file = self.storage_path / "eval_history.json"
            # Keep last 100 results
            if len(self.history) > 100:
                self.history = self.history[-100:]
            history_file.write_text(json.dumps(self.history, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Error saving eval history: {e}")
    
    def register_suite(self, suite: TestSuite) -> str:
        """Register a test suite"""
        self.suites[suite.id] = suite
        logger.info(f"Registered test suite: {suite.name} ({len(suite.tests)} tests)")
        return suite.id
    
    def run_suite(
        self,
        suite_id: str,
        handler: Callable[[Dict[str, Any]], Any]
    ) -> Optional[SuiteResult]:
        """Run a test suite with given handler"""
        suite = self.suites.get(suite_id)
        if not suite:
            logger.error(f"Suite not found: {suite_id}")
            return None
        
        result = SuiteResult(suite_id=suite_id, suite_name=suite.name)
        
        for test in suite.tests:
            start = time.time()
            
            try:
                output = handler(test.input_data)
                latency = (time.time() - start) * 1000
                
                # Evaluate
                if test.expected_output is not None:
                    score = MetricCalculator.partial_match(output, test.expected_output)
                    passed = score >= 0.8  # 80% threshold
                else:
                    score = 1.0 if output else 0.0
                    passed = bool(output)
                
                test_result = TestResult(
                    test_id=test.id,
                    passed=passed,
                    score=score,
                    output=output,
                    latency_ms=latency
                )
                
            except Exception as e:
                test_result = TestResult(
                    test_id=test.id,
                    passed=False,
                    score=0.0,
                    error=str(e),
                    latency_ms=(time.time() - start) * 1000
                )
            
            result.results.append(test_result)
        
        result.completed_at = time.time()
        self.results[result.suite_id] = result
        
        # Save to history
        history_entry = result.to_dict()
        history_entry["timestamp"] = time.time()
        self.history.append(history_entry)
        self._save_history()
        
        logger.info(
            f"Suite '{suite.name}' completed: "
            f"{result.pass_rate:.1%} pass rate, "
            f"{result.average_latency:.0f}ms avg latency"
        )
        
        return result
    
    def get_result(self, suite_id: str) -> Optional[SuiteResult]:
        """Get suite result"""
        return self.results.get(suite_id)
    
    def compare_runs(self, suite_name: str, last_n: int = 5) -> List[Dict[str, Any]]:
        """Compare last N runs of a suite"""
        runs = [
            h for h in self.history
            if h.get("suite_name") == suite_name
        ][-last_n:]
        
        return [{
            "run": i + 1,
            "pass_rate": run.get("pass_rate", 0),
            "avg_score": run.get("average_score", 0),
            "avg_latency": run.get("average_latency_ms", 0),
            "duration": run.get("duration_ms", 0)
        } for i, run in enumerate(runs)]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get evaluation statistics"""
        if not self.history:
            return {"total_runs": 0, "total_tests": 0}
        
        return {
            "total_runs": len(self.history),
            "total_tests": sum(h.get("total_tests", 0) for h in self.history),
            "average_pass_rate": sum(h.get("pass_rate", 0) for h in self.history) / len(self.history),
            "average_latency": sum(h.get("average_latency_ms", 0) for h in self.history if h.get("average_latency_ms")) / max(1, sum(1 for h in self.history if h.get("average_latency_ms"))),
            "best_pass_rate": max((h.get("pass_rate", 0) for h in self.history), default=0),
            "worst_pass_rate": min((h.get("pass_rate", 0) for h in self.history), default=0)
        }


# Global instance
_evaluator: Optional[Evaluator] = None

def get_evaluator(storage_path: Optional[Path] = None) -> Evaluator:
    global _evaluator
    if _evaluator is None:
        _evaluator = Evaluator(storage_path)
    return _evaluator
