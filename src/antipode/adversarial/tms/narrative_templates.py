"""
Narrative templates for TMS alert generation.

Templates for:
1. Alert narratives - what the analyst sees when opening an alert
2. Investigation notes - ground truth resolution narratives
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date
import random


# =============================================================================
# ALERT NARRATIVE TEMPLATES (visible to agents)
# =============================================================================

ALERT_NARRATIVES = {
    "structuring": (
        "Account {account_id} held by {customer_name} ({segment} segment) generated "
        "{txn_count} transactions totaling ${total_amount:,.2f} within a {days}-day "
        "lookback period. {near_threshold_count} transaction(s) fell within 10% of the "
        "${threshold:,.0f} reporting threshold. Largest transaction: ${max_amount:,.2f}. "
        "Structuring score: {score:.1f}."
    ),
    "rapid_movement": (
        "Rapid fund movement detected on account {account_id} ({customer_name}). "
        "${total_amount:,.2f} moved through the account within {hours} hours via "
        "{txn_count} transactions. In-out ratio: {in_out_ratio:.2f}. "
        "Movement score: {score:.1f}/1.0."
    ),
    "volume_anomaly": (
        "Account {account_id} ({customer_name}, {segment}) exhibited unusual "
        "transaction volume. Current 30-day volume of ${volume_30d:,.2f} represents "
        "{zscore:.1f}x the historical average. {txn_count} transactions in the period. "
        "Declared monthly turnover: ${declared_turnover:,.2f}."
    ),
    "high_risk_corridor": (
        "Account {account_id} ({customer_name}) processed {txn_count} transaction(s) "
        "totaling ${total_amount:,.2f} involving high-risk jurisdiction(s): "
        "{jurisdictions}. Corridor risk score: {corridor_score:.1f}/100. "
        "{cross_border_detail}"
    ),
    "network_risk": (
        "Network analysis flagged account {account_id} ({customer_name}). "
        "Risk flow into account: ${risk_flow_in:,.2f}. "
        "Connected to {connected_entities} entities in the transaction network. "
        "{pep_sanctions_detail}"
    ),
    "adverse_media": (
        "Adverse media detected for {customer_name} (account {account_id}). "
        "{media_count} adverse media hit(s) identified. "
        "Severity: {severity}. Categories: {categories}. "
        "Customer risk rating: {risk_rating}."
    ),
    "kyc_refresh": (
        "KYC review overdue for {customer_name} (account {account_id}). "
        "Last KYC update: {kyc_age_days} days ago ({last_kyc_date}). "
        "Customer segment: {segment}. Risk rating: {risk_rating}. "
        "{pep_detail}"
    ),
    "declared_mismatch": (
        "Account {account_id} ({customer_name}, {segment}) shows significant "
        "deviation between declared and actual activity. Declared monthly turnover: "
        "${declared_turnover:,.2f}. Actual 30-day volume: ${volume_30d:,.2f} "
        "({ratio:.1f}x declared). {txn_count} transactions in the period."
    ),
    "high_cash": (
        "High cash activity on account {account_id} ({customer_name}). "
        "Cash transactions represent {cash_pct:.0%} of total activity. "
        "{cash_txn_count} cash transaction(s) totaling ${cash_amount:,.2f} "
        "in the lookback period. {structuring_note}"
    ),
    "dormant_reactivation": (
        "Dormant account reactivated: {account_id} ({customer_name}). "
        "Account was inactive for {dormancy_days} days before {txn_count} "
        "transaction(s) totaling ${total_amount:,.2f} were processed. "
        "Current velocity: {velocity:.0f} transactions/30 days."
    ),
    "round_amounts": (
        "Round amount pattern detected on account {account_id} ({customer_name}). "
        "{round_count} of {txn_count} transactions ({round_pct:.0%}) involved "
        "round amounts. Total round-amount volume: ${round_amount:,.2f}. "
        "Average transaction size: ${avg_txn:,.2f}."
    ),
    "new_counterparties": (
        "Unusual counterparty activity on account {account_id} ({customer_name}). "
        "{new_cp_count} new counterparties identified in the past 30 days, "
        "representing {new_cp_rate:.0%} of all counterparties. "
        "Total transaction volume with new counterparties: ${new_cp_volume:,.2f}."
    ),
}

# Fallback for any alert type not in the templates
DEFAULT_ALERT_NARRATIVE = (
    "Alert generated for account {account_id} ({customer_name}) by rule "
    "{rule_name} ({rule_id}). Risk level: {risk_level}. Score: {score:.1f}/100. "
    "{txn_count} transaction(s) totaling ${total_amount:,.2f} flagged during "
    "the {days}-day lookback period."
)


# =============================================================================
# INVESTIGATION NOTE TEMPLATES (ground truth - not visible to agents)
# =============================================================================

FP_INVESTIGATION_NOTES = {
    "FALSE_POSITIVE": [
        "Reviewed {txn_count} flagged transactions on account {account_id}. "
        "Activity is consistent with customer's {segment} profile and declared "
        "business purpose ({declared_purpose}). No indicators of suspicious activity. "
        "Closing as false positive.",

        "Investigation of alert {alert_id} on {customer_name}'s account found "
        "no evidence of illicit activity. Transaction patterns align with "
        "historical behavior for this customer segment. Alert triggered by "
        "{alert_type} rule but activity is within expected parameters.",

        "Alert {alert_id} reviewed. {customer_name} ({segment}) account activity "
        "examined. Flagged transactions are consistent with legitimate {activity_type}. "
        "No unusual counterparty relationships or geographic patterns identified. "
        "Recommend closing as false positive with no further action.",
    ],
    "NORMAL_BUSINESS": [
        "Alert {alert_id}: Flagged activity on {customer_name}'s account represents "
        "normal business operations. {detail} Transaction volume and patterns are "
        "within expected norms for {segment} segment customers. No SAR required.",

        "Reviewed alert {alert_id}. Activity on account {account_id} is attributable "
        "to routine {activity_type}. Customer has maintained consistent patterns since "
        "onboarding. Risk factors do not warrant escalation.",
    ],
    "CUSTOMER_EXPLAINED": [
        "Alert {alert_id}: Customer {customer_name} provided satisfactory explanation "
        "for flagged activity. {explanation} Documentation reviewed and verified. "
        "No further action required.",

        "Customer contact made regarding alert {alert_id}. {customer_name} explained "
        "that {explanation} Supporting documentation obtained and filed. Activity is "
        "consistent with explanation. Closing alert.",
    ],
    "INSUFFICIENT_INFO": [
        "Alert {alert_id}: Unable to obtain sufficient information to determine "
        "if activity is suspicious. {customer_name}'s account shows {detail}. "
        "No definitive indicators of money laundering identified. Closing due to "
        "insufficient evidence but flagging for enhanced monitoring.",
    ],
}

TP_INVESTIGATION_NOTES = {
    "SUSPICIOUS_ACTIVITY": [
        "Alert {alert_id}: Investigation revealed suspicious {typology} pattern "
        "on {customer_name}'s account ({account_id}). {detail} "
        "Pattern is consistent with money laundering indicators. "
        "Escalating for SAR filing review.",

        "Comprehensive review of alert {alert_id} identified indicators of "
        "{typology} activity. {customer_name}'s transactions show {detail} "
        "Multiple risk factors present: {risk_factors}. "
        "Recommending SAR filing and enhanced due diligence.",
    ],
    "CONFIRMED_FRAUD": [
        "Alert {alert_id}: Confirmed {typology} scheme involving {customer_name} "
        "({account_id}). {detail} Total suspicious amount: ${suspicious_amount:,.2f}. "
        "SAR filed. Account restricted pending law enforcement referral.",

        "Investigation of alert {alert_id} confirmed deliberate {typology} activity. "
        "{detail} Evidence sufficient for law enforcement referral. "
        "SAR {sar_id} filed on {filing_date}.",
    ],
}

# Customer explanation templates (for FP with CUSTOMER_EXPLAINED disposition)
CUSTOMER_EXPLANATIONS = {
    "structuring": [
        "the transactions below reporting thresholds were regular business deposits from daily cash sales",
        "the series of smaller transfers was to meet payment obligations to multiple vendors on the same day",
        "they routinely deposit daily cash receipts from their retail store operations",
    ],
    "volume_anomaly": [
        "the volume increase was due to seasonal business (end-of-quarter inventory purchases)",
        "they recently received an inheritance/insurance settlement being invested across accounts",
        "business expansion required larger-than-usual vendor payments this month",
    ],
    "high_risk_corridor": [
        "they have family in the flagged jurisdiction and regularly send remittances",
        "their company imports goods from the flagged region as part of normal trade operations",
        "the wire transfer was for a real estate purchase in the destination country",
    ],
    "rapid_movement": [
        "the rapid transfers were part of a time-sensitive business acquisition closing",
        "they were consolidating funds from multiple accounts for a large purchase",
        "the transfers were to meet a same-day payment deadline with a key supplier",
    ],
    "round_amounts": [
        "the round amounts are regular payroll disbursements to salaried employees",
        "monthly rent and insurance payments are fixed amounts as per their lease/policy",
        "the transfers represent regular mortgage and utility payments",
    ],
    "high_cash": [
        "the cash deposits are from their cash-intensive retail business (convenience store)",
        "the cash activity is consistent with their declared business as a restaurant operator",
        "they operate a laundromat and regularly deposit coin and currency",
    ],
}

# Activity type descriptions for FP investigation notes
FP_ACTIVITY_TYPES = {
    "structuring": "routine business deposits",
    "rapid_movement": "time-sensitive fund transfers",
    "volume_anomaly": "seasonal business activity",
    "high_risk_corridor": "international trade payments",
    "network_risk": "normal business network activity",
    "adverse_media": "media coverage unrelated to financial crime",
    "kyc_refresh": "standard account operations",
    "declared_mismatch": "business growth-related activity",
    "high_cash": "cash-intensive business deposits",
    "dormant_reactivation": "resumed business operations",
    "round_amounts": "regular payroll or fixed payments",
    "new_counterparties": "new business relationships",
}

# TP detail descriptions by typology
TP_TYPOLOGY_DETAILS = {
    "structuring": [
        "Multiple cash deposits consistently just below the $10,000 reporting threshold. "
        "Deposits spread across {n_accounts} accounts over {n_days} days.",
        "Systematic splitting of large amounts into sub-threshold deposits. "
        "Total structured amount: ${amount:,.2f} across {n_txns} transactions.",
    ],
    "layering": [
        "Funds moved through {n_layers} intermediate accounts across {n_jurisdictions} "
        "jurisdictions to obscure origin. Transfer chain shows decreasing amounts "
        "consistent with fee skimming.",
        "Complex web of transfers between {n_entities} entities designed to obscure "
        "the audit trail. Rapid movement through shell accounts with no apparent "
        "business purpose.",
    ],
    "mule_network": [
        "Account identified as part of a {n_mules}-member money mule network. "
        "Pattern of incoming wires followed by rapid cash withdrawals or outbound transfers.",
        "Coordination between {n_mules} accounts showing synchronized deposit-withdrawal "
        "patterns. Minimal holding period before funds are dispersed.",
    ],
    "shell_company": [
        "Entity shows characteristics of a shell company: minimal employees, "
        "recently incorporated, registered agent address, no verifiable business operations. "
        "Transactions lack commercial rationale.",
        "Shell company used to receive and redirect ${amount:,.2f} with no corresponding "
        "goods or services. Beneficial ownership structure designed to obscure control.",
    ],
    "trade_based": [
        "Invoice values appear inflated by {inflation_pct}% compared to market prices for "
        "declared goods. Over-invoicing suspected across {n_invoices} trade transactions.",
        "Trade documentation shows inconsistencies: goods described do not match typical "
        "trade corridors, quantities appear unrealistic for declared business size.",
    ],
    "integration": [
        "Proceeds appear to be integrated into legitimate economy through real estate "
        "purchases and business investments. Funds originated from known suspicious sources.",
        "Final stage of laundering detected: cleaned funds being invested in "
        "{investment_type} to create appearance of legitimate wealth.",
    ],
    "crypto_mixing": [
        "Funds converted to cryptocurrency and passed through mixing/tumbling services "
        "before re-entering the banking system. {n_hops} intermediate crypto wallets identified.",
        "Pattern of fiat-to-crypto-to-fiat conversions with obfuscation layers. "
        "Total value processed: ${amount:,.2f}.",
    ],
}

# Simulated analyst names
ANALYST_POOL = [
    "AML-A001", "AML-A002", "AML-A003", "AML-A004", "AML-A005",
    "AML-A006", "AML-A007", "AML-A008", "AML-A009", "AML-A010",
    "AML-S001", "AML-S002", "AML-S003",  # Senior analysts
    "AML-M001",  # Manager
]


def generate_alert_narrative(
    alert_type: str,
    alert_data: Dict[str, Any],
) -> str:
    """Generate an alert narrative from template and data.

    Args:
        alert_type: The type of alert (e.g., 'structuring', 'volume_anomaly')
        alert_data: Dictionary of values to fill into the template

    Returns:
        Formatted narrative string
    """
    template = ALERT_NARRATIVES.get(alert_type, DEFAULT_ALERT_NARRATIVE)

    # Provide defaults for all possible template variables
    defaults = {
        "account_id": "UNKNOWN",
        "customer_name": "Unknown Customer",
        "segment": "unknown",
        "txn_count": 0,
        "total_amount": 0.0,
        "days": 30,
        "near_threshold_count": 0,
        "threshold": 10000,
        "max_amount": 0.0,
        "score": 0.0,
        "hours": 24,
        "in_out_ratio": 1.0,
        "volume_30d": 0.0,
        "zscore": 0.0,
        "declared_turnover": 0.0,
        "jurisdictions": "N/A",
        "corridor_score": 0.0,
        "cross_border_detail": "",
        "risk_flow_in": 0.0,
        "connected_entities": 0,
        "pep_sanctions_detail": "",
        "media_count": 0,
        "severity": "unknown",
        "categories": "N/A",
        "risk_rating": "standard",
        "kyc_age_days": 0,
        "last_kyc_date": "unknown",
        "pep_detail": "",
        "ratio": 0.0,
        "cash_pct": 0.0,
        "cash_txn_count": 0,
        "cash_amount": 0.0,
        "structuring_note": "",
        "dormancy_days": 0,
        "velocity": 0.0,
        "round_count": 0,
        "round_pct": 0.0,
        "round_amount": 0.0,
        "avg_txn": 0.0,
        "new_cp_count": 0,
        "new_cp_rate": 0.0,
        "new_cp_volume": 0.0,
        "rule_name": "Unknown Rule",
        "rule_id": "UNKNOWN",
        "risk_level": "LOW",
        "declared_purpose": "general banking",
        "activity_type": "account activity",
    }

    # Merge defaults with provided data
    merged = {**defaults, **alert_data}

    try:
        return template.format(**merged)
    except (KeyError, ValueError, IndexError):
        # Fallback to default template
        try:
            return DEFAULT_ALERT_NARRATIVE.format(**merged)
        except Exception:
            return f"Alert on account {merged['account_id']} ({merged['customer_name']}). Rule: {merged.get('rule_name', 'Unknown')}."


def generate_investigation_note(
    is_true_positive: bool,
    disposition: str,
    alert_data: Dict[str, Any],
    typology: Optional[str] = None,
) -> str:
    """Generate an investigation note for ground truth.

    Args:
        is_true_positive: Whether this alert is a true positive
        disposition: The disposition reason
        alert_data: Dictionary of values for template filling
        typology: For TPs, the specific typology

    Returns:
        Investigation note string
    """
    defaults = {
        "alert_id": "UNKNOWN",
        "account_id": "UNKNOWN",
        "customer_name": "Unknown Customer",
        "segment": "unknown",
        "txn_count": 0,
        "total_amount": 0.0,
        "alert_type": "unknown",
        "declared_purpose": "general banking",
        "detail": "",
        "risk_factors": "",
        "suspicious_amount": 0.0,
        "sar_id": "N/A",
        "filing_date": "N/A",
        "typology": typology or "unknown",
        "activity_type": FP_ACTIVITY_TYPES.get(alert_data.get("alert_type", ""), "account activity"),
        "explanation": "",
    }
    merged = {**defaults, **alert_data}

    if is_true_positive:
        templates = TP_INVESTIGATION_NOTES.get(disposition, TP_INVESTIGATION_NOTES["SUSPICIOUS_ACTIVITY"])

        # Add typology-specific detail
        if typology and typology in TP_TYPOLOGY_DETAILS:
            detail_templates = TP_TYPOLOGY_DETAILS[typology]
            merged["detail"] = random.choice(detail_templates).format(
                n_accounts=random.randint(2, 5),
                n_days=random.randint(7, 30),
                amount=merged.get("total_amount", 50000),
                n_txns=merged.get("txn_count", 10),
                n_layers=random.randint(3, 6),
                n_jurisdictions=random.randint(2, 4),
                n_entities=random.randint(3, 8),
                n_mules=random.randint(3, 10),
                inflation_pct=random.randint(20, 200),
                n_invoices=random.randint(3, 15),
                investment_type=random.choice(["real estate", "business ventures", "securities"]),
                n_hops=random.randint(3, 8),
            )
    else:
        templates = FP_INVESTIGATION_NOTES.get(disposition, FP_INVESTIGATION_NOTES["FALSE_POSITIVE"])

        # Add customer explanation if applicable
        if disposition == "CUSTOMER_EXPLAINED":
            alert_type = merged.get("alert_type", "")
            explanations = CUSTOMER_EXPLANATIONS.get(alert_type, ["the activity was part of normal operations"])
            merged["explanation"] = random.choice(explanations)

        # Add detail for normal business
        if disposition == "NORMAL_BUSINESS":
            merged["detail"] = random.choice([
                "Transaction volumes are within 1 standard deviation of historical patterns.",
                "Account activity is consistent with peer group behavior.",
                "All counterparties have been previously verified.",
                "Activity corresponds with known seasonal business patterns.",
            ])

    template = random.choice(templates)

    try:
        return template.format(**merged)
    except (KeyError, ValueError):
        if is_true_positive:
            return f"Alert {merged['alert_id']}: Suspicious {merged.get('typology', 'unknown')} activity confirmed on {merged['customer_name']}'s account."
        else:
            return f"Alert {merged['alert_id']}: Reviewed and closed as {disposition}. No suspicious activity identified."


def select_analyst(risk_level: str = "LOW") -> str:
    """Select an analyst based on alert risk level.

    Higher risk alerts get assigned to senior analysts or managers.
    """
    if risk_level in ("CRITICAL", "critical"):
        # Senior analyst or manager
        return random.choice(ANALYST_POOL[-4:])
    elif risk_level in ("HIGH", "high"):
        # Senior or regular analyst
        return random.choice(ANALYST_POOL[-7:])
    else:
        # Regular analyst
        return random.choice(ANALYST_POOL[:10])
