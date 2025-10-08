"""
Enhanced Contract Search Service
Supports queries for enhanced schema including liability caps, obligations, compliance, etc.
"""

from neo4j import GraphDatabase
from typing import List, Dict, Optional
from .schema import (
    Agreement, LiabilityCap, Obligation, ComplianceFramework,
    IntellectualProperty, Party, Termination
)
from neo4j_graphrag.retrievers import VectorCypherRetriever, Text2CypherRetriever
from neo4j_graphrag.embeddings import OpenAIEmbeddings
from neo4j_graphrag.llm import OpenAILLM


class ContractSearchServiceEnhanced:
    """Enhanced contract search service supporting comprehensive queries."""

    def __init__(self, uri, user, pwd):
        driver = GraphDatabase.driver(uri, auth=(user, pwd))
        self._driver = driver
        self._openai_embedder = OpenAIEmbeddings(model="text-embedding-3-small")
        self._llm = OpenAILLM(model_name="gpt-4o", model_params={"temperature": 0})

    # ========================================================================
    # BASIC AGREEMENT QUERIES
    # ========================================================================

    async def get_contract(self, contract_id: int) -> Agreement:
        """Get complete contract with all enhanced fields."""
        GET_CONTRACT_QUERY = """
            MATCH (a:Agreement {contract_id: $contract_id})
            OPTIONAL MATCH (a)-[:IS_PARTY_TO]-(p:Organization)
                          -[:INCORPORATED_IN]->(country:Country)
            OPTIONAL MATCH (a)-[:HAS_LIABILITY_CAP]->(cap:LiabilityCap)
            OPTIONAL MATCH (a)-[:HAS_OBLIGATION]->(obl:Obligation)
            OPTIONAL MATCH (a)-[:COMPLIES_WITH]->(comp:ComplianceRequirement)
                          -[:FRAMEWORK_TYPE]->(framework:ComplianceFramework)
            OPTIONAL MATCH (a)-[:HAS_IP_PROVISION]->(ip:IntellectualProperty)
            OPTIONAL MATCH (a)-[:HAS_TERMINATION_PROVISIONS]->(term:Termination)

            RETURN a as agreement,
                   collect(DISTINCT p) as parties,
                   collect(DISTINCT country) as countries,
                   cap,
                   collect(DISTINCT obl) as obligations,
                   collect(DISTINCT {framework: framework.framework_name, compliance: comp}) as compliance,
                   collect(DISTINCT ip) as ip_provisions,
                   term
        """

        records, _, _ = self._driver.execute_query(
            GET_CONTRACT_QUERY,
            {'contract_id': contract_id}
        )

        if not records:
            return None

        record = records[0]
        agreement_node = record.get('agreement')

        # Build enhanced agreement object
        agreement: Agreement = {
            'contract_id': agreement_node.get('contract_id'),
            'agreement_name': agreement_node.get('name'),
            'agreement_type': agreement_node.get('agreement_type'),
            'effective_date': agreement_node.get('effective_date'),
            'expiration_date': agreement_node.get('expiration_date'),
            'renewal_term': agreement_node.get('renewal_term'),
            'parties': await self._build_parties(record.get('parties'), record.get('countries'))
        }

        # Add liability cap if exists
        cap_node = record.get('cap')
        if cap_node:
            agreement['liability_cap'] = {
                'exists': True,
                'cap_amount': cap_node.get('cap_amount'),
                'currency': cap_node.get('currency'),
                'cap_type': cap_node.get('cap_type'),
                'calculation_basis': cap_node.get('calculation_basis'),
                'applies_to_party': cap_node.get('applies_to_party'),
                'carve_outs': cap_node.get('carve_outs', []),
                'excerpts': []
            }

        # Add obligations
        obligations = record.get('obligations', [])
        if obligations and obligations[0] is not None:
            agreement['obligations'] = [
                {
                    'obligation_type': obl.get('obligation_type'),
                    'obligated_party': obl.get('obligated_party'),
                    'description': obl.get('description'),
                    'deadline': obl.get('deadline'),
                    'deliverables': obl.get('deliverables', []),
                    'performance_standards': obl.get('performance_standards'),
                    'consequences_of_breach': obl.get('consequences_of_breach'),
                    'excerpts': []
                }
                for obl in obligations
            ]

        # Add compliance frameworks
        compliance_data = record.get('compliance', [])
        if compliance_data and compliance_data[0] is not None:
            agreement['compliance_frameworks'] = [
                {
                    'framework_name': comp['framework'],
                    'certification_required': comp['compliance'].get('certification_required'),
                    'audit_rights': comp['compliance'].get('audit_rights'),
                    'audit_frequency': comp['compliance'].get('audit_frequency'),
                    'specific_requirements': comp['compliance'].get('specific_requirements', []),
                    'excerpts': []
                }
                for comp in compliance_data
                if comp['framework'] is not None
            ]

        # Add IP provisions
        ip_provisions = record.get('ip_provisions', [])
        if ip_provisions and ip_provisions[0] is not None:
            agreement['intellectual_property'] = [
                {
                    'ip_type': ip.get('ip_type'),
                    'owner': ip.get('owner'),
                    'subject_matter': ip.get('subject_matter'),
                    'license_details': {
                        'license_type': ip.get('license_type'),
                        'scope': ip.get('scope'),
                        'territory': ip.get('territory'),
                        'duration': ip.get('duration'),
                        'sublicensable': ip.get('sublicensable'),
                        'transferable': ip.get('transferable'),
                        'perpetual': ip.get('perpetual'),
                        'irrevocable': ip.get('irrevocable')
                    } if ip.get('license_type') else None,
                    'excerpts': []
                }
                for ip in ip_provisions
            ]

        return agreement

    # ========================================================================
    # LIABILITY CAP QUERIES
    # ========================================================================

    async def get_contracts_by_liability_cap(
        self,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        cap_type: Optional[str] = None
    ) -> List[Agreement]:
        """Find contracts by liability cap criteria."""
        query_parts = ["MATCH (a:Agreement)-[:HAS_LIABILITY_CAP]->(cap:LiabilityCap)"]
        where_clauses = []

        if min_amount is not None:
            where_clauses.append("cap.cap_amount >= $min_amount")
        if max_amount is not None:
            where_clauses.append("cap.cap_amount <= $max_amount")
        if cap_type:
            where_clauses.append("cap.cap_type = $cap_type")

        if where_clauses:
            query_parts.append("WHERE " + " AND ".join(where_clauses))

        query_parts.append("""
            RETURN a as agreement, cap
            ORDER BY cap.cap_amount DESC
        """)

        query = "\n".join(query_parts)
        params = {}
        if min_amount is not None:
            params['min_amount'] = min_amount
        if max_amount is not None:
            params['max_amount'] = max_amount
        if cap_type:
            params['cap_type'] = cap_type

        records, _, _ = self._driver.execute_query(query, params)

        agreements = []
        for record in records:
            agreement_node = record['agreement']
            cap_node = record['cap']

            agreement: Agreement = {
                'contract_id': agreement_node.get('contract_id'),
                'agreement_name': agreement_node.get('name'),
                'agreement_type': agreement_node.get('agreement_type'),
                'liability_cap': {
                    'exists': True,
                    'cap_amount': cap_node.get('cap_amount'),
                    'currency': cap_node.get('currency'),
                    'cap_type': cap_node.get('cap_type'),
                    'carve_outs': cap_node.get('carve_outs', []),
                    'excerpts': []
                }
            }
            agreements.append(agreement)

        return agreements

    async def get_liability_cap_statistics(self) -> Dict:
        """Get statistics on liability caps across all contracts."""
        STATS_QUERY = """
            MATCH (a:Agreement)-[:HAS_LIABILITY_CAP]->(cap:LiabilityCap)
            WHERE cap.cap_amount IS NOT NULL
            RETURN
                avg(cap.cap_amount) as avg_cap,
                min(cap.cap_amount) as min_cap,
                max(cap.cap_amount) as max_cap,
                count(cap) as total_contracts,
                collect(DISTINCT cap.cap_type) as cap_types,
                collect(DISTINCT cap.currency) as currencies
        """

        records, _, _ = self._driver.execute_query(STATS_QUERY)
        if not records:
            return {}

        record = records[0]
        return {
            'average_cap': record['avg_cap'],
            'minimum_cap': record['min_cap'],
            'maximum_cap': record['max_cap'],
            'total_contracts_with_caps': record['total_contracts'],
            'cap_types': record['cap_types'],
            'currencies': record['currencies']
        }

    # ========================================================================
    # OBLIGATION QUERIES
    # ========================================================================

    async def get_obligations_by_party(self, party_name: str) -> List[Dict]:
        """Get all obligations for a specific party."""
        QUERY = """
            MATCH (a:Agreement)-[:HAS_OBLIGATION]->(o:Obligation)
            WHERE o.obligated_party CONTAINS $party_name
            RETURN a.name as contract,
                   a.contract_id as contract_id,
                   o.obligation_type as type,
                   o.description as description,
                   o.deadline as deadline,
                   o.consequences_of_breach as penalty
            ORDER BY a.name
        """

        records, _, _ = self._driver.execute_query(QUERY, {'party_name': party_name})

        return [
            {
                'contract_name': r['contract'],
                'contract_id': r['contract_id'],
                'obligation_type': r['type'],
                'description': r['description'],
                'deadline': r['deadline'],
                'breach_consequences': r['penalty']
            }
            for r in records
        ]

    async def get_contracts_with_sla(self) -> List[Agreement]:
        """Find contracts with performance SLAs."""
        QUERY = """
            MATCH (a:Agreement)-[:HAS_OBLIGATION]->(o:Obligation)
            WHERE o.performance_standards IS NOT NULL
            RETURN DISTINCT a as agreement,
                   collect(o) as obligations
        """

        records, _, _ = self._driver.execute_query(QUERY)

        agreements = []
        for record in records:
            agreement_node = record['agreement']
            obligations = record['obligations']

            agreement: Agreement = {
                'contract_id': agreement_node.get('contract_id'),
                'agreement_name': agreement_node.get('name'),
                'agreement_type': agreement_node.get('agreement_type'),
                'obligations': [
                    {
                        'obligation_type': obl.get('obligation_type'),
                        'performance_standards': obl.get('performance_standards'),
                        'consequences_of_breach': obl.get('consequences_of_breach'),
                        'excerpts': []
                    }
                    for obl in obligations
                ]
            }
            agreements.append(agreement)

        return agreements

    # ========================================================================
    # COMPLIANCE QUERIES
    # ========================================================================

    async def get_contracts_by_compliance_framework(
        self,
        framework_name: str
    ) -> List[Agreement]:
        """Find contracts complying with specific framework."""
        QUERY = """
            MATCH (a:Agreement)-[:COMPLIES_WITH]->(c:ComplianceRequirement)
                  -[:FRAMEWORK_TYPE]->(f:ComplianceFramework {framework_name: $framework_name})
            RETURN a as agreement, c as compliance
        """

        records, _, _ = self._driver.execute_query(
            QUERY,
            {'framework_name': framework_name}
        )

        agreements = []
        for record in records:
            agreement_node = record['agreement']
            compliance = record['compliance']

            agreement: Agreement = {
                'contract_id': agreement_node.get('contract_id'),
                'agreement_name': agreement_node.get('name'),
                'agreement_type': agreement_node.get('agreement_type'),
                'compliance_frameworks': [{
                    'framework_name': framework_name,
                    'certification_required': compliance.get('certification_required'),
                    'audit_rights': compliance.get('audit_rights'),
                    'audit_frequency': compliance.get('audit_frequency'),
                    'excerpts': []
                }]
            }
            agreements.append(agreement)

        return agreements

    async def get_non_compliant_contracts(self, framework_name: str) -> List[Dict]:
        """Find contracts NOT complying with specific framework."""
        QUERY = """
            MATCH (a:Agreement)
            WHERE NOT exists((a)-[:COMPLIES_WITH]->(:ComplianceRequirement)
                            -[:FRAMEWORK_TYPE]->(:ComplianceFramework {framework_name: $framework_name}))
            RETURN a.contract_id as contract_id,
                   a.name as contract_name,
                   a.agreement_type as contract_type
        """

        records, _, _ = self._driver.execute_query(
            QUERY,
            {'framework_name': framework_name}
        )

        return [
            {
                'contract_id': r['contract_id'],
                'contract_name': r['contract_name'],
                'contract_type': r['contract_type']
            }
            for r in records
        ]

    # ========================================================================
    # IP QUERIES
    # ========================================================================

    async def get_contracts_by_ip_type(self, ip_type: str) -> List[Agreement]:
        """Find contracts with specific IP type (license, ownership, etc.)."""
        QUERY = """
            MATCH (a:Agreement)-[:HAS_IP_PROVISION]->(ip:IntellectualProperty {ip_type: $ip_type})
            RETURN a as agreement, collect(ip) as ip_provisions
        """

        records, _, _ = self._driver.execute_query(QUERY, {'ip_type': ip_type})

        agreements = []
        for record in records:
            agreement_node = record['agreement']
            ip_provisions = record['ip_provisions']

            agreement: Agreement = {
                'contract_id': agreement_node.get('contract_id'),
                'agreement_name': agreement_node.get('name'),
                'agreement_type': agreement_node.get('agreement_type'),
                'intellectual_property': [
                    {
                        'ip_type': ip.get('ip_type'),
                        'owner': ip.get('owner'),
                        'subject_matter': ip.get('subject_matter'),
                        'license_details': {
                            'license_type': ip.get('license_type'),
                            'scope': ip.get('scope'),
                            'territory': ip.get('territory'),
                            'sublicensable': ip.get('sublicensable')
                        } if ip.get('license_type') else None,
                        'excerpts': []
                    }
                    for ip in ip_provisions
                ]
            }
            agreements.append(agreement)

        return agreements

    # ========================================================================
    # LEGACY COMPATIBILITY
    # ========================================================================

    async def get_contracts(self, organization_name: str) -> List[Agreement]:
        """Get contracts by organization (legacy compatible)."""
        GET_CONTRACTS_BY_PARTY_NAME = """
            CALL db.index.fulltext.queryNodes('organizationNameTextIndex', $organization_name)
            YIELD node AS o, score
            WITH o, score
            ORDER BY score DESC
            LIMIT 1
            WITH o
            MATCH (o)-[:IS_PARTY_TO]->(a:Agreement)
            RETURN a as agreement
        """

        records, _, _ = self._driver.execute_query(
            GET_CONTRACTS_BY_PARTY_NAME,
            {'organization_name': organization_name}
        )

        agreements = []
        for row in records:
            agreement_node = row['agreement']
            agreement: Agreement = {
                'contract_id': agreement_node.get('contract_id'),
                'agreement_name': agreement_node.get('name'),
                'agreement_type': agreement_node.get('agreement_type')
            }
            agreements.append(agreement)

        return agreements

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    async def _build_parties(self, party_nodes, country_nodes) -> List[Party]:
        """Build party list from nodes."""
        if not party_nodes:
            return []

        parties = []
        for i, party in enumerate(party_nodes):
            if party is None:
                continue

            p: Party = {
                'name': party.get('name'),
                'role': 'Unknown',  # Would need to get from relationship
                'incorporation_country': country_nodes[i].get('name') if i < len(country_nodes) else '',
                'incorporation_state': ''  # Would need to get from relationship
            }
            parties.append(p)

        return parties

    def close(self):
        """Close Neo4j connection."""
        self._driver.close()
