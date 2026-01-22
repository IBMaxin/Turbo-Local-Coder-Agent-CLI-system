"""
Tests for Enhanced Agents
"""
import pytest
import os
import tempfile
from agent.team.rag_system import RAGEnhancedAgent, RAGKnowledgeBase


class TestRAGEnhancedAgent:
    """Tests for RAGEnhancedAgent class."""
    
    def test_initialization(self):
        """Test that RAGEnhancedAgent initializes correctly."""
        agent = RAGEnhancedAgent("Test Agent", "Test Role")
        assert agent is not None
        assert agent.name == "Test Agent"
        assert agent.role == "Test Role"
        assert isinstance(agent.rag_kb, RAGKnowledgeBase)
    
    def test_enhance_prompt(self):
        """Test that prompts are enhanced with relevant knowledge."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            agent = RAGEnhancedAgent("Test Agent", "Test Role", RAGKnowledgeBase(db_path))
            
            # Test enhancement for a testing query
            original_prompt = "How do I write unit tests in Python?"
            enhanced_prompt = agent.enhance_prompt(original_prompt)
            
            assert original_prompt in enhanced_prompt
            assert "=== RELEVANT KNOWLEDGE ===" in enhanced_prompt
            assert "=== END KNOWLEDGE ===" in enhanced_prompt
            
            # Check that relevant knowledge is included
            assert any(keyword in enhanced_prompt.lower() for keyword in ["test", "testing", "unittest", "pytest"])
            
        finally:
            os.unlink(db_path)
    
    def test_add_experience(self):
        """Test that experience can be added."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            agent = RAGEnhancedAgent("Test Agent", "Test Role", RAGKnowledgeBase(db_path))
            
            # Add some experience
            query = "How to read a file in Python?"
            successful_result = "To read a file in Python, use: with open('file.txt', 'r') as f: content = f.read()"
            
            agent.add_experience(query, successful_result)
            
            # Verify the experience was added
            results = agent.rag_kb.retrieve_relevant("How to read a file in Python?")
            assert len(results) > 0
            
        finally:
            os.unlink(db_path)
    
    def test_prompt_enhancement_with_different_query_types(self):
        """Test that different query types get appropriate context."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        try:
            agent = RAGEnhancedAgent("Test Agent", "Test Role", RAGKnowledgeBase(db_path))
            
            # Test for best practices query
            prompt1 = "What are Python best practices?"
            enhanced1 = agent.enhance_prompt(prompt1)
            assert "best practices" in enhanced1.lower()
            
            # Test for pattern/design query
            prompt2 = "Show me some Python design patterns"
            enhanced2 = agent.enhance_prompt(prompt2)
            assert any(pattern in enhanced2.lower() for pattern in ["singleton", "factory", "decorator"])
            
        finally:
            os.unlink(db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
