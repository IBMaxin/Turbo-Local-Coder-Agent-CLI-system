#!/usr/bin/env python3
"""
Convenient script to run the RAG-enhanced agent team.
"""

import sys
import argparse
from agent.team.workflow import CodingWorkflow


def main():
    parser = argparse.ArgumentParser(description="Run RAG-Enhanced Coding Agent Team")
    parser.add_argument("task", help="Description of the coding task")
    parser.add_argument("--apply", action="store_true", help="Actually execute changes (default: True)")
    parser.add_argument("--skip-review", action="store_true", help="Skip code review phase")
    parser.add_argument("--skip-testing", action="store_true", help="Skip testing phase")
    parser.add_argument("--dry-run", action="store_true", help="Plan only, don't execute")
    
    args = parser.parse_args()
    
    print("🤖 RAG-Enhanced Coding Agent Team")
    print("=" * 50)
    print(f"📝 Task: {args.task}")
    print(f"🔧 Mode: {'Dry Run' if args.dry_run else 'Full Execution'}")
    print()
    
    # Initialize workflow
    workflow = CodingWorkflow()
    
    # Execute workflow
    if args.dry_run:
        print("🧠 Planning phase only...")
        # Just run planning phase for dry run
        from agent.team.core import Task
        task = Task(description=args.task)
        plan_result = workflow._execute_planning_phase(args.task)
        
        if plan_result:
            print("\n📋 Generated Plan:")
            for i, step in enumerate(plan_result.get("plan_steps", []), 1):
                print(f"  {i}. {step}")
            
            print(f"\n🎯 Task Breakdown:")
            breakdown = plan_result.get("task_breakdown", {})
            print(f"  - Complexity: {breakdown.get('complexity', 'unknown')}")
            print(f"  - Estimated Files: {breakdown.get('estimated_files', 'unknown')}")
            print(f"  - RAG Insights: {breakdown.get('rag_insights', 0)} relevant knowledge chunks")
            
            if breakdown.get("suggested_patterns"):
                print(f"  - Suggested Patterns: {', '.join(breakdown['suggested_patterns'])}")
        else:
            print("❌ Planning failed")
            return 1
    else:
        result = workflow.execute_full_workflow(
            args.task,
            skip_review=args.skip_review,
            skip_testing=args.skip_testing
        )
        
        # Print summary
        print(workflow.get_workflow_summary(result))
        
        # Additional details if successful
        if result.success and result.code:
            print("\n📁 Generated Files:")
            files = result.code.get("generated_files", {})
            for filename, content in files.items():
                lines = len([l for l in content.split('\n') if l.strip()])
                print(f"  - {filename}: {lines} lines")
            
            knowledge_applied = result.code.get("knowledge_applied", [])
            if knowledge_applied:
                print(f"\n🧠 RAG Knowledge Applied:")
                for knowledge in knowledge_applied:
                    print(f"  - {knowledge}")
        
        return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())