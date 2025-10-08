"""
Enhanced LangChain Tools for Contract Analysis
Supports queries against enhanced schema including liability caps, obligations, compliance, etc.
"""

from langchain.tools import tool
from neo4j import GraphDatabase
from typing import List, Dict
import os
import sys
from pathlib import Path

# Import enhanced client validation system
try:
    legal_graph_path = Path("/Users/liz/Desktop/legal_graph_project")
    sys.path.insert(0, str(legal_graph_path))
    from legal_knowledge_graph import LegalKnowledgeGraph
    HAS_ONTOLOGY = True
except ImportError:
    HAS_ONTOLOGY = False
    LegalKnowledgeGraph = None

from .client_validator import ClientKGManagerEnhanced, ClientStandards

NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USERNAME', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'contractpass')

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Initialize enhanced client validation manager
master_ontology = LegalKnowledgeGraph() if HAS_ONTOLOGY else None
client_manager = ClientKGManagerEnhanced(master_ontology)

# Register sample clients with enhanced standards
client_manager.register_client(ClientStandards(
    client_id="BIGBANK",
    client_name="BigBank Corp",
    max_liability_cap=5_000_000,
    min_liability_cap=1_000_000,
    preferred_cap_type="aggregate",
    required_carve_outs=["gross negligence", "fraud", "IP infringement"],
    required_sla_uptime=99.9,
    ip_ownership_required=True,
    sublicensing_allowed=False,
    required_frameworks=["SOC2", "PCI-DSS"],
    certification_required=True,
    audit_rights_required=True,
    min_general_liability=2_000_000,
    min_cyber_liability=10_000_000,
    gdpr_required=False,
    termination_for_convenience_required=True
))

client_manager.register_client(ClientStandards(
    client_id="TECHSTARTUP",
    client_name="TechStartup Inc",
    max_liability_cap=None,
    shared_ip_allowed=True,
    sublicensing_allowed=True,
    required_frameworks=["GDPR"],
    gdpr_required=True,
    termination_for_convenience_required=False
))

client_manager.register_client(ClientStandards(
    client_id="MEDTECH",
    client_name="MedTech Solutions",
    max_liability_cap=10_000_000,
    min_liability_cap=2_000_000,
    ip_ownership_required=True,
    required_frameworks=["HIPAA", "FDA_CFR"],
    certification_required=True,
    audit_rights_required=True,
    min_professional_liability=5_000_000,
    gdpr_required=True,
    breach_notification_max_hours=24,
    termination_for_convenience_required=True
))


# ============================================================================
# ENHANCED SCHEMA TOOLS
# ============================================================================

@tool
def get_liability_cap_summary() -> str:
    """Get summary of liability caps across all contracts.
    Shows cap amounts, types, and common exceptions."""

    query = """
    MATCH (a:Agreement)-[:HAS_LIABILITY_CAP]->(cap:LiabilityCap)
    RETURN a.contract_id as contract_id,
           a.name as contract_name,
           cap.cap_amount as amount,
           cap.currency as currency,
           cap.cap_type as cap_type,
           cap.carve_outs as carve_outs
    ORDER BY cap.cap_amount DESC
    """

    records, _, _ = driver.execute_query(query)

    if not records:
        return "No liability caps found in contracts."

    result = f"Liability Cap Summary ({len(records)} contracts):\n\n"

    for record in records:
        result += f"Contract {record['contract_id']}: {record['contract_name']}\n"
        if record['amount']:
            result += f"  Cap: ${record['amount']:,.0f} {record['currency']} ({record['cap_type']})\n"
        else:
            result += f"  Cap: Unlimited ({record['cap_type']})\n"

        if record['carve_outs']:
            result += f"  Exceptions: {', '.join(record['carve_outs'])}\n"
        result += "\n"

    return result


@tool
def search_contracts_by_liability_cap(min_amount: float = None, max_amount: float = None) -> str:
    """Search for contracts within a specific liability cap range.

    Args:
        min_amount: Minimum liability cap amount (optional)
        max_amount: Maximum liability cap amount (optional)
    """

    where_clauses = []
    params = {}

    if min_amount is not None:
        where_clauses.append("cap.cap_amount >= $min_amount")
        params['min_amount'] = min_amount

    if max_amount is not None:
        where_clauses.append("cap.cap_amount <= $max_amount")
        params['max_amount'] = max_amount

    where_clause = " AND ".join(where_clauses) if where_clauses else "TRUE"

    query = f"""
    MATCH (a:Agreement)-[:HAS_LIABILITY_CAP]->(cap:LiabilityCap)
    WHERE {where_clause}
    RETURN a.contract_id as contract_id,
           a.name as contract_name,
           cap.cap_amount as amount,
           cap.cap_type as type
    ORDER BY cap.cap_amount DESC
    """

    records, _, _ = driver.execute_query(query, params)

    if not records:
        return "No contracts found matching the liability cap criteria."

    result = f"Found {len(records)} contracts:\n\n"
    for record in records:
        result += f"Contract {record['contract_id']}: {record['contract_name']}\n"
        result += f"  Liability Cap: ${record['amount']:,.0f} ({record['type']})\n\n"

    return result


