# Setup Guide

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI API (required for extraction)
OPENAI_API_KEY=your_openai_api_key_here

# Neo4j Database (required for knowledge graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password_here
```

### 3. Set Up Neo4j

You can use either:

**Option A: Neo4j Desktop**
- Download from https://neo4j.com/download/
- Create a new database
- Set password
- Start the database

**Option B: Neo4j AuraDB (Cloud)**
- Sign up at https://neo4j.com/cloud/aura/
- Create a free instance
- Copy connection URI and credentials

### 4. Verify Installation

Test that imports work:

```bash
python3 -c "from src import Agreement, ContractSearchServiceEnhanced; print('✓ Installation successful')"
```

## Usage

### Extract Contracts from PDFs

1. Place PDF contracts in `data/input/`
2. Run extraction:

```bash
python3 extract_contracts.py
```

Output:
- Structured JSON in `data/output/`
- Debug info in `data/debug/`

### Create Knowledge Graph

After extraction, create the Neo4j graph:

```bash
python3 create_knowledge_graph.py
```

This creates 18 node types and 30+ relationship types in Neo4j.

### Query the Graph

```python
from src.service import ContractSearchServiceEnhanced
import asyncio

async def main():
    service = ContractSearchServiceEnhanced()

    # Find contracts with high liability caps
    contracts = await service.get_contracts_by_liability_cap(
        min_amount=1_000_000
    )

    for contract in contracts:
        print(f"{contract['name']}: ${contract.get('liability_cap', {}).get('cap_amount', 0):,.0f}")

asyncio.run(main())
```

### Validate Against Client Standards

```python
from src.client_validator import ClientKGManagerEnhanced, ClientStandards
from neo4j import GraphDatabase
import os

# Initialize
manager = ClientKGManagerEnhanced()

# Define client standards
standards = ClientStandards(
    client_id="CLIENT_A",
    client_name="BigBank Corp",
    max_liability_cap=5_000_000,
    required_frameworks=["SOC2", "GDPR"],
    required_sla_uptime=99.9
)

manager.register_client(standards)

# Connect to Neo4j
driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USERNAME'), os.getenv('NEO4J_PASSWORD'))
)

# Validate a contract
validation = manager.validate_contract_for_client(
    "CLIENT_A",
    driver,
    contract_id=1
)

# Print report
print(manager.generate_validation_report(validation))

driver.close()
```

## Project Structure

```
graphrag-contract-intelligence/
├── data/
│   ├── input/          # PDF contracts (you add these)
│   ├── output/         # Extracted JSON (generated)
│   └── debug/          # Debug output (generated)
├── prompts/
│   ├── system_prompt.txt       # System instructions
│   └── extraction_prompt.txt   # Extraction template
├── src/
│   ├── __init__.py            # Package initialization
│   ├── schema.py              # Data structures (TypedDict)
│   ├── extract.py             # PDF extraction logic
│   ├── create_graph.py        # Neo4j graph creation
│   ├── service.py             # Query service
│   ├── client_validator.py    # Client validation
│   ├── langchain_tools.py     # LangChain tools
│   └── utils.py               # Utilities
├── extract_contracts.py       # Executable: Extract PDFs
├── create_knowledge_graph.py  # Executable: Create graph
├── requirements.txt           # Python dependencies
├── README.md                  # Main documentation
└── SETUP.md                   # This file

```

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError`, install dependencies:
```bash
pip install -r requirements.txt
```

### Neo4j Connection Errors

1. Verify Neo4j is running
2. Check `.env` credentials
3. Test connection:
```bash
python3 -c "from neo4j import GraphDatabase; driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password')); driver.verify_connectivity(); print('✓ Connected')"
```

### OpenAI API Errors

1. Verify API key in `.env`
2. Check quota: https://platform.openai.com/usage
3. Ensure you have access to GPT-4

## Next Steps

1. Extract a few sample contracts
2. Create the knowledge graph
3. Explore queries in Neo4j Browser
4. Set up client validation standards
5. Build custom queries for your use case

## Support

For issues or questions, check:
- README.md for detailed documentation
- Neo4j Browser at http://localhost:7474 for graph visualization
- OpenAI docs at https://platform.openai.com/docs
