"""
Enhanced Agreement Schema - TypedDict classes for enhanced contract data model
Supports comprehensive extraction including liability caps, obligations, compliance, etc.
"""

from typing import TypedDict, List, Optional
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class CapType(Enum):
    PER_INCIDENT = "per_incident"
    AGGREGATE = "aggregate"
    ANNUAL = "annual"
    UNLIMITED = "unlimited"


class LicenseType(Enum):
    EXCLUSIVE = "exclusive"
    NON_EXCLUSIVE = "non_exclusive"
    SOLE = "sole"


class IPType(Enum):
    OWNERSHIP = "ownership"
    LICENSE = "license"
    JOINT_OWNERSHIP = "joint_ownership"
    ASSIGNMENT = "assignment"


class DisputeMethod(Enum):
    ARBITRATION = "arbitration"
    LITIGATION = "litigation"
    MEDIATION = "mediation"
    NEGOTIATION = "negotiation"


# ============================================================================
# BASIC TYPES
# ============================================================================

class Party(TypedDict):
    name: str
    role: str
    incorporation_country: str
    incorporation_state: str


class GoverningLaw(TypedDict):
    country: str
    state: str
    most_favored_country: str


class ContractValue(TypedDict, total=False):
    amount: float
    currency: str


# ============================================================================
# ENHANCED TYPES
# ============================================================================

class DisputeResolution(TypedDict, total=False):
    method: str  # DisputeMethod value
    venue: str
    jurisdiction: str
    governing_rules: str


class LiabilityCap(TypedDict, total=False):
    exists: bool
    cap_amount: Optional[float]
    currency: Optional[str]
    cap_type: str  # CapType value
    calculation_basis: str
    applies_to_party: str
    carve_outs: List[str]
    excerpts: List[str]


class Indemnification(TypedDict, total=False):
    indemnitor: str
    indemnitee: str
    scope: str
    triggers: List[str]
    limitations: List[str]
    excerpts: List[str]


class Obligation(TypedDict, total=False):
    obligation_type: str
    obligated_party: str
    description: str
    deadline: str
    deliverables: List[str]
    performance_standards: str
    consequences_of_breach: str
    excerpts: List[str]


class PaymentTerms(TypedDict, total=False):
    payment_schedule: str
    payment_method: str
    currency: str
    late_payment_penalty: str
    pricing_model: str
    price_increases: str
    excerpts: List[str]


class LicenseDetails(TypedDict, total=False):
    license_type: str  # LicenseType value
    scope: str
    territory: str
    duration: str
    sublicensable: bool
    transferable: bool
    perpetual: bool
    irrevocable: bool


class IntellectualProperty(TypedDict, total=False):
    ip_type: str  # IPType value
    owner: str
    subject_matter: str
    license_details: Optional[LicenseDetails]
    excerpts: List[str]


class Confidentiality(TypedDict, total=False):
    exists: bool
    duration: str
    surviving_termination: bool
    exceptions: List[str]
    return_obligations: bool
    excerpts: List[str]


class DataProtection(TypedDict, total=False):
    gdpr_compliant: bool
    data_processing_agreement: bool
    data_subject_rights: List[str]
    breach_notification_period: str
    data_location_restrictions: List[str]
    subprocessor_consent_required: bool
    excerpts: List[str]


class ComplianceFramework(TypedDict, total=False):
    framework_name: str
    certification_required: bool
    audit_rights: bool
    audit_frequency: str
    specific_requirements: List[str]
    excerpts: List[str]


class Warranty(TypedDict, total=False):
    warranty_type: str
    warrantor: str
    warranty_statement: str
    duration: str
    remedies: List[str]
    disclaimers: List[str]
    excerpts: List[str]


class TerminationForConvenience(TypedDict, total=False):
    allowed: bool
    notice_period: str
    termination_fee: str
    allowed_parties: List[str]


class TerminationForCause(TypedDict, total=False):
    breach_types: List[str]
    cure_period: str
    notice_required: bool


class PostTerminationObligation(TypedDict, total=False):
    obligation: str
    responsible_party: str
    duration: str


class Termination(TypedDict, total=False):
    termination_for_convenience: TerminationForConvenience
    termination_for_cause: TerminationForCause
    post_termination_obligations: List[PostTerminationObligation]
    surviving_clauses: List[str]
    excerpts: List[str]


class InsuranceType(TypedDict, total=False):
    insurance_type: str
    minimum_coverage: float
    currency: str
    additional_insured_required: bool


class Insurance(TypedDict, total=False):
    required: bool
    types: List[InsuranceType]
    proof_required: bool
    excerpts: List[str]


class Restriction(TypedDict, total=False):
    restriction_type: str
    restricted_party: str
    description: str
    duration: str
    geographic_scope: str
    exceptions: List[str]
    excerpts: List[str]


class ChangeOfControl(TypedDict, total=False):
    triggers_termination: bool
    requires_consent: bool
    notification_required: bool
    affected_party: str
    excerpts: List[str]


