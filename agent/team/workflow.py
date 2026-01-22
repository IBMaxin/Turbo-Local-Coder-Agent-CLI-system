"""
Complete workflow orchestration for the coding agent team.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import time
import subprocess
from .core import TeamOrchestrator, Task, TaskStatus
from .specialized_agents import PlannerAgent, CoderAgent, ReviewerAgent, TesterAgent


@dataclass
class WorkflowResult:
    """Complete workflow execution result."""
    success: bool
    task_id: str
    plan: Optional[Dict[str, Any]] = None
    code: Optional[Dict[str, Any]] = None
    review: Optional[Dict[str, Any]] = None
    tests: Optional[Dict[str, Any]] = None
    pr_url: Optional[str] = None
    total_time: float = 0.0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class CodingWorkflow:
    """Orchestrates the complete coding workflow with multiple agents."""
    
    def __init__(self):
        self.orchestrator = TeamOrchestrator()
        self._setup_agents()
    
    def _setup_agents(self):
        """Initialize and register all specialized agents."""
        self.planner = PlannerAgent("planner-1")
        self.coder = CoderAgent("coder-1") 
        self.reviewer = ReviewerAgent("reviewer-1")
        self.tester = TesterAgent("tester-1")
        
        self.orchestrator.register_agent(self.planner)
        self.orchestrator.register_agent(self.coder)
        self.orchestrator.register_agent(self.reviewer)
        self.orchestrator.register_agent(self.tester)
    
    def execute_full_workflow(self, description: str, 
                            skip_review: bool = False,
                            skip_testing: bool = False,
                            apply_changes: bool = True,
                            max_retries: int = 3,
                            auto_pr: bool = False) -> WorkflowResult:
        """Execute the complete coding workflow with self-healing loop."""
        start_time = time.time()
        result = WorkflowResult(success=False, task_id="", total_time=0.0)
        
        try:
            # Step 1: Planning
            print("[PLAN] Planning phase...")
            plan_result = self._execute_planning_phase(description)
            if not plan_result:
                result.errors.append("Planning phase failed")
                return result
            
            result.plan = plan_result
            result.task_id = plan_result.get("task_id", "")
            
            # Step 2: Loop (Coding -> Linting -> Testing -> Patching)
            attempts = 0
            current_code = None
            
            while attempts < max_retries:
                attempts += 1
                print(f"[LOOP] Iteration {attempts}/{max_retries}")
                
                # 2a. Coding / Patching
                if attempts == 1:
                    print("[CODE] Generating initial code...")
                    current_code = self._execute_coding_phase(plan_result)
                else:
                    print(f"[PATCH] Patching based on {len(result.errors)} errors...")
                    current_code = self._execute_patching_phase(current_code, result.errors)
                
                if not current_code:
                    result.errors.append("Coding/Patching phase failed to return result")
                    break

                result.code = current_code
                result.errors = [] # Reset errors for this attempt
                
                # 2b. Linting & Formatting (Fail-fast)
                if apply_changes:
                    print("[LINT] Running linting and formatting...")
                    lint_result = self._execute_linting_phase(current_code)
                    if not lint_result['success']:
                        result.errors.append(f"Linting failed: {lint_result['output']}")
                        continue

                # 2c. Testing
                if not skip_testing:
                    print("[TEST] Testing phase...")
                    test_result = self._execute_testing_phase(
                        current_code, 
                        plan_result.get("suggested_tests", [])
                    )
                    if test_result:
                        result.tests = test_result
                        if not test_result.get("overall_success", False):
                            result.errors.append("Testing phase failed")
                            continue
                
                # If we made it here, success!
                result.success = True
                break
            
            # Step 3: Review (optional, after loop success)
            if result.success and not skip_review:
                print("[REVIEW] Review phase...")
                review_result = self._execute_review_phase(result.code)
                if review_result:
                    result.review = review_result
                    if not review_result.get("approved", False):
                        result.errors.append("Code review failed - improvements needed")
                        result.success = False

            # Step 4: PR Creation (Optional)
            if result.success and auto_pr and apply_changes:
                print("[PR] Creating Pull Request...")
                pr_result = self._execute_pr_creation_phase(description)
                if pr_result.get("success"):
                    result.pr_url = pr_result.get("pr_url")
                    print(f"[PR] Created successfully: {result.pr_url}")
                else:
                    print(f"[PR] Failed: {pr_result.get('error')}")

            result.total_time = time.time() - start_time
            return result
            
        except Exception as e:
            result.errors.append(f"Workflow exception: {str(e)}")
            result.total_time = time.time() - start_time
            return result
    
    def _execute_planning_phase(self, description: str) -> Optional[Dict[str, Any]]:
        """Execute planning phase."""
        try:
            task = Task(description=description)
            task_id = self.orchestrator.submit_task(task)
            if not self.orchestrator.assign_task(task_id, "planner-1"): return None
            results = self.orchestrator.get_task_results(task_id)
            if not results or not results[0].success: return None
            
            plan_data = results[0].output
            plan_data["task_id"] = task_id
            return plan_data
        except Exception as e:
            print(f"Planning phase error: {e}")
            return None
    
    def _execute_coding_phase(self, plan_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute coding phase."""
        try:
            task = Task(description="Generate code based on plan", requirements={"plan": plan_data})
            task_id = self.orchestrator.submit_task(task)
            if not self.orchestrator.assign_task(task_id, "coder-1"): return None
            results = self.orchestrator.get_task_results(task_id)
            if not results or not results[0].success: return None
            
            code_data = results[0].output
            code_data["task_id"] = task_id
            return code_data
        except Exception as e:
            print(f"Coding phase error: {e}")
            return None

    def _execute_patching_phase(self, code_data: Dict[str, Any], errors: List[str]) -> Optional[Dict[str, Any]]:
        """Execute patching phase based on errors."""
        try:
            error_context = "\n".join(errors)
            prompt = (
                f"The previous code failed validation.\n"
                f"ERRORS:\n{error_context}\n\n"
                f"Please analyze these errors and use tools to PATCH the files. "
                f"Do not rewrite everything, just fix the specific issues."
            )
            
            # Reuse coding agent for patching
            task = Task(description=prompt, requirements=code_data)
            task_id = self.orchestrator.submit_task(task)
            if not self.orchestrator.assign_task(task_id, "coder-1"): return None
            results = self.orchestrator.get_task_results(task_id)
            if not results or not results[0].success: return None
            
            return results[0].output
        except Exception as e:
            print(f"Patching phase error: {e}")
            return None

    def _execute_linting_phase(self, code_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute linting and formatting."""
        try:
            # 1. Auto-format with Black (if available)
            try:
                subprocess.run(["black", "."], check=False, capture_output=True)
            except FileNotFoundError:
                pass # Black not installed
            
            # 2. Lint with Ruff (if available)
            try:
                proc = subprocess.run(
                    ["ruff", "check", ".", "--fix"], 
                    capture_output=True, 
                    text=True
                )
                if proc.returncode != 0:
                     return {"success": False, "output": proc.stdout or proc.stderr}
            except FileNotFoundError:
                pass # Ruff not installed
                
            return {"success": True, "output": "Linting passed or skipped"}
        except Exception as e:
            return {"success": False, "output": str(e)}

    def _execute_review_phase(self, code_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute review phase."""
        try:
            task = Task(description="Review generated code", requirements=code_data)
            task_id = self.orchestrator.submit_task(task)
            if not self.orchestrator.assign_task(task_id, "reviewer-1"): return None
            results = self.orchestrator.get_task_results(task_id)
            if not results or not results[0].success: return None
            
            review_data = results[0].output
            review_data["task_id"] = task_id
            return review_data
        except Exception as e:
            print(f"Review phase error: {e}")
            return None
    
    def _execute_testing_phase(self, code_data: Dict[str, Any], suggested_tests: List[str]) -> Optional[Dict[str, Any]]:
        """Execute testing phase."""
        try:
            requirements = code_data.copy() if code_data else {}
            requirements["suggested_tests"] = suggested_tests
            
            task = Task(description="Test generated code", requirements=requirements)
            task_id = self.orchestrator.submit_task(task)
            if not self.orchestrator.assign_task(task_id, "tester-1"): return None
            results = self.orchestrator.get_task_results(task_id)
            if not results or not results[0].success: return None
            
            test_data = results[0].output
            test_data["task_id"] = task_id
            return test_data
        except Exception as e:
            print(f"Testing phase error: {e}")
            return None

    def _execute_pr_creation_phase(self, description: str) -> Dict[str, Any]:
        """Create a GitHub Pull Request using gh CLI."""
        try:
            # Get current branch
            branch_res = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True)
            branch = branch_res.stdout.strip()
            if not branch: return {"success": False, "error": "Could not determine branch"}

            # Create PR via gh CLI
            cmd = [
                "gh", "pr", "create",
                "--base", "main",
                "--head", branch,
                "--title", f"[AUTO] {description[:50]}...",
                "--body", f"Automated PR for task: {description}\n\nGenerated by Turbo Agent."
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                return {"success": True, "pr_url": result.stdout.strip()}
            else:
                return {"success": False, "error": result.stderr}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_workflow_summary(self, result: WorkflowResult) -> str:
        """Generate a human-readable workflow summary."""
        summary = [
            f"[RESULT] Workflow Result: {'[OK] SUCCESS' if result.success else '[FAIL] FAILED'}",
            f"[TIME] Total Time: {result.total_time:.2f} seconds",
            f"[ID] Task ID: {result.task_id}",
            ""
        ]
        
        if result.plan:
            plan_steps = len(result.plan.get("plan_steps", []))
            summary.append(f"[PLAN] Planning: {plan_steps} steps generated")
        
        if result.code:
            files = result.code.get("generated_files", {})
            lines = result.code.get("code_metrics", {}).get("total_lines", 0)
            summary.append(f"[CODE] Coding: {len(files)} files, {lines} lines")
        
        if result.review:
            score = result.review.get("overall_score", 0)
            issues = result.review.get("total_issues", 0)
            approved = result.review.get("approved", False)
            status = "[OK] APPROVED" if approved else "[WARN] NEEDS WORK"
            summary.append(f"[REVIEW] Review: {score:.1f}/10 score, {issues} issues ({status})")
        
        if result.tests:
            success = result.tests.get("overall_success", False)
            coverage = result.tests.get("coverage_estimate", {}).get("coverage", 0)
            status = "[OK] PASSED" if success else "[FAIL] FAILED" 
            summary.append(f"[TEST] Testing: {status}, ~{coverage:.0f}% coverage")
        
        if result.pr_url:
            summary.append(f"[PR] Pull Request: {result.pr_url}")

        if result.errors:
            summary.append("")
            summary.append("[ERR] Errors:")
            for error in result.errors:
                summary.append(f"   • {error}")
        
        return "\n".join(summary)


def demo_workflow():
    """Demonstration of the complete workflow."""
    print("[EXEC] Initializing Coding Agent Team Workflow")
    print("=" * 50)
    
    workflow = CodingWorkflow()
    
    # Example coding task
    task_description = "Create a Python function that calculates the fibonacci sequence recursively and iteratively, with error handling for negative inputs"
    
    print(f"[TASK] Task: {task_description}")
    print()
    
    # Execute workflow
    result = workflow.execute_full_workflow(
        task_description,
        skip_review=False,
        skip_testing=False,
        max_retries=2,
        auto_pr=True # Enable PR creation for demo
    )
    
    # Print summary
    print()
    print("=" * 50)
    print(workflow.get_workflow_summary(result))
    
    return result


if __name__ == "__main__":
    demo_workflow()