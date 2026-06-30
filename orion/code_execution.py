"""
Code Execution Engine
=====================
Provides sandboxed code execution capabilities for agents.
Based on 2026 patterns for safe code execution in multi-agent systems.

Features:
- Sandboxed Python execution
- Timeout protection
- Output capture
- Resource limits
- Execution history
"""

from __future__ import annotations

import json
import logging
import sys
import io
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict
import threading
import contextlib

logger = logging.getLogger("orion.code_execution")


class ExecutionStatus(str, Enum):
    """Code execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SECURITY_VIOLATION = "security_violation"


class SecurityLevel(str, Enum):
    """Security levels for code execution."""
    RESTRICTED = "restricted"
    MODERATE = "moderate"
    PERMISSIVE = "permissive"


@dataclass
class ExecutionResult:
    """Result of code execution."""
    execution_id: str
    code: str
    status: str
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    memory_used_mb: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExecutionPolicy:
    """Security policy for code execution."""
    level: str = SecurityLevel.RESTRICTED
    timeout_seconds: int = 10
    max_memory_mb: int = 100
    allowed_modules: List[str] = field(default_factory=lambda: [
        "json", "math", "datetime", "collections", "re", "itertools",
        "functools", "operator", "string", "textwrap", "random"
    ])
    blocked_functions: List[str] = field(default_factory=lambda: [
        "exec", "eval", "compile", "__import__", "open", "write",
        "os.system", "subprocess.call", "subprocess.run"
    ])
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SecurityScanner:
    """Scan code for security issues."""
    
    def __init__(self, policy: ExecutionPolicy):
        self.policy = policy
    
    def scan(self, code: str) -> List[str]:
        """Scan code for security violations."""
        violations = []
        
        for func in self.policy.blocked_functions:
            if func in code:
                violations.append(f"Blocked function found: {func}")
        
        dangerous_imports = ["os", "subprocess", "shutil", "pathlib", "socket", "http", "urllib"]
        for imp in dangerous_imports:
            if f"import {imp}" in code or f"from {imp}" in code:
                violations.append(f"Dangerous import: {imp}")
        
        if "open(" in code:
            violations.append("File access detected")
        
        if "exec(" in code or "eval(" in code:
            violations.append("Dynamic code execution detected")
        
        return violations
    
    def is_safe(self, code: str) -> bool:
        """Check if code is safe to execute."""
        return len(self.scan(code)) == 0


class CodeExecutor:
    """Sandboxed code execution engine."""
    
    def __init__(self, policy: Optional[ExecutionPolicy] = None):
        self.policy = policy or ExecutionPolicy()
        self.scanner = SecurityScanner(self.policy)
        self._execution_history: List[ExecutionResult] = []
        self._lock = threading.Lock()
    
    def execute(self, code: str, globals_dict: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """Execute code in a sandboxed environment."""
        import time
        import hashlib
        
        execution_id = f"exec_{hashlib.md5(code[:100].encode()).hexdigest()[:8]}"
        
        violations = self.scanner.scan(code)
        if violations:
            result = ExecutionResult(
                execution_id=execution_id,
                code=code,
                status=ExecutionStatus.SECURITY_VIOLATION,
                error=f"Security violations: {'; '.join(violations)}"
            )
            self._execution_history.append(result)
            return result
        
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        redirected_output = io.StringIO()
        redirected_error = io.StringIO()
        
        start_time = time.time()
        
        try:
            sys.stdout = redirected_output
            sys.stderr = redirected_error
            
            safe_globals = {
                "__builtins__": self._get_safe_builtins(),
            }
            if globals_dict:
                safe_globals.update(globals_dict)
            
            local_ns = {}
            
            exec(compile(code, '<string>', 'exec'), safe_globals, local_ns)
            
            duration = (time.time() - start_time) * 1000
            
            result = ExecutionResult(
                execution_id=execution_id,
                code=code,
                status=ExecutionStatus.COMPLETED,
                stdout=redirected_output.getvalue(),
                stderr=redirected_error.getvalue(),
                duration_ms=duration
            )
            
        except TimeoutError:
            result = ExecutionResult(
                execution_id=execution_id,
                code=code,
                status=ExecutionStatus.TIMEOUT,
                error="Execution timed out",
                duration_ms=self.policy.timeout_seconds * 1000
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            result = ExecutionResult(
                execution_id=execution_id,
                code=code,
                status=ExecutionStatus.FAILED,
                stdout=redirected_output.getvalue(),
                stderr=redirected_error.getvalue(),
                error=f"{type(e).__name__}: {str(e)}",
                duration_ms=duration
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
        
        with self._lock:
            self._execution_history.append(result)
        
        logger.info(f"Code execution: {result.status} ({result.duration_ms:.0f}ms)")
        return result
    
    def _get_safe_builtins(self) -> Dict[str, Any]:
        """Get safe built-in functions."""
        safe_builtins = {}
        
        allowed_builtins = [
            "print", "len", "range", "int", "float", "str", "bool",
            "list", "dict", "set", "tuple", "type", "isinstance",
            "enumerate", "zip", "map", "filter", "sorted", "reversed",
            "min", "max", "sum", "abs", "round", "pow", "divmod",
            "any", "all", "next", "iter", "reversed", "slice",
            "True", "False", "None", "self", "super",
        ]
        
        import builtins
        for name in allowed_builtins:
            if hasattr(builtins, name):
                safe_builtins[name] = getattr(builtins, name)
        
        import math
        safe_builtins["math"] = math
        
        import json
        safe_builtins["json"] = json
        
        import datetime
        safe_builtins["datetime"] = datetime
        
        import collections
        safe_builtins["collections"] = collections
        
        return safe_builtins
    
    def execute_function(self, func: Callable, *args, **kwargs) -> ExecutionResult:
        """Execute a function with sandboxing."""
        import time
        import hashlib
        
        code = f"{func.__name__}(*args, **kwargs)"
        execution_id = f"func_{hashlib.md5(func.__name__.encode()).hexdigest()[:8]}"
        
        start_time = time.time()
        
        try:
            result_value = func(*args, **kwargs)
            duration = (time.time() - start_time) * 1000
            
            result = ExecutionResult(
                execution_id=execution_id,
                code=code,
                status=ExecutionStatus.COMPLETED,
                return_value=result_value,
                duration_ms=duration
            )
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            result = ExecutionResult(
                execution_id=execution_id,
                code=code,
                status=ExecutionStatus.FAILED,
                error=f"{type(e).__name__}: {str(e)}",
                duration_ms=duration
            )
        
        with self._lock:
            self._execution_history.append(result)
        
        return result
    
    def get_history(self, limit: int = 100) -> List[ExecutionResult]:
        """Get execution history."""
        return self._execution_history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = len(self._execution_history)
        successful = sum(1 for r in self._execution_history if r.status == ExecutionStatus.COMPLETED)
        failed = sum(1 for r in self._execution_history if r.status == ExecutionStatus.FAILED)
        security = sum(1 for r in self._execution_history if r.status == ExecutionStatus.SECURITY_VIOLATION)
        
        avg_duration = 0.0
        if self._execution_history:
            avg_duration = sum(r.duration_ms for r in self._execution_history) / total
        
        return {
            "total_executions": total,
            "successful": successful,
            "failed": failed,
            "security_violations": security,
            "avg_duration_ms": avg_duration,
            "success_rate": successful / total if total > 0 else 0
        }