class ForceMajeure(TypedDict, total=False):
    exists: bool
    covered_events: List[str]
    notice_period: str
    suspension_of_obligations: bool
    termination_allowed: bool
    termination_trigger_period: str
    excerpts: List[str]


# ============================================================================
# LEGACY CLAUSE TYPE (for backward compatibility)
# ============================================================================

class ContractClause(TypedDict):
    clause_type: str
    excerpts: List[str]


# ============================================================================
# MAIN AGREEMENT TYPE
# ============================================================================

class Agreement(TypedDict, total=False):
    # Basic Information
    agreement_name: str
    agreement_type: str
    contract_id: int
    effective_date: str
    expiration_date: str
    agreement_date: str
    renewal_term: str
    notice_period_to_terminate_renewal: str
    auto_renewal: bool
    total_contract_value: Optional[ContractValue]

    # Parties and Governance
    parties: List[Party]
    governing_law: GoverningLaw
    dispute_resolution: DisputeResolution

    # Liability and Risk
    liability_cap: LiabilityCap
    indemnification: List[Indemnification]
    insurance: Insurance

    # Obligations and Performance
    obligations: List[Obligation]
    payment_terms: PaymentTerms
    warranties: List[Warranty]

    # Intellectual Property
    intellectual_property: List[IntellectualProperty]

    # Confidentiality and Data
    confidentiality: Confidentiality
    data_protection: DataProtection

    # Compliance
    compliance_frameworks: List[ComplianceFramework]

    # Termination
    termination: Termination

    # Restrictions and Controls
    restrictions: List[Restriction]
    change_of_control: ChangeOfControl
    force_majeure: ForceMajeure

    # Legacy field for backward compatibility
    clauses: List[ContractClause]


# ============================================================================
# LEGACY CLAUSE TYPES (for backward compatibility with original CUAD schema)
# ============================================================================

class ClauseType(Enum):
    # Original CUAD types
    ANTI_ASSIGNMENT = "Anti-Assignment"
    COMPETITIVE_RESTRICTION = "Competitive Restriction Exception"
    NON_COMPETE = "Non-Compete"
    EXCLUSIVITY = "Exclusivity"
    NO_SOLICIT_CUSTOMERS = "No-Solicit of Customers"
    NO_SOLICIT_EMPLOYEES = "No-Solicit Of Employees"
    NON_DISPARAGEMENT = "Non-Disparagement"
    TERMINATION_FOR_CONVENIENCE = "Termination For Convenience"
    ROFR_ROFO_ROFN = "Rofr/Rofo/Rofn"
    CHANGE_OF_CONTROL = "Change of Control"
    REVENUE_PROFIT_SHARING = "Revenue/Profit Sharing"
    PRICE_RESTRICTION = "Price Restrictions"
    MINIMUM_COMMITMENT = "Minimum Commitment"
    VOLUME_RESTRICTION = "Volume Restriction"
    IP_OWNERSHIP_ASSIGNMENT = "IP Ownership Assignment"
    JOINT_IP_OWNERSHIP = "Joint IP Ownership"
    LICENSE_GRANT = "License grant"
    NON_TRANSFERABLE_LICENSE = "Non-Transferable License"
    AFFILIATE_LICENSE_LICENSOR = "Affiliate License-Licensor"
    AFFILIATE_LICENSE_LICENSEE = "Affiliate License-Licensee"
    UNLIMITED_LICENSE = "Unlimited/All-You-Can-Eat-License"
    PERPETUAL_LICENSE = "Irrevocable Or Perpetual License"
    SOURCE_CODE_SCROW = "Source Code Escrow"
    POST_TERMINATION_SERVICES = "Post-Termination Services"
    AUDIT_RIGHTS = "Audit Rights"
    UNCAPPED_LIABILITY = "Uncapped Liability"
    CAP_ON_LIABILITY = "Cap On Liability"
    LIQUIDATED_DAMAGES = "Liquidated Damages"
    WARRANTY_DURATION = "Warranty Duration"
    INSURANCE = "Insurance"
    COVENANT_NOT_TO_SUE = "Covenant Not To Sue"
    THIRD_PARTY_BENEFICIARY = "Third Party Beneficiary"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_empty_agreement(contract_id: int = 0) -> Agreement:
    """Create an empty agreement with default values."""
    return Agreement(
        contract_id=contract_id,
        parties=[],
        clauses=[],
        obligations=[],
        indemnification=[],
        intellectual_property=[],
        compliance_frameworks=[],
        warranties=[],
        restrictions=[]
    )


def has_enhanced_data(agreement: Agreement) -> bool:
    """Check if agreement has enhanced schema data."""
    enhanced_fields = [
        'liability_cap',
        'obligations',
        'payment_terms',
        'intellectual_property',
        'confidentiality',
        'data_protection',
        'compliance_frameworks',
        'termination'
    ]
    return any(field in agreement for field in enhanced_fields)


def is_legacy_format(agreement: Agreement) -> bool:
    """Check if agreement is in legacy (original) format."""
    return 'clauses' in agreement and not has_enhanced_data(agreement)