@tool
def get_all_obligations(contract_id: int = None) -> str:
    """Get all obligations from contracts, optionally filtered by contract ID.

    Args:
        contract_id: Optional contract ID to filter by specific contract
    """

    if contract_id:
        query = """
        MATCH (a:Agreement {contract_id: $contract_id})-[:HAS_OBLIGATION]->(o:Obligation)
        RETURN a.name as contract_name,
               o.obligation_type as type,
               o.obligated_party as party,
               o.description as description,
               o.deadline as deadline,
               o.performance_standards as sla,
               o.consequences_of_breach as penalty
        """
        params = {'contract_id': contract_id}
    else:
        query = """
        MATCH (a:Agreement)-[:HAS_OBLIGATION]->(o:Obligation)
        RETURN a.contract_id as contract_id,
               a.name as contract_name,
               o.obligation_type as type,
               o.obligated_party as party,
               o.description as description,
               o.deadline as deadline
        ORDER BY a.contract_id
        LIMIT 20
        """
        params = {}

    records, _, _ = driver.execute_query(query, params)

    if not records:
        return "No obligations found."

    result = f"Obligations Found ({len(records)}):\n\n"

    for record in records:
        if contract_id:
            result += f"📋 {record['type']}\n"
            result += f"   Party: {record['party']}\n"
            result += f"   Description: {record['description']}\n"
            result += f"   Deadline: {record['deadline']}\n"
            if record.get('sla'):
                result += f"   SLA: {record['sla']}\n"
            if record.get('penalty'):
                result += f"   Breach Consequences: {record['penalty']}\n"
            result += "\n"
        else:
            result += f"Contract {record['contract_id']}: {record['contract_name']}\n"
            result += f"  {record['type']} - {record['party']} - Due: {record['deadline']}\n\n"

    return result


@tool
def search_by_compliance_framework(framework_name: str) -> str:
    """Search for contracts that comply with a specific framework (GDPR, SOC2, HIPAA, etc.).

    Args:
        framework_name: Name of compliance framework (e.g., 'GDPR', 'SOC2', 'HIPAA')
    """

    query = """
    MATCH (a:Agreement)-[:COMPLIES_WITH]->(c:ComplianceRequirement)
          -[:FRAMEWORK_TYPE]->(f:ComplianceFramework {framework_name: $framework_name})
    RETURN a.contract_id as contract_id,
           a.name as contract_name,
           c.certification_required as cert_required,
           c.audit_rights as audit_rights,
           c.audit_frequency as audit_frequency
    """

    records, _, _ = driver.execute_query(query, {'framework_name': framework_name})

    if not records:
        return f"No contracts found complying with {framework_name}."

    result = f"Contracts Complying with {framework_name} ({len(records)}):\n\n"

    for record in records:
        result += f"Contract {record['contract_id']}: {record['contract_name']}\n"
        result += f"  Certification Required: {'Yes' if record['cert_required'] else 'No'}\n"
        result += f"  Audit Rights: {'Yes' if record['audit_rights'] else 'No'}\n"
        if record['audit_frequency']:
            result += f"  Audit Frequency: {record['audit_frequency']}\n"
        result += "\n"

    return result


@tool
def find_non_compliant_contracts(framework_name: str) -> str:
    """Find contracts that do NOT comply with a specific framework.

    Args:
        framework_name: Name of compliance framework (e.g., 'GDPR', 'SOC2')
    """

    query = """
    MATCH (a:Agreement)
    WHERE NOT exists((a)-[:COMPLIES_WITH]->(:ComplianceRequirement)
                    -[:FRAMEWORK_TYPE]->(:ComplianceFramework {framework_name: $framework_name}))
    RETURN a.contract_id as contract_id,
           a.name as contract_name,
           a.agreement_type as type
    ORDER BY a.contract_id
    """

    records, _, _ = driver.execute_query(query, {'framework_name': framework_name})

    if not records:
        return f"All contracts comply with {framework_name}."

    result = f"Contracts NOT Complying with {framework_name} ({len(records)}):\n\n"

    for record in records:
        result += f"Contract {record['contract_id']}: {record['contract_name']} ({record['type']})\n"

    return result


