"""
Auto-Enhancement System for Small Language Models

This module provides automatic RAG and prompting enhancements to boost
the performance of smaller models to compete with larger ones.
"""

from __future__ import annotations
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json
import hashlib

class TaskComplexity(Enum):
    SIMPLE = "simple"      # Single file, basic operations
    MEDIUM = "medium"      # Multiple files, some logic
    COMPLEX = "complex"    # Architecture changes, complex logic

class TaskType(Enum):
    FILE_CREATION = "file_creation"
    BUG_FIX = "bug_fix"
    FEATURE_ADD = "feature_add"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TESTING = "testing"

@dataclass
class TaskAnalysis:
    complexity: TaskComplexity
    task_type: TaskType
    keywords: List[str]
    files_involved: List[str]
    confidence: float

@dataclass
class EnhancementContext:
    examples: List[str]
    patterns: List[str]
    best_practices: List[str]
    warnings: List[str]
    related_code: Dict[str, str]

class TaskClassifier:
    """Analyzes tasks to determine complexity and type."""
    
    def __init__(self):
        self.complexity_patterns = {
            TaskComplexity.SIMPLE: [
                r'\bcreate\s+\w+\.(py|js|ts|go|rs)\b',
                r'\badd\s+(simple|basic)\b',
                r'\bfix\s+typo\b',
                r'\bupdate\s+\w+\s+to\s+\w+\b'
            ],
            TaskComplexity.COMPLEX: [
                r'\brefactor\s+(architecture|system)\b',
                r'\badd\s+(authentication|authorization)\b',
                r'\bimplement\s+(api|service|framework)\b',
                r'\bmigrate\s+to\b',
                r'\bredesign\b'
            ]
        }
        
        self.type_patterns = {
            TaskType.FILE_CREATION: [r'\bcreate\b', r'\badd.*file\b', r'\bnew.*\.(py|js|ts)\b'],
            TaskType.BUG_FIX: [r'\bfix\b', r'\bbug\b', r'\berror\b', r'\bissue\b'],
            TaskType.FEATURE_ADD: [r'\badd\b', r'\bimplement\b', r'\bbuild\b', r'\bcreate.*feature\b'],
            TaskType.REFACTOR: [r'\brefactor\b', r'\breorganize\b', r'\bclean\s+up\b'],
            TaskType.DOCUMENTATION: [r'\bdoc\b', r'\breadme\b', r'\bcomment\b', r'\bdocstring\b'],
            TaskType.TESTING: [r'\btest\b', r'\bunit\s+test\b', r'\bspec\b']
        }
    
    def analyze(self, task: str) -> TaskAnalysis:
        """Analyze a task string and return classification."""
        task_lower = task.lower()
        
        # Determine complexity
        complexity = TaskComplexity.MEDIUM  # Default
        max_confidence = 0.0
        
        for comp, patterns in self.complexity_patterns.items():
            confidence = sum(1 for p in patterns if re.search(p, task_lower))
            if confidence > max_confidence:
                complexity = comp
                max_confidence = confidence
        
        # Determine type
        task_type = TaskType.FEATURE_ADD  # Default
        type_confidence = 0.0
        
        for t_type, patterns in self.type_patterns.items():
            confidence = sum(1 for p in patterns if re.search(p, task_lower))
            if confidence > type_confidence:
                task_type = t_type
                type_confidence = confidence
        
        # Extract keywords
        keywords = re.findall(r'\b\w+\b', task_lower)
        
        # Extract file mentions
        files_involved = re.findall(r'\b\w+\.[a-z]+\b', task)
        
        return TaskAnalysis(
            complexity=complexity,
            task_type=task_type,
            keywords=keywords,
            files_involved=files_involved,
            confidence=max(max_confidence, type_confidence) / 3.0  # Normalize
        )

