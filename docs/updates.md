# updates.md

Date: 2026-01-22
Branch: `refactor/extreme-modularization-secure`

## Scope of this scan

This document summarizes an end-to-end structural scan of the repository (top-level layout + core agent execution path + CI config), and highlights breakages introduced by the executor refactor so they can be fixed before merging. 

## What changed (high level)

- Introduced a new executor package at `agent/core/executor/` containing `__init__.py`, `base.py`, `runner.py`, `sandbox.py`, `types.py`, and `tools.py`.
- Added a new orchestrator package at `agent/core/orchestrator/`.
- Added CI config: `.github/workflows/ci.yml`, `mypy.ini`, and `pyproject.toml`.
- Added initial unit test `tests/test_executor.py`.
- Kept patch artifacts in `patches/`.

## Current repo layout (top level)

Top-level items observed include `.github/`, `agent/`, `docs/`, `patches/`, test/config files (`pytest.ini`, `requirements*.txt`), and project docs (`README.md`, `REPORT.md`, etc.).

## Known breakages (must fix)

### 1) CLI orchestrator imports removed executor API

`agent/core/orchestrator.py` imports `execute` via `from .executor import execute`, but the monolithic `agent/core/executor.py` was removed during the refactor.

**Impact:** Running the CLI entrypoint that depends on `agent/core/orchestrator.py` will raise an import error until this import is redirected or a compatibility shim is added.

### 2) Executor package now contains mixed generations of code

The `agent/core/executor/` directory currently contains additional existing modules like `dispatch.py`, `formatters.py`, and `orchestrator.py` alongside the newly-added `runner.py/tools.py` stack.

**Impact:** These older modules may expect functions/types that were present in older versions of `executor/base.py` (e.g., sanitizers), and may break at import/runtime if their assumptions no longer hold.

## Recommended remediation plan (minimal churn)

1. **Restore CLI compatibility** (fastest path):
   - Option A: Update `agent/core/orchestrator.py` to import the correct execution entrypoint (wherever `execute()` lives now).
   - Option B: Add a compatibility `execute()` function into `agent/core/executor/__init__.py` that delegates to the new executor pipeline.

2. **Choose a single authoritative executor path**:
   - If `dispatch.py` is the “secure dispatcher” and already does validation/sanitization, make `runner.py` delegate to it.
   - Otherwise, migrate the validation logic into `sandbox.py` and retire `dispatch.py` (and any unused legacy modules).

3. **Unify tool schema typing**:
   - Either redefine `ToolSchema` to match the schema objects returned by `tools.get_tool_schemas()`, or change `get_tool_schemas()` to return `ToolSchema` objects.

## CI notes

The repository contains both `pytest.ini` and `pyproject.toml` pytest config sections; standardize to one location to avoid confusion.

## Next checks to run locally

- `python -m pytest -q`
- `mypy agent/`
- `python -m agent.core.orchestrator run "<task>" --apply` (after import fix)
