# Quick Start Guide

## 5-Minute Setup

### 1. Install Dependencies (1 min)

```bash
cd /Users/liz/graphrag-contract-intelligence
pip install -r requirements.txt
```

### 2. Configure Environment (1 min)

Create `.env` file:

```bash
cat > .env << 'EOF'
OPENAI_API_KEY=sk-your-key-here
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password-here
EOF
```

### 3. Extract Contracts (2 min)

You already have 73 PDF contracts in `data/input/`!

```bash
python3 extract_contracts.py
```

This will:
- Process all PDFs in `data/input/`
- Extract 60+ data points per contract
- Save JSON to `data/output/`
- Save debug info to `data/debug/`
- Emit a stable `contract_id` for every agreement (sourced from the JSON payload or the PDF filename)

> ℹ️  Large documents: the extractor enforces a character budget (~120k by default) to stay within the model's context window. Set `EXTRACT_MAX_CHARS` in your `.env` if you need to tune the limit.

### 4. Create Knowledge Graph (1 min)

```bash
python3 create_knowledge_graph.py
```

This creates a Neo4j graph with:
- 18 node types
- 30+ relationship types
- Full semantic search capability

## What You Get

### Enhanced Extraction

Each contract produces JSON with:

```json
{
  "agreement": {
    "name": "Service Agreement",
    "parties": ["Company A", "Company B"],
    "effective_date": "2024-01-01",
    "liability_cap": {
      "exists": true,
      "cap_amount": 5000000,
      "currency": "USD",
      "cap_type": "aggregate",
      "carve_outs": ["gross negligence", "fraud"],
      "excerpts": ["Full text from contract..."]
    },
    "obligations": [
      {
        "obligation_type": "Service Level Agreement",
        "performance_standards": "99.9% uptime",
        "consequences_of_breach": "10% monthly fee credit",
        "deliverables": ["Monthly reports", "24/7 support"]
      }
    ],
    "compliance_frameworks": [
      {
        "framework_name": "SOC2",
        "certification_required": true,
        "audit_rights": true
      }
    ],
    "intellectual_property": [...],
    "insurance_requirements": [...],
    "data_protection": {...},
    "termination": {...},
    "payment_terms": {...}
  }
}
```

### Knowledge Graph Queries

After creating the graph, open Neo4j Browser at `http://localhost:7474` and try:

```cypher
// Find contracts with high liability caps
MATCH (a:Agreement)-[:HAS_LIABILITY_CAP]->(cap:LiabilityCap)
WHERE cap.cap_amount > 1000000
RETURN a.name, cap.cap_amount, cap.currency
ORDER BY cap.cap_amount DESC

// Find GDPR-compliant contracts
MATCH (a:Agreement)-[:COMPLIES_WITH]->(:ComplianceRequirement)
      -[:FRAMEWORK_TYPE]->(f:ComplianceFramework)
WHERE f.framework_name = "GDPR"
RETURN a.name, a.effective_date

// Find contracts with specific SLAs
MATCH (a:Agreement)-[:HAS_OBLIGATION]->(o:Obligation)
WHERE o.performance_standards CONTAINS "99.9%"
RETURN a.name, o.performance_standards, o.consequences_of_breach
```

### Python Queries

```python
from src.service import ContractSearchServiceEnhanced
import asyncio

async def main():
    service = ContractSearchServiceEnhanced()

    # Find contracts with liability caps over $1M
    contracts = await service.get_contracts_by_liability_cap(
        min_amount=1_000_000
    )

    for contract in contracts:
        cap = contract.get('liability_cap', {})
        print(f"{contract['name']}: ${cap.get('cap_amount', 0):,.0f}")

asyncio.run(main())
```

### Client Validation

```python
from src.client_validator import ClientKGManagerEnhanced, ClientStandards
from neo4j import GraphDatabase
import os

# Define standards
manager = ClientKGManagerEnhanced()
standards = ClientStandards(
    client_id="BIGBANK",
    client_name="BigBank Corp",
    max_liability_cap=5_000_000,
    required_frameworks=["SOC2", "PCI-DSS"],
    required_sla_uptime=99.9,
    min_cyber_liability=10_000_000
)
manager.register_client(standards)

# Validate contract
driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD'))
)

validation = manager.validate_contract_for_client(
    "BIGBANK",
    driver,
    contract_id=1
)

print(manager.generate_validation_report(validation))
driver.close()
```

## Current Status

✅ **73 PDF contracts** ready to process in `data/input/`
✅ **Clean output folders** ready for extraction
✅ **All dependencies** defined in requirements.txt
✅ **Complete documentation** in README.md and SETUP.md
✅ **Migration complete** - standalone project ready to use

## Next Steps

1. **Right now:** Run extraction on 73 contracts
2. **5 minutes:** Create knowledge graph in Neo4j
3. **10 minutes:** Explore queries in Neo4j Browser
4. **15 minutes:** Set up client validation standards
5. **30 minutes:** Build custom queries for your use case

## Comparison: Before vs After

### Before (Basic System)
- ❌ 15 data points per contract
- ❌ Binary yes/no detection only
- ❌ Incomplete excerpts
- ❌ No structured data
- ❌ Limited to 34 CUAD clause types
- ❌ No liability amounts, SLAs, or compliance details

### After (Enhanced System)
- ✅ 60+ data points per contract
- ✅ Complete structured extraction
- ✅ Full text excerpts with context
- ✅ Liability caps with amounts, types, carve-outs
- ✅ Obligations with SLAs, deliverables, penalties
- ✅ Compliance frameworks with certifications
- ✅ IP provisions, insurance, data protection
- ✅ Client validation against standards

## Files Overview

```
graphrag-contract-intelligence/
├── extract_contracts.py       # Run this first
├── create_knowledge_graph.py  # Run this second
├── requirements.txt           # Install dependencies
├── README.md                  # Full documentation
├── SETUP.md                   # Detailed setup guide
├── QUICKSTART.md             # This file
└── MIGRATION_SUMMARY.md      # Migration details
```

## Ready to Start?

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure .env (add your API keys)

# 3. Extract
python3 extract_contracts.py

# 4. Create graph
python3 create_knowledge_graph.py

# 5. Query!
```

That's it! You now have a production-ready contract intelligence system.
