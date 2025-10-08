# GraphRAG Contract Intelligence

Comprehensive contract extraction and analysis system using GraphRAG.

## Overview

This system extracts structured data from PDF contracts and creates a Neo4j knowledge graph for advanced querying and validation.

### Enhanced Extraction Features

- **60+ data points** extracted per contract (vs 15 in basic systems)
- **Liability caps** with amounts, types, carve-outs, calculation basis
- **Obligations** with SLAs, deliverables, deadlines, penalties
- **Compliance frameworks** (GDPR, SOC2, HIPAA, ISO27001, etc.)
- **Intellectual property** provisions (licenses, ownership, restrictions)
- **Insurance requirements** with coverage amounts and types
- **Data protection** provisions and breach notification periods
- **Termination clauses** with notice periods and fees
- **Payment terms** with schedules, late fees, invoicing details

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file:

```bash
# OpenAI API (required for extraction)
OPENAI_API_KEY=your_openai_api_key

# Neo4j Database (required for knowledge graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

### 3. Extract Contracts

Place PDF contracts in `data/input/` and run:

```bash
python extract_contracts.py
```

This extracts structured JSON to `data/output/` with debug info in `data/debug/`.

### 4. Create Knowledge Graph

```bash
python create_knowledge_graph.py
```

This creates a Neo4j graph with 18 node types and 30+ relationship types.

## Architecture

### Pipeline Stages

1. **PDF Extraction** (`src/extract.py`) - Extracts structured data using OpenAI Assistant API
2. **Knowledge Graph Creation** (`src/create_graph.py`) - Creates Neo4j graph from JSON
3. **Query Service** (`src/service.py`) - Advanced querying with semantic search
4. **Client Validation** (`src/client_validator.py`) - Multi-tenant validation against standards

### Schema

**18 Node Types:**
- Agreement, LiabilityCap, Obligation, ComplianceFramework
- IntellectualProperty, InsuranceRequirement, DataProtection
- Termination, PaymentTerms, Warranty, Indemnification
- ThirdPartyBeneficiaries, Amendment, Counterparts
- Dispute Resolution, Confidentiality, ForcemajeureTerm, Renewal

**30+ Relationship Types:**
- HAS_LIABILITY_CAP, HAS_OBLIGATION, COMPLIES_WITH
- HAS_IP_PROVISION, HAS_INSURANCE_REQUIREMENT
- And many more connecting agreements to provisions

## Usage Examples

### Query Contracts by Liability Cap

```python
from src.service import ContractSearchServiceEnhanced

service = ContractSearchServiceEnhanced()

# Find contracts with liability caps over $1M
contracts = await service.get_contracts_by_liability_cap(min_amount=1_000_000)
```

### Validate Against Client Standards

```python
from src.client_validator import ClientKGManagerEnhanced, ClientStandards

manager = ClientKGManagerEnhanced()

# Define client standards
standards = ClientStandards(
    client_id="CLIENT_A",
    client_name="BigBank Corp",
    max_liability_cap=5_000_000,
    required_frameworks=["SOC2", "PCI-DSS"],
    required_sla_uptime=99.9,
    min_cyber_liability=10_000_000
)

manager.register_client(standards)

# Validate a contract
validation = manager.validate_contract_for_client(
    "CLIENT_A",
    neo4j_driver,
    contract_id=1
)
```

### Search with LangChain

```python
from src.langchain_tools import (
    get_liability_cap_summary,
    search_contracts_by_compliance_framework
)

# Get liability cap summary
summary = get_liability_cap_summary()

# Find GDPR-compliant contracts
gdpr_contracts = search_contracts_by_compliance_framework("GDPR")
```

## Project Structure

```
graphrag-contract-intelligence/
├── data/
│   ├── input/          # PDF contracts
│   ├── output/         # Extracted JSON
│   └── debug/          # Debug output
├── prompts/
│   ├── system_prompt.txt
│   └── extraction_prompt.txt
├── src/
│   ├── __init__.py
│   ├── schema.py       # TypedDict data structures
│   ├── extract.py      # PDF extraction
│   ├── create_graph.py # Neo4j graph creation
│   ├── service.py      # Query service
│   ├── client_validator.py  # Client validation
│   ├── langchain_tools.py   # LangChain tools
│   └── utils.py        # Utilities
├── extract_contracts.py       # Extraction script
├── create_knowledge_graph.py  # Graph creation script
├── requirements.txt
└── README.md
```

## Advanced Features

### Client Validation

Validate contracts against client-specific standards:
- Liability cap limits
- Required compliance frameworks
- SLA requirements
- Insurance minimums
- IP ownership policies
- Data protection requirements

### Semantic Search

Search contract excerpts using vector embeddings:
```python
results = await service.search_excerpts_by_query(
    "data breach notification requirements"
)
```

### Multi-Tenant Support

Manage multiple clients with different standards in a single knowledge graph.

## Data Output

Each contract produces JSON with:
- **Agreement metadata**: parties, effective dates, governing law
- **Liability caps**: amounts, types, carve-outs, excerpts
- **Obligations**: deliverables, SLAs, penalties, deadlines
- **Compliance**: frameworks, certifications, audit rights
- **IP provisions**: licenses, ownership, sublicensing
- **Insurance**: coverage types and amounts
- **Data protection**: GDPR compliance, breach notification
- **Full text excerpts** for every provision

## Requirements

- Python 3.9+
- OpenAI API key (for GPT-4 extraction)
- Neo4j database (local or cloud)
- See `requirements.txt` for Python packages

## License

Proprietary - All rights reserved
