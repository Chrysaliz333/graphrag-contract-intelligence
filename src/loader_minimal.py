"""
Minimal Neo4j loader for enhanced contract extraction output.

This utility focuses on the new Agreement/Clause/Variable structure produced by
the enhanced prompt. It guards optional fields carefully and only creates graph
elements when the source data provides non-null identifiers.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from neo4j import GraphDatabase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def to_neo_value(value: Any) -> Any:
    """Convert Python values into Neo4j-friendly scalars."""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        result: List[Any] = []
        for item in value:
            casted = to_neo_value(item)
            if casted is not None:
                result.append(casted)
        return result
    if isinstance(value, dict):
        # Nested maps are converted to JSON strings for simplicity.
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(value, ensure_ascii=False)


def coalesce_agreement_id(doc: Dict[str, Any], fallback: str) -> Optional[str]:
    """Build a non-null agreement id using the recommended precedence."""
    agreement = doc.get("agreement") or {}
    return (
        agreement.get("agreement_name")
        or agreement.get("agreement_id")
        or doc.get("contract_id")
        or doc.get("file_name")
        or fallback
    )


def normalize_clause_id(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return str(int(raw)) if isinstance(raw, int) or raw.is_integer() else str(raw)
    return str(raw)


def iter_json_files(folder: Path) -> Iterable[Path]:
    for path in sorted(folder.glob("*.json")):
        if path.is_file():
            yield path
def adapt_legacy(doc: dict) -> dict:
    ag = doc.get("agreement") or {}
    bai = ag.get("basic_agreement_information") or {}

    # Promote basics
    # names consistent with your enhanced schema
    if "agreement_name" not in ag and "agreement_name" in bai:
        ag["agreement_name"] = bai["agreement_name"]
    if "agreement_type" not in ag and "contract_type" in bai:
        ag["agreement_type"] = bai["contract_type"]
    if "agreement_date" not in ag and "agreement_date" in bai:
        ag["agreement_date"] = bai["agreement_date"]
    if "effective_date" not in ag and "effective_date" in bai:
        ag["effective_date"] = bai["effective_date"]
    if "expiration_date" not in ag and "expiration_date" in bai:
        ag["expiration_date"] = bai["expiration_date"]
    if "renewal_term" not in ag and "renewal_term" in bai:
        ag["renewal_term"] = bai["renewal_term"]
    if "notice_period_to_terminate_renewal" not in ag and "notice_period_to_terminate_renewal" in bai:
        ag["notice_period_to_terminate_renewal"] = bai["notice_period_to_terminate_renewal"]
    if "auto_renewal" not in ag and "auto_renew" in bai:
        ag["auto_renewal"] = bai["auto_renew"]
    if "total_contract_value" not in ag and "total_contract_value" in bai:
        ag["total_contract_value"] = bai["total_contract_value"]

    # Governing law & disputes
    gladr = ag.get("governing_law_and_dispute_resolution") or {}
    if gladr:
        ag.setdefault("governing_law", {
            "country": gladr.get("governing_country"),
            "state": gladr.get("governing_state"),
            "most_favored_country": gladr.get("most_favored_country"),
        })
        ag.setdefault("dispute_resolution", {
            "method": (gladr.get("dispute_resolution_method") or "").lower() or None,
            "venue": gladr.get("venue"),
            "jurisdiction": gladr.get("jurisdiction"),
            "governing_rules": gladr.get("rules") or gladr.get("rules_governing_dispute_resolution")
        })

    # Finalize
    ag.pop("basic_agreement_information", None)
    ag.pop("governing_law_and_dispute_resolution", None)
    doc["agreement"] = ag
    if "clauses" not in doc:
        doc["clauses"] = []
    return doc


# ---------------------------------------------------------------------------
# Neo4j ingestion routines
# ---------------------------------------------------------------------------

def upsert_agreement(tx, agreement_id: str, doc: Dict[str, Any]) -> None:
    agreement = doc.get("agreement") or {}
    params = {
        "agreement_id": agreement_id,
        "name": agreement.get("agreement_name") or agreement_id,
        "agreement_type": agreement.get("agreement_type"),
        "effective_date": agreement.get("effective_date"),
        "expiration_date": agreement.get("expiration_date"),
        "agreement_date": agreement.get("agreement_date"),
        "auto_renewal": agreement.get("auto_renewal"),
        "renewal_term": agreement.get("renewal_term"),
        "notice_period": agreement.get("notice_period_to_terminate_renewal"),
        "total_contract_value": to_neo_value(
            (agreement.get("total_contract_value") or {}).get("amount")
        ),
        "contract_currency": (agreement.get("total_contract_value") or {}).get("currency"),
    }

    tx.run(
        """
        MERGE (a:Agreement {agreement_id: $agreement_id})
        SET  a.name = $name,
             a.type = $agreement_type,
             a.effective_date = $effective_date,
             a.expiration_date = $expiration_date,
             a.agreement_date = $agreement_date,
             a.auto_renewal = $auto_renewal,
             a.renewal_term = $renewal_term,
             a.notice_period_to_terminate_renewal = $notice_period,
             a.total_contract_value = $total_contract_value,
             a.contract_currency = $contract_currency
        """,
        params,
    )

    governing = agreement.get("governing_law") or {}
    country = governing.get("country")
    if country:
        tx.run(
            """
            MATCH (a:Agreement {agreement_id:$agreement_id})
            MERGE (c:Country {name:$country})
            MERGE (a)-[r:GOVERNED_BY]->(c)
            SET r.state = $state
            """,
            {
                "agreement_id": agreement_id,
                "country": country,
                "state": governing.get("state"),
            },
        )

    parties = agreement.get("parties") or []
    for party in parties:
        name = party.get("name")
        if not name:
            continue
        tx.run(
            """
            MATCH (a:Agreement {agreement_id:$agreement_id})
            MERGE (p:Organization {name:$name})
            MERGE (p)-[r:IS_PARTY_TO]->(a)
            SET r.role = $role,
                r.incorporation_country = $country,
                r.incorporation_state = $state
            """,
            {
                "agreement_id": agreement_id,
                "name": name,
                "role": party.get("role"),
                "country": party.get("incorporation_country"),
                "state": party.get("incorporation_state"),
            },
        )


def upsert_clause(tx, agreement_id: str, clause: Dict[str, Any], idx: int) -> Optional[str]:
    clause_id = normalize_clause_id(clause.get("clause_id") or idx)
    if clause_id is None:
        return None

    clause_key = f"{agreement_id}:::{clause_id}"
    drafts = clause.get("drafts") or {}

    params = {
        "agreement_id": agreement_id,
        "clause_id": clause_id,
        "clause_key": clause_key,
        "title": clause.get("title"),
        "right_holder": clause.get("right_holder"),
        "obligor": clause.get("obligor"),
        "dependencies": [dep for dep in (clause.get("dependencies") or []) if dep],
        "excerpts": [ext for ext in (clause.get("excerpts") or []) if ext],
        "source_document_id": (clause.get("provenance") or {}).get("source_document_id"),
        "page_refs": to_neo_value((clause.get("provenance") or {}).get("page_refs")),
        "confidence_overall": clause.get("confidence_overall"),
        "defaults_applied": [item for item in (clause.get("defaults_applied") or []) if item],
        "external_inference_used": clause.get("external_inference_used"),
        "draft_p0_full": drafts.get("p0_full"),
        "draft_p50_full": drafts.get("p50_full"),
        "draft_p100_full": drafts.get("p100_full"),
        "draft_p25_delta": to_neo_value(drafts.get("p25_delta")),
        "draft_p75_delta": to_neo_value(drafts.get("p75_delta")),
        "clause_order": idx,
    }

    tx.run(
        """
        MATCH (a:Agreement {agreement_id:$agreement_id})
        MERGE (c:Clause {agreement_id:$agreement_id, clause_id:$clause_id})
        SET  c.title = $title,
             c.right_holder = $right_holder,
             c.obligor = $obligor,
             c.dependencies = $dependencies,
             c.excerpts = $excerpts,
             c.source_document_id = $source_document_id,
             c.page_refs = $page_refs,
             c.confidence_overall = $confidence_overall,
             c.defaults_applied = $defaults_applied,
             c.external_inference_used = $external_inference_used,
             c.draft_p0_full = $draft_p0_full,
             c.draft_p50_full = $draft_p50_full,
             c.draft_p100_full = $draft_p100_full,
             c.draft_p25_delta = $draft_p25_delta,
             c.draft_p75_delta = $draft_p75_delta,
             c.clause_order = $clause_order
        MERGE (a)-[:HAS_CLAUSE]->(c)
        """,
        params,
    )

    for excerpt in params["excerpts"]:
        tx.run(
            """
            MATCH (c:Clause {agreement_id:$agreement_id, clause_id:$clause_id})
            MERGE (e:Excerpt {text:$text})
            MERGE (c)-[:HAS_EXCERPT]->(e)
            """,
            {"agreement_id": agreement_id, "clause_id": clause_id, "text": excerpt},
        )

    return clause_key


def upsert_variable(tx, clause_key: str, agreement_id: str, clause_id: str, variable: Dict[str, Any]) -> None:
    name = variable.get("name")
    if not name:
        return

    params = {
        "clause_key": clause_key,
        "agreement_id": agreement_id,
        "clause_id": clause_id,
        "name": name,
        "value": to_neo_value(variable.get("value")),
        "type": variable.get("type"),
        "unit": variable.get("unit"),
        "evidence": variable.get("evidence"),
        "confidence": variable.get("confidence"),
        "defaults_applied": to_neo_value(variable.get("defaults_applied")),
    }

    tx.run(
        """
        MATCH (c:Clause {agreement_id:$agreement_id, clause_id:$clause_id})
        MERGE (v:Variable {clause_key:$clause_key, name:$name})
        SET  v.value = $value,
             v.type = $type,
             v.unit = $unit,
             v.evidence = $evidence,
             v.confidence = $confidence,
             v.defaults_applied = $defaults_applied
        MERGE (c)-[:HAS_VARIABLE]->(v)
        """,
        params,
    )

    if params["type"] == "enum" and params["value"] not in (None, ""):
        tx.run(
            """
            MATCH (v:Variable {clause_key:$clause_key, name:$name})
            MERGE (ev:EnumValue {name:$enum_name})
            MERGE (v)-[:HAS_VALUE]->(ev)
            """,
            {
                "clause_key": clause_key,
                "name": name,
                "enum_name": params["value"],
            },
        )
    )


def load_document(tx, doc: Dict[str, Any], filename: str) -> Optional[str]:
    doc = dict(doc)  # shallow copy
    doc.setdefault("file_name", filename)

    agreement_id = coalesce_agreement_id(doc, filename)
    if not agreement_id:
        return None

    upsert_agreement(tx, agreement_id, doc)

    clauses = doc.get("clauses") or []
    for idx, clause in enumerate(clauses, start=1):
        clause_key = upsert_clause(tx, agreement_id, clause, idx)
        if not clause_key:
            continue
        clause_id = clause.get("clause_id") or idx
        for variable in clause.get("variables") or []:
            upsert_variable(tx, clause_key, agreement_id, normalize_clause_id(clause_id) or str(idx), variable)

    return agreement_id


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Minimal loader for enhanced extraction JSON.")
    parser.add_argument("--input", type=Path, default=Path("data/output"), help="Folder containing JSON documents.")
    parser.add_argument("--uri", dest="uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    parser.add_argument("--user", dest="user", default=os.getenv("NEO4J_USER") or os.getenv("NEO4J_USERNAME", "neo4j"))
    parser.add_argument("--password", dest="password", default=os.getenv("NEO4J_PASSWORD"))
    parser.add_argument("--database", dest="database", default=os.getenv("NEO4J_DATABASE", "neo4j"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_folder: Path = args.input

    if not input_folder.exists():
        print(f"Input directory not found: {input_folder}")
        return

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))

    ingested = 0
    skipped = 0

    with driver.session(database=args.database) as session:
        for json_path in iter_json_files(input_folder):
            try:
                doc = json.loads(json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                print(f"✗ Failed to parse {json_path.name}: {exc}")
                skipped += 1
                continue

            agreement_id = session.execute_write(load_document, doc, json_path.name)
            if agreement_id:
                print(f"✓ Loaded {json_path.name} as agreement_id={agreement_id}")
                ingested += 1
            else:
                print(f"⚠ Skipped {json_path.name}: missing agreement identifier")
                skipped += 1

    driver.close()
    print("\n=== Loader summary ===")
    print(f"Ingested: {ingested}")
    print(f"Skipped : {skipped}")


if __name__ == "__main__":
    main()
