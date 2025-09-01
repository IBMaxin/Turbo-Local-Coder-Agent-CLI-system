"""
Smart Configuration with Auto-Detection and Intelligent Defaults

Automatically detects project context, complexity, and optimal settings
to provide zero-config experience for most use cases.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from .config import Settings
from .errors import TurboError, ErrorCategory, create_error_context


class ProjectType(Enum):
    """Detected project types for smart defaults."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    JAVA = "java"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class TaskComplexity(Enum):
    """Task complexity levels for auto-configuration."""
    SIMPLE = "simple"      # 1-5 steps, single file
    MEDIUM = "medium"      # 6-15 steps, multiple files
    COMPLEX = "complex"    # 16+ steps, architecture changes
    ENTERPRISE = "enterprise"  # Multi-component, testing required


@dataclass
class ProjectContext:
    """Detected project context information."""
    project_type: ProjectType
    languages: List[str]
    frameworks: List[str]
    has_tests: bool
    has_ci_cd: bool
    file_count: int
    complexity_indicators: List[str]
    recommended_max_steps: int
    needs_enhanced_mode: bool


class SmartConfigDetector:
    """Detects project context and provides intelligent defaults."""
    
    def __init__(self, project_path: Path = Path(".")):
        self.project_path = project_path.resolve()
        self._file_patterns = {
            ProjectType.PYTHON: [".py", "requirements.txt", "pyproject.toml", "setup.py"],
            ProjectType.JAVASCRIPT: ["package.json", ".js", ".jsx"],
            ProjectType.TYPESCRIPT: ["tsconfig.json", ".ts", ".tsx"],
            ProjectType.RUST: ["Cargo.toml", ".rs"],
            ProjectType.GO: ["go.mod", ".go"],
            ProjectType.JAVA: ["pom.xml", "build.gradle", ".java"]
        }
        
        self._complexity_indicators = {
            "microservices": ["docker-compose.yml", "kubernetes", "helm"],
            "web_framework": ["django", "flask", "fastapi", "express", "react", "vue"],
            "database": ["models.py", "migrations", "schema.sql"],
            "testing": ["test_", "tests/", "spec/", ".test.", ".spec."],
            "ci_cd": [".github/", ".gitlab-ci", "Jenkinsfile", ".travis.yml"],
            "documentation": ["docs/", "README.md", "CHANGELOG.md"]
        }
    
    def detect_project_context(self) -> ProjectContext:
        """Analyze project and return detected context."""
        try:
            # Count files and detect languages
            files = list(self.project_path.rglob("*"))
            code_files = [f for f in files if f.is_file() and not self._is_ignored_file(f)]
            
            project_type = self._detect_primary_language(code_files)
            languages = self._detect_all_languages(code_files)
            frameworks = self._detect_frameworks(code_files)
            
            # Analyze complexity
            has_tests = self._has_tests(code_files)
            has_ci_cd = self._has_ci_cd(code_files)
            complexity_indicators = self._detect_complexity_indicators(code_files)
            
            # Calculate recommended settings
            max_steps = self._calculate_max_steps(len(code_files), complexity_indicators)
            needs_enhanced = self._should_use_enhanced_mode(complexity_indicators)
            
            return ProjectContext(
                project_type=project_type,
                languages=languages,
                frameworks=frameworks,
                has_tests=has_tests,
                has_ci_cd=has_ci_cd,
                file_count=len(code_files),
                complexity_indicators=complexity_indicators,
                recommended_max_steps=max_steps,
                needs_enhanced_mode=needs_enhanced
            )
            
        except Exception as e:
            # Return minimal context on error
            return ProjectContext(
                project_type=ProjectType.UNKNOWN,
                languages=[],
                frameworks=[],
                has_tests=False,
                has_ci_cd=False,
                file_count=0,
                complexity_indicators=[],
                recommended_max_steps=25,
                needs_enhanced_mode=False
            )
    
    def _is_ignored_file(self, file_path: Path) -> bool:
        """Check if file should be ignored in analysis."""
        ignored_patterns = [
            ".git", "__pycache__", "node_modules", "venv", ".venv",
            "build", "dist", "target", ".pytest_cache", ".mypy_cache",
            ".DS_Store", "*.log", "*.tmp"
        ]
        
        file_str = str(file_path).lower()
        return any(pattern in file_str for pattern in ignored_patterns)
    
    def _detect_primary_language(self, files: List[Path]) -> ProjectType:
        """Detect the primary programming language."""
        language_counts = {}
        
        for project_type, patterns in self._file_patterns.items():
            count = 0
            for file in files:
                if any(pattern in file.name or file.suffix == pattern.replace("*", "") 
                      for pattern in patterns):
                    count += 1
            if count > 0:
                language_counts[project_type] = count
        
        if not language_counts:
            return ProjectType.UNKNOWN
        
        # Return the most common language type
        primary = max(language_counts.items(), key=lambda x: x[1])
        
        # If multiple languages have similar counts, mark as mixed
        max_count = primary[1]
        similar_count_langs = [lang for lang, count in language_counts.items() 
                              if count >= max_count * 0.7]
        
        if len(similar_count_langs) > 1:
            return ProjectType.MIXED
        
        return primary[0]
    
    def _detect_all_languages(self, files: List[Path]) -> List[str]:
        """Detect all languages present in the project."""
        languages = set()
        
        for file in files:
            if file.suffix == ".py":
                languages.add("python")
            elif file.suffix in [".js", ".jsx"]:
                languages.add("javascript")
            elif file.suffix in [".ts", ".tsx"]:
                languages.add("typescript")
            elif file.suffix == ".rs":
                languages.add("rust")
            elif file.suffix == ".go":
                languages.add("go")
            elif file.suffix == ".java":
                languages.add("java")
        
        return list(languages)
    
    def _detect_frameworks(self, files: List[Path]) -> List[str]:
        """Detect frameworks in use."""
        frameworks = set()
        
        # Check for common framework indicators
        framework_indicators = {
            "django": ["manage.py", "settings.py", "django"],
            "flask": ["app.py", "flask"],
            "fastapi": ["fastapi", "uvicorn"],
            "react": ["package.json", "react"],
            "vue": ["vue.config.js", "vue"],
            "express": ["express", "app.js"],
            "spring": ["pom.xml", "spring"],
        }
        
        for framework, indicators in framework_indicators.items():
            for file in files:
                if any(indicator in file.name.lower() or 
                      (file.is_file() and indicator in file.read_text(errors="ignore").lower())
                      for indicator in indicators):
                    frameworks.add(framework)
                    break
        
        return list(frameworks)
    
    def _has_tests(self, files: List[Path]) -> bool:
        """Check if project has test files."""
        test_patterns = ["test_", "tests/", "_test.", ".test.", ".spec.", "spec/"]
        return any(any(pattern in str(file).lower() for pattern in test_patterns) 
                  for file in files)
    
    def _has_ci_cd(self, files: List[Path]) -> bool:
        """Check if project has CI/CD configuration."""
        ci_patterns = [".github/workflows", ".gitlab-ci", "Jenkinsfile", ".travis.yml"]
        return any(any(pattern in str(file).lower() for pattern in ci_patterns) 
                  for file in files)
    
    def _detect_complexity_indicators(self, files: List[Path]) -> List[str]:
        """Detect indicators of project complexity."""
        indicators = []
        
        for indicator_name, patterns in self._complexity_indicators.items():
            if any(any(pattern in str(file).lower() for pattern in patterns) 
                  for file in files):
                indicators.append(indicator_name)
        
        return indicators
    
    def _calculate_max_steps(self, file_count: int, complexity_indicators: List[str]) -> int:
        """Calculate recommended max steps based on project complexity."""
        base_steps = 25
        
        # Adjust based on file count
        if file_count > 100:
            base_steps += 20
        elif file_count > 50:
            base_steps += 10
        
        # Adjust based on complexity indicators
        complexity_bonus = {
            "microservices": 25,
            "web_framework": 10,
            "database": 15,
            "testing": 10,
            "ci_cd": 5,
            "documentation": 5
        }
        
        for indicator in complexity_indicators:
            base_steps += complexity_bonus.get(indicator, 0)
        
        return min(base_steps, 100)  # Cap at 100 steps
    
    def _should_use_enhanced_mode(self, complexity_indicators: List[str]) -> bool:
        """Determine if enhanced mode should be recommended."""
        complex_indicators = ["microservices", "database", "web_framework"]
        return any(indicator in complexity_indicators for indicator in complex_indicators)


