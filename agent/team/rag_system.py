"""
Efficient Built-in RAG (Retrieval-Augmented Generation) System
Provides context and knowledge base access for smaller models.
"""

from __future__ import annotations
import json
import hashlib
import sqlite3
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import time


@dataclass
class KnowledgeChunk:
    """A chunk of knowledge with metadata."""
    id: str
    content: str
    source: str
    chunk_type: str  # code, documentation, example, pattern
    keywords: List[str]
    embedding_hash: Optional[str] = None
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


class SimpleEmbedding:
    """Lightweight embedding system using TF-IDF style scoring."""
    
    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.doc_freq: Dict[str, int] = {}
        self.total_docs = 0
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization."""
        # Convert to lowercase, split on non-alphanumeric
        tokens = re.findall(r'\b\w+\b', text.lower())
        # Add code-specific tokens
        code_tokens = re.findall(r'[A-Za-z_][A-Za-z0-9_]*', text)
        return list(set(tokens + [t.lower() for t in code_tokens]))
    
    def add_document(self, text: str) -> Dict[str, float]:
        """Add document and return TF-IDF scores."""
        tokens = self._tokenize(text)
        
        # Update vocabulary and document frequency
        for token in set(tokens):
            if token not in self.vocab:
                self.vocab[token] = len(self.vocab)
            if token not in self.doc_freq:
                self.doc_freq[token] = 0
            self.doc_freq[token] += 1
        
        self.total_docs += 1
        
        # Calculate TF-IDF
        tf_idf = {}
        token_count = len(tokens)
        
        for token in tokens:
            tf = tokens.count(token) / token_count
            idf = math.log(self.total_docs / self.doc_freq[token])
            tf_idf[token] = tf * idf
        
        return tf_idf
    
    def get_similarity(self, query: str, doc_scores: Dict[str, float]) -> float:
        """Calculate similarity between query and document."""
        query_tokens = self._tokenize(query)
        
        if not query_tokens:
            return 0.0
        
        score = 0.0
        for token in query_tokens:
            if token in doc_scores:
                score += doc_scores[token]
        
        return score / len(query_tokens)


class RAGKnowledgeBase:
    """Lightweight knowledge base with retrieval capabilities."""
    
    def __init__(self, db_path: str = "rag_knowledge.db"):
        self.db_path = db_path
        self.embedding = SimpleEmbedding()
        self._init_db()
        self._load_builtin_knowledge()
    
    def _init_db(self):
        """Initialize SQLite database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    chunk_type TEXT NOT NULL,
                    keywords TEXT NOT NULL,
                    tf_idf_scores TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_keywords ON knowledge_chunks(keywords)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_type ON knowledge_chunks(chunk_type)
            """)
    
    def add_knowledge(self, chunk: KnowledgeChunk) -> str:
        """Add knowledge chunk to the database."""
        # Calculate TF-IDF scores
        tf_idf_scores = self.embedding.add_document(chunk.content)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO knowledge_chunks
                (id, content, source, chunk_type, keywords, tf_idf_scores, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk.id,
                chunk.content,
                chunk.source,
                chunk.chunk_type,
                json.dumps(chunk.keywords),
                json.dumps(tf_idf_scores),
                chunk.created_at
            ))
        
        return chunk.id
    
    def retrieve_relevant(self, query: str, 
                         chunk_types: Optional[List[str]] = None,
                         limit: int = 5) -> List[Tuple[KnowledgeChunk, float]]:
        """Retrieve most relevant knowledge chunks."""
        with sqlite3.connect(self.db_path) as conn:
            # Base query
            sql = "SELECT * FROM knowledge_chunks"
            params = []
            
            # Filter by chunk type if specified
            if chunk_types:
                placeholders = ','.join('?' * len(chunk_types))
                sql += f" WHERE chunk_type IN ({placeholders})"
                params.extend(chunk_types)
            
            cursor = conn.execute(sql, params)
            rows = cursor.fetchall()
        
        # Calculate relevance scores
        scored_chunks = []
        for row in rows:
            chunk = KnowledgeChunk(
                id=row[0],
                content=row[1],
                source=row[2],
                chunk_type=row[3],
                keywords=json.loads(row[4]),
                created_at=row[6]
            )
            
            tf_idf_scores = json.loads(row[5])
            relevance = self.embedding.get_similarity(query, tf_idf_scores)
            
            scored_chunks.append((chunk, relevance))
        
        # Sort by relevance and return top results
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:limit]
    
    def _load_builtin_knowledge(self):
        """Load built-in programming knowledge."""
        builtin_knowledge = [
            KnowledgeChunk(
                id="python-best-practices",
                content="""
                Python Best Practices:
                - Use descriptive variable names
                - Write docstrings for functions and classes
                - Follow PEP 8 style guide
                - Use type hints for better code clarity
                - Handle exceptions properly with try/except
                - Use list comprehensions for simple iterations
                - Prefer f-strings for string formatting
                - Use context managers (with statements) for resource handling
                """,
                source="builtin",
                chunk_type="documentation",
                keywords=["python", "best", "practices", "pep8", "docstring", "type", "hints"]
            ),
            
            KnowledgeChunk(
                id="common-patterns",
                content="""
                Common Programming Patterns:
                
                Singleton Pattern:
                class Singleton:
                    _instance = None
                    def __new__(cls):
                        if cls._instance is None:
                            cls._instance = super().__new__(cls)
                        return cls._instance
                
                Factory Pattern:
                def create_object(obj_type):
                    if obj_type == "A":
                        return ClassA()
                    elif obj_type == "B":
                        return ClassB()
                
                Decorator Pattern:
                def my_decorator(func):
                    def wrapper(*args, **kwargs):
                        # Before function call
                        result = func(*args, **kwargs)
                        # After function call
                        return result
                    return wrapper
                """,
                source="builtin",
                chunk_type="pattern",
                keywords=["singleton", "factory", "decorator", "pattern", "design"]
            ),
            
            KnowledgeChunk(
                id="error-handling",
                content="""
                Error Handling Best Practices:
                
                Specific Exception Handling:
                try:
                    risky_operation()
                except ValueError as e:
                    print(f"Value error: {e}")
                except FileNotFoundError:
                    print("File not found")
                except Exception as e:
                    print(f"Unexpected error: {e}")
                finally:
                    cleanup_resources()
                
                Custom Exceptions:
                class CustomError(Exception):
                    def __init__(self, message):
                        self.message = message
                        super().__init__(self.message)
                
                Validation:
                def validate_input(value):
                    if not isinstance(value, int):
                        raise TypeError("Expected integer")
                    if value < 0:
                        raise ValueError("Value must be positive")
                """,
                source="builtin",
                chunk_type="code",
                keywords=["error", "exception", "handling", "try", "catch", "validation"]
            ),
            
            KnowledgeChunk(
                id="testing-patterns",
                content="""
                Testing Patterns:
                
                Unit Test Structure:
                import unittest
                
                class TestMyFunction(unittest.TestCase):
                    def setUp(self):
                        # Setup before each test
                        pass
                    
                    def test_normal_case(self):
                        result = my_function(valid_input)
                        self.assertEqual(result, expected_output)
                    
                    def test_edge_case(self):
                        with self.assertRaises(ValueError):
                            my_function(invalid_input)
                
                Pytest Style:
                def test_function():
                    assert my_function(input) == expected
                
                def test_exception():
                    with pytest.raises(ValueError):
                        my_function(bad_input)
                
                Fixtures:
                @pytest.fixture
                def sample_data():
                    return {"key": "value"}
                """,
                source="builtin",
                chunk_type="code",
                keywords=["testing", "unittest", "pytest", "fixture", "assert", "mock"]
            ),
            
            KnowledgeChunk(
                id="algorithms",
                content="""
                Common Algorithms:
                
                Binary Search:
                def binary_search(arr, target):
                    left, right = 0, len(arr) - 1
                    while left <= right:
                        mid = (left + right) // 2
                        if arr[mid] == target:
                            return mid
                        elif arr[mid] < target:
                            left = mid + 1
                        else:
                            right = mid - 1
                    return -1
                
                Fibonacci:
                def fibonacci(n):
                    if n <= 1:
                        return n
                    return fibonacci(n-1) + fibonacci(n-2)
                
                def fibonacci_iterative(n):
                    if n <= 1:
                        return n
                    a, b = 0, 1
                    for _ in range(2, n + 1):
                        a, b = b, a + b
                    return b
                """,
                source="builtin",
                chunk_type="code", 
                keywords=["algorithm", "binary", "search", "fibonacci", "recursive", "iterative"]
            )
        ]
        
        # Check if knowledge already exists
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM knowledge_chunks")
            count = cursor.fetchone()[0]
        
        # Only add if database is empty
        if count == 0:
            for chunk in builtin_knowledge:
                self.add_knowledge(chunk)
    
    def get_context_for_query(self, query: str, max_tokens: int = 2000) -> str:
        """Get relevant context for a query, limited by token count."""
        # Determine what type of help is needed
        query_lower = query.lower()
        chunk_types = []
        
        if any(word in query_lower for word in ["test", "testing", "pytest", "unittest"]):
            chunk_types.append("testing")
        if any(word in query_lower for word in ["pattern", "design", "architecture"]):
            chunk_types.append("pattern")
        if any(word in query_lower for word in ["best", "practice", "convention", "style"]):
            chunk_types.append("documentation")
        if any(word in query_lower for word in ["algorithm", "function", "code", "implement"]):
            chunk_types.append("code")
        
        # Get relevant chunks
        relevant_chunks = self.retrieve_relevant(query, chunk_types, limit=3)
        
        # Build context string within token limit
        context_parts = ["=== RELEVANT KNOWLEDGE ===\n"]
        current_tokens = len(context_parts[0].split())
        
        for chunk, score in relevant_chunks:
            chunk_text = f"\n[{chunk.chunk_type.upper()}] {chunk.source}:\n{chunk.content}\n"
            chunk_tokens = len(chunk_text.split())
            
            if current_tokens + chunk_tokens <= max_tokens:
                context_parts.append(chunk_text)
                current_tokens += chunk_tokens
            else:
                break
        
        context_parts.append("\n=== END KNOWLEDGE ===\n")
        return "".join(context_parts)


class RAGEnhancedAgent:
    """Base class for agents with RAG capabilities."""
    
    def __init__(self, name: str, role: str, rag_kb: Optional[RAGKnowledgeBase] = None):
        self.name = name
        self.role = role
        self.rag_kb = rag_kb or RAGKnowledgeBase()
    
    def enhance_prompt(self, original_prompt: str) -> str:
        """Enhance prompt with relevant knowledge."""
        context = self.rag_kb.get_context_for_query(original_prompt)
        
        enhanced_prompt = f"""
{context}