class ContextRetriever:
    """Retrieves relevant context for tasks."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.cache = {}
        self._build_codebase_index()
    
    def _build_codebase_index(self):
        """Build an index of the current codebase."""
        self.codebase_index = {
            "files": [],
            "functions": {},
            "classes": {},
            "imports": set(),
            "patterns": {}
        }
        
        # Scan Python files
        for py_file in self.project_root.rglob("*.py"):
            if "/__pycache__/" in str(py_file):
                continue
                
            try:
                content = py_file.read_text(encoding='utf-8')
                self.codebase_index["files"].append(str(py_file))
                
                # Extract functions
                functions = re.findall(r'def\s+(\w+)', content)
                self.codebase_index["functions"][str(py_file)] = functions
                
                # Extract classes
                classes = re.findall(r'class\s+(\w+)', content)
                self.codebase_index["classes"][str(py_file)] = classes
                
                # Extract imports
                imports = re.findall(r'(?:from\s+[\w.]+\s+)?import\s+([\w., ]+)', content)
                for imp in imports:
                    self.codebase_index["imports"].update(imp.split(', '))
                    
            except Exception:
                continue  # Skip files with encoding issues
    
    def get_context(self, analysis: TaskAnalysis) -> EnhancementContext:
        """Get relevant context for a task."""
        examples = self._get_examples(analysis)
        patterns = self._get_patterns(analysis)
        best_practices = self._get_best_practices(analysis)
        warnings = self._get_warnings(analysis)
        related_code = self._get_related_code(analysis)
        
        return EnhancementContext(
            examples=examples,
            patterns=patterns,
            best_practices=best_practices,
            warnings=warnings,
            related_code=related_code
        )
    
    def _get_examples(self, analysis: TaskAnalysis) -> List[str]:
        """Get relevant code examples."""
        examples = []
        
        if analysis.task_type == TaskType.FILE_CREATION:
            examples = [
                "# Example Python module structure:\n# mymodule.py\n\"\"\"\nModule docstring.\n\"\"\"\n\nfrom typing import Optional\n\nclass MyClass:\n    def __init__(self):\n        pass",
                "# Simple function file:\n# utils.py\n\ndef helper_function(arg: str) -> str:\n    \"\"\"Helper function docstring.\"\"\"\n    return arg.upper()"
            ]
        
        elif analysis.task_type == TaskType.BUG_FIX:
            examples = [
                "# Common fix pattern:\n# Before: if x = 5:\n# After: if x == 5:",
                "# Null check pattern:\n# Before: obj.method()\n# After: if obj: obj.method()"
            ]
        
        return examples
    
    def _get_patterns(self, analysis: TaskAnalysis) -> List[str]:
        """Get code patterns from current codebase."""
        patterns = []
        
        # Look for similar files or functions
        if analysis.files_involved:
            for file_name in analysis.files_involved:
                base_name = file_name.split('.')[0]
                for indexed_file in self.codebase_index["files"]:
                    if base_name in indexed_file:
                        patterns.append(f"Similar file structure found in: {indexed_file}")
        
        return patterns
    
    def _get_best_practices(self, analysis: TaskAnalysis) -> List[str]:
        """Get relevant best practices."""
        practices = {
            TaskType.FILE_CREATION: [
                "Always include module docstrings",
                "Use type hints for function parameters",
                "Follow PEP 8 naming conventions",
                "Import only what you need"
            ],
            TaskType.BUG_FIX: [
                "Write a test that reproduces the bug first",
                "Make minimal changes to fix the issue",
                "Check for similar issues in other parts of the code"
            ],
            TaskType.REFACTOR: [
                "Preserve existing functionality",
                "Break changes into small steps",
                "Update tests after refactoring"
            ]
        }
        
        return practices.get(analysis.task_type, [])
    
    def _get_warnings(self, analysis: TaskAnalysis) -> List[str]:
        """Get relevant warnings and pitfalls."""
        warnings = {
            TaskType.FILE_CREATION: [
                "Don't forget to add __init__.py for packages",
                "Check if file already exists before creating"
            ],
            TaskType.BUG_FIX: [
                "Make sure the fix doesn't break other functionality",
                "Consider edge cases"
            ]
        }
        
        return warnings.get(analysis.task_type, [])
    
    def _get_related_code(self, analysis: TaskAnalysis) -> Dict[str, str]:
        """Get snippets of related code."""
        related = {}
        
        # Find functions with similar names
        for keyword in analysis.keywords:
            for file_path, functions in self.codebase_index["functions"].items():
                for func in functions:
                    if keyword in func.lower() or func.lower() in keyword:
                        related[f"{file_path}:{func}"] = f"def {func}(...): ..."
        
        return related

class PromptEnhancer:
    """Enhances prompts with context and advanced prompting techniques."""
    
    def __init__(self):
        self.templates = {
            TaskComplexity.SIMPLE: self._simple_template,
            TaskComplexity.MEDIUM: self._medium_template,
            TaskComplexity.COMPLEX: self._complex_template
        }
    
    def enhance_prompt(self, original_prompt: str, context: EnhancementContext, analysis: TaskAnalysis) -> str:
        """Enhance a prompt with context and advanced techniques."""
        template = self.templates[analysis.complexity]
        return template(original_prompt, context, analysis)
    
    def _simple_template(self, prompt: str, context: EnhancementContext, analysis: TaskAnalysis) -> str:
        """Template for simple tasks - minimal enhancement."""
        enhancement = ""
        
        if context.examples:
            enhancement += f"Example format:\n{context.examples[0]}\n\n"
        
        if context.best_practices:
            enhancement += f"Remember: {'; '.join(context.best_practices[:2])}\n\n"
        
        return f"{enhancement}Task: {prompt}"
    
    def _medium_template(self, prompt: str, context: EnhancementContext, analysis: TaskAnalysis) -> str:
        """Template for medium complexity tasks."""
        enhancement = "Context and Guidelines:\n"
        
        if context.examples:
            enhancement += f"Examples:\n{chr(10).join(context.examples[:2])}\n\n"
        
        if context.patterns:
            enhancement += f"Codebase patterns:\n{chr(10).join(context.patterns)}\n\n"
        
        if context.best_practices:
            enhancement += f"Best practices:\n{chr(10).join(['- ' + bp for bp in context.best_practices])}\n\n"
        
        enhancement += f"Task: {prompt}\n\n"
        enhancement += "Approach this step by step:\n1. Understand the requirements\n2. Plan the implementation\n3. Write the code\n4. Consider edge cases"
        
        return enhancement
    
    def _complex_template(self, prompt: str, context: EnhancementContext, analysis: TaskAnalysis) -> str:
        """Template for complex tasks - full enhancement."""
        enhancement = "# Advanced Task Analysis\n\n"
        
        enhancement += f"## Task Classification\n"
        enhancement += f"- Type: {analysis.task_type.value}\n"
        enhancement += f"- Complexity: {analysis.complexity.value}\n"
        enhancement += f"- Files involved: {', '.join(analysis.files_involved)}\n\n"
        
        if context.related_code:
            enhancement += f"## Related Code Context\n"
            for ref, code in list(context.related_code.items())[:3]:
                enhancement += f"From {ref}:\n```python\n{code}\n```\n\n"
        
        if context.examples:
            enhancement += f"## Examples\n"
            for i, example in enumerate(context.examples[:2], 1):
                enhancement += f"Example {i}:\n```python\n{example}\n```\n\n"
        
        if context.best_practices:
            enhancement += f"## Best Practices\n"
            enhancement += chr(10).join([f"- {bp}" for bp in context.best_practices])
            enhancement += "\n\n"
        
        if context.warnings:
            enhancement += f"## ⚠️ Important Warnings\n"
            enhancement += chr(10).join([f"- {w}" for w in context.warnings])
            enhancement += "\n\n"
        
        enhancement += f"## Task\n{prompt}\n\n"
        enhancement += """## Approach
