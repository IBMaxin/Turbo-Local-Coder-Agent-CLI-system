"""
Tests for RAG System
"""
import pytest
import os
import tempfile
import sqlite3
from agent.team.rag_system import RAGKnowledgeBase, KnowledgeChunk


class TestRAGKnowledgeBase:
    """Tests for RAGKnowledgeBase class."""
    
    def test_initialization(self):
        """Test that RAGKnowledgeBase initializes correctly."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            rag_kb = RAGKnowledgeBase(db_path)
            assert rag_kb is not None
            
            # Check that built-in knowledge was loaded
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM knowledge_chunks")
                count = cursor.fetchone()[0]
                assert count > 0
                
        finally:
            os.unlink(db_path)
    
    def test_retrieve_relevant(self):
        """Test that relevant knowledge is retrieved for a query."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            rag_kb = RAGKnowledgeBase(db_path)
            
            # Test retrieval for Python best practices
            results = rag_kb.retrieve_relevant("Python best practices")
            assert len(results) > 0
            assert any("best practices" in chunk.content.lower() for chunk, score in results)
            
            # Test retrieval for testing
            results = rag_kb.retrieve_relevant("How to write unit tests in Python")
            assert len(results) > 0
            assert any("testing" in chunk.content.lower() for chunk, score in results)
            
            # Test retrieval for algorithms
            results = rag_kb.retrieve_relevant("Implement fibonacci function")
            assert len(results) > 0
            assert any("fibonacci" in chunk.content.lower() for chunk, score in results)
            
        finally:
            os.unlink(db_path)
    
    def test_add_knowledge(self):
        """Test that adding knowledge works."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            rag_kb = RAGKnowledgeBase(db_path)
            
            # Add new knowledge
            new_chunk = KnowledgeChunk(
                id="test-chunk",
                content="This is a test knowledge chunk about Python dictionaries.",
                source="test",
                chunk_type="code",
                keywords=["python", "dictionary", "test"]
            )
            
            rag_kb.add_knowledge(new_chunk)
            
            # Verify it was added
            results = rag_kb.retrieve_relevant("Python dictionary")
            assert len(results) > 0
            assert any("test knowledge chunk" in chunk.content for chunk, score in results)
            
        finally:
            os.unlink(db_path)
    
    def test_get_context_for_query(self):
        """Test that context is provided for queries."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            rag_kb = RAGKnowledgeBase(db_path)
            
            # Test getting context for testing query
            context = rag_kb.get_context_for_query("How do I test Python code?")
            assert "=== RELEVANT KNOWLEDGE ===" in context
            assert "=== END KNOWLEDGE ===" in context
            assert len(context) > 100
            
        finally:
            os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
