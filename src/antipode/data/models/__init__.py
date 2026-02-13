"""
Data models for AML/KYC compliance systems.

This package contains pure data classes (dataclasses) only.
Generation logic is in the 'generators' package.
"""

from .entity import (
    Customer, Company, Counterparty, Address, Identifier,
    EntityType, CustomerSegment, CompanyType, CompanyStatus,
    PEPType, PEPStatus, RiskRating,
)
from .news_event import NewsEvent, EVENT_CATEGORIES, NEWS_SOURCES, EventSeverity, DisclosureStatus, SourceCredibility
from .alert import Alert, AlertRiskLevel, AlertStatus, Case, DispositionReason, ALERT_DISTRIBUTION
from .transaction import Transaction, TransactionType, TransactionDirection, TransactionChannel
from .account import Account, AccountType, AccountStatus

__all__ = [
    # Entities
    "Customer",
    "Company",
    "Counterparty",
    "Address",
    "Identifier",
    "EntityType",
    "CustomerSegment",
    "CompanyType",
    "CompanyStatus",
    "PEPType",
    "PEPStatus",
    "RiskRating",
    # News events
    "NewsEvent",
    "EVENT_CATEGORIES",
    "NEWS_SOURCES",
    "EventSeverity",
    "DisclosureStatus",
    "SourceCredibility",
    # Alerts
    "Alert",
    "AlertRiskLevel",
    "AlertStatus",
    "Case",
    "DispositionReason",
    "ALERT_DISTRIBUTION",
    # Transactions
    "Transaction",
    "TransactionType",
    "TransactionDirection",
    "TransactionChannel",
    # Accounts
    "Account",
    "AccountType",
    "AccountStatus",
]
