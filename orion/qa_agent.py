#!/usr/bin/env python3
"""
ORION QA Agent - Quality Assurance & Validation
================================================
Agente dedicado a testes reais e validação de código.
Este agente É OBRIGATÓRIO antes de marcar qualquer tarefa como concluída.

Missão: Garantir que tudo funciona A PRIMEIRA, sem fictícios.
"""

import sys
import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestResult(Enum):
    PASS = "✅ PASS"
    FAIL = "❌ FAIL"
    WARN = "⚠️ WARN"
    SKIP = "⏭️ SKIP"


@dataclass
class Test:
    name: str
    command: str
    expected: str = None
    timeout: int = 30
    critical: bool = True


class QAAgent:
    """
    Agente de Quality Assurance - Validação Real
    =============================================
    
    REGRAS OBRIGATÓRIAS:
    1. NUNCA marcar tarefa como concluída sem testes reais
    2. NUNCA assumir que código funciona sem executar
    3. NUNCA usar output fictício em testes
    4. SEMPRE executar comandos reais
    5. SEMPRE reportar erros reais encontrados
    """
    
    PROJECT_PATH = r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo"
    PYTHON_PATH = r"C:\Users\BIG_P\AppData\Local\Programs\Python\Python314\python.exe"
    
    def __init__(self):
        self.results: List[Dict] = []
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def run_command(self, command: str, timeout: int = 30, cwd: str = None) -> Dict:
        """Executa um comando REAL e retorna o output"""
        if cwd is None:
            cwd = self.PROJECT_PATH
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                env={**__import__('os').environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Timeout after {timeout}s",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }
    
    def test_python_import(self, module: str) -> Test:
        """Testa se um módulo Python pode ser importado"""
        return Test(
            name=f"Import {module}",
            command=f'"{self.PYTHON_PATH}" -c "import {module}; print(\'OK\')"',
            expected="OK"
        )
    
    def test_file_exists(self, filepath: str) -> Test:
        """Testa se um ficheiro existe"""
        return Test(
            name=f"File exists: {filepath}",
            command=f'if exist "{filepath}" (echo EXISTS) else (echo MISSING)',
            expected="EXISTS"
        )
    
    def test_server_health(self, url: str) -> Test:
        """Testa se um servidor está saudável"""
        return Test(
            name=f"Health check: {url}",
            command=f'curl -s {url}',
            expected='"status": "healthy"'
        )
    
    def test_port_open(self, port: int) -> Test:
        """Testa se uma porta está aberta"""
        return Test(
            name=f"Port {port} open",
            command=f'netstat -ano | findstr ":{port}"',
            expected=None  # Any output means port is open
        )
    
    def execute_test(self, test: Test) -> Dict:
        """Executa um teste REAL"""
        result = self.run_command(test.command, test.timeout)
        
        passed = False
        if result["success"]:
            if test.expected:
                passed = test.expected in result["stdout"]
            else:
                passed = bool(result["stdout"].strip())
        
        test_result = {
            "name": test.name,
            "passed": passed,
            "output": result["stdout"],
            "error": result["stderr"],
            "critical": test.critical
        }
        
        self.results.append(test_result)
        
        if passed:
            print(f"  {TestResult.PASS.value}: {test.name}")
        else:
            if test.critical:
                self.errors.append(f"{test.name}: {result['stderr'] or result['stdout']}")
                print(f"  {TestResult.FAIL.value}: {test.name}")
            else:
                self.warnings.append(f"{test.name}: {result['stderr'] or result['stdout']}")
                print(f"  {TestResult.WARN.value}: {test.name}")
        
        return test_result
    
    def validate_orion_system(self) -> bool:
        """Validação completa do sistema ORION"""
        print("\n" + "="*60)
        print("  ORION QA AGENT - VALIDAÇÃO REAL")
        print("="*60 + "\n")
        
        tests = [
            # Testes de importação
            self.test_python_import("orion"),
            self.test_python_import("orion.agents"),
            self.test_python_import("orion.daemon"),
            self.test_python_import("orion.mcp_server"),
            
            # Testes de ficheiros
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\orion_mcp_server_http.py"),
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\orion\agents.py"),
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\orion\daemon.py"),
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\ORION_SYSTEM\start_general.ps1"),
            
            # Testes de dependências
            Test(
                name="Dependencies installed",
                command=f'"{self.PYTHON_PATH}" -c "import fastapi; import uvicorn; import aiohttp; print(\'OK\')"',
                expected="OK"
            ),
        ]
        
        print("1. Executando testes de importação e ficheiros...")
        for test in tests:
            self.execute_test(test)
        
        print("\n2. Testando servidor MCP HTTP...")
        
        # Verificar se já está a correr
        port_test = self.test_port_open(8001)
        self.execute_test(port_test)
        
        # Verificar health check
        health_test = self.test_server_health("http://localhost:8001/api/health")
        self.execute_test(health_test)
        
        print("\n3. Testando tools do General...")
        
        tools_test = Test(
            name="Tools endpoint responds",
            command='curl -s http://localhost:8001/api/tools',
            expected="general_analyze"
        )
        self.execute_test(tools_test)
        
        # Resumo
        print("\n" + "="*60)
        print("  RESUMO DA VALIDAÇÃO")
        print("="*60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        failed = sum(1 for r in self.results if not r["passed"] and r["critical"])
        warnings = sum(1 for r in self.results if not r["passed"] and not r["critical"])
        
        print(f"\n  Total: {total}")
        print(f"  ✅ Passou: {passed}")
        print(f"  ❌ Falhou: {failed}")
        print(f"  ⚠️ Avisos: {warnings}")
        
        if self.errors:
            print(f"\n  ERROS CRÍTICOS:")
            for error in self.errors:
                print(f"    - {error}")
        
        if self.warnings:
            print(f"\n  AVISOS:")
            for warn in self.warnings:
                print(f"    - {warn}")
        
        success = failed == 0
        if success:
            print(f"\n  {'='*60}")
            print(f"  ✅ SISTEMA VALIDADO COM SUCESSO!")
            print(f"  {'='*60}")
        else:
            print(f"\n  {'='*60}")
            print(f"  ❌ SISTEMA COM PROBLEMAS - CORRIJA ANTES DE CONTINUAR")
            print(f"  {'='*60}")
        
        return success
    
    def validate_script(self, script_path: str) -> bool:
        """Valida que um script específico funciona"""
        print(f"\nValidando script: {script_path}")
        
        test = Test(
            name=f"Script {Path(script_path).name}",
            command=f'"{self.PYTHON_PATH}" "{script_path}" --test',
            timeout=10
        )
        
        result = self.execute_test(test)
        return result["passed"]
    
    def validate_deployment(self) -> bool:
        """Valida que o deployment está correto"""
        print("\n" + "="*60)
        print("  VALIDAÇÃO DE DEPLOYMENT")
        print("="*60 + "\n")
        
        tests = [
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\cloud\deploy.sh"),
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\cloud\docker-compose.cloud.yml"),
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\cloud\Dockerfile.cloud"),
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\cloud\requirements.txt"),
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\ORION_SYSTEM\sandbox\Dockerfile"),
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\ORION_SYSTEM\sandbox\docker-compose.yml"),
            self.test_file_exists(r"C:\Users\BIG_P\OneDrive\READET~1\Ai\Jogo\ORION_SYSTEM\sandbox\deploy.sh"),
        ]
        
        for test in tests:
            self.execute_test(test)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        
        return passed == total
    
    def get_report(self) -> str:
        """Gera relatório de validação"""
        report = []
        report.append("="*60)
        report.append("  RELATÓRIO DE VALIDAÇÃO - ORION QA AGENT")
        report.append("="*60)
        report.append("")
        
        for result in self.results:
            status = "✅" if result["passed"] else "❌"
            report.append(f"{status} {result['name']}")
            if not result["passed"] and result["error"]:
                report.append(f"   Erro: {result['error']}")
        
        report.append("")
        report.append("="*60)
        
        return "\n".join(report)


def main():
    """Ponto de entrada principal"""
    agent = QAAgent()
    success = agent.validate_orion_system()
    
    if not success:
        sys.exit(1)
    
    print("\nRelatório guardado em: qa_report.txt")
    with open("qa_report.txt", "w", encoding="utf-8") as f:
        f.write(agent.get_report())


if __name__ == "__main__":
    main()