def detect_task_complexity(task_description: str) -> TaskComplexity:
    """Analyze task description to determine complexity level."""
    task_lower = task_description.lower()
    
    # Simple task indicators
    simple_patterns = [
        r"\b(fix|update|change|modify|add)\s+\w+\s+(function|method|variable|import)",
        r"\b(create|write|make)\s+a?\s+(simple|basic|small)\b",
        r"\b(rename|delete|remove)\s+",
        r"\b(format|lint|style)\b"
    ]
    
    # Complex task indicators  
    complex_patterns = [
        r"\b(architecture|microservice|system|framework|infrastructure)\b",
        r"\b(refactor|restructure|redesign|migrate)\b",
        r"\b(multiple|several|many)\s+(files|components|services)\b",
        r"\b(integration|deployment|ci/cd|pipeline)\b",
        r"\b(database|api|authentication|authorization)\b"
    ]
    
    # Enterprise task indicators
    enterprise_patterns = [
        r"\b(enterprise|production|scalable|high.?availability)\b",
        r"\b(monitoring|logging|observability|metrics)\b",
        r"\b(security|compliance|audit)\b",
        r"\b(multi.?tenant|distributed|cluster)\b"
    ]
    
    # Check patterns
    if any(re.search(pattern, task_lower) for pattern in enterprise_patterns):
        return TaskComplexity.ENTERPRISE
    elif any(re.search(pattern, task_lower) for pattern in complex_patterns):
        return TaskComplexity.COMPLEX
    elif any(re.search(pattern, task_lower) for pattern in simple_patterns):
        return TaskComplexity.SIMPLE
    else:
        # Default to medium for unclear tasks
        return TaskComplexity.MEDIUM


