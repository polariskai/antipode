"""
Alert Packager - builds rich alert packages for TMS output.

An AlertPackage contains everything an analyst (or AML agent) would see
when opening an alert from the transaction monitoring system queue.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from collections import Counter, defaultdict

from .narrative_templates import generate_alert_narrative


def _safe_float(value, default=0.0):
    """Safely convert a value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass
class AlertPackage:
    """
    Rich alert package as output by a Tier 1 bank's TMS.

    This is the primary input for the AML detection agent swarm.
    Contains all information an analyst would see when opening an alert,
    but does NOT contain the resolution (that's in ground_truth).
    """

    # === Alert Header ===
    alert_id: str
    created_at: str  # ISO format
    alert_type: str
    rule_id: str
    rule_name: str
    risk_level: str  # LOW / MEDIUM / HIGH / CRITICAL
    score: float  # 0-100
    status: str  # NEW

    # === Auto-generated Narrative ===
    narrative: str

    # === Subject of Alert ===
    customer_summary: Dict[str, Any]
    account_summary: Dict[str, Any]

    # === Triggering Evidence ===
    triggering_transactions: List[Dict[str, Any]]
    risk_factors: List[str]
    triggering_signals: Dict[str, float]

    # === Context for Investigation ===
    account_activity_summary: Dict[str, Any]
    recent_transactions: List[Dict[str, Any]]
    counterparty_summary: List[Dict[str, Any]]

    # === Historical Context ===
    prior_alerts: List[Dict[str, Any]] = field(default_factory=list)

    # === Metadata ===
    lookback_start: str = ""  # ISO date
    lookback_end: str = ""  # ISO date
    amount_involved: float = 0.0
    currency: str = "USD"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "alert_id": self.alert_id,
            "created_at": self.created_at,
            "alert_type": self.alert_type,
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "risk_level": self.risk_level,
            "score": self.score,
            "status": self.status,
            "narrative": self.narrative,
            "customer_summary": self.customer_summary,
            "account_summary": self.account_summary,
            "triggering_transactions": self.triggering_transactions,
            "risk_factors": self.risk_factors,
            "triggering_signals": self.triggering_signals,
            "account_activity_summary": self.account_activity_summary,
            "recent_transactions": self.recent_transactions,
            "counterparty_summary": self.counterparty_summary,
            "prior_alerts": self.prior_alerts,
            "lookback_start": self.lookback_start,
            "lookback_end": self.lookback_end,
            "amount_involved": self.amount_involved,
            "currency": self.currency,
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Compact summary for alert index."""
        return {
            "alert_id": self.alert_id,
            "created_at": self.created_at,
            "alert_type": self.alert_type,
            "rule_id": self.rule_id,
            "risk_level": self.risk_level,
            "score": round(self.score, 1),
            "customer_name": self.customer_summary.get("name", "Unknown"),
            "customer_id": self.customer_summary.get("customer_id", ""),
            "account_id": self.account_summary.get("account_id", ""),
            "amount_involved": round(self.amount_involved, 2),
            "txn_count": len(self.triggering_transactions),
            "status": self.status,
        }


class AlertPackager:
    """
    Builds AlertPackage instances from raw alert data + bank records.

    Takes the output of AlertRulesEngine and enriches it with full
    customer/account/transaction context to create investigation-ready
    alert packages.
    """

    def __init__(self, lookback_days: int = 30):
        self.lookback_days = lookback_days

    def package_alert(
        self,
        alert: Dict[str, Any],
        entity: Optional[Dict[str, Any]],
        account: Optional[Dict[str, Any]],
        all_transactions: List[Dict[str, Any]],
        signals: Optional[Dict[str, Any]] = None,
        prior_alerts: Optional[List[Dict[str, Any]]] = None,
    ) -> AlertPackage:
        """
        Build a rich AlertPackage from raw alert and bank data.

        Args:
            alert: Raw alert dict from AlertRulesEngine
            entity: Customer/entity record
            account: Account record
            all_transactions: All transactions for this account
            signals: Computed signals for this account
            prior_alerts: Historical alerts for this customer/account

        Returns:
            Rich AlertPackage ready for agent consumption
        """
        alert_type = alert.get("alert_type", "unknown")
        account_id = alert.get("account_id", "")
        customer_name = (entity or {}).get("name", "Unknown Customer")

        # Determine lookback window
        created_at = alert.get("created_ts", datetime.now().isoformat())
        if isinstance(created_at, datetime):
            lookback_end = created_at.date()
        elif isinstance(created_at, str):
            try:
                lookback_end = datetime.fromisoformat(created_at).date()
            except ValueError:
                lookback_end = date.today()
        else:
            lookback_end = date.today()
        lookback_start = lookback_end - timedelta(days=self.lookback_days)

        # Get account transactions
        acct_txns = self._get_account_transactions(all_transactions, account_id)

        # Get recent transactions (within lookback)
        recent_txns = self._filter_by_date(acct_txns, lookback_start, lookback_end)

        # Get triggering transactions
        triggering_txn_ids = alert.get("transaction_ids", [])
        triggering_txns = [
            self._sanitize_transaction(t)
            for t in acct_txns
            if t.get("txn_id") in triggering_txn_ids
        ]

        # Calculate amount involved
        if triggering_txns:
            amount_involved = sum(t.get("amount", 0) for t in triggering_txns)
        else:
            amount_involved = sum(t.get("amount", 0) for t in recent_txns)

        # Build customer summary
        customer_summary = self._summarize_customer(entity)

        # Build account summary
        account_summary = self._summarize_account(account)

        # Build activity summary
        activity_summary = self._get_activity_summary(acct_txns, lookback_start, lookback_end)

        # Build counterparty summary
        counterparty_summary = self._get_counterparty_summary(recent_txns)

        # Sanitize recent transactions for output (limit to 50)
        recent_txns_output = [self._sanitize_transaction(t) for t in recent_txns[:50]]

        # Generate narrative
        narrative_data = self._build_narrative_data(
            alert=alert,
            customer_name=customer_name,
            entity=entity,
            account=account,
            signals=signals or {},
            triggering_txns=triggering_txns,
            recent_txns=recent_txns,
            activity_summary=activity_summary,
        )
        narrative = generate_alert_narrative(alert_type, narrative_data)

        # Format prior alerts
        formatted_prior = []
        if prior_alerts:
            for pa in prior_alerts:
                formatted_prior.append({
                    "alert_id": pa.get("alert_id"),
                    "created_at": str(pa.get("created_ts", "")),
                    "alert_type": pa.get("alert_type"),
                    "risk_level": pa.get("risk_level"),
                    "status": pa.get("status", "CLOSED_NO_ISSUE"),
                    "disposition": pa.get("disposition", "FALSE_POSITIVE"),
                })

        return AlertPackage(
            alert_id=alert.get("alert_id", ""),
            created_at=str(created_at),
            alert_type=alert_type,
            rule_id=alert.get("rule_id", ""),
            rule_name=alert.get("rule_name", ""),
            risk_level=alert.get("risk_level", "LOW"),
            score=alert.get("score", 0.0),
            status="NEW",
            narrative=narrative,
            customer_summary=customer_summary,
            account_summary=account_summary,
            triggering_transactions=triggering_txns,
            risk_factors=alert.get("risk_factors", []),
            triggering_signals=alert.get("triggering_signals", {}),
            account_activity_summary=activity_summary,
            recent_transactions=recent_txns_output,
            counterparty_summary=counterparty_summary,
            prior_alerts=formatted_prior,
            lookback_start=str(lookback_start),
            lookback_end=str(lookback_end),
            amount_involved=round(amount_involved, 2),
            currency="USD",
        )

    def _get_account_transactions(
        self,
        all_transactions: List[Dict[str, Any]],
        account_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all transactions for a specific account."""
        return [
            t for t in all_transactions
            if t.get("account_id") == account_id
            or t.get("from_account_id") == account_id
            or t.get("to_account_id") == account_id
        ]

    def _filter_by_date(
        self,
        transactions: List[Dict[str, Any]],
        start: date,
        end: date,
    ) -> List[Dict[str, Any]]:
        """Filter transactions by date range."""
        result = []
        for t in transactions:
            ts = t.get("timestamp", "")
            if isinstance(ts, str):
                try:
                    txn_date = datetime.fromisoformat(ts).date()
                except ValueError:
                    continue
            elif isinstance(ts, datetime):
                txn_date = ts.date()
            elif isinstance(ts, date):
                txn_date = ts
            else:
                continue

            if start <= txn_date <= end:
                result.append(t)
        return result

    def _sanitize_transaction(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        """Remove ground truth fields from transaction for alert output."""
        return {k: v for k, v in txn.items() if not k.startswith("_")}

    def _summarize_customer(self, entity: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build customer summary from entity record."""
        if not entity:
            return {"name": "Unknown", "customer_id": "", "type": "unknown"}

        return {
            "customer_id": entity.get("customer_id", entity.get("entity_id", "")),
            "name": entity.get("name", "Unknown"),
            "type": entity.get("entity_type", entity.get("type", "individual")),
            "segment": entity.get("segment", entity.get("declared_segment", "retail")),
            "country": entity.get("country", "US"),
            "risk_rating": entity.get("risk_rating", "standard"),
            "pep_status": entity.get("pep_type", entity.get("pep_status", "none")),
            "onboarding_date": str(entity.get("onboarding_date", entity.get("created_at", ""))),
            "industry": entity.get("industry", entity.get("sic_description", "")),
        }

    def _summarize_account(self, account: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Build account summary from account record."""
        if not account:
            return {"account_id": "Unknown", "type": "unknown"}

        return {
            "account_id": account.get("account_id", ""),
            "type": account.get("account_type", account.get("type", "checking")),
            "currency": account.get("currency", "USD"),
            "status": account.get("status", "active"),
            "opened_date": str(account.get("opened_date", account.get("created_at", ""))),
            "declared_purpose": account.get("declared_purpose", "general banking"),
            "declared_monthly_turnover": account.get("declared_monthly_turnover", 0),
            "declared_segment": account.get("declared_segment", account.get("segment", "")),
        }

    def _get_activity_summary(
        self,
        transactions: List[Dict[str, Any]],
        start: date,
        end: date,
    ) -> Dict[str, Any]:
        """Compute account activity summary over the lookback period."""
        recent = self._filter_by_date(transactions, start, end)

        if not recent:
            return {
                "period_start": str(start),
                "period_end": str(end),
                "total_transactions": 0,
                "total_volume": 0.0,
                "avg_transaction_size": 0.0,
                "max_transaction": 0.0,
                "min_transaction": 0.0,
                "credit_count": 0,
                "debit_count": 0,
                "credit_volume": 0.0,
                "debit_volume": 0.0,
                "unique_counterparties": 0,
                "cash_transaction_count": 0,
                "wire_transaction_count": 0,
            }

        amounts = [t.get("amount", 0) for t in recent]
        credits = [t for t in recent if t.get("direction", "").upper() == "CREDIT"]
        debits = [t for t in recent if t.get("direction", "").upper() == "DEBIT"]

        # Count transaction types
        type_counts = Counter(t.get("txn_type", "").upper() for t in recent)
        cash_types = {"CASH_DEPOSIT", "CASH_WITHDRAWAL", "CASH"}
        wire_types = {"WIRE", "WIRE_TRANSFER"}
        cash_count = sum(type_counts.get(ct, 0) for ct in cash_types)
        wire_count = sum(type_counts.get(wt, 0) for wt in wire_types)

        # Unique counterparties
        counterparties = set()
        for t in recent:
            cp = t.get("counterparty_name_raw") or t.get("counterparty_name") or t.get("counterparty_id")
            if cp:
                counterparties.add(cp)

        return {
            "period_start": str(start),
            "period_end": str(end),
            "total_transactions": len(recent),
            "total_volume": round(sum(amounts), 2),
            "avg_transaction_size": round(sum(amounts) / len(amounts), 2) if amounts else 0,
            "max_transaction": round(max(amounts), 2) if amounts else 0,
            "min_transaction": round(min(amounts), 2) if amounts else 0,
            "credit_count": len(credits),
            "debit_count": len(debits),
            "credit_volume": round(sum(t.get("amount", 0) for t in credits), 2),
            "debit_volume": round(sum(t.get("amount", 0) for t in debits), 2),
            "unique_counterparties": len(counterparties),
            "cash_transaction_count": cash_count,
            "wire_transaction_count": wire_count,
            "transaction_type_breakdown": dict(type_counts),
        }

    def _get_counterparty_summary(
        self,
        transactions: List[Dict[str, Any]],
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        """Summarize top counterparties by frequency and volume."""
        cp_data: Dict[str, Dict] = defaultdict(lambda: {
            "name": "", "count": 0, "total_volume": 0.0, "countries": set(),
            "banks": set(), "last_txn": "",
        })

        for t in transactions:
            cp_name = t.get("counterparty_name_raw") or t.get("counterparty_name") or "Unknown"
            if cp_name == "Unknown":
                continue

            entry = cp_data[cp_name]
            entry["name"] = cp_name
            entry["count"] += 1
            entry["total_volume"] += t.get("amount", 0)

            country = t.get("counterparty_country") or t.get("dest_country") or t.get("orig_country")
            if country:
                entry["countries"].add(country)

            bank = t.get("counterparty_bank_name")
            if bank:
                entry["banks"].add(bank)

            ts = t.get("timestamp", "")
            if str(ts) > str(entry["last_txn"]):
                entry["last_txn"] = str(ts)

        # Sort by volume and take top N
        sorted_cps = sorted(cp_data.values(), key=lambda x: x["total_volume"], reverse=True)[:top_n]

        return [
            {
                "name": cp["name"],
                "transaction_count": cp["count"],
                "total_volume": round(cp["total_volume"], 2),
                "countries": list(cp["countries"]),
                "banks": list(cp["banks"]),
                "last_transaction": cp["last_txn"],
            }
            for cp in sorted_cps
        ]

    def _build_narrative_data(
        self,
        alert: Dict[str, Any],
        customer_name: str,
        entity: Optional[Dict[str, Any]],
        account: Optional[Dict[str, Any]],
        signals: Dict[str, Any],
        triggering_txns: List[Dict[str, Any]],
        recent_txns: List[Dict[str, Any]],
        activity_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build the data dictionary for narrative template formatting."""
        amounts = [t.get("amount", 0) for t in triggering_txns] or [0]

        # Count near-threshold transactions (within 10% of $10K)
        threshold = 10000
        near_threshold = sum(
            1 for t in triggering_txns
            if threshold * 0.9 <= t.get("amount", 0) < threshold
        )

        # Cash transactions
        cash_txns = [
            t for t in recent_txns
            if (t.get("txn_type", "").upper() in ("CASH_DEPOSIT", "CASH_WITHDRAWAL", "CASH"))
        ]
        total_volume = activity_summary.get("total_volume", 0)

        return {
            "account_id": alert.get("account_id", ""),
            "customer_name": customer_name,
            "segment": (entity or {}).get("segment", (entity or {}).get("declared_segment", "retail")),
            "txn_count": len(triggering_txns) or activity_summary.get("total_transactions", 0),
            "total_amount": sum(amounts),
            "days": self.lookback_days,
            "near_threshold_count": near_threshold,
            "threshold": threshold,
            "max_amount": max(amounts),
            "score": alert.get("score", 0),
            "hours": 48,  # default lookback for rapid movement
            "in_out_ratio": signals.get("in_out_ratio", 1.0),
            "volume_30d": signals.get("volume_30d", total_volume),
            "zscore": signals.get("volume_zscore", 0),
            "declared_turnover": (account or {}).get("declared_monthly_turnover", 0),
            "jurisdictions": ", ".join(set(
                t.get("counterparty_country", "")
                for t in triggering_txns
                if t.get("counterparty_country")
            )) or "N/A",
            "corridor_score": signals.get("corridor_risk_score", 0),
            "cross_border_detail": "",
            "risk_flow_in": signals.get("risk_flow_in", 0),
            "connected_entities": signals.get("degree_centrality", 0),
            "pep_sanctions_detail": self._pep_sanctions_detail(signals),
            "media_count": signals.get("adverse_media_count", 0),
            "severity": "high" if _safe_float(signals.get("adverse_media_severity", 0)) > 0.7 else "moderate",
            "categories": "financial crime" if signals.get("adverse_media_flag") else "N/A",
            "risk_rating": (entity or {}).get("risk_rating", "standard"),
            "kyc_age_days": int(_safe_float(signals.get("kyc_age_days", 0))),
            "last_kyc_date": str(
                (date.today() - timedelta(days=int(_safe_float(signals.get("kyc_age_days", 0)))))
            ),
            "pep_detail": "Customer is a PEP." if signals.get("pep_flag") else "",
            "ratio": signals.get("declared_vs_actual_volume", 0),
            "cash_pct": signals.get("cash_intensity", 0),
            "cash_txn_count": len(cash_txns),
            "cash_amount": sum(t.get("amount", 0) for t in cash_txns),
            "structuring_note": (
                f"Structuring score: {signals.get('structuring_score', 0):.1f}"
                if signals.get("structuring_score", 0) > 0 else ""
            ),
            "dormancy_days": int(_safe_float(signals.get("dormancy_days", 0))),
            "velocity": _safe_float(signals.get("velocity_30d", 0)),
            "round_count": int(_safe_float(signals.get("round_amount_ratio", 0)) * len(recent_txns)),
            "round_pct": _safe_float(signals.get("round_amount_ratio", 0)),
            "round_amount": _safe_float(signals.get("round_amount_ratio", 0)) * total_volume,
            "avg_txn": activity_summary.get("avg_transaction_size", 0),
            "new_cp_count": int(signals.get("new_counterparty_rate", 0) * max(1, activity_summary.get("unique_counterparties", 1))),
            "new_cp_rate": signals.get("new_counterparty_rate", 0),
            "new_cp_volume": signals.get("new_counterparty_rate", 0) * total_volume * 0.5,
            "rule_name": alert.get("rule_name", ""),
            "rule_id": alert.get("rule_id", ""),
            "risk_level": alert.get("risk_level", "LOW"),
            "declared_purpose": (account or {}).get("declared_purpose", "general banking"),
        }

    def _pep_sanctions_detail(self, signals: Dict[str, Any]) -> str:
        """Generate PEP/sanctions proximity detail."""
        details = []
        pep_dist = _safe_float(signals.get("pep_distance"), default=float("inf"))
        sanctions_dist = _safe_float(signals.get("sanctions_distance"), default=float("inf"))

        if pep_dist < 3:
            details.append(f"PEP proximity: {int(pep_dist)} hop(s) away")
        if sanctions_dist < 3:
            details.append(f"Sanctions proximity: {int(sanctions_dist)} hop(s) away")

        return ". ".join(details) + "." if details else ""
