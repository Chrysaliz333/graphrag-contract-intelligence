"""
Enhanced Graph Creation Script
Supports comprehensive contract extraction including liability caps, obligations,
compliance frameworks, and all fields from enhanced schema.
"""

from neo4j import GraphDatabase
import json
import os
from pathlib import Path


CREATE_ENHANCED_GRAPH_STATEMENT = """
WITH $data AS data
WITH $data.agreement AS a

// Create main Agreement node with enhanced properties
MERGE (agreement:Agreement {contract_id: a.contract_id})
ON CREATE SET
  agreement.name = a.agreement_name,
  agreement.effective_date = a.effective_date,
  agreement.expiration_date = a.expiration_date,
  agreement.agreement_date = a.agreement_date,
  agreement.agreement_type = a.agreement_type,
  agreement.renewal_term = a.renewal_term,
  agreement.notice_period_to_terminate_renewal = a.notice_period_to_terminate_renewal,
  agreement.auto_renewal = a.auto_renewal,
  agreement.total_contract_value = CASE WHEN a.total_contract_value IS NOT NULL
    THEN a.total_contract_value.amount ELSE null END,
  agreement.contract_currency = CASE WHEN a.total_contract_value IS NOT NULL
    THEN a.total_contract_value.currency ELSE null END

// Governing Law
WITH a, agreement
FOREACH (countryName IN CASE
    WHEN a.governing_law IS NOT NULL AND a.governing_law.country IS NOT NULL
    THEN [a.governing_law.country]
    ELSE []
  END |
  MERGE (gl_country:Country {name: countryName})
  MERGE (agreement)-[gbl:GOVERNED_BY_LAW]->(gl_country)
  SET gbl.state = a.governing_law.state
)

// Dispute Resolution
WITH a, agreement
CALL {
  WITH a, agreement
  WITH a, agreement WHERE a.dispute_resolution IS NOT NULL

  // MERGE node without optional/null properties in the pattern
  MERGE (agreement)-[dr:HAS_DISPUTE_RESOLUTION]->(dispute:DisputeResolution)

  // SET required/likely-present fields directly
  SET dispute.method = a.dispute_resolution.method,
      dispute.venue = a.dispute_resolution.venue,
      dispute.jurisdiction = a.dispute_resolution.jurisdiction

  // Only set governing_rules if it is NOT NULL
  FOREACH (_ IN CASE WHEN a.dispute_resolution.governing_rules IS NULL THEN [] ELSE [1] END |
    SET dispute.governing_rules = a.dispute_resolution.governing_rules
  )

  RETURN count(*) as dispute_count
}
// Parties
WITH a, agreement
FOREACH (party IN CASE WHEN a.parties IS NOT NULL THEN a.parties ELSE [] END |
  FOREACH (_ IN CASE WHEN party.name IS NOT NULL THEN [1] ELSE [] END |
    MERGE (p:Organization {name: party.name})
    MERGE (p)-[ipt:IS_PARTY_TO]->(agreement)
    SET ipt.role = party.role
    FOREACH (incCountry IN CASE WHEN party.incorporation_country IS NOT NULL THEN [party.incorporation_country] ELSE [] END |
      MERGE (country_of_incorporation:Country {name: incCountry})
      MERGE (p)-[incorporated:INCORPORATED_IN]->(country_of_incorporation)
      SET incorporated.state = party.incorporation_state
    )
  )
)

// Liability Cap
WITH a, agreement
CALL {
  WITH a, agreement
  WITH a, agreement WHERE a.liability_cap IS NOT NULL AND a.liability_cap.exists = true
  MERGE (agreement)-[hlc:HAS_LIABILITY_CAP]->(cap:LiabilityCap {
    cap_amount: a.liability_cap.cap_amount,
    currency: a.liability_cap.currency,
    cap_type: a.liability_cap.cap_type,
    calculation_basis: a.liability_cap.calculation_basis,
    applies_to_party: a.liability_cap.applies_to_party,
    carve_outs: a.liability_cap.carve_outs
  })
  FOREACH (excerpt IN CASE
      WHEN a.liability_cap.excerpts IS NULL THEN []
      ELSE [ex IN a.liability_cap.excerpts WHERE ex IS NOT NULL]
    END |
    MERGE (cap)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
  RETURN count(*) as cap_count
}

// Indemnification
WITH a, agreement
FOREACH (indem IN CASE WHEN a.indemnification IS NOT NULL THEN a.indemnification ELSE [] END |
  CREATE (i:Indemnification {
    indemnitor: indem.indemnitor,
    indemnitee: indem.indemnitee,
    scope: indem.scope,
    triggers: indem.triggers,
    limitations: indem.limitations
  })
  MERGE (agreement)-[:HAS_INDEMNIFICATION]->(i)
  FOREACH (excerpt IN CASE
      WHEN indem.excerpts IS NULL THEN []
      ELSE [ex IN indem.excerpts WHERE ex IS NOT NULL]
    END |
    MERGE (i)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
)

// Obligations
WITH a, agreement
FOREACH (obl IN CASE WHEN a.obligations IS NOT NULL THEN a.obligations ELSE [] END |
  CREATE (o:Obligation {
    obligation_type: obl.obligation_type,
    obligated_party: obl.obligated_party,
    description: obl.description,
    deadline: obl.deadline,
    deliverables: obl.deliverables,
    performance_standards: obl.performance_standards,
    consequences_of_breach: obl.consequences_of_breach
  })
  MERGE (agreement)-[:HAS_OBLIGATION]->(o)
  FOREACH (excerpt IN CASE
      WHEN obl.excerpts IS NULL THEN []
      ELSE [ex IN obl.excerpts WHERE ex IS NOT NULL]
    END |
    MERGE (o)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
)

// Payment Terms
WITH a, agreement
CALL {
  WITH a, agreement
  WITH a, agreement WHERE a.payment_terms IS NOT NULL
  MERGE (agreement)-[:HAS_PAYMENT_TERMS]->(pt:PaymentTerms {
    payment_schedule: a.payment_terms.payment_schedule,
    payment_method: a.payment_terms.payment_method,
    currency: a.payment_terms.currency,
    late_payment_penalty: a.payment_terms.late_payment_penalty,
    pricing_model: a.payment_terms.pricing_model,
    price_increases: a.payment_terms.price_increases
  })
  FOREACH (excerpt IN CASE
      WHEN a.payment_terms.excerpts IS NULL THEN []
      ELSE [ex IN a.payment_terms.excerpts WHERE ex IS NOT NULL]
    END |
    MERGE (pt)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
  RETURN count(*) as pt_count
}

// Intellectual Property
WITH a, agreement
FOREACH (ip IN CASE WHEN a.intellectual_property IS NOT NULL THEN a.intellectual_property ELSE [] END |
  CREATE (ip_node:IntellectualProperty {
    ip_type: ip.ip_type,
    owner: ip.owner,
    subject_matter: ip.subject_matter,
    license_type: CASE WHEN ip.license_details IS NOT NULL THEN ip.license_details.license_type ELSE null END,
    scope: CASE WHEN ip.license_details IS NOT NULL THEN ip.license_details.scope ELSE null END,
    territory: CASE WHEN ip.license_details IS NOT NULL THEN ip.license_details.territory ELSE null END,
    duration: CASE WHEN ip.license_details IS NOT NULL THEN ip.license_details.duration ELSE null END,
    sublicensable: CASE WHEN ip.license_details IS NOT NULL THEN ip.license_details.sublicensable ELSE null END,
    transferable: CASE WHEN ip.license_details IS NOT NULL THEN ip.license_details.transferable ELSE null END,
    perpetual: CASE WHEN ip.license_details IS NOT NULL THEN ip.license_details.perpetual ELSE null END,
    irrevocable: CASE WHEN ip.license_details IS NOT NULL THEN ip.license_details.irrevocable ELSE null END
  })
  MERGE (agreement)-[:HAS_IP_PROVISION]->(ip_node)
  FOREACH (excerpt IN CASE
      WHEN ip.excerpts IS NULL THEN []
      ELSE [ex IN ip.excerpts WHERE ex IS NOT NULL]
    END |
    MERGE (ip_node)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
)

// Confidentiality
WITH a, agreement
CALL {
  WITH a, agreement
  WITH a, agreement WHERE a.confidentiality IS NOT NULL AND a.confidentiality.exists = true
  MERGE (agreement)-[:HAS_CONFIDENTIALITY]->(conf:Confidentiality {
    duration: a.confidentiality.duration,
    surviving_termination: a.confidentiality.surviving_termination,
    exceptions: a.confidentiality.exceptions,
    return_obligations: a.confidentiality.return_obligations
  })
  FOREACH (excerpt IN CASE WHEN a.confidentiality.excerpts IS NULL THEN [] ELSE [ex IN a.confidentiality.excerpts WHERE ex IS NOT NULL] END |
    MERGE (conf)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
  RETURN count(*) as conf_count
}

// Data Protection
WITH a, agreement
CALL {
  WITH a, agreement
  WITH a, agreement WHERE a.data_protection IS NOT NULL
  MERGE (agreement)-[:HAS_DATA_PROTECTION]->(dp:DataProtection {
    gdpr_compliant: a.data_protection.gdpr_compliant,
    data_processing_agreement: a.data_protection.data_processing_agreement,
    data_subject_rights: a.data_protection.data_subject_rights,
    breach_notification_period: a.data_protection.breach_notification_period,
    data_location_restrictions: a.data_protection.data_location_restrictions,
    subprocessor_consent_required: a.data_protection.subprocessor_consent_required
  })
  FOREACH (excerpt IN CASE WHEN a.data_protection.excerpts IS NULL THEN [] ELSE [ex IN a.data_protection.excerpts WHERE ex IS NOT NULL] END |
    MERGE (dp)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
  RETURN count(*) as dp_count
}

// Compliance Frameworks
WITH a, agreement
FOREACH (cf IN CASE WHEN a.compliance_frameworks IS NOT NULL THEN a.compliance_frameworks ELSE [] END |
  FOREACH (_ IN CASE WHEN cf.framework_name IS NOT NULL THEN [1] ELSE [] END |
    MERGE (framework:ComplianceFramework {framework_name: cf.framework_name})
    CREATE (compliance:ComplianceRequirement {
      certification_required: cf.certification_required,
      audit_rights: cf.audit_rights,
      audit_frequency: cf.audit_frequency,
      specific_requirements: cf.specific_requirements
    })
    MERGE (agreement)-[:COMPLIES_WITH]->(compliance)
    MERGE (compliance)-[:FRAMEWORK_TYPE]->(framework)
    FOREACH (excerpt IN CASE WHEN cf.excerpts IS NOT NULL THEN [ex IN cf.excerpts WHERE ex IS NOT NULL] ELSE [] END |
      MERGE (compliance)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
    )
  )
)

// Warranties
WITH a, agreement
FOREACH (warranty IN CASE WHEN a.warranties IS NOT NULL THEN a.warranties ELSE [] END |
  CREATE (w:Warranty {
    warranty_type: warranty.warranty_type,
    warrantor: warranty.warrantor,
    warranty_statement: warranty.warranty_statement,
    duration: warranty.duration,
    remedies: warranty.remedies,
    disclaimers: warranty.disclaimers
  })
  MERGE (agreement)-[:HAS_WARRANTY]->(w)
  FOREACH (excerpt IN CASE WHEN warranty.excerpts IS NULL THEN [] ELSE [ex IN warranty.excerpts WHERE ex IS NOT NULL] END |
    MERGE (w)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
)

// Termination
WITH a, agreement
CALL {
  WITH a, agreement
  WITH a, agreement WHERE a.termination IS NOT NULL
  MERGE (agreement)-[:HAS_TERMINATION_PROVISIONS]->(term:Termination {
    convenience_allowed: CASE WHEN a.termination.termination_for_convenience IS NOT NULL
      THEN a.termination.termination_for_convenience.allowed ELSE null END,
    convenience_notice_period: CASE WHEN a.termination.termination_for_convenience IS NOT NULL
      THEN a.termination.termination_for_convenience.notice_period ELSE null END,
    termination_fee: CASE WHEN a.termination.termination_for_convenience IS NOT NULL
      THEN a.termination.termination_for_convenience.termination_fee ELSE null END,
    convenience_parties: CASE WHEN a.termination.termination_for_convenience IS NOT NULL
      THEN a.termination.termination_for_convenience.allowed_parties ELSE null END,
    cause_breach_types: CASE WHEN a.termination.termination_for_cause IS NOT NULL
      THEN a.termination.termination_for_cause.breach_types ELSE null END,
    cause_cure_period: CASE WHEN a.termination.termination_for_cause IS NOT NULL
      THEN a.termination.termination_for_cause.cure_period ELSE null END,
    cause_notice_required: CASE WHEN a.termination.termination_for_cause IS NOT NULL
      THEN a.termination.termination_for_cause.notice_required ELSE null END,
    surviving_clauses: a.termination.surviving_clauses
  })
  FOREACH (excerpt IN CASE WHEN a.termination.excerpts IS NULL THEN [] ELSE [ex IN a.termination.excerpts WHERE ex IS NOT NULL] END |
    MERGE (term)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
  FOREACH (post_obl IN CASE WHEN a.termination.post_termination_obligations IS NOT NULL
    THEN a.termination.post_termination_obligations ELSE [] END |
    CREATE (pto:PostTerminationObligation {
      obligation: post_obl.obligation,
      responsible_party: post_obl.responsible_party,
      duration: post_obl.duration
    })
    MERGE (term)-[:HAS_POST_TERMINATION_OBLIGATION]->(pto)
  )
  RETURN count(*) as term_count
}

// Insurance
WITH a, agreement
CALL {
  WITH a, agreement
  WITH a, agreement WHERE a.insurance IS NOT NULL AND a.insurance.required = true
  MERGE (agreement)-[:HAS_INSURANCE_REQUIREMENT]->(ins:InsuranceRequirement {
    proof_required: a.insurance.proof_required
  })
  FOREACH (ins_type IN CASE WHEN a.insurance.types IS NOT NULL THEN a.insurance.types ELSE [] END |
    CREATE (it:InsuranceType {
      insurance_type: ins_type.insurance_type,
      minimum_coverage: ins_type.minimum_coverage,
      currency: ins_type.currency,
      additional_insured_required: ins_type.additional_insured_required
    })
    MERGE (ins)-[:REQUIRES_INSURANCE_TYPE]->(it)
  )
  FOREACH (excerpt IN CASE WHEN a.insurance.excerpts IS NULL THEN [] ELSE [ex IN a.insurance.excerpts WHERE ex IS NOT NULL] END |
    MERGE (ins)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
  RETURN count(*) as ins_count
}

// Restrictions
WITH a, agreement
FOREACH (restriction IN CASE WHEN a.restrictions IS NOT NULL THEN a.restrictions ELSE [] END |
  CREATE (r:Restriction {
    restriction_type: restriction.restriction_type,
    restricted_party: restriction.restricted_party,
    description: restriction.description,
    duration: restriction.duration,
    geographic_scope: restriction.geographic_scope,
    exceptions: restriction.exceptions
  })
  MERGE (agreement)-[:HAS_RESTRICTION]->(r)
  FOREACH (excerpt IN CASE WHEN restriction.excerpts IS NULL THEN [] ELSE [ex IN restriction.excerpts WHERE ex IS NOT NULL] END |
    MERGE (r)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
)

// Change of Control
WITH a, agreement
CALL {
  WITH a, agreement
  WITH a, agreement WHERE a.change_of_control IS NOT NULL
  MERGE (agreement)-[:HAS_CHANGE_OF_CONTROL]->(coc:ChangeOfControl {
    triggers_termination: a.change_of_control.triggers_termination,
    requires_consent: a.change_of_control.requires_consent,
    notification_required: a.change_of_control.notification_required,
    affected_party: a.change_of_control.affected_party
  })
  FOREACH (excerpt IN CASE WHEN a.change_of_control.excerpts IS NULL THEN [] ELSE [ex IN a.change_of_control.excerpts WHERE ex IS NOT NULL] END |
    MERGE (coc)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
  RETURN count(*) as coc_count
}

// Force Majeure
WITH a, agreement
CALL {
  WITH a, agreement
  WITH a, agreement WHERE a.force_majeure IS NOT NULL AND a.force_majeure.exists = true
  MERGE (agreement)-[:HAS_FORCE_MAJEURE]->(fm:ForceMajeure {
    covered_events: a.force_majeure.covered_events,
    notice_period: a.force_majeure.notice_period,
    suspension_of_obligations: a.force_majeure.suspension_of_obligations,
    termination_allowed: a.force_majeure.termination_allowed,
    termination_trigger_period: a.force_majeure.termination_trigger_period
  })
  FOREACH (excerpt IN CASE WHEN a.force_majeure.excerpts IS NULL THEN [] ELSE [ex IN a.force_majeure.excerpts WHERE ex IS NOT NULL] END |
    MERGE (fm)-[:HAS_EXCERPT]->(e:Excerpt {text: excerpt})
  )
  RETURN count(*) as fm_count
}

RETURN 'ok' AS status
"""