@tool
def get_ip_provisions(contract_id: int = None) -> str:
    """Get intellectual property provisions from contracts.

    Args:
        contract_id: Optional contract ID to filter by specific contract
    """

    if contract_id:
        query = """
        MATCH (a:Agreement {contract_id: $contract_id})-[:HAS_IP_PROVISION]->(ip:IntellectualProperty)
        RETURN a.name as contract_name,
               ip.ip_type as type,
               ip.owner as owner,
               ip.subject_matter as subject,
               ip.license_type as license_type,
               ip.scope as scope,
               ip.territory as territory,
               ip.sublicensable as sublicensable
        """
        params = {'contract_id': contract_id}
    else:
        query = """
        MATCH (a:Agreement)-[:HAS_IP_PROVISION]->(ip:IntellectualProperty)
        RETURN a.contract_id as contract_id,
               a.name as contract_name,
               ip.ip_type as type,
               ip.owner as owner,
               ip.license_type as license_type
        ORDER BY a.contract_id
        LIMIT 20
        """
        params = {}

    records, _, _ = driver.execute_query(query, params)

    if not records:
        return "No IP provisions found."

    result = f"Intellectual Property Provisions ({len(records)}):\n\n"

    for record in records:
        if contract_id:
            result += f"Type: {record['type']}\n"
            result += f"  Owner: {record['owner']}\n"
            result += f"  Subject: {record['subject']}\n"
            if record.get('license_type'):
                result += f"  License: {record['license_type']}\n"
                result += f"  Scope: {record['scope']}\n"
                result += f"  Territory: {record['territory']}\n"
                result += f"  Sublicensable: {'Yes' if record['sublicensable'] else 'No'}\n"
            result += "\n"
        else:
            result += f"Contract {record['contract_id']}: {record['contract_name']}\n"
            result += f"  Type: {record['type']} - Owner: {record['owner']}\n\n"

    return result


@tool
def get_insurance_requirements(contract_id: int = None) -> str:
    """Get insurance requirements from contracts.

    Args:
        contract_id: Optional contract ID to filter by specific contract
    """

    if contract_id:
        query = """
        MATCH (a:Agreement {contract_id: $contract_id})-[:HAS_INSURANCE_REQUIREMENT]->(:InsuranceRequirement)
              -[:REQUIRES_INSURANCE_TYPE]->(it:InsuranceType)
        RETURN a.name as contract_name,
               it.insurance_type as type,
               it.minimum_coverage as coverage,
               it.currency as currency,
               it.additional_insured_required as additional_insured
        """
        params = {'contract_id': contract_id}
    else:
        query = """
        MATCH (a:Agreement)-[:HAS_INSURANCE_REQUIREMENT]->(:InsuranceRequirement)
              -[:REQUIRES_INSURANCE_TYPE]->(it:InsuranceType)
        RETURN a.contract_id as contract_id,
               a.name as contract_name,
               it.insurance_type as type,
               it.minimum_coverage as coverage
        ORDER BY a.contract_id
        LIMIT 20
        """
        params = {}

    records, _, _ = driver.execute_query(query, params)

    if not records:
        return "No insurance requirements found."

    result = f"Insurance Requirements ({len(records)}):\n\n"

    for record in records:
        if contract_id:
            result += f"{record['type']}\n"
            result += f"  Minimum Coverage: ${record['coverage']:,.0f} {record['currency']}\n"
            result += f"  Additional Insured: {'Required' if record['additional_insured'] else 'Not Required'}\n\n"
        else:
            result += f"Contract {record['contract_id']}: {record['contract_name']}\n"
            result += f"  {record['type']}: ${record['coverage']:,.0f}\n\n"

    return result


@tool
def get_termination_provisions(contract_id: int) -> str:
    """Get termination provisions for a specific contract.

    Args:
        contract_id: The contract ID number
    """

    query = """
    MATCH (a:Agreement {contract_id: $contract_id})-[:HAS_TERMINATION_PROVISIONS]->(t:Termination)
    RETURN a.name as contract_name,
           t.convenience_allowed as convenience_allowed,
           t.convenience_notice_period as notice_period,
           t.termination_fee as fee,
           t.cause_breach_types as breach_types,
           t.cause_cure_period as cure_period
    """

    records, _, _ = driver.execute_query(query, {'contract_id': contract_id})

    if not records:
        return f"No termination provisions found for contract {contract_id}."

    record = records[0]
    result = f"Termination Provisions for {record['contract_name']}:\n\n"

    result += "Termination for Convenience:\n"
    result += f"  Allowed: {'Yes' if record['convenience_allowed'] else 'No'}\n"
    if record['notice_period']:
        result += f"  Notice Period: {record['notice_period']}\n"
    if record['fee']:
        result += f"  Termination Fee: {record['fee']}\n"

    result += "\nTermination for Cause:\n"
    if record['breach_types']:
        result += f"  Breach Types: {', '.join(record['breach_types'])}\n"
    if record['cure_period']:
        result += f"  Cure Period: {record['cure_period']}\n"

    return result


