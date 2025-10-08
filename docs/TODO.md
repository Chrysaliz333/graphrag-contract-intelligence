# Repository TODO

## Immediate Fixes
- [x] Update `src/service.py` to build parties defensively: guard against `None` entries from optional `INCORPORATED_IN` matches and surface whatever metadata is available instead of crashing.
- [x] Stop `src/create_graph.py` from assigning sequential `contract_id` values. Respect the ID supplied in the JSON (or derive a deterministic fallback from the filename/hash) and ensure imports use a stable identifier.
- [x] In `src/create_graph.py`, skip the embedding generation loop when `OPENAI_API_KEY` is not configured, and optionally log a hint so users know how to enable it.
- [x] Add length management to `src/extract.py` (chunking or early truncation with warnings) so very large PDFs do not overflow the OpenAI model context and silently fail.

## Follow-Up Enhancements
- [ ] Capture party role/incorporation metadata directly in the Cypher query (via relationship properties) so `_build_parties` can populate those fields accurately.
- [ ] Document the contract ID expectations in `README.md`/`QUICKSTART.md` so downstream tooling relies on the same identifier contract.