CREATE_VECTOR_INDEX_STATEMENT = """
CREATE VECTOR INDEX excerpt_embedding IF NOT EXISTS
    FOR (e:Excerpt) ON (e.embedding)
    OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`:'cosine'}}
"""

CREATE_ENHANCED_FULL_TEXT_INDICES = [
    ("excerptTextIndex", "CREATE FULLTEXT INDEX excerptTextIndex IF NOT EXISTS FOR (e:Excerpt) ON EACH [e.text]"),
    ("agreementTypeTextIndex", "CREATE FULLTEXT INDEX agreementTypeTextIndex IF NOT EXISTS FOR (a:Agreement) ON EACH [a.agreement_type]"),
    ("organizationNameTextIndex", "CREATE FULLTEXT INDEX organizationNameTextIndex IF NOT EXISTS FOR (o:Organization) ON EACH [o.name]"),
    ("contractIdIndex","CREATE INDEX agreementContractId IF NOT EXISTS FOR (a:Agreement) ON (a.contract_id)"),
    ("liabilityCapAmountIndex", "CREATE INDEX liabilityCapAmount IF NOT EXISTS FOR (lc:LiabilityCap) ON (lc.cap_amount)"),
    ("obligationTypeIndex", "CREATE FULLTEXT INDEX obligationTypeIndex IF NOT EXISTS FOR (o:Obligation) ON EACH [o.obligation_type]"),
    ("complianceFrameworkIndex", "CREATE FULLTEXT INDEX complianceFrameworkIndex IF NOT EXISTS FOR (cf:ComplianceFramework) ON EACH [cf.framework_name]"),
]

