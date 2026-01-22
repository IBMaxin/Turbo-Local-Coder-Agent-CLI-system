"""
Complete workflow orchestration for the coding agent team.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import time
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
                            apply_changes: bool = True) -> WorkflowResult:
        """Execute the complete coding workflow."""
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
            
            # Step 2: Coding
            print("[CODE] Coding phase...")
            code_result = self._execute_coding_phase(plan_result)
            if not code_result:
                result.errors.append("Coding phase failed")
                return result
            
            result.code = code_result
            
            # Step 3: Review (optional)
            if not skip_review:
                print("[REVIEW] Review phase...")
                review_result = self._execute_review_phase(code_result)
                if review_result:
                    result.review = review_result
                    if not review_result.get("approved", False):
                        result.errors.append("Code review failed - improvements needed")
            
            # Step 4: Testing (optional)
            if not skip_testing:
                print("[TEST] Testing phase...")
                test_result = self._execute_testing_phase(
                    code_result, 
                    plan_result.get("suggested_tests", [])
                )
                if test_result:
                    result.tests = test_result
                    if not test_result.get("overall_success", False):
                        result.errors.append("Testing phase failed")
            
            result.success = len(result.errors) == 0
            result.total_time = time.time() - start_time
            
            return result
            
        except Exception as e:
            result.errors.append(f"Workflow exception: {str(e)}")
            result.total_time = time.time() - start_time
            return result
    
    def _execute_planning_phase(self, description: str) -> Optional[Dict[str, Any]]:
        """Execute planning phase."""
        try:
            # Create planning task
            task = Task(description=description)
            task_id = self.orchestrator.submit_task(task)
            
            # Assign to planner
            success = self.orchestrator.assign_task(task_id, "planner-1")
            if not success:
                return None
            
            # Get results
            results = self.orchestrator.get_task_results(task_id)
            if not results or not results[0].success:
                return None
            
            plan_data = results[0].output
            plan_data["task_id"] = task_id
            return plan_data
            
        except Exception as e:
            print(f"Planning phase error: {e}")
            return None
    
    def _execute_coding_phase(self, plan_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute coding phase."""
        try:
            # Create coding task with plan data
            task = Task(
                description="Generate code based on plan",
                requirements={"plan": plan_data}
            )
            task_id = self.orchestrator.submit_task(task)
            
            # Assign to coder
            success = self.orchestrator.assign_task(task_id, "coder-1")
            if not success:
                return None
            
            # Get results
            results = self.orchestrator.get_task_results(task_id)
            if not results or not results[0].success:
                return None
            
            code_data = results[0].output
            code_data["task_id"] = task_id
            return code_data
            
        except Exception as e:
            print(f"Coding phase error: {e}")
            return None
    
    def _execute_review_phase(self, code_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute review phase."""
        try:
            # Create review task
            task = Task(
                description="Review generated code",
                requirements=code_data
            )
            task_id = self.orchestrator.submit_task(task)
            
            # Assign to reviewer
            success = self.orchestrator.assign_task(task_id, "reviewer-1")
            if not success:
                return None
            
            # Get results
            results = self.orchestrator.get_task_results(task_id)
            if not results or not results[0].success:
                return None
            
            review_data = results[0].output
            review_data["task_id"] = task_id
            return review_data
            
        except Exception as e:
            print(f"Review phase error: {e}")
            return None
    
    def _execute_testing_phase(self, code_data: Dict[str, Any], 
                              suggested_tests: List[str]) -> Optional[Dict[str, Any]]:
        """Execute testing phase."""
        try:
            # Create testing task
            requirements = code_data.copy()
            requirements["suggested_tests"] = suggested_tests
            
            task = Task(
                description="Test generated code",
                requirements=requirements
            )
            task_id = self.orchestrator.submit_task(task)
            
            # Assign to tester
            success = self.orchestrator.assign_task(task_id, "tester-1")
            if not success:
                return None
            
            # Get results
            results = self.orchestrator.get_task_results(task_id)
            if not results or not results[0].success:
                return None
            
            test_data = results[0].output
            test_data["task_id"] = task_id
            return test_data
            
        except Exception as e:
            print(f"Testing phase error: {e}")
            return None
    
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
        skip_testing=False
    )
    
    # Print summary
    print()
    print("=" * 50)
    print(workflow.get_workflow_summary(result))
    
    return result


if __name__ == "__main__":
    demo_workflow()