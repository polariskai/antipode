"""
Entity models for AML/KYC compliance systems.

Defines Customer (individual) and Company entity dataclasses with:
- KYC fields (declared information)
- Risk indicators (PEP, sanctions, adverse media flags)
- Identification documents
- NO derived signals (those are computed separately)
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Dict, Any
from enum import Enum


class EntityType(str, Enum):
    """Entity type classification."""
    PERSON = "person"
    COMPANY = "company"


class CustomerSegment(str, Enum):
    """Customer segment classification."""
    RETAIL = "retail"
    HNW = "hnw"  # High Net Worth
    SMB = "smb"  # Small/Medium Business
    CORPORATE = "corporate"
    CORRESPONDENT = "correspondent"
    PEP = "pep"  # Politically Exposed Person
    NGO = "ngo"  # Non-Governmental Organization
    MSB = "msb"  # Money Services Business


class PEPType(str, Enum):
    """PEP classification type."""
    NONE = "none"
    DOMESTIC = "domestic"
    FOREIGN = "foreign"
    INTERNATIONAL_ORG = "international_org"
    FAMILY_MEMBER = "family_member"
    CLOSE_ASSOCIATE = "close_associate"


class PEPStatus(str, Enum):
    """PEP status."""
    NOT_PEP = "not_pep"
    CURRENT = "current"
    FORMER = "former"


class RiskRating(str, Enum):
    """Entity risk rating."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CompanyType(str, Enum):
    """Company classification."""
    PUBLIC = "public"
    PRIVATE = "private"
    SMB = "smb"
    CORPORATE = "corporate"
    NGO = "ngo"
    MSB = "msb"
    SHELL = "shell"
    SPV = "spv"  # Special Purpose Vehicle


class CompanyStatus(str, Enum):
    """Company operational status."""
    ACTIVE = "active"
    DORMANT = "dormant"
    DISSOLVED = "dissolved"
    SUSPENDED = "suspended"
    LIQUIDATION = "liquidation"


@dataclass
class Identifier:
    """Identity document or identifier."""
    id_type: str  # passport, ssn, drivers_license, tax_id, etc.
    id_number: str
    issuing_country: str = ""
    issue_date: Optional[date] = None
    expiry_date: Optional[date] = None
    verified: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id_type": self.id_type,
            "id_number": self.id_number,
            "issuing_country": self.issuing_country,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "verified": self.verified,
        }


@dataclass
class Address:
    """Physical or mailing address."""
    address_type: str = "residential"  # residential, business, registered, mailing
    street_line1: str = ""
    street_line2: str = ""
    city: str = ""
    state_province: str = ""
    postal_code: str = ""
    country: str = ""
    is_primary: bool = True
    
    # Risk indicators
    is_virtual_office: bool = False
    is_mail_forwarding: bool = False
    is_registered_agent: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "address_type": self.address_type,
            "street_line1": self.street_line1,
            "street_line2": self.street_line2,
            "city": self.city,
            "state_province": self.state_province,
            "postal_code": self.postal_code,
            "country": self.country,
            "is_primary": self.is_primary,
            "is_virtual_office": self.is_virtual_office,
            "is_mail_forwarding": self.is_mail_forwarding,
            "is_registered_agent": self.is_registered_agent,
        }
    
    @property
    def full_address(self) -> str:
        """Format as single-line address."""
        parts = [self.street_line1]
        if self.street_line2:
            parts.append(self.street_line2)
        parts.extend([self.city, self.state_province, self.postal_code, self.country])
        return ", ".join(p for p in parts if p)


