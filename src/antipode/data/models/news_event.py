"""
News and corporate event models for synthetic data generation.
Supports adverse media screening, M&A events, corporate actions, and clinical trials.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class EventSeverity(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    CRITICAL = "critical"


class DisclosureStatus(str, Enum):
    PRE_ANNOUNCEMENT = "pre_announcement"
    ANNOUNCED = "announced"
    RUMOR = "rumor"
    CONFIRMED = "confirmed"


class SourceCredibility(str, Enum):
    TIER1 = "tier1"      # Reuters, Bloomberg, WSJ, FT
    TIER2 = "tier2"      # Business Insider, MarketWatch
    TIER3 = "tier3"      # Blogs, local news
    REGULATORY = "regulatory"  # SEC, DOJ, FCA
    SOCIAL = "social"    # Twitter, Reddit


@dataclass
class NewsEvent:
    """Represents a news or corporate event."""
    
    event_id: str
    timestamp: datetime
    entity_id: str                      # Company or Person this relates to
    entity_type: str                    # company, person
    
    # Event classification
    event_category: str                 # See EVENT_CATEGORIES
    event_type: str                     # Specific type within category
    severity: EventSeverity = EventSeverity.NEUTRAL
    
    # Content
    headline: str = ""
    summary: str = ""
    source: str = ""
    source_credibility: SourceCredibility = SourceCredibility.TIER2
    
    # For trade surveillance (market-moving events)
    is_material: bool = False           # Could affect stock price
    disclosure_status: DisclosureStatus = DisclosureStatus.ANNOUNCED
    
    # Related entities (for M&A, etc.)
    related_entity_ids: List[str] = field(default_factory=list)
    
    # Hidden ground truth (for evaluation only)
    _is_synthetic_adverse: bool = False
    _linked_typology: Optional[str] = None
    _linked_transaction_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "event_category": self.event_category,
            "event_type": self.event_type,
            "severity": self.severity.value if isinstance(self.severity, Enum) else self.severity,
            "headline": self.headline,
            "summary": self.summary,
            "source": self.source,
            "source_credibility": self.source_credibility.value if isinstance(self.source_credibility, Enum) else self.source_credibility,
            "is_material": self.is_material,
            "disclosure_status": self.disclosure_status.value if isinstance(self.disclosure_status, Enum) else self.disclosure_status,
            "related_entity_ids": self.related_entity_ids,
        }


EVENT_CATEGORIES: Dict[str, Dict[str, Any]] = {
    "adverse_media": {
        "types": [
            "fraud_allegation",
            "corruption_investigation",
            "sanctions_violation",
            "money_laundering",
            "tax_evasion",
            "environmental_violation",
            "labor_violation",
            "data_breach",
            "executive_misconduct",
            "regulatory_action",
            "bribery",
            "embezzlement",
            "insider_trading",
            "market_manipulation",
        ],
        "severity_default": EventSeverity.NEGATIVE,
        "is_material_default": True,
    },
    "regulatory": {
        "types": [
            "sec_enforcement",
            "doj_investigation",
            "fca_action",
            "sebi_order",
            "rbi_penalty",
            "consent_order",
            "cease_desist",
            "license_revocation",
            "fine_imposed",
            "warning_letter",
        ],
        "severity_default": EventSeverity.CRITICAL,
        "is_material_default": True,
    },
    "corporate_action": {
        "types": [
            "merger_announcement",
            "acquisition_announcement",
            "spinoff",
            "stock_split",
            "dividend_declaration",
            "buyback_announcement",
            "rights_issue",
            "delisting",
            "ipo_filing",
            "secondary_offering",
        ],
        "severity_default": EventSeverity.NEUTRAL,
        "is_material_default": True,
    },
    "financial": {
        "types": [
            "earnings_announcement",
            "earnings_miss",
            "earnings_beat",
            "guidance_update",
            "guidance_lowered",
            "guidance_raised",
            "credit_rating_upgrade",
            "credit_rating_downgrade",
            "debt_default",
            "bankruptcy_filing",
            "restructuring",
            "covenant_breach",
        ],
        "severity_default": EventSeverity.NEUTRAL,
        "is_material_default": True,
    },
    "clinical_trial": {
        "types": [
            "trial_initiation",
            "trial_results_positive",
            "trial_results_negative",
            "trial_results_mixed",
            "fda_approval",
            "fda_rejection",
            "fda_complete_response",
            "trial_halt",
            "safety_concern",
            "breakthrough_designation",
            "priority_review",
        ],
        "severity_default": EventSeverity.NEUTRAL,
        "is_material_default": True,
    },
    "leadership": {
        "types": [
            "ceo_change",
            "cfo_change",
            "board_change",
            "executive_departure",
            "executive_hire",
            "executive_arrest",
            "whistleblower_complaint",
            "activist_investor",
        ],
        "severity_default": EventSeverity.NEUTRAL,
        "is_material_default": False,
    },
    "market": {
        "types": [
            "trading_halt",
            "unusual_volume",
            "price_spike",
            "price_drop",
            "short_interest_surge",
            "insider_trading_filing",
            "large_block_trade",
            "options_activity",
        ],
        "severity_default": EventSeverity.NEUTRAL,
        "is_material_default": False,
    },
    "geopolitical": {
        "types": [
            "sanctions_imposed",
            "sanctions_lifted",
            "trade_restriction",
            "political_instability",
            "regime_change",
            "war_conflict",
            "natural_disaster",
        ],
        "severity_default": EventSeverity.NEGATIVE,
        "is_material_default": True,
    },
}


NEWS_SOURCES: Dict[str, List[str]] = {
    "tier1": ["Reuters", "Bloomberg", "Wall Street Journal", "Financial Times", "CNBC"],
    "tier2": ["Business Insider", "MarketWatch", "Economic Times", "Mint", "The Hindu Business Line"],
    "tier3": ["Industry blogs", "Local news", "Trade publications", "Regional papers"],
    "regulatory": ["SEC", "DOJ", "FCA", "SEBI", "RBI", "FinCEN", "OFAC", "EU Commission"],
    "social": ["Twitter/X", "Reddit", "LinkedIn", "StockTwits"],
}


def get_event_types(category: str) -> List[str]:
    """Get all event types for a category."""
    return EVENT_CATEGORIES.get(category, {}).get("types", [])


def get_all_adverse_types() -> List[str]:
    """Get all adverse media event types."""
    return EVENT_CATEGORIES["adverse_media"]["types"]
