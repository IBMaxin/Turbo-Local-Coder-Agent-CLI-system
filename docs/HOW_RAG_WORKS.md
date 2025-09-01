# How the RAG System Gets Knowledge

## 🧠 Knowledge Acquisition Methods

Your RAG system gets knowledge through **4 different channels**:

### 1. 🏗️ **Built-in Knowledge (Pre-loaded)**
The system comes with curated programming knowledge:

```python
# Located in: agent_team/rag_system.py -> _load_builtin_knowledge()
builtin_knowledge = [
    "Python best practices (PEP 8, docstrings, type hints)",
    "Common design patterns (Singleton, Factory, Decorator)", 
    "Error handling strategies (try/except, custom exceptions)",
    "Testing patterns (unittest, pytest, fixtures)",
    "Common algorithms (binary search, fibonacci, etc.)"
]
```

**How it's loaded:**
- Automatically when `RAGKnowledgeBase()` is first initialized
- Stored in SQLite database (`rag_knowledge.db`)
- Only loads if database is empty (first run)

### 2. 📚 **Manual Knowledge Addition**
You can add your own successful patterns:

```python
from agent_team.rag_system import RAGKnowledgeBase, KnowledgeChunk

rag_kb = RAGKnowledgeBase()

# Add your successful code pattern
custom_pattern = KnowledgeChunk(
    id="my_api_pattern",
    content="Your successful API implementation...",
    source="my_project", 
    chunk_type="pattern",
    keywords=["api", "client", "authentication", "error", "handling"]
)

rag_kb.add_knowledge(custom_pattern)
```

### 3. 🤖 **Automatic Learning from Success**
Agents automatically learn from successful implementations:

```python
# In enhanced_agents.py -> RAGCoderAgent.process_task()
if generated_files:
    self.add_experience(
        query=task.description,
        successful_result=str(list(generated_files.values())),
        result_type="code_example"
    )
```

**When this happens:**
- Every time `RAGCoderAgent` successfully generates code
- Captures the original query + successful code output
- Stores as new knowledge chunk for future reference

### 4. 📁 **Codebase Analysis (Future Enhancement)**
*You could add this capability:*

```python
def learn_from_codebase(directory_path):
    """Analyze existing codebase and extract patterns."""
    rag_kb = RAGKnowledgeBase()
    
    for python_file in find_python_files(directory_path):
        if is_high_quality_code(python_file):
            pattern = extract_pattern(python_file)
            rag_kb.add_knowledge(pattern)
```

## 🔍 Knowledge Retrieval Process

### Step 1: Query Analysis
```python
def retrieve_relevant(self, query: str, chunk_types=None, limit=5):
    # Query: "create API client with error handling"
    # Extracts keywords: ["create", "api", "client", "error", "handling"]
```

### Step 2: TF-IDF Scoring  
```python
def get_similarity(self, query, doc_scores):
    # Compares query keywords against stored knowledge
    # Returns relevance score (higher = more relevant)
```

### Step 3: Context Assembly
```python
def get_context_for_query(self, query, max_tokens=2000):
    # Builds context string with most relevant knowledge
    # Stays within token limits for the smaller model
```

### Step 4: Prompt Enhancement
```python
enhanced_prompt = f"""
=== RELEVANT KNOWLEDGE ===
{context}

ORIGINAL REQUEST:
{original_prompt}

Please use the relevant knowledge above...
"""
```

## 📊 Knowledge Base Structure

**SQLite Database Schema:**
```sql
CREATE TABLE knowledge_chunks (
    id TEXT PRIMARY KEY,           -- Unique identifier
    content TEXT NOT NULL,         -- The actual knowledge
    source TEXT NOT NULL,          -- Where it came from (builtin, experience, custom)
    chunk_type TEXT NOT NULL,      -- code, documentation, pattern, example
    keywords TEXT NOT NULL,        -- JSON array of keywords
    tf_idf_scores TEXT NOT NULL,   -- JSON of TF-IDF scores for retrieval
    created_at REAL NOT NULL       -- Timestamp
)
```

**Knowledge Types:**
- `documentation`: Best practices, guidelines
- `pattern`: Design patterns, architectural approaches  
- `code`: Working code examples
- `example`: Successful implementations from experience

## 🎯 Why This Makes Small Models Smarter

### Before RAG:
```
User: "Create API client"
qwen2.5-coder: *generates basic code with potential issues*
```

### After RAG:
```
User: "Create API client"  
RAG System: *finds relevant knowledge*
Enhanced Prompt: "Create API client + [best practices + error handling + authentication patterns]"
qwen2.5-coder: *generates high-quality code following best practices*
```

## 🔄 Continuous Improvement Loop

1. **User Request** → RAG enhances with relevant knowledge
2. **Code Generation** → Higher quality due to context
3. **Success Capture** → Good results stored as new knowledge  
4. **Future Requests** → Even better due to learned patterns

This creates a **positive feedback loop** where the system gets progressively better at your specific coding patterns and domain.

## 🎛️ Tuning the RAG System

### Adjust Retrieval Sensitivity:
```python
# More strict (only highly relevant knowledge)
relevant = rag_kb.retrieve_relevant(query, limit=2)

# More permissive (include more context)  
relevant = rag_kb.retrieve_relevant(query, limit=5)
```

### Control Context Size:
```python
# For simple tasks (save tokens)
context = rag_kb.get_context_for_query(query, max_tokens=500)

# For complex tasks (more context)
context = rag_kb.get_context_for_query(query, max_tokens=3000)
```

### Filter Knowledge Types:
```python
# Only get coding examples
relevant = rag_kb.retrieve_relevant(query, chunk_types=["code", "example"])

# Only get best practices
relevant = rag_kb.retrieve_relevant(query, chunk_types=["documentation"])
```

## 🚀 Real Impact

**Quality Improvements Observed:**
- ✅ Better error handling (learns from error-handling patterns)
- ✅ Consistent code style (follows best practices)
- ✅ Proper documentation (includes docstrings)  
- ✅ Appropriate patterns (applies design patterns when relevant)
- ✅ Domain expertise (learns your specific coding patterns over time)

The RAG system effectively gives your small local model access to the "memory" and "experience" that larger models have built into their parameters, but in a way that's:
- **Controllable** (you can see and modify the knowledge)
- **Updatable** (learns from your successes)
- **Efficient** (only relevant knowledge is retrieved)
- **Private** (all knowledge stays local)