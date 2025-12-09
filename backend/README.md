**Backend Overview**

This backend folder contains a minimal, safe FastAPI backend and helper modules used by the local AI chatbot.

* **Active files**:
  * `app_simple.py`: Lightweight FastAPI app used for quick testing. Uses Ollama via HTTP to generate answers.
  * `llm_client.py`: LLM client helpers for calling Ollama or OpenAI (reads `.env`).
  * `file_extractor.py`: Utilities to extract text from local files (used by indexer when enabled).
  * `requirements.txt`: Minimal Python requirements for the simplified backend.

* **Archived / heavy files**:
  * `archive/`: Contains the original full-featured `app.py`, `indexer.py`, `search.py` and `requirements_full.txt` used for vector indexing and RAG. These are intentionally archived because those packages (sentence-transformers, chromadb, transformers, etc.) can cause local dependency/version conflicts.

Why archived: the full indexing stack requires tightly pinned ML dependencies which often conflict on local Windows setups. To keep the project runnable out-of-the-box, the heavy implementation is moved to `archive/`. Restore it only after creating a clean virtual environment and installing `backend/archive/requirements_full.txt`.

How to tidy the workspace:

* Use the provided cleanup script: `./scripts/cleanup_workspace.ps1` (dry run) or `./scripts/cleanup_workspace.ps1 -Execute` to move common heavy files into `backend/archive` and remove `__pycache__` directories.

How to restore the full backend:

1. Create a fresh Python virtual environment (recommended):
   * `python -m venv .venv` ; `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` ; `.\.venv\Scripts\Activate.ps1`
2. Install archived requirements: `pip install -r backend/archive/requirements_full.txt`
3. Replace `backend/app_simple.py` or run the original `backend/archive/app.py` after ensuring dependencies are satisfied.

If you want, I can help by:
* Running `./scripts/cleanup_workspace.ps1` (dry run) here to show what would change.
* Running it with `-Execute` to apply the tidy changes.
* Diagnosing `ollama pull` errors — show me the exact error or allow me to run `ollama list` / `ollama pull <model>` here and I will capture the output.