def create_smart_settings(task_description: str, 
                         user_overrides: Optional[Dict[str, Any]] = None) -> Settings:
    """Create optimized settings based on task and project context."""
    from .config import load_settings
    
    # Load base settings
    base_settings = load_settings()
    
    # Detect project context
    detector = SmartConfigDetector()
    project_context = detector.detect_project_context()
    task_complexity = detect_task_complexity(task_description)
    
    # Calculate optimal settings
    optimal_max_steps = _calculate_optimal_max_steps(task_complexity, project_context)
    should_use_enhanced = _should_enable_enhanced_mode(task_complexity, project_context)
    
    # Apply smart defaults
    smart_overrides = {
        "max_steps": optimal_max_steps,
        "dry_run": False if should_use_enhanced else base_settings.dry_run,
    }
    
    # Apply user overrides
    if user_overrides:
        smart_overrides.update({k: v for k, v in user_overrides.items() if v is not None})
    
    return base_settings.with_overrides(**smart_overrides)


def _calculate_optimal_max_steps(task_complexity: TaskComplexity, 
                                project_context: ProjectContext) -> int:
    """Calculate optimal max steps based on task and project complexity."""
    base_steps = {
        TaskComplexity.SIMPLE: 10,
        TaskComplexity.MEDIUM: 25,
        TaskComplexity.COMPLEX: 50,
        TaskComplexity.ENTERPRISE: 80
    }
    
    steps = base_steps[task_complexity]
    
    # Adjust based on project context
    if project_context.needs_enhanced_mode:
        steps += 10
    if project_context.has_tests:
        steps += 5
    if project_context.file_count > 50:
        steps += 10
    
    return min(steps, project_context.recommended_max_steps)


def _should_enable_enhanced_mode(task_complexity: TaskComplexity,
                                project_context: ProjectContext) -> bool:
    """Determine if enhanced mode should be automatically enabled."""
    return (
        task_complexity in [TaskComplexity.COMPLEX, TaskComplexity.ENTERPRISE] or
        project_context.needs_enhanced_mode or
        len(project_context.complexity_indicators) >= 3
    )