# ============================================================================
# LEGACY COMPATIBILITY TOOLS
# ============================================================================

@tool
def get_all_agreements() -> str:
    """Get a list of all agreements/contracts in the database with their parties."""

    query = """
    MATCH (a:Agreement)
    OPTIONAL MATCH (p:Organization)-[r:IS_PARTY_TO]->(a)
    RETURN a.contract_id as contract_id,
           a.name as agreement_name,
           a.agreement_type as agreement_type,
           collect(p.name + ' (' + r.role + ')') as parties
    ORDER BY a.contract_id
    """

    records, _, _ = driver.execute_query(query)

    result = f"Found {len(records)} agreements in database:\n\n"
    for record in records:
        result += f"Contract {record['contract_id']}: {record['agreement_name']}\n"
        result += f"Type: {record['agreement_type']}\n"
        if record['parties'] and record['parties'][0]:
            result += f"Parties: {', '.join([p for p in record['parties'] if p != ' ()'])}\n"
        result += "\n"

    return result


# ============================================================================
# CLIENT VALIDATION TOOLS
# ============================================================================

@tool
def validate_contract_for_client(contract_id: int, client_id: str) -> str:
    """Validate a contract against client-specific standards using enhanced schema.

    Args:
        contract_id: The contract ID number to validate
        client_id: The client ID (BIGBANK, TECHSTARTUP, or MEDTECH)

    Returns detailed validation report with liability, obligation, compliance, IP, insurance checks.
    """

    try:
        report = client_manager.validate_contract_for_client(client_id, driver, contract_id)

        # Get contract name
        query = "MATCH (a:Agreement {contract_id: $contract_id}) RETURN a.name as name"
        records, _, _ = driver.execute_query(query, {'contract_id': contract_id})
        contract_name = records[0]['name'] if records else f"Contract {contract_id}"

        result = f"Enhanced Validation Report for {contract_name}\n"
        result += f"Client: {report['client_name']}\n"
        result += f"{'='*60}\n\n"

        # Overall status
        if report['compliant']:
            result += "✅ OVERALL STATUS: COMPLIANT\n\n"
        else:
            result += "❌ OVERALL STATUS: NOT COMPLIANT\n\n"

        # Critical issues
        if report['critical_issues']:
            result += f"🔴 CRITICAL ISSUES ({len(report['critical_issues'])}):\n"
            for issue in report['critical_issues']:
                result += f"  • {issue['message']}\n"
            result += "\n"

        # Warnings
        if report['warnings']:
            result += f"⚠️  WARNINGS ({len(report['warnings'])}):\n"
            for warning in report['warnings']:
                result += f"  • {warning['message']}\n"
            result += "\n"

        # Info
        if report['info']:
            result += f"ℹ️  INFORMATION:\n"
            for info in report['info']:
                result += f"  • {info}\n"
            result += "\n"

        if not report['critical_issues'] and not report['warnings']:
            result += "✅ No issues found - contract fully compliant\n"

        return result

    except ValueError as e:
        return f"Error: {str(e)}. Available clients: BIGBANK, TECHSTARTUP, MEDTECH"


@tool
def get_available_clients() -> str:
    """Get list of available clients and their enhanced validation standards."""

    result = "Available Clients for Enhanced Validation:\n\n"

    for client_id, standards in client_manager.clients.items():
        result += f"🏢 {client_id}: {standards.client_name}\n"
        result += f"   Max Liability: ${standards.max_liability_cap:,}\n" if standards.max_liability_cap else "   Max Liability: Unlimited\n"
        if standards.min_liability_cap:
            result += f"   Min Liability: ${standards.min_liability_cap:,}\n"
        if standards.required_sla_uptime:
            result += f"   Required SLA: {standards.required_sla_uptime}%\n"
        result += f"   IP Ownership Required: {standards.ip_ownership_required}\n"
        result += f"   Required Frameworks: {', '.join(standards.required_frameworks)}\n"
        if standards.min_cyber_liability:
            result += f"   Min Cyber Insurance: ${standards.min_cyber_liability:,}\n"
        result += "\n"

    return result


# Export all enhanced tools
contract_tools_enhanced = [
    # Enhanced schema tools
    get_liability_cap_summary,
    search_contracts_by_liability_cap,
    get_all_obligations,
    search_by_compliance_framework,
    find_non_compliant_contracts,
    get_ip_provisions,
    get_insurance_requirements,
    get_termination_provisions,

    # Legacy compatibility
    get_all_agreements,

    # Client validation
    validate_contract_for_client,
    get_available_clients
]