EMBEDDINGS_STATEMENT = """
MATCH (e:Excerpt)
WHERE e.text is not null and e.embedding is null
WITH e LIMIT 100
SET e.embedding = genai.vector.encode(e.text, "OpenAI", {
                    token: $token, model: "text-embedding-3-small", dimensions: 1536
                  })
"""

def index_exists(driver, index_name):
    check_index_query = "SHOW INDEXES WHERE name = $index_name"
    result = driver.execute_query(check_index_query, {"index_name": index_name})
    return len(result.records) > 0

def create_full_text_indices(driver):
    with driver.session() as session:
        for index_name, create_query in CREATE_ENHANCED_FULL_TEXT_INDICES:
            if not index_exists(driver, index_name):
                print(f"Creating index: {index_name}")
                driver.execute_query(create_query)
            else:
                print(f"Index {index_name} already exists.")

def main():
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USERNAME', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    JSON_CONTRACT_FOLDER = Path(os.getenv('EXTRACT_OUTPUT_DIR', './data/output/'))

    if not JSON_CONTRACT_FOLDER.exists():
        print(f"Creating output directory: {JSON_CONTRACT_FOLDER}")
        JSON_CONTRACT_FOLDER.mkdir(parents=True, exist_ok=True)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    json_contracts = sorted(JSON_CONTRACT_FOLDER.glob('*.json'))

    if not json_contracts:
        print(f"No JSON files found in {JSON_CONTRACT_FOLDER}")
        print("Please run the enhanced extraction script first.")
        return

    for json_path in json_contracts:
        print(f"Processing {json_path.name}...")
        with open(json_path, 'r', encoding='utf-8') as file:
            json_data = json.load(file)

        agreement = json_data.get('agreement', {})
        contract_id = (
            json_data.get('contract_id')
            or agreement.get('contract_id')
            or json_data.get('file_name')
            or json_path.stem
        )

        if not contract_id:
            raise ValueError(f"Unable to determine contract_id for {json_path}")

        json_data['contract_id'] = contract_id
        agreement['contract_id'] = contract_id
        json_data['agreement'] = agreement

        driver.execute_query(CREATE_ENHANCED_GRAPH_STATEMENT, data=json_data)

    print("\nCreating indices...")
    create_full_text_indices(driver)
    driver.execute_query(CREATE_VECTOR_INDEX_STATEMENT)

    if OPENAI_API_KEY:
        print("\nGenerating embeddings for contract excerpts...")
        # Process in batches to avoid timeout
        while True:
            result = driver.execute_query(EMBEDDINGS_STATEMENT, token=OPENAI_API_KEY)
            if result.summary.counters.properties_set == 0:
                break
            print("  Processed batch of embeddings...")
    else:
        print("\nSkipping excerpt embeddings: OPENAI_API_KEY not configured.")

    print("\n✅ Enhanced graph creation complete!")
    driver.close()

if __name__ == '__main__':
    main()