@dataclass
class Customer:
    """
    Individual customer entity.
    
    Contains KYC-declared information only.
    Derived signals (expected volume, behavior patterns) are NOT stored here.
    """
    
    # Core identifiers
    customer_id: str
    entity_type: EntityType = EntityType.PERSON
    
    # Personal information
    first_name: str = ""
    last_name: str = ""
    middle_name: str = ""
    date_of_birth: Optional[date] = None
    gender: str = ""
    
    # Nationality and residence
    nationality: str = ""
    country_of_residence: str = ""
    tax_residency: str = ""
    
    # Contact
    email: str = ""
    phone: str = ""
    mobile: str = ""
    
    # Address
    addresses: List[Address] = field(default_factory=list)
    
    # Identification documents
    identifiers: List[Identifier] = field(default_factory=list)
    
    # Employment / Source of funds
    occupation: str = ""
    employer_name: str = ""
    employer_industry: str = ""
    employment_status: str = ""  # employed, self_employed, retired, student, unemployed
    
    # Financial profile (KYC-declared, NOT actual behavior)
    declared_annual_income: float = 0.0
    declared_net_worth: float = 0.0
    declared_source_of_wealth: str = ""  # employment, business, inheritance, investments, etc.
    declared_source_of_funds: str = ""
    
    # Segment classification
    segment: CustomerSegment = CustomerSegment.RETAIL
    
    # PEP status
    is_pep: bool = False
    pep_type: PEPType = PEPType.NONE
    pep_status: PEPStatus = PEPStatus.NOT_PEP
    pep_position: str = ""  # Government Minister, Judge, etc.
    pep_country: str = ""
    
    # Sanctions and watchlist
    is_sanctioned: bool = False
    sanctions_program: str = ""  # OFAC SDN, EU Sanctions, etc.
    watchlist_matches: List[str] = field(default_factory=list)
    
    # Adverse media
    has_adverse_media: bool = False
    adverse_media_categories: List[str] = field(default_factory=list)
    
    # Risk rating (assigned by compliance)
    risk_rating: RiskRating = RiskRating.LOW
    risk_factors: List[str] = field(default_factory=list)
    
    # Lifecycle
    onboarding_date: Optional[date] = None
    kyc_date: Optional[date] = None
    kyc_refresh_date: Optional[date] = None
    status: str = "active"  # active, dormant, suspended, closed
    
    # Relationships
    related_parties: List[str] = field(default_factory=list)  # IDs of related customers
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "customer_id": self.customer_id,
            "entity_type": self.entity_type.value,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "middle_name": self.middle_name,
            "full_name": self.full_name,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "gender": self.gender,
            "nationality": self.nationality,
            "country_of_residence": self.country_of_residence,
            "tax_residency": self.tax_residency,
            "email": self.email,
            "phone": self.phone,
            "mobile": self.mobile,
            "addresses": [a.to_dict() for a in self.addresses],
            "identifiers": [i.to_dict() for i in self.identifiers],
            "occupation": self.occupation,
            "employer_name": self.employer_name,
            "employer_industry": self.employer_industry,
            "employment_status": self.employment_status,
            "declared_annual_income": self.declared_annual_income,
            "declared_net_worth": self.declared_net_worth,
            "declared_source_of_wealth": self.declared_source_of_wealth,
            "declared_source_of_funds": self.declared_source_of_funds,
            "segment": self.segment.value,
            "is_pep": self.is_pep,
            "pep_type": self.pep_type.value if self.is_pep else None,
            "pep_status": self.pep_status.value if self.is_pep else None,
            "pep_position": self.pep_position if self.is_pep else None,
            "pep_country": self.pep_country if self.is_pep else None,
            "is_sanctioned": self.is_sanctioned,
            "sanctions_program": self.sanctions_program if self.is_sanctioned else None,
            "watchlist_matches": self.watchlist_matches,
            "has_adverse_media": self.has_adverse_media,
            "adverse_media_categories": self.adverse_media_categories,
            "risk_rating": self.risk_rating.value,
            "risk_factors": self.risk_factors,
            "onboarding_date": self.onboarding_date.isoformat() if self.onboarding_date else None,
            "kyc_date": self.kyc_date.isoformat() if self.kyc_date else None,
            "kyc_refresh_date": self.kyc_refresh_date.isoformat() if self.kyc_refresh_date else None,
            "status": self.status,
            "related_parties": self.related_parties,
        }
    
    @property
    def full_name(self) -> str:
        """Full name combining first, middle, last."""
        parts = [self.first_name, self.middle_name, self.last_name]
        return " ".join(p for p in parts if p)
    
    @property
    def primary_address(self) -> Optional[Address]:
        """Get primary address."""
        for addr in self.addresses:
            if addr.is_primary:
                return addr
        return self.addresses[0] if self.addresses else None
    
    @property
    def is_high_risk(self) -> bool:
        """Check if customer is high risk."""
        return self.risk_rating in [RiskRating.HIGH, RiskRating.CRITICAL]


