"""
Specialized agent implementations for different coding tasks.
"""

from __future__ import annotations
import time
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional, List
from .core import Agent, Task, AgentResult, TaskStatus

# Import from existing Turbo system
from ..core.planner import get_plan
from ..core.executor import execute
from ..core.config import load_settings
from ..tools.fs import fs_write, fs_read
from ..tools.python_exec import python_run


class PlannerAgent(Agent):
    """Agent specialized in creating detailed plans for coding tasks."""
    
    def __init__(self, name: str = "planner"):
        super().__init__(name, "planner")
        self.settings = load_settings()
    
    def process_task(self, task: Task) -> AgentResult:
        """Generate a detailed plan for a coding task."""
        start_time = time.time()
        
        try:
            # Use the existing Turbo planner
            plan = get_plan(task.description, self.settings)
            
            result = {
                "plan_steps": plan.plan,
                "detailed_instructions": plan.coder_prompt,
                "suggested_tests": plan.tests,
                "task_breakdown": self._break_down_task(task.description)
            }
            
            return AgentResult(
                agent_name=self.name,
                task_id=task.id,
                success=True,
                output=result,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                task_id=task.id,
                success=False,
                output=None,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _break_down_task(self, description: str) -> Dict[str, Any]:
        """Break down task into sub-components."""
        # Simple heuristic-based breakdown
        breakdown = {
            "complexity": "medium",
            "estimated_files": 1,
            "dependencies": [],
            "requires_testing": True
        }
        
        if any(word in description.lower() for word in ["api", "web", "server"]):
            breakdown["complexity"] = "high"
            breakdown["estimated_files"] = 3
            breakdown["dependencies"] = ["requests", "fastapi"]
            
        if any(word in description.lower() for word in ["simple", "hello", "basic"]):
            breakdown["complexity"] = "low"
            breakdown["requires_testing"] = False
            
        return breakdown


class CoderAgent(Agent):
    """Agent specialized in writing code based on plans."""
    
    def __init__(self, name: str = "coder"):
        super().__init__(name, "coder")
        self.settings = load_settings()
    
    def process_task(self, task: Task) -> AgentResult:
        """Generate code based on task requirements."""
        start_time = time.time()
        
        try:
            # Extract plan from task requirements if available
            if "plan" in task.requirements:
                plan = task.requirements["plan"]
                coder_prompt = plan.get("detailed_instructions", task.description)
            else:
                coder_prompt = task.description
            
            # Use the existing Turbo executor
            summary = execute(coder_prompt, self.settings)
            
            # Collect generated files
            generated_files = self._collect_generated_files()
            
            result = {
                "execution_summary": {
                    "steps_taken": summary.steps,
                    "last_message": summary.last
                },
                "generated_files": generated_files,
                "code_metrics": self._analyze_code(generated_files)
            }
            
            return AgentResult(
                agent_name=self.name,
                task_id=task.id,
                success=True,
                output=result,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                task_id=task.id,
                success=False,
                output=None,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _collect_generated_files(self) -> Dict[str, str]:
        """Collect recently generated Python files."""
        files = {}
        try:
            # Look for Python files in current directory
            for filename in os.listdir("."):
                if filename.endswith(".py") and not filename.startswith("__"):
                    result = fs_read(filename)
                    if result.ok:
                        files[filename] = result.detail
        except Exception:
            pass
        return files
    
    def _analyze_code(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Basic code analysis metrics."""
        total_lines = 0
        total_functions = 0
        total_classes = 0

        for content in files.values():
            lines = content.split('\n')
            total_lines += len(lines)
            total_functions += content.count('def ')
            total_classes += content.count('class ')

        return {
            "total_lines": total_lines,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "files_count": len(files)
        }


class ReviewerAgent(Agent):
    """Agent specialized in code review and quality analysis."""
    
    def __init__(self, name: str = "reviewer"):
        super().__init__(name, "reviewer")
    
    def process_task(self, task: Task) -> AgentResult:
        """Review code and provide feedback."""
        start_time = time.time()
        
        try:
            # Get code from task requirements
            code_files = task.requirements.get("generated_files", {})
            
            if not code_files:
                return AgentResult(
                    agent_name=self.name,
                    task_id=task.id,
                    success=False,
                    output=None,
                    error="No code files provided for review"
                )
            
            review_results = {}
            overall_score = 0
            issue_count = 0
            
            for filename, content in code_files.items():
                file_review = self._review_file(filename, content)
                review_results[filename] = file_review
                overall_score += file_review["score"]
                issue_count += len(file_review["issues"])
            
            overall_score = overall_score / len(code_files) if code_files else 0
            
            result = {
                "overall_score": overall_score,
                "total_issues": issue_count,
                "file_reviews": review_results,
                "recommendations": self._generate_recommendations(review_results),
                "approved": overall_score >= 7.0 and issue_count < 5
            }
            
            return AgentResult(
                agent_name=self.name,
                task_id=task.id,
                success=True,
                output=result,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                task_id=task.id,
                success=False,
                output=None,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _review_file(self, filename: str, content: str) -> Dict[str, Any]:
        """Review a single file."""
        issues = []
        score = 10.0
        
        lines = content.split('\n')
        
        # Check for docstrings
        if 'def ' in content and '"""' not in content and "'''" not in content:
            issues.append("Missing docstrings for functions")
            score -= 1.0
        
        # Check for long lines
        long_lines = [i for i, line in enumerate(lines, 1) if len(line) > 100]
        if long_lines:
            issues.append(f"Lines too long: {long_lines[:3]}")
            score -= 0.5
        
        # Check for hardcoded values
        if any(char in content for char in ['"localhost"', "'localhost'", "127.0.0.1"]):
            issues.append("Hardcoded network addresses found")
            score -= 0.5
        
        # Check for basic error handling
        if 'try:' not in content and ('open(' in content or 'requests.' in content):
            issues.append("Missing error handling for file/network operations")
            score -= 1.0
        
        # Check for type hints
        if 'def ' in content and '->' not in content:
            issues.append("Missing return type hints")
            score -= 0.5
        
        return {
            "score": max(0, score),
            "issues": issues,
            "line_count": len([l for l in lines if l.strip()]),
            "complexity": "low" if len(lines) < 50 else "medium" if len(lines) < 200 else "high"
        }
    
    def _generate_recommendations(self, reviews: Dict[str, Dict]) -> List[str]:
        """Generate overall recommendations."""
        recommendations = []
        
        total_issues = sum(len(review["issues"]) for review in reviews.values())
        avg_score = sum(review["score"] for review in reviews.values()) / len(reviews)
        
        if avg_score < 7.0:
            recommendations.append("Code quality needs improvement - focus on documentation and error handling")
        
        if total_issues > 5:
            recommendations.append("Too many issues found - consider refactoring")
        
        if any("long" in str(review["issues"]) for review in reviews.values()):
            recommendations.append("Consider breaking long lines and functions into smaller pieces")
        
        return recommendations


class TesterAgent(Agent):
    """Agent specialized in testing code."""
    
    def __init__(self, name: str = "tester"):
        super().__init__(name, "tester")
    
    def process_task(self, task: Task) -> AgentResult:
        """Test the generated code."""
        start_time = time.time()
        
        try:
            # Get code and tests from task requirements
            code_files = task.requirements.get("generated_files", {})
            suggested_tests = task.requirements.get("suggested_tests", [])
            
            if not code_files:
                return AgentResult(
                    agent_name=self.name,
                    task_id=task.id,
                    success=False,
                    output=None,
                    error="No code files provided for testing"
                )
            
            test_results = {
                "syntax_check": self._check_syntax(code_files),
                "execution_test": self._test_execution(code_files),
                "pytest_results": self._run_pytest(),
                "unit_tests": self._run_unit_tests(suggested_tests)
            }
            
            overall_success = all([
                test_results["syntax_check"]["passed"],
                test_results["execution_test"]["passed"]
            ])
            
            result = {
                "overall_success": overall_success,
                "test_results": test_results,
                "coverage_estimate": self._estimate_coverage(code_files, suggested_tests),
                "recommendations": self._generate_test_recommendations(test_results)
            }
            
            return AgentResult(
                agent_name=self.name,
                task_id=task.id,
                success=True,
                output=result,
                processing_time=time.time() - start_time
            )
            
        except Exception as e:
            return AgentResult(
                agent_name=self.name,
                task_id=task.id,
                success=False,
                output=None,
                error=str(e),
                processing_time=time.time() - start_time
            )
    
    def _check_syntax(self, code_files: Dict[str, str]) -> Dict[str, Any]:
        """Check syntax of all code files."""
        results = {"passed": True, "errors": []}
        
        for filename, content in code_files.items():
            try:
                compile(content, filename, 'exec')
            except SyntaxError as e:
                results["passed"] = False
                results["errors"].append(f"{filename}: {str(e)}")
        
        return results
    
    def _test_execution(self, code_files: Dict[str, str]) -> Dict[str, Any]:
        """Test basic execution of code files."""
        results = {"passed": True, "outputs": {}, "errors": []}
        
        for filename, content in code_files.items():
            if filename.endswith('.py'):
                try:
                    # Use python_run tool for safe execution
                    exec_result = python_run("snippet", content)
                    results["outputs"][filename] = {
                        "stdout": exec_result.stdout,
                        "stderr": exec_result.stderr,
                        "success": exec_result.ok
                    }
                    
                    if not exec_result.ok:
                        results["passed"] = False
                        results["errors"].append(f"{filename}: {exec_result.stderr}")
                        
                except Exception as e:
                    results["passed"] = False
                    results["errors"].append(f"{filename}: {str(e)}")
        
        return results
    
    def _run_pytest(self) -> Dict[str, Any]:
        """Run pytest if test files exist."""
        try:
            pytest_result = python_run("pytest")
            return {
                "executed": True,
                "success": pytest_result.ok,
                "output": pytest_result.stdout,
                "errors": pytest_result.stderr
            }
        except Exception as e:
            return {
                "executed": False,
                "error": str(e)
            }
    
    def _run_unit_tests(self, suggested_tests: List[str]) -> Dict[str, Any]:
        """Run unit tests from suggested test cases."""
        if not suggested_tests:
            return {"executed": False, "reason": "No suggested tests provided"}
        
        results = {"executed": True, "test_results": [], "passed": 0, "failed": 0}
        
        for i, test_code in enumerate(suggested_tests):
            try:
                test_result = python_run("snippet", test_code)
                results["test_results"].append({
                    "test_index": i,
                    "success": test_result.ok,
                    "output": test_result.stdout,
                    "error": test_result.stderr if not test_result.ok else None
                })
                
                if test_result.ok:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                results["test_results"].append({
                    "test_index": i,
                    "success": False,
                    "error": str(e)
                })
                results["failed"] += 1
        
        return results
    
    def _estimate_coverage(self, code_files: Dict[str, str], tests: List[str]) -> Dict[str, Any]:
        """Estimate test coverage."""
        # Simple heuristic: estimate based on function/class coverage
        total_functions = sum(content.count('def ') for content in code_files.values())
        total_classes = sum(content.count('class ') for content in code_files.values())
        total_testable = total_functions + total_classes

        if total_testable == 0:
            return {"coverage": 100, "reason": "No testable units found"}

        if not tests:
            return {"coverage": 0, "reason": "No tests available"}

        # Rough estimate based on number of tests vs testable units
        estimated_coverage = min(100, (len(tests) / total_testable) * 100)

        return {
            "coverage": estimated_coverage,
            "testable_units": total_testable,
            "test_count": len(tests)
        }
    
    def _generate_test_recommendations(self, test_results: Dict[str, Any]) -> List[str]:
        """Generate testing recommendations."""
        recommendations = []
        
        if not test_results["syntax_check"]["passed"]:
            recommendations.append("Fix syntax errors before proceeding")
        
        if not test_results["execution_test"]["passed"]:
            recommendations.append("Code has runtime errors that need to be addressed")
        
        if test_results["unit_tests"].get("failed", 0) > 0:
            recommendations.append("Some unit tests are failing - review and fix")
        
        pytest_results = test_results.get("pytest_results", {})
        if pytest_results.get("executed") and not pytest_results.get("success"):
            recommendations.append("Pytest suite is failing - review test cases")
        
        coverage = test_results.get("coverage_estimate", {}).get("coverage", 0)
        if coverage < 50:
            recommendations.append("Low test coverage - consider adding more tests")
        
        return recommendations