ORIGINAL REQUEST:
{original_prompt}

Please use the relevant knowledge above to improve your response. Focus on:
1. Following best practices mentioned in the knowledge base
2. Using appropriate patterns and techniques
3. Including proper error handling and testing approaches
4. Writing clean, well-documented code

RESPONSE:
"""
        return enhanced_prompt
    
    def add_experience(self, query: str, successful_result: str, result_type: str = "example"):
        """Add successful results as new knowledge."""
        chunk_id = hashlib.md5(f"{query}_{successful_result}".encode()).hexdigest()[:12]
        
        chunk = KnowledgeChunk(
            id=f"experience_{chunk_id}",
            content=f"Query: {query}\n\nSuccessful Solution:\n{successful_result}",
            source="experience",
            chunk_type=result_type,
            keywords=self._extract_keywords(query + " " + successful_result)
        )
        
        self.rag_kb.add_knowledge(chunk)
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter common words and keep meaningful ones
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords = [w for w in words if len(w) > 2 and w not in stop_words]
        return list(set(keywords))


# Add math import that was missing
import math


def demo_rag_system():
    """Demonstrate the RAG system capabilities."""
    print("🧠 RAG Knowledge Base Demonstration")
    print("=" * 50)
    
    # Initialize RAG system
    rag_kb = RAGKnowledgeBase()
    
    # Test queries
    test_queries = [
        "How do I write unit tests in Python?",
        "What are Python best practices?",
        "Implement fibonacci function",
        "How to handle exceptions properly?",
        "Show me design patterns"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        print("-" * 30)
        
        relevant_chunks = rag_kb.retrieve_relevant(query, limit=2)
        
        for chunk, score in relevant_chunks:
            print(f"📊 Relevance: {score:.3f}")
            print(f"📝 Type: {chunk.chunk_type}")
            print(f"📖 Content: {chunk.content[:200]}...")
            print()
    
    # Demo enhanced prompt
    print("\n🚀 Enhanced Prompt Example")
    print("=" * 50)
    
    agent = RAGEnhancedAgent("demo-agent", "coder", rag_kb)
    original = "Create a function to validate user input"
    enhanced = agent.enhance_prompt(original)
    
    print("Original prompt:", original)
    print("\nEnhanced prompt preview:")
    print(enhanced[:500] + "...")


if __name__ == "__main__":
    demo_rag_system()