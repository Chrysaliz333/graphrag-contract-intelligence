# Repository Guidelines

## Project Structure & Module Organization
- Core Python modules live in `src/`, grouped by pipeline stage: extraction (`extract.py`), graph creation (`create_graph.py`), querying (`service.py`), validation (`client_validator.py`), and shared utilities (`utils.py`, `schema.py`).
- Entry-point scripts (`extract_contracts.py`, `create_knowledge_graph.py`) sit at the repo root for quick CLI execution.
- Input/output artifacts are kept in `data/` (`input/`, `output/`, `debug/`), while prompt templates reside in `prompts/`. Long-form references and setup docs are under `docs/`, `SETUP.md`, and `QUICKSTART.md`.

## Build, Test, and Development Commands
- Install runtime dependencies: `pip install -r requirements.txt`.
- Run contract extraction against PDFs in `data/input/`: `python extract_contracts.py`. Outputs land in `data/output/` with diagnostics in `data/debug/`.
- Populate Neo4j with extracted contracts: `python create_knowledge_graph.py`. Ensure the Neo4j instance and `.env` credentials are reachable first.
- For ad-hoc validation or notebooks, load helpers directly from `src/` (e.g., `python -m src.create_graph --help` once a CLI wrapper is added).

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and descriptive, snake_case function and variable names. Classes use PascalCase (`ContractSearchServiceEnhanced`).
- Maintain type hints as seen in `src/service.py` and keep docstrings factual and single-purpose.
- Prefer f-strings for formatting, avoid implicit relative imports, and group imports by standard library, third-party, project.

## Testing Guidelines
- Place automated tests under `tests/`, mirroring `src/` structure (e.g., `tests/test_extract.py`).
- Use `pytest` for new tests; document any optional dependencies in the PR and add them to a dev-requirements file if created.
- Target contract fixtures or stubbed Neo4j clients for deterministic behavior. Include integration smoke tests when touching pipeline scripts.

## Commit & Pull Request Guidelines
- Write imperative, scope-focused commit messages (e.g., `Add liability cap aggregation query`). Squash noisy WIP commits before pushing.
- Each PR should include: summary of changes, test evidence (`pytest`, manual run logs), required environment notes, and links to related issues.
- Provide before/after data samples or screenshots when adjusting extraction prompts or graph schemas to aid reviewer context.

## Environment & Security Notes
- Keep `.env` out of version control; provide `.env.example` updates if new variables are required.
- Do not commit real contracts or client-sensitive data. Use sanitized PDFs in `data/input/` and redact any logs placed in `data/debug/`.
