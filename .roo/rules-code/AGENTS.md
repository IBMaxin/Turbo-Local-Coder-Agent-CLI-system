# Project Coding Rules (Non-Obvious Only)

- Shell commands restricted to whitelist: `python`, `pytest`, `pip`, `ls`, `cat`, `echo`, `mkdir`, `rm`, `touch`, `git` only
- Configuration validation collects all errors before failing (not fail-fast)
- Auto-complexity detection adjusts execution strategy (simple/medium/complex/enterprise)
- Enhanced execution with Super-RAG requires both `--apply` and `--enhanced` flags
- Settings use dataclass with `__post_init__` validation pattern
- Error handling uses custom ErrorContext and safe_execute patterns