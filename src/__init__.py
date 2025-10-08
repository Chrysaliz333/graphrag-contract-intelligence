"""
GraphRAG Contract Intelligence

A comprehensive contract extraction and analysis system using GraphRAG.
"""

__version__ = "1.0.0"

from .schema import (
    Agreement,
    LiabilityCap,
    Obligation,
    ComplianceFramework,
    IntellectualProperty
)

from .service import ContractSearchServiceEnhanced
from .client_validator import ClientKGManagerEnhanced, ClientStandards

__all__ = [
    'Agreement',
    'LiabilityCap',
    'Obligation',
    'ComplianceFramework',
    'IntellectualProperty',
    'ClientStandards',
    'ContractSearchServiceEnhanced',
    'ClientKGManagerEnhanced',
]
