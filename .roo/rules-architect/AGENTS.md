# Project Architecture Rules (Non-Obvious Only)

- Two-phase execution requires architectural decisions consider both planning and execution phases
- Super-RAG knowledge system permanently learns from executions (forward-only architecture)
- Auto-complexity detection influences execution strategy (simple/medium/complex/enterprise)
- Sandboxed tools architecture restricts available operations for security
- Configuration validation uses comprehensive error collection pattern