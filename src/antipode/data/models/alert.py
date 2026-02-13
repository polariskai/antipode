"""
Alert model for synthetic data generation.
Supports realistic alert distribution with risk levels.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class AlertRiskLevel(str, Enum):
    """Alert risk levels with target distribution."""
    LOW = "low"           # ~70% of alerts
    MEDIUM = "medium"     # ~20% of alerts
    HIGH = "high"         # ~8% of alerts
    CRITICAL = "critical" # ~1-2% of alerts (SAR-able)


class AlertStatus(str, Enum):
    """Alert lifecycle status."""
    NEW = "new"
    IN_REVIEW = "in_review"
    ESCALATED = "escalated"
    CLOSED_NO_ISSUE = "closed_no_issue"
    CLOSED_MONITORED = "closed_monitored"
    SAR_FILED = "sar_filed"


class DispositionReason(str, Enum):
    """Reason for alert disposition."""
    FALSE_POSITIVE = "false_positive"
    NORMAL_BUSINESS = "normal_business"
    INSUFFICIENT_INFO = "insufficient_info"
    CUSTOMER_EXPLAINED = "customer_explained"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CONFIRMED_FRAUD = "confirmed_fraud"
    REGULATORY_REQUIREMENT = "regulatory_requirement"


# Target distribution for alert generation
ALERT_DISTRIBUTION = {
    AlertRiskLevel.LOW: 0.70,
    AlertRiskLevel.MEDIUM: 0.20,
    AlertRiskLevel.HIGH: 0.08,
    AlertRiskLevel.CRITICAL: 0.02,
}


@dataclass
class Alert:
    """Represents an AML/compliance alert."""
    
    alert_id: str
    created_ts: datetime
    rule_id: str
    rule_name: str
    account_id: str
    customer_id: str
    
    # Alert scoring
    risk_level: AlertRiskLevel = AlertRiskLevel.LOW
    score: float = 0.0                  # 0-100 confidence
    risk_factors: List[str] = field(default_factory=list)
    
    # Triggering information
    transaction_ids: List[str] = field(default_factory=list)
    triggering_signals: Dict[str, float] = field(default_factory=dict)
    
    # Alert details
    alert_type: str = ""                # structuring, rapid_movement, etc.
    description: str = ""
    amount_involved: float = 0.0
    currency: str = "USD"
    
    # Temporal context
    lookback_start: Optional[datetime] = None
    lookback_end: Optional[datetime] = None
    
    # Case linkage
    case_id: Optional[str] = None
    status: AlertStatus = AlertStatus.NEW
    disposition: Optional[DispositionReason] = None
    disposition_ts: Optional[datetime] = None
    analyst_id: Optional[str] = None
    
    # Hidden ground truth (for evaluation only)
    _true_positive: Optional[bool] = None
    _scenario_id: Optional[str] = None
    _typology: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "created_ts": self.created_ts.isoformat() if self.created_ts else None,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "account_id": self.account_id,
            "customer_id": self.customer_id,
            "risk_level": self.risk_level.value if isinstance(self.risk_level, Enum) else self.risk_level,
            "score": self.score,
            "risk_factors": self.risk_factors,
            "transaction_ids": self.transaction_ids,
            "triggering_signals": self.triggering_signals,
            "alert_type": self.alert_type,
            "description": self.description,
            "amount_involved": self.amount_involved,
            "currency": self.currency,
            "lookback_start": self.lookback_start.isoformat() if self.lookback_start else None,
            "lookback_end": self.lookback_end.isoformat() if self.lookback_end else None,
            "case_id": self.case_id,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "disposition": self.disposition.value if self.disposition else None,
            "disposition_ts": self.disposition_ts.isoformat() if self.disposition_ts else None,
            "analyst_id": self.analyst_id,
        }
    
    @property
    def is_sar_able(self) -> bool:
        """Check if alert is SAR-able (critical risk)."""
        return self.risk_level == AlertRiskLevel.CRITICAL
    
    @property
    def is_closed(self) -> bool:
        """Check if alert is closed."""
        return self.status in [
            AlertStatus.CLOSED_NO_ISSUE,
            AlertStatus.CLOSED_MONITORED,
            AlertStatus.SAR_FILED,
        ]


@dataclass
class Case:
    """Represents an investigation case (aggregates alerts)."""
    
    case_id: str
    created_ts: datetime
    alert_ids: List[str] = field(default_factory=list)
    customer_id: str = ""
    
    # Case details
    case_type: str = ""                 # aml, fraud, sanctions, etc.
    priority: str = "medium"            # low, medium, high, critical
    assigned_analyst: Optional[str] = None
    
    # Status
    status: str = "open"                # open, in_progress, escalated, closed
    disposition: Optional[str] = None
    disposition_ts: Optional[datetime] = None
    sar_filed: bool = False
    sar_id: Optional[str] = None
    
    # Investigation notes
    notes: List[Dict[str, Any]] = field(default_factory=list)
    
    # Hidden ground truth
    _true_positive: Optional[bool] = None
    _scenario_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "case_id": self.case_id,
            "created_ts": self.created_ts.isoformat() if self.created_ts else None,
            "alert_ids": self.alert_ids,
            "customer_id": self.customer_id,
            "case_type": self.case_type,
            "priority": self.priority,
            "assigned_analyst": self.assigned_analyst,
            "status": self.status,
            "disposition": self.disposition,
            "disposition_ts": self.disposition_ts.isoformat() if self.disposition_ts else None,
            "sar_filed": self.sar_filed,
            "sar_id": self.sar_id,
            "notes": self.notes,
        }
