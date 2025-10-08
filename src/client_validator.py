"""
Enhanced Client Knowledge Graph Manager

Manages client-specific validation against enhanced contract schema.
Now works with actual extracted liability caps, obligations, compliance frameworks, etc.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from neo4j import GraphDatabase
import json

# Optional master ontology support - can be provided externally if needed
HAS_ONTOLOGY = False
LegalKnowledgeGraph = None


@dataclass
class ClientStandards:
    """Client-specific contract standards and policies."""
    client_id: str
    client_name: str

    # Liability standards
    max_liability_cap: Optional[float] = None  # None = unlimited OK
    min_liability_cap: Optional[float] = None
    preferred_cap_type: str = "aggregate"  # aggregate, per_incident, unlimited
    required_carve_outs: List[str] = None  # Must have these exceptions

    # Obligation standards
    required_sla_uptime: Optional[float] = None  # e.g., 99.9%
    max_acceptable_penalty: Optional[str] = None  # e.g., "25% monthly fees"
    required_deliverables: List[str] = None  # Must-have deliverables

    # IP standards
    ip_ownership_required: bool = True  # Must own all IP
    shared_ip_allowed: bool = False
    open_source_policy: str = "prohibited"  # prohibited, restricted, encouraged
    sublicensing_allowed: bool = False

    # Compliance requirements
    required_frameworks: List[str] = None  # ["GDPR", "SOC2", "HIPAA"]
    certification_required: bool = False
    audit_rights_required: bool = True

    # Insurance requirements
    min_general_liability: Optional[float] = None  # Minimum coverage
    min_cyber_liability: Optional[float] = None
    min_professional_liability: Optional[float] = None

    # Data protection
    gdpr_required: bool = False
    data_location_restrictions: List[str] = None  # e.g., ["US", "EU"]
    breach_notification_max_hours: Optional[int] = None  # e.g., 24 hours

    # Termination requirements
    termination_for_convenience_required: bool = False
    max_termination_fee_percent: Optional[float] = None  # e.g., 25%

    # Legacy compatibility
    mandatory_clauses: List[str] = None  # Must-have clause types
    prohibited_clauses: List[str] = None  # Never allowed
    non_negotiable_terms: List[str] = None
    auto_reject_if_missing: List[str] = None

    # Custom rules
    custom_rules: Dict = None

    def __post_init__(self):
        if self.required_frameworks is None:
            self.required_frameworks = []
        if self.mandatory_clauses is None:
            self.mandatory_clauses = []
        if self.prohibited_clauses is None:
            self.prohibited_clauses = []
        if self.non_negotiable_terms is None:
            self.non_negotiable_terms = []
        if self.auto_reject_if_missing is None:
            self.auto_reject_if_missing = []
        if self.custom_rules is None:
            self.custom_rules = {}
        if self.required_carve_outs is None:
            self.required_carve_outs = []
        if self.required_deliverables is None:
            self.required_deliverables = []
        if self.data_location_restrictions is None:
            self.data_location_restrictions = []


class ClientKGManagerEnhanced:
    """
    Enhanced client manager that validates against actual extracted contract data.
    Works with LiabilityCap, Obligation, ComplianceFramework nodes, etc.
    """

    def __init__(self, master_ontology: Optional[LegalKnowledgeGraph] = None):
        """
        Initialize with optional master ontology.

        Args:
            master_ontology: The base legal knowledge graph (optional)
        """
        self.master_ontology = master_ontology
        self.clients: Dict[str, ClientStandards] = {}

    def register_client(self, standards: ClientStandards) -> None:
        """Register a client with their specific standards."""
        self.clients[standards.client_id] = standards
        print(f"✅ Registered client: {standards.client_name} ({standards.client_id})")

    def get_client_standards(self, client_id: str) -> ClientStandards:
        """Get standards for a specific client."""
        if client_id not in self.clients:
            raise ValueError(f"Client {client_id} not registered")
        return self.clients[client_id]

    def validate_contract_for_client(
        self,
        client_id: str,
        neo4j_driver: GraphDatabase.driver,
        contract_id: int
    ) -> Dict:
        """
        Validate a contract against client-specific standards using enhanced schema.

        Returns validation report with:
        - Liability cap validation
        - Obligation validation
        - Compliance validation
        - IP validation
        - Insurance validation
        - Overall pass/fail
        """
        standards = self.get_client_standards(client_id)
        report = {
            'client_id': client_id,
            'client_name': standards.client_name,
            'contract_id': contract_id,
            'passes_validation': True,
            'critical_issues': [],
            'warnings': [],
            'info': [],
            'compliant': False
        }

        # 1. Validate Liability Cap
        liability_issues = self._validate_liability_cap(neo4j_driver, contract_id, standards)
        report['critical_issues'].extend([i for i in liability_issues if i['severity'] == 'critical'])
        report['warnings'].extend([i for i in liability_issues if i['severity'] == 'warning'])

        # 2. Validate Obligations
        obligation_issues = self._validate_obligations(neo4j_driver, contract_id, standards)
        report['critical_issues'].extend([i for i in obligation_issues if i['severity'] == 'critical'])
        report['warnings'].extend([i for i in obligation_issues if i['severity'] == 'warning'])

        # 3. Validate Compliance Frameworks
        compliance_issues = self._validate_compliance(neo4j_driver, contract_id, standards)
        report['critical_issues'].extend([i for i in compliance_issues if i['severity'] == 'critical'])
        report['warnings'].extend([i for i in compliance_issues if i['severity'] == 'warning'])

        # 4. Validate IP Provisions
        ip_issues = self._validate_ip(neo4j_driver, contract_id, standards)
        report['critical_issues'].extend([i for i in ip_issues if i['severity'] == 'critical'])
        report['warnings'].extend([i for i in ip_issues if i['severity'] == 'warning'])

        # 5. Validate Insurance
        insurance_issues = self._validate_insurance(neo4j_driver, contract_id, standards)
        report['critical_issues'].extend([i for i in insurance_issues if i['severity'] == 'critical'])
        report['warnings'].extend([i for i in insurance_issues if i['severity'] == 'warning'])

        # 6. Validate Data Protection
        data_issues = self._validate_data_protection(neo4j_driver, contract_id, standards)
        report['critical_issues'].extend([i for i in data_issues if i['severity'] == 'critical'])
        report['warnings'].extend([i for i in data_issues if i['severity'] == 'warning'])

        # 7. Validate Termination
        term_issues = self._validate_termination(neo4j_driver, contract_id, standards)
        report['critical_issues'].extend([i for i in term_issues if i['severity'] == 'critical'])
        report['warnings'].extend([i for i in term_issues if i['severity'] == 'warning'])

        # Determine overall compliance
        report['passes_validation'] = len(report['critical_issues']) == 0
        report['compliant'] = report['passes_validation']

        return report

    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================

    def _validate_liability_cap(
        self,
        driver: GraphDatabase.driver,
        contract_id: int,
        standards: ClientStandards
    ) -> List[Dict]:
        """Validate liability cap against client standards."""
        issues = []

        # Get liability cap from enhanced schema
        query = """
        MATCH (a:Agreement {contract_id: $contract_id})-[:HAS_LIABILITY_CAP]->(cap:LiabilityCap)
        RETURN cap.cap_amount as amount,
               cap.cap_type as type,
               cap.carve_outs as carve_outs,
               cap.applies_to_party as party
        """
        records, _, _ = driver.execute_query(query, {'contract_id': contract_id})

        if not records:
            if standards.max_liability_cap is not None or standards.min_liability_cap is not None:
                issues.append({
                    'type': 'missing_liability_cap',
                    'severity': 'critical',
                    'message': 'Contract has no liability cap, but client requires one'
                })
            return issues

        cap = records[0]
        cap_amount = cap['amount']

        # Check max cap
        if standards.max_liability_cap and cap_amount and cap_amount > standards.max_liability_cap:
            issues.append({
                'type': 'liability_cap_exceeds_max',
                'severity': 'critical',
                'found': cap_amount,
                'allowed': standards.max_liability_cap,
                'message': f'Liability cap ${cap_amount:,.0f} exceeds client max of ${standards.max_liability_cap:,.0f}'
            })

        # Check min cap
        if standards.min_liability_cap and cap_amount and cap_amount < standards.min_liability_cap:
            issues.append({
                'type': 'liability_cap_below_min',
                'severity': 'warning',
                'found': cap_amount,
                'required': standards.min_liability_cap,
                'message': f'Liability cap ${cap_amount:,.0f} below client minimum of ${standards.min_liability_cap:,.0f}'
            })

        # Check cap type
        if standards.preferred_cap_type and cap['type'] != standards.preferred_cap_type:
            issues.append({
                'type': 'wrong_cap_type',
                'severity': 'warning',
                'found': cap['type'],
                'preferred': standards.preferred_cap_type,
                'message': f'Cap type is {cap["type"]}, client prefers {standards.preferred_cap_type}'
            })

        # Check required carve-outs
        carve_outs = cap.get('carve_outs', [])
        for required_carve_out in standards.required_carve_outs:
            found = any(required_carve_out.lower() in co.lower() for co in carve_outs)
            if not found:
                issues.append({
                    'type': 'missing_carve_out',
                    'severity': 'warning',
                    'required': required_carve_out,
                    'message': f'Missing required carve-out: {required_carve_out}'
                })

        return issues

    def _validate_obligations(
        self,
        driver: GraphDatabase.driver,
        contract_id: int,
        standards: ClientStandards
    ) -> List[Dict]:
        """Validate obligations against client standards."""
        issues = []

        query = """
        MATCH (a:Agreement {contract_id: $contract_id})-[:HAS_OBLIGATION]->(o:Obligation)
        RETURN o.performance_standards as sla,
               o.consequences_of_breach as penalty,
               o.deliverables as deliverables
        """
        records, _, _ = driver.execute_query(query, {'contract_id': contract_id})

        if not records:
            if standards.required_deliverables:
                issues.append({
                    'type': 'missing_obligations',
                    'severity': 'warning',
                    'message': 'No obligations defined in contract'
                })
            return issues

        # Check SLA requirements
        if standards.required_sla_uptime:
            has_acceptable_sla = any(
                r['sla'] and str(standards.required_sla_uptime) in r['sla']
                for r in records
            )
            if not has_acceptable_sla:
                issues.append({
                    'type': 'insufficient_sla',
                    'severity': 'critical',
                    'required': f'{standards.required_sla_uptime}% uptime',
                    'message': f'Contract does not specify required SLA of {standards.required_sla_uptime}%'
                })

        # Check required deliverables
        all_deliverables = []
        for record in records:
            if record['deliverables']:
                all_deliverables.extend(record['deliverables'])

        for required_deliverable in standards.required_deliverables:
            found = any(required_deliverable.lower() in d.lower() for d in all_deliverables)
            if not found:
                issues.append({
                    'type': 'missing_deliverable',
                    'severity': 'warning',
                    'required': required_deliverable,
                    'message': f'Missing required deliverable: {required_deliverable}'
                })

        return issues

    def _validate_compliance(
        self,
        driver: GraphDatabase.driver,
        contract_id: int,
        standards: ClientStandards
    ) -> List[Dict]:
        """Validate compliance frameworks."""
        issues = []

        query = """
        MATCH (a:Agreement {contract_id: $contract_id})-[:COMPLIES_WITH]->(c:ComplianceRequirement)
              -[:FRAMEWORK_TYPE]->(f:ComplianceFramework)
        RETURN f.framework_name as framework,
               c.certification_required as cert_required,
               c.audit_rights as audit_rights
        """
        records, _, _ = driver.execute_query(query, {'contract_id': contract_id})

        frameworks = {r['framework'] for r in records}

        # Check required frameworks
        for required_framework in standards.required_frameworks:
            if required_framework not in frameworks:
                issues.append({
                    'type': 'missing_compliance_framework',
                    'severity': 'critical',
                    'required': required_framework,
                    'message': f'Contract does not comply with required framework: {required_framework}'
                })

        # Check certification and audit rights
        if standards.certification_required or standards.audit_rights_required:
            for record in records:
                if standards.certification_required and not record['cert_required']:
                    issues.append({
                        'type': 'certification_not_required',
                        'severity': 'warning',
                        'framework': record['framework'],
                        'message': f'{record["framework"]} certification not required in contract'
                    })

                if standards.audit_rights_required and not record['audit_rights']:
                    issues.append({
                        'type': 'no_audit_rights',
                        'severity': 'critical',
                        'framework': record['framework'],
                        'message': f'No audit rights for {record["framework"]}'
                    })

        return issues

    def _validate_ip(
        self,
        driver: GraphDatabase.driver,
        contract_id: int,
        standards: ClientStandards
    ) -> List[Dict]:
        """Validate IP provisions."""
        issues = []

        query = """
        MATCH (a:Agreement {contract_id: $contract_id})-[:HAS_IP_PROVISION]->(ip:IntellectualProperty)
        RETURN ip.ip_type as type,
               ip.owner as owner,
               ip.sublicensable as sublicensable
        """
        records, _, _ = driver.execute_query(query, {'contract_id': contract_id})

        if standards.ip_ownership_required:
            # Check if client owns IP
            client_owns = any(r['type'] == 'ownership' for r in records)
            if not client_owns:
                issues.append({
                    'type': 'no_ip_ownership',
                    'severity': 'critical',
                    'message': 'Client does not own IP, but ownership is required'
                })

        if not standards.sublicensing_allowed:
            has_sublicensing = any(r.get('sublicensable') == True for r in records)
            if has_sublicensing:
                issues.append({
                    'type': 'sublicensing_not_allowed',
                    'severity': 'critical',
                    'message': 'Contract allows sublicensing, but client policy prohibits it'
                })

        return issues

    def _validate_insurance(
        self,
        driver: GraphDatabase.driver,
        contract_id: int,
        standards: ClientStandards
    ) -> List[Dict]:
        """Validate insurance requirements."""
        issues = []

        query = """
        MATCH (a:Agreement {contract_id: $contract_id})-[:HAS_INSURANCE_REQUIREMENT]->(:InsuranceRequirement)
              -[:REQUIRES_INSURANCE_TYPE]->(it:InsuranceType)
        RETURN it.insurance_type as type,
               it.minimum_coverage as coverage
        """
        records, _, _ = driver.execute_query(query, {'contract_id': contract_id})

        coverage_by_type = {r['type']: r['coverage'] for r in records}

        # Check general liability
        if standards.min_general_liability:
            gl_coverage = coverage_by_type.get('Commercial General Liability')
            if not gl_coverage or gl_coverage < standards.min_general_liability:
                issues.append({
                    'type': 'insufficient_general_liability',
                    'severity': 'critical',
                    'found': gl_coverage,
                    'required': standards.min_general_liability,
                    'message': f'General liability coverage insufficient'
                })

        # Check cyber liability
        if standards.min_cyber_liability:
            cyber_coverage = coverage_by_type.get('Cyber Liability')
            if not cyber_coverage or cyber_coverage < standards.min_cyber_liability:
                issues.append({
                    'type': 'insufficient_cyber_liability',
                    'severity': 'critical',
                    'found': cyber_coverage,
                    'required': standards.min_cyber_liability,
                    'message': f'Cyber liability coverage insufficient'
                })

        return issues

    def _validate_data_protection(
        self,
        driver: GraphDatabase.driver,
        contract_id: int,
        standards: ClientStandards
    ) -> List[Dict]:
        """Validate data protection provisions."""
        issues = []

        query = """
        MATCH (a:Agreement {contract_id: $contract_id})-[:HAS_DATA_PROTECTION]->(dp:DataProtection)
        RETURN dp.gdpr_compliant as gdpr_compliant,
               dp.breach_notification_period as breach_period,
               dp.data_location_restrictions as location_restrictions
        """
        records, _, _ = driver.execute_query(query, {'contract_id': contract_id})

        if not records:
            if standards.gdpr_required:
                issues.append({
                    'type': 'no_data_protection',
                    'severity': 'critical',
                    'message': 'No data protection provisions found'
                })
            return issues

        dp = records[0]

        if standards.gdpr_required and not dp.get('gdpr_compliant'):
            issues.append({
                'type': 'not_gdpr_compliant',
                'severity': 'critical',
                'message': 'Contract is not GDPR compliant'
            })

        # Check breach notification period
        if standards.breach_notification_max_hours:
            breach_period = dp.get('breach_period', '')
            # Simple check - would need better parsing in production
            if '24' not in breach_period and standards.breach_notification_max_hours <= 24:
                issues.append({
                    'type': 'breach_notification_too_long',
                    'severity': 'warning',
                    'found': breach_period,
                    'required': f'{standards.breach_notification_max_hours} hours',
                    'message': 'Breach notification period may exceed client requirements'
                })

        return issues

    def _validate_termination(
        self,
        driver: GraphDatabase.driver,
        contract_id: int,
        standards: ClientStandards
    ) -> List[Dict]:
        """Validate termination provisions."""
        issues = []

        query = """
        MATCH (a:Agreement {contract_id: $contract_id})-[:HAS_TERMINATION_PROVISIONS]->(t:Termination)
        RETURN t.convenience_allowed as convenience_allowed,
               t.termination_fee as termination_fee
        """
        records, _, _ = driver.execute_query(query, {'contract_id': contract_id})

        if not records:
            if standards.termination_for_convenience_required:
                issues.append({
                    'type': 'no_termination_provisions',
                    'severity': 'critical',
                    'message': 'No termination provisions found'
                })
            return issues

        term = records[0]

        if standards.termination_for_convenience_required and not term.get('convenience_allowed'):
            issues.append({
                'type': 'no_termination_for_convenience',
                'severity': 'critical',
                'message': 'Termination for convenience not allowed'
            })

        return issues

    # ========================================================================
    # REPORTING
    # ========================================================================

    def generate_validation_report(self, validation_result: Dict) -> str:
        """Generate human-readable validation report."""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(f"CONTRACT VALIDATION REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Client: {validation_result['client_name']} ({validation_result['client_id']})")
        report_lines.append(f"Contract ID: {validation_result['contract_id']}")
        report_lines.append(f"Overall Status: {'✅ PASS' if validation_result['compliant'] else '❌ FAIL'}")
        report_lines.append("")

        if validation_result['critical_issues']:
            report_lines.append("🔴 CRITICAL ISSUES:")
            for issue in validation_result['critical_issues']:
                report_lines.append(f"  • {issue['message']}")
            report_lines.append("")

        if validation_result['warnings']:
            report_lines.append("⚠️  WARNINGS:")
            for issue in validation_result['warnings']:
                report_lines.append(f"  • {issue['message']}")
            report_lines.append("")

        if validation_result['info']:
            report_lines.append("ℹ️  INFORMATION:")
            for info in validation_result['info']:
                report_lines.append(f"  • {info}")
            report_lines.append("")

        report_lines.append("=" * 80)

        return "\n".join(report_lines)


# Example usage
if __name__ == "__main__":
    import os

    # Initialize manager (without ontology if not available)
    manager = ClientKGManagerEnhanced(master_ontology=None)

    # Define client standards using enhanced schema
    client_a = ClientStandards(
        client_id="CLIENT_A",
        client_name="BigBank Corp",
        max_liability_cap=5_000_000,
        min_liability_cap=1_000_000,
        preferred_cap_type="aggregate",
        required_carve_outs=["gross negligence", "fraud", "IP infringement"],
        required_sla_uptime=99.9,
        required_frameworks=["SOC2", "PCI-DSS"],
        certification_required=True,
        audit_rights_required=True,
        min_general_liability=2_000_000,
        min_cyber_liability=10_000_000,
        gdpr_required=False,
        termination_for_convenience_required=True
    )

    manager.register_client(client_a)

    # Connect to Neo4j and validate
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USERNAME', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')

    if NEO4J_PASSWORD:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        # Validate contract 1 against Client A standards
        validation = manager.validate_contract_for_client("CLIENT_A", driver, 1)

        # Print report
        print(manager.generate_validation_report(validation))

        driver.close()
    else:
        print("Set NEO4J_PASSWORD to run validation example")
