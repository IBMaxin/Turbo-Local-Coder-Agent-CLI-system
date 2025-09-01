"""
RAG-enhanced specialized agents with built-in knowledge retrieval.
"""

from __future__ import annotations
import time
from typing import Dict, Any, Optional, List

from .core import Agent, Task, AgentResult
from .rag_system import RAGKnowledgeBase, RAGEnhancedAgent
from ..core.planner import get_plan
from ..core.executor import execute
from ..core.config import load_settings


class RAGPlannerAgent(RAGEnhancedAgent, Agent):
    """RAG-enhanced planning agent."""
    
    def __init__(self, name: str = "rag-planner"):
        Agent.__init__(self, name, "planner")
        RAGEnhancedAgent.__init__(self, name, "planner")
        self.settings = load_settings()
    
    def process_task(self, task: Task) -> AgentResult:
        """Generate enhanced plan using RAG knowledge."""
        start_time = time.time()
        
        try:
            # Enhance the prompt with relevant knowledge
            enhanced_description = self.enhance_prompt(task.description)
            
            # Use enhanced prompt with the planner
            plan = get_plan(enhanced_description, self.settings)
            
            # Add learning context
            context_info = self.rag_kb.get_context_for_query(task.description, max_tokens=500)
            
            result = {
                "plan_steps": plan.plan,
                "detailed_instructions": plan.coder_prompt,
                "suggested_tests": plan.tests,
                "rag_context_used": len(context_info.split()) > 50,  # Check if context was useful
                "enhanced_prompt": enhanced_description[:300] + "...",  # Preview
                "task_breakdown": self._analyze_task_with_rag(task.description)
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
    
    def _analyze_task_with_rag(self, description: str) -> Dict[str, Any]:
        """Analyze task using RAG knowledge."""
        # Get relevant knowledge to inform task analysis
        relevant_chunks = self.rag_kb.retrieve_relevant(description, limit=3)
        
        complexity = "medium"
        estimated_files = 1
        dependencies = []
        requires_testing = True
        suggested_patterns = []
        
        # Analyze based on relevant knowledge
        for chunk, score in relevant_chunks:
            if chunk.chunk_type == "pattern" and score > 0.1:
                suggested_patterns.append(chunk.content.split('\n')[0])  # Get pattern name
            
            if "complex" in chunk.content.lower() or "advanced" in chunk.content.lower():
                complexity = "high"
                estimated_files = max(estimated_files, 3)
            
            if any(lib in chunk.content.lower() for lib in ["requests", "flask", "fastapi"]):
                dependencies.extend(["requests", "flask"])
        
        # Task-specific analysis
        desc_lower = description.lower()
        if any(word in desc_lower for word in ["api", "web", "server", "database"]):
            complexity = "high"
            estimated_files = 3
            requires_testing = True
        
        if any(word in desc_lower for word in ["simple", "hello", "basic", "print"]):
            complexity = "low"
            requires_testing = False
        
        return {
            "complexity": complexity,
            "estimated_files": estimated_files,
            "dependencies": list(set(dependencies)),
            "requires_testing": requires_testing,
            "suggested_patterns": suggested_patterns,
            "rag_insights": len(relevant_chunks)
        }


class RAGCoderAgent(RAGEnhancedAgent, Agent):
    """RAG-enhanced coding agent."""
    
    def __init__(self, name: str = "rag-coder"):
        Agent.__init__(self, name, "coder")
        RAGEnhancedAgent.__init__(self, name, "coder")
        self.settings = load_settings()
    
    def process_task(self, task: Task) -> AgentResult:
        """Generate code with RAG enhancement."""
        start_time = time.time()
        
        try:
            # Extract plan from task requirements
            if "plan" in task.requirements:
                plan_data = task.requirements["plan"]
                base_prompt = plan_data.get("detailed_instructions", task.description)
            else:
                base_prompt = task.description
            
            # Enhance the coding prompt with relevant knowledge
            enhanced_prompt = self.enhance_prompt(base_prompt)
            
            # Execute with enhanced prompt
            summary = execute(enhanced_prompt, self.settings)
            
            # Collect generated files
            generated_files = self._collect_generated_files()
            
            # Analyze code quality using RAG knowledge
            quality_analysis = self._analyze_code_quality_with_rag(generated_files)
            
            result = {
                "execution_summary": {
                    "steps_taken": summary.steps,
                    "last_message": summary.last
                },
                "generated_files": generated_files,
                "code_metrics": self._analyze_code(generated_files),
                "quality_analysis": quality_analysis,
                "rag_enhanced": True,
                "knowledge_applied": self._identify_applied_knowledge(generated_files)
            }
            
            # Learn from successful generation
            if generated_files:
                self.add_experience(
                    task.description,
                    str(list(generated_files.values())),
                    "code_example"
                )
            
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
    
    def _analyze_code_quality_with_rag(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Analyze code quality using RAG knowledge."""
        if not files:
            return {"analysis": "No files to analyze"}
        
        # Get best practices knowledge
        best_practices = self.rag_kb.retrieve_relevant("python best practices", ["documentation"], 1)
        
        quality_score = 0
        max_score = 10
        issues = []
        good_practices = []
        
        for filename, content in files.items():
            # Check for docstrings (from RAG knowledge)
            if '"""' in content or "'''" in content:
                good_practices.append("Has docstrings")
                quality_score += 2
            else:
                issues.append("Missing docstrings")
            
            # Check for type hints (from RAG knowledge)
            if '->' in content and ':' in content:
                good_practices.append("Uses type hints")
                quality_score += 1
            
            # Check for error handling (from RAG knowledge)
            if 'try:' in content and 'except' in content:
                good_practices.append("Includes error handling")
                quality_score += 2
            elif any(word in content.lower() for word in ['file', 'open', 'request']):
                issues.append("Missing error handling for risky operations")
            
            # Check for f-strings (from RAG knowledge)
            if 'f"' in content or "f'" in content:
                good_practices.append("Uses f-strings")
                quality_score += 0.5
        
        return {
            "quality_score": min(quality_score, max_score),
            "max_score": max_score,
            "good_practices": good_practices,
            "issues": issues,
            "rag_analysis": "Applied RAG knowledge for quality assessment"
        }
    
    def _identify_applied_knowledge(self, files: Dict[str, str]) -> List[str]:
        """Identify what RAG knowledge was applied in the code."""
        applied = []
        all_content = " ".join(files.values()).lower()
        
        if 'try:' in all_content and 'except' in all_content:
            applied.append("Error handling patterns")
        
        if '"""' in all_content:
            applied.append("Documentation practices")
        
        if 'def __init__' in all_content or 'class ' in all_content:
            applied.append("Object-oriented patterns")
        
        if 'pytest' in all_content or 'unittest' in all_content or 'assert' in all_content:
            applied.append("Testing patterns")
        
        if '@' in all_content:  # Decorators
            applied.append("Decorator patterns")
        
        return applied
    
    def _collect_generated_files(self) -> Dict[str, str]:
        """Collect generated files (same as parent class)."""
        import os
        from ..tools.fs import fs_read
        
        files = {}
        try:
            for filename in os.listdir("."):
                if filename.endswith(".py") and not filename.startswith("__"):
                    result = fs_read(filename)
                    if result.ok:
                        files[filename] = result.detail
        except Exception:
            pass
        return files
    
    def _analyze_code(self, files: Dict[str, str]) -> Dict[str, Any]:
        """Basic code analysis (same as parent class)."""
        total_lines = 0
        total_functions = 0
        total_classes = 0
        
        for content in files.values():
            lines = content.split('\n')
            total_lines += len([l for l in lines if l.strip()])
            total_functions += content.count('def ')
            total_classes += content.count('class ')
        
        return {
            "total_lines": total_lines,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "files_count": len(files)
        }


class RAGReviewerAgent(RAGEnhancedAgent, Agent):
    """RAG-enhanced code review agent."""
    
    def __init__(self, name: str = "rag-reviewer"):
        Agent.__init__(self, name, "reviewer")
        RAGEnhancedAgent.__init__(self, name, "reviewer")
    
    def process_task(self, task: Task) -> AgentResult:
        """Enhanced code review using RAG knowledge."""
        start_time = time.time()
        
        try:
            code_files = task.requirements.get("generated_files", {})
            
            if not code_files:
                return AgentResult(
                    agent_name=self.name,
                    task_id=task.id,
                    success=False,
                    output=None,
                    error="No code files provided for review"
                )
            
            # Get relevant review knowledge
            review_knowledge = self.rag_kb.retrieve_relevant(
                "python best practices code review", 
                ["documentation", "pattern"], 
                3
            )
            
            review_results = {}
            overall_score = 0
            issue_count = 0
            knowledge_based_suggestions = []
            
            for filename, content in code_files.items():
                file_review = self._review_file_with_rag(filename, content, review_knowledge)
                review_results[filename] = file_review
                overall_score += file_review["score"]
                issue_count += len(file_review["issues"])
                knowledge_based_suggestions.extend(file_review.get("rag_suggestions", []))
            
            overall_score = overall_score / len(code_files) if code_files else 0
            
            result = {
                "overall_score": overall_score,
                "total_issues": issue_count,
                "file_reviews": review_results,
                "recommendations": self._generate_rag_recommendations(review_results, review_knowledge),
                "knowledge_based_suggestions": list(set(knowledge_based_suggestions)),
                "approved": overall_score >= 8.0 and issue_count < 3,  # Higher standards with RAG
                "rag_enhanced_review": True
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
    
    def _review_file_with_rag(self, filename: str, content: str, 
                             knowledge: List[tuple]) -> Dict[str, Any]:
        """Review file using RAG knowledge."""
        issues = []
        score = 10.0
        rag_suggestions = []
        
        lines = content.split('\n')
        
        # Apply knowledge-based review criteria
        for chunk, relevance in knowledge:
            chunk_content = chunk.content.lower()
            
            # Check for best practices mentioned in knowledge
            if "docstring" in chunk_content and ('"""' not in content and "'''" not in content):
                if 'def ' in content:
                    issues.append("Missing docstrings for functions (RAG recommendation)")
                    rag_suggestions.append("Add comprehensive docstrings as per best practices")
                    score -= 1.5
            
            if "type hint" in chunk_content and '->' not in content:
                if 'def ' in content:
                    issues.append("Missing type hints (RAG recommendation)")
                    rag_suggestions.append("Add type hints for better code clarity")
                    score -= 1.0
            
            if "exception" in chunk_content or "error handling" in chunk_content:
                risky_ops = ['open(', 'requests.', 'json.load', 'int(', 'float(']
                if any(op in content for op in risky_ops) and 'try:' not in content:
                    issues.append("Missing error handling for risky operations (RAG recommendation)")
                    rag_suggestions.append("Add proper exception handling as per best practices")
                    score -= 2.0
        
        # Additional RAG-informed checks
        if len(lines) > 100:
            rag_suggestions.append("Consider breaking large files into smaller modules")
        
        # Check for code smells using RAG knowledge
        if content.count('def ') > 10:
            rag_suggestions.append("High number of functions - consider class-based organization")
        
        return {
            "score": max(0, score),
            "issues": issues,
            "line_count": len([l for l in lines if l.strip()]),
            "complexity": self._assess_complexity(content),
            "rag_suggestions": rag_suggestions
        }
    
    def _assess_complexity(self, content: str) -> str:
        """Assess code complexity."""
        lines = len([l for l in content.split('\n') if l.strip()])
        functions = content.count('def ')
        classes = content.count('class ')
        nested_loops = content.count('for ') * content.count('while ') 
        
        complexity_score = lines * 0.1 + functions * 2 + classes * 3 + nested_loops * 1.5
        
        if complexity_score < 20:
            return "low"
        elif complexity_score < 60:
            return "medium"
        else:
            return "high"
    
    def _generate_rag_recommendations(self, reviews: Dict[str, Dict], 
                                    knowledge: List[tuple]) -> List[str]:
        """Generate recommendations using RAG knowledge."""
        recommendations = []
        
        total_issues = sum(len(review["issues"]) for review in reviews.values())
        avg_score = sum(review["score"] for review in reviews.values()) / len(reviews)
        
        # Standard recommendations
        if avg_score < 8.0:
            recommendations.append("Code quality needs significant improvement based on best practices")
        
        if total_issues > 3:
            recommendations.append("Multiple issues found - prioritize fixing critical ones first")
        
        # RAG-informed recommendations
        for chunk, relevance in knowledge:
            if relevance > 0.2:  # Highly relevant knowledge
                if "best practice" in chunk.content.lower():
                    recommendations.append(f"Review and apply best practices from knowledge base")
                if "pattern" in chunk.content.lower():
                    recommendations.append(f"Consider implementing appropriate design patterns")
        
        return list(set(recommendations))  # Remove duplicates


def demo_enhanced_agents():
    """Demonstrate RAG-enhanced agents."""
    print("🚀 RAG-Enhanced Agents Demo")
    print("=" * 50)
    
    # Initialize RAG knowledge base
    rag_kb = RAGKnowledgeBase()
    
    # Create RAG-enhanced agents
    planner = RAGPlannerAgent("rag-planner")
    coder = RAGCoderAgent("rag-coder")
    reviewer = RAGReviewerAgent("rag-reviewer")
    
    print("✅ RAG-enhanced agents initialized")
    print(f"📊 Knowledge base contains {len(rag_kb.retrieve_relevant('', limit=100))} chunks")
    
    # Demo query enhancement
    test_query = "Create a function to validate email addresses"
    enhanced = planner.enhance_prompt(test_query)
    
    print(f"\n🔍 Original query: {test_query}")
    print(f"📈 Enhanced query preview: {enhanced[:200]}...")
    
    return planner, coder, reviewer


if __name__ == "__main__":
    demo_enhanced_agents()