"""
Transaction model for synthetic data generation.
Raw transaction events without derived signals.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class TransactionType(str, Enum):
    """Transaction types."""
    WIRE = "wire"
    ACH = "ach"
    CASH_DEPOSIT = "cash_deposit"
    CASH_WITHDRAWAL = "cash_withdrawal"
    CHECK = "check"
    CARD = "card"
    INTERNAL_TRANSFER = "internal_transfer"
    FX = "fx"
    SECURITIES_TRADE = "securities_trade"
    LOAN_PAYMENT = "loan_payment"
    PAYROLL = "payroll"
    REMITTANCE = "remittance"


class TransactionDirection(str, Enum):
    """Transaction direction."""
    CREDIT = "credit"   # Incoming
    DEBIT = "debit"     # Outgoing


class TransactionChannel(str, Enum):
    """Transaction channel."""
    ONLINE = "online"
    MOBILE = "mobile"
    BRANCH = "branch"
    ATM = "atm"
    API = "api"
    SWIFT = "swift"
    PHONE = "phone"


@dataclass
class Transaction:
    """Represents a raw financial transaction."""
    
    txn_id: str
    timestamp: datetime
    
    # Amount
    amount: float
    currency: str = "USD"
    amount_usd: Optional[float] = None  # Normalized to USD
    
    # Transaction details
    txn_type: TransactionType = TransactionType.WIRE
    direction: TransactionDirection = TransactionDirection.DEBIT
    channel: TransactionChannel = TransactionChannel.ONLINE
    
    # Accounts
    from_account_id: Optional[str] = None
    to_account_id: Optional[str] = None
    
    # Counterparty (raw, as received)
    counterparty_id: Optional[str] = None
    originator_name_raw: str = ""
    beneficiary_name_raw: str = ""
    
    # Geography
    orig_country: str = ""
    orig_city: str = ""
    dest_country: str = ""
    dest_city: str = ""
    
    # Reference data
    reference: str = ""
    purpose: str = ""
    memo: str = ""
    
    # Metadata
    batch_id: Optional[str] = None
    source_system: str = ""
    
    # Hidden ground truth (for evaluation only)
    _is_suspicious: bool = False
    _typology: Optional[str] = None
    _scenario_id: Optional[str] = None
    _linked_event_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excludes hidden fields)."""
        return {
            "txn_id": self.txn_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "amount": self.amount,
            "currency": self.currency,
            "amount_usd": self.amount_usd,
            "txn_type": self.txn_type.value if isinstance(self.txn_type, Enum) else self.txn_type,
            "direction": self.direction.value if isinstance(self.direction, Enum) else self.direction,
            "channel": self.channel.value if isinstance(self.channel, Enum) else self.channel,
            "from_account_id": self.from_account_id,
            "to_account_id": self.to_account_id,
            "counterparty_id": self.counterparty_id,
            "originator_name_raw": self.originator_name_raw,
            "beneficiary_name_raw": self.beneficiary_name_raw,
            "orig_country": self.orig_country,
            "orig_city": self.orig_city,
            "dest_country": self.dest_country,
            "dest_city": self.dest_city,
            "reference": self.reference,
            "purpose": self.purpose,
            "memo": self.memo,
            "batch_id": self.batch_id,
            "source_system": self.source_system,
        }
    
    def to_dict_with_labels(self) -> Dict[str, Any]:
        """Convert to dictionary including hidden labels (for training data)."""
        d = self.to_dict()
        d["_is_suspicious"] = self._is_suspicious
        d["_typology"] = self._typology
        d["_scenario_id"] = self._scenario_id
        d["_linked_event_id"] = self._linked_event_id
        return d
    
    @property
    def is_cross_border(self) -> bool:
        """Check if transaction crosses borders."""
        return self.orig_country != self.dest_country and self.orig_country and self.dest_country
    
    @property
    def is_cash(self) -> bool:
        """Check if transaction involves cash."""
        return self.txn_type in [TransactionType.CASH_DEPOSIT, TransactionType.CASH_WITHDRAWAL]