Think through this systematically:

1. **Analysis**: What exactly needs to be done?
2. **Planning**: What's the best approach? What files/functions are needed?
3. **Design**: How should this integrate with existing code?
4. **Implementation**: Write the code step by step
5. **Validation**: Check for errors and edge cases

Let's start:"""
        
        return enhancement

class AutoEnhancementSystem:
    """Main system that coordinates all enhancement components."""
    
    def __init__(self, project_root: str = "."):
        self.classifier = TaskClassifier()
        self.retriever = ContextRetriever(project_root)
        self.enhancer = PromptEnhancer()
        
    def enhance_task(self, task: str) -> tuple[str, TaskAnalysis]:
        """
        Enhance a task with automatic RAG and prompting improvements.
        
        Returns:
            tuple: (enhanced_prompt, task_analysis)
        """
        # Step 1: Analyze the task
        analysis = self.classifier.analyze(task)
        
        # Step 2: Retrieve relevant context
        context = self.retriever.get_context(analysis)
        
        # Step 3: Enhance the prompt
        enhanced_prompt = self.enhancer.enhance_prompt(task, context, analysis)
        
        return enhanced_prompt, analysis
    
    def should_use_enhancement(self, task: str) -> bool:
        """Determine if a task would benefit from enhancement."""
        analysis = self.classifier.analyze(task)
        
        # Always enhance medium and complex tasks
        if analysis.complexity in [TaskComplexity.MEDIUM, TaskComplexity.COMPLEX]:
            return True
            
        # Enhance simple tasks if confidence is low
        if analysis.confidence < 0.5:
            return True
            
        return False