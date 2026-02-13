"""
Account model for synthetic data generation.
Raw account data without derived signals (expected_volume, corridors are NOT stored here).
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


class AccountStatus(str, Enum):
    """Account status."""
    ACTIVE = "active"
    DORMANT = "dormant"
    SUSPENDED = "suspended"
    CLOSED = "closed"
    PENDING = "pending"


class AccountType(str, Enum):
    """Account product types."""
    CHECKING = "checking"
    SAVINGS = "savings"
    MONEY_MARKET = "money_market"
    BUSINESS_CHECKING = "business_checking"
    BUSINESS_SAVINGS = "business_savings"
    TREASURY = "treasury"
    BROKERAGE = "brokerage"
    LOAN = "loan"
    CREDIT_CARD = "credit_card"
    NOSTRO = "nostro"
    VOSTRO = "vostro"


@dataclass
class Account:
    """
    Represents a bank account.
    
    Note: expected_monthly_volume and expected_corridors are NOT stored here.
    Those are derived signals computed from transaction history by analysis models.
    Only KYC-declared values are stored on the raw account.
    """
    
    account_id: str
    customer_id: str
    
    # Account details
    product_type: AccountType = AccountType.CHECKING
    currency: str = "USD"
    country: str = "US"
    branch: str = ""
    
    # Lifecycle
    open_date: Optional[date] = None
    close_date: Optional[date] = None
    status: AccountStatus = AccountStatus.ACTIVE
    
    # Channel profile (how customer typically transacts)
    channel_profile: Dict[str, float] = field(default_factory=dict)
    
    # KYC-declared fields (from onboarding - may differ from actual behavior)
    declared_segment: str = "retail"
    declared_monthly_turnover: float = 0.0
    declared_purpose: str = ""
    declared_source_of_funds: str = ""
    
    # Risk flags (from KYC/onboarding)
    is_pep: bool = False
    is_high_risk: bool = False
    kyc_date: Optional[date] = None
    next_review_date: Optional[date] = None
    
    # Metadata
    source_system: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "account_id": self.account_id,
            "customer_id": self.customer_id,
            "product_type": self.product_type.value if isinstance(self.product_type, Enum) else self.product_type,
            "currency": self.currency,
            "country": self.country,
            "branch": self.branch,
            "open_date": self.open_date.isoformat() if self.open_date else None,
            "close_date": self.close_date.isoformat() if self.close_date else None,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "channel_profile": self.channel_profile,
            "declared_segment": self.declared_segment,
            "declared_monthly_turnover": self.declared_monthly_turnover,
            "declared_purpose": self.declared_purpose,
            "declared_source_of_funds": self.declared_source_of_funds,
            "is_pep": self.is_pep,
            "is_high_risk": self.is_high_risk,
            "kyc_date": self.kyc_date.isoformat() if self.kyc_date else None,
            "next_review_date": self.next_review_date.isoformat() if self.next_review_date else None,
            "source_system": self.source_system,
        }
    
    @property
    def is_active(self) -> bool:
        """Check if account is active."""
        return self.status == AccountStatus.ACTIVE
    
    @property
    def account_age_days(self) -> int:
        """Get account age in days."""
        if not self.open_date:
            return 0
        return (date.today() - self.open_date).days
    
    @property
    def kyc_age_days(self) -> int:
        """Get days since last KYC review."""
        if not self.kyc_date:
            return 999  # Unknown, treat as stale
        return (date.today() - self.kyc_date).days