@dataclass
class Company:
    """
    Company/corporate entity.
    
    Contains KYC-declared information and corporate structure.
    Derived signals are NOT stored here.
    """
    
    # Core identifiers
    company_id: str
    entity_type: EntityType = EntityType.COMPANY
    
    # Company information
    legal_name: str = ""
    trading_name: str = ""
    former_names: List[str] = field(default_factory=list)
    
    # Registration
    registration_number: str = ""
    tax_id: str = ""
    lei: str = ""  # Legal Entity Identifier
    
    # Incorporation
    country_of_incorporation: str = ""
    state_of_incorporation: str = ""
    incorporation_date: Optional[date] = None
    
    # Operations
    country_of_operation: str = ""
    operating_countries: List[str] = field(default_factory=list)
    
    # Classification
    company_type: CompanyType = CompanyType.PRIVATE
    industry: str = ""
    industry_code: str = ""  # SIC/NAICS code
    
    # Size indicators
    employee_count: int = 0
    annual_revenue: float = 0.0
    total_assets: float = 0.0
    
    # Public company info
    is_publicly_traded: bool = False
    stock_exchange: str = ""
    stock_symbol: str = ""
    
    # Contact
    website: str = ""
    email: str = ""
    phone: str = ""
    
    # Addresses
    addresses: List[Address] = field(default_factory=list)
    
    # Identifiers
    identifiers: List[Identifier] = field(default_factory=list)
    
    # Ownership structure
    ultimate_beneficial_owners: List[str] = field(default_factory=list)  # Customer IDs
    parent_company_id: str = ""
    subsidiary_ids: List[str] = field(default_factory=list)
    
    # Officers and directors
    officers: List[Dict[str, Any]] = field(default_factory=list)
    directors: List[Dict[str, Any]] = field(default_factory=list)
    
    # Risk indicators
    is_shell_company: bool = False
    is_offshore: bool = False
    in_high_risk_jurisdiction: bool = False
    
    # Sanctions and watchlist
    is_sanctioned: bool = False
    sanctions_program: str = ""
    watchlist_matches: List[str] = field(default_factory=list)
    
    # Adverse media
    has_adverse_media: bool = False
    adverse_media_categories: List[str] = field(default_factory=list)
    regulatory_actions: List[Dict[str, Any]] = field(default_factory=list)
    
    # Risk rating
    risk_rating: RiskRating = RiskRating.LOW
    risk_factors: List[str] = field(default_factory=list)
    
    # Lifecycle
    onboarding_date: Optional[date] = None
    kyc_date: Optional[date] = None
    kyc_refresh_date: Optional[date] = None
    status: CompanyStatus = CompanyStatus.ACTIVE
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "company_id": self.company_id,
            "entity_type": self.entity_type.value,
            "legal_name": self.legal_name,
            "trading_name": self.trading_name,
            "former_names": self.former_names,
            "registration_number": self.registration_number,
            "tax_id": self.tax_id,
            "lei": self.lei,
            "country_of_incorporation": self.country_of_incorporation,
            "state_of_incorporation": self.state_of_incorporation,
            "incorporation_date": self.incorporation_date.isoformat() if self.incorporation_date else None,
            "country_of_operation": self.country_of_operation,
            "operating_countries": self.operating_countries,
            "company_type": self.company_type.value,
            "industry": self.industry,
            "industry_code": self.industry_code,
            "employee_count": self.employee_count,
            "annual_revenue": self.annual_revenue,
            "total_assets": self.total_assets,
            "is_publicly_traded": self.is_publicly_traded,
            "stock_exchange": self.stock_exchange if self.is_publicly_traded else None,
            "stock_symbol": self.stock_symbol if self.is_publicly_traded else None,
            "website": self.website,
            "email": self.email,
            "phone": self.phone,
            "addresses": [a.to_dict() for a in self.addresses],
            "identifiers": [i.to_dict() for i in self.identifiers],
            "ultimate_beneficial_owners": self.ultimate_beneficial_owners,
            "parent_company_id": self.parent_company_id,
            "subsidiary_ids": self.subsidiary_ids,
            "officers": self.officers,
            "directors": self.directors,
            "is_shell_company": self.is_shell_company,
            "is_offshore": self.is_offshore,
            "in_high_risk_jurisdiction": self.in_high_risk_jurisdiction,
            "is_sanctioned": self.is_sanctioned,
            "sanctions_program": self.sanctions_program if self.is_sanctioned else None,
            "watchlist_matches": self.watchlist_matches,
            "has_adverse_media": self.has_adverse_media,
            "adverse_media_categories": self.adverse_media_categories,
            "regulatory_actions": self.regulatory_actions,
            "risk_rating": self.risk_rating.value,
            "risk_factors": self.risk_factors,
            "onboarding_date": self.onboarding_date.isoformat() if self.onboarding_date else None,
            "kyc_date": self.kyc_date.isoformat() if self.kyc_date else None,
            "kyc_refresh_date": self.kyc_refresh_date.isoformat() if self.kyc_refresh_date else None,
            "status": self.status.value,
        }
    
    @property
    def name(self) -> str:
        """Primary name (trading name or legal name)."""
        return self.trading_name or self.legal_name
    
    @property
    def registered_address(self) -> Optional[Address]:
        """Get registered office address."""
        for addr in self.addresses:
            if addr.address_type == "registered":
                return addr
        return self.addresses[0] if self.addresses else None
    
    @property
    def is_high_risk(self) -> bool:
        """Check if company is high risk."""
        return (
            self.risk_rating in [RiskRating.HIGH, RiskRating.CRITICAL]
            or self.is_shell_company
            or self.is_offshore
            or self.in_high_risk_jurisdiction
        )


@dataclass 
class Counterparty:
    """
    External counterparty (not a direct customer).
    
    Represents entities that customers transact with but are not
    directly onboarded as customers.
    """
    
    counterparty_id: str
    entity_type: EntityType = EntityType.PERSON
    
    # Basic info
    name: str = ""
    country: str = ""
    
    # Bank details (for wire transfers)
    bank_name: str = ""
    bank_country: str = ""
    bank_swift: str = ""
    account_number: str = ""
    
    # Risk indicators
    is_high_risk_jurisdiction: bool = False
    risk_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "counterparty_id": self.counterparty_id,
            "entity_type": self.entity_type.value,
            "name": self.name,
            "country": self.country,
            "bank_name": self.bank_name,
            "bank_country": self.bank_country,
            "bank_swift": self.bank_swift,
            "account_number": self.account_number,
            "is_high_risk_jurisdiction": self.is_high_risk_jurisdiction,
            "risk_score": self.risk_score,
        }
