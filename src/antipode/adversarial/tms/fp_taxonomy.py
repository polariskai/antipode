"""
FP Alert Taxonomy & Investigation Playbooks

Comprehensive categorization of why false positive alerts fire and what
bank datasets provide evidence to resolve them as legitimate.

Each FP alert type maps to 2-5 FPCategory entries. Each category specifies:
- WHY the alert fired (triggering rule, signals, flag reason)
- WHAT legitimate explanation exists
- WHICH bank datasets provide exonerating evidence
- HOW to investigate (step-by-step playbook with specific queries)
- WHEN to close (resolution criteria)

Evidence datasets map directly to tables in sql/bank_schema.sql (14 raw + 6 derived).
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from collections import Counter, defaultdict


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class EvidenceDataset(str, Enum):
    """Bank data tables/views that provide evidence for FP resolution.
    Maps 1:1 to tables in sql/bank_schema.sql."""

    # Raw tables
    CUSTOMER = "Customer"
    CUSTOMER_PERSON = "CustomerPerson"
    CUSTOMER_COMPANY = "CustomerCompany"
    COMPANY_OFFICER = "CompanyOfficer"
    CUSTOMER_ADDRESS = "CustomerAddress"
    CUSTOMER_IDENTIFIER = "CustomerIdentifier"
    ACCOUNT = "Account"
    ACCOUNT_OWNERSHIP = "AccountOwnership"
    TRANSACTION = "Transaction"
    COUNTERPARTY = "Counterparty"
    CUSTOMER_RELATIONSHIP = "CustomerRelationship"
    NEWS_EVENT = "NewsEvent"
    ALERT_HISTORY = "Alert"
    ALERT_TRANSACTION = "AlertTransaction"
    # Derived / analytics tables
    ACCOUNT_SIGNALS = "AccountSignals"
    TRANSACTION_AGGREGATION = "TransactionAggregation"
    CUSTOMER_RISK_PROFILE = "CustomerRiskProfile"
    NETWORK_METRICS = "NetworkMetrics"
    COUNTERPARTY_PROFILE = "CounterpartyProfile"
    CORRIDOR_ANALYSIS = "CorridorAnalysis"


@dataclass
class EvidenceQuery:
    """A specific lookup against a bank dataset to gather evidence."""
    dataset: EvidenceDataset
    description: str
    fields: List[str]
    expected_finding: str = ""


@dataclass
class InvestigationStep:
    """One step in the investigation playbook."""
    step_number: int
    action: str
    evidence_queries: List[EvidenceQuery]
    decision_criteria: str
    expected_outcome_fp: str = ""


@dataclass
class FPCategory:
    """A specific false-positive category for a given alert type."""

    category_id: str            # e.g. "VOL_ANOM_FP_SEASONAL"
    alert_type: str             # alert_type value this applies to
    triggering_rule: str        # rule_id from rules.py
    triggering_signals: List[str]

    # WHY it was flagged
    flag_reason: str

    # WHAT legitimate explanation exists
    legitimate_explanation: str
    applicable_dispositions: List[str]

    # Link to benign_agents.py FP trigger (optional)
    benign_trigger_type: Optional[str] = None

    # WHICH datasets provide evidence
    evidence_datasets: List[EvidenceDataset] = field(default_factory=list)

    # HOW to investigate
    investigation_steps: List[InvestigationStep] = field(default_factory=list)

    # Resolution criteria
    resolution_criteria: str = ""

    # Selection weight within alert_type
    weight: float = 1.0

    # ----- serialisation -----
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category_id": self.category_id,
            "alert_type": self.alert_type,
            "triggering_rule": self.triggering_rule,
            "triggering_signals": self.triggering_signals,
            "flag_reason": self.flag_reason,
            "legitimate_explanation": self.legitimate_explanation,
            "applicable_dispositions": self.applicable_dispositions,
            "benign_trigger_type": self.benign_trigger_type,
            "evidence_datasets": [d.value for d in self.evidence_datasets],
            "investigation_steps": [
                {
                    "step": s.step_number,
                    "action": s.action,
                    "queries": [
                        {
                            "dataset": q.dataset.value,
                            "description": q.description,
                            "fields": q.fields,
                            "expected_finding": q.expected_finding,
                        }
                        for q in s.evidence_queries
                    ],
                    "decision_criteria": s.decision_criteria,
                    "expected_outcome_fp": s.expected_outcome_fp,
                }
                for s in self.investigation_steps
            ],
            "resolution_criteria": self.resolution_criteria,
        }

    def to_ground_truth_fields(self) -> Dict[str, Any]:
        """Return the 7 enrichment fields for a ground-truth resolution."""
        return {
            "fp_category": self.category_id,
            "fp_flag_reason": self.flag_reason,
            "fp_legitimate_explanation": self.legitimate_explanation,
            "fp_evidence_datasets": [d.value for d in self.evidence_datasets],
            "fp_investigation_playbook": [
                {
                    "step": s.step_number,
                    "action": s.action,
                    "queries": [
                        {"dataset": q.dataset.value, "description": q.description, "fields": q.fields}
                        for q in s.evidence_queries
                    ],
                    "decision_criteria": s.decision_criteria,
                }
                for s in self.investigation_steps
            ],
            "fp_resolution_criteria": self.resolution_criteria,
            "fp_benign_trigger_type": self.benign_trigger_type,
        }


# ---------------------------------------------------------------------------
# Helper shortcuts
# ---------------------------------------------------------------------------

def _eq(ds: EvidenceDataset, desc: str, fields: List[str], finding: str = "") -> EvidenceQuery:
    """Shorthand constructor for EvidenceQuery."""
    return EvidenceQuery(dataset=ds, description=desc, fields=fields, expected_finding=finding)


def _step(n: int, action: str, queries: List[EvidenceQuery], criteria: str, outcome: str = "") -> InvestigationStep:
    return InvestigationStep(step_number=n, action=action, evidence_queries=queries,
                             decision_criteria=criteria, expected_outcome_fp=outcome)


D = EvidenceDataset  # short alias


# ---------------------------------------------------------------------------
# THE FULL TAXONOMY  (Dict[alert_type, List[FPCategory]])
# ---------------------------------------------------------------------------

FP_CATEGORIES: Dict[str, List[FPCategory]] = {

    # ===================================================================
    # VOLUME ANOMALY  (VOL_ANOM_001: volume_zscore > 2.5)
    # ===================================================================
    "volume_anomaly": [
        FPCategory(
            category_id="VOL_ANOM_FP_SEASONAL",
            alert_type="volume_anomaly",
            triggering_rule="VOL_ANOM_001",
            triggering_signals=["volume_zscore", "volume_30d", "velocity_30d"],
            flag_reason="Transaction volume exceeded 2.5 standard deviations from historical average",
            legitimate_explanation="Seasonal business cycle causing predictable volume spike (holiday retail, tax season, harvest)",
            applicable_dispositions=["FALSE_POSITIVE", "NORMAL_BUSINESS"],
            benign_trigger_type="high_volume_seasonal",
            evidence_datasets=[D.TRANSACTION_AGGREGATION, D.ACCOUNT_SIGNALS, D.CUSTOMER_COMPANY, D.ACCOUNT],
            investigation_steps=[
                _step(1, "Pull 12-month transaction aggregation to identify seasonal patterns",
                      [_eq(D.TRANSACTION_AGGREGATION,
                           "Monthly volume over past 12 months for this account",
                           ["period_start", "period_end", "total_credit_amount", "total_debit_amount",
                            "total_credit_count", "total_debit_count"],
                           "Volume shows recurring spikes in same months across years")],
                      "Compare current month volume to same month in prior year(s)",
                      "Current volume is within 20% of same seasonal period historically"),
                _step(2, "Verify customer business type supports seasonal patterns",
                      [_eq(D.CUSTOMER_COMPANY,
                           "Industry classification and business activity",
                           ["industry_code", "industry_description", "annual_revenue"],
                           "Industry has known seasonal patterns (retail, agriculture, tourism)"),
                       _eq(D.ACCOUNT,
                           "Declared turnover and account purpose",
                           ["declared_monthly_turnover", "purpose", "declared_source_of_funds"],
                           "Declared turnover accounts for seasonal variation")],
                      "Business type is consistent with observed seasonal spike",
                      "Customer's industry has known seasonal patterns matching observed behavior"),
                _step(3, "Check counterparty consistency during spike period",
                      [_eq(D.COUNTERPARTY_PROFILE,
                           "Top counterparties by volume in the spike period",
                           ["name", "total_volume_usd", "txn_count_30d", "first_seen_date"],
                           "Counterparties are established, recurring business partners")],
                      "No new/unknown counterparties dominate the spike period",
                      "Volume increase comes from existing relationships"),
            ],
            resolution_criteria="Volume spike is consistent with historical seasonal patterns for this business type, "
                               "counterparties are established, and no structuring or layering indicators present",
            weight=1.5,
        ),
        FPCategory(
            category_id="VOL_ANOM_FP_GROWTH",
            alert_type="volume_anomaly",
            triggering_rule="VOL_ANOM_001",
            triggering_signals=["volume_zscore", "volume_30d"],
            flag_reason="Transaction volume exceeded 2.5 standard deviations from historical average",
            legitimate_explanation="Business growth or expansion causing organic increase in transaction volume",
            applicable_dispositions=["NORMAL_BUSINESS"],
            evidence_datasets=[D.TRANSACTION_AGGREGATION, D.ACCOUNT, D.CUSTOMER_COMPANY, D.COUNTERPARTY_PROFILE],
            investigation_steps=[
                _step(1, "Review volume trend over 6+ months for gradual increase pattern",
                      [_eq(D.TRANSACTION_AGGREGATION,
                           "Monthly volume trend over past 6 months",
                           ["period_start", "total_credit_amount", "total_debit_amount", "unique_counterparties"],
                           "Volume shows gradual upward trend, not sudden spike")],
                      "Volume increase is gradual and sustained, not sudden",
                      "Consistent month-over-month growth pattern"),
                _step(2, "Verify business has documented growth indicators",
                      [_eq(D.CUSTOMER_COMPANY,
                           "Business attributes indicating growth",
                           ["employee_count", "annual_revenue", "operational_countries"],
                           "Revenue and/or employee count increased")],
                      "Business metrics support the volume increase",
                      "Documented business growth explains volume change"),
            ],
            resolution_criteria="Volume increase corresponds with documented business growth; "
                               "gradual trend without suspicious counterparty patterns",
            weight=1.0,
        ),
        FPCategory(
            category_id="VOL_ANOM_FP_INHERITANCE",
            alert_type="volume_anomaly",
            triggering_rule="VOL_ANOM_001",
            triggering_signals=["volume_zscore", "volume_30d"],
            flag_reason="Transaction volume exceeded 2.5 standard deviations from historical average",
            legitimate_explanation="One-time large receipt (inheritance, insurance settlement, asset sale) causing temporary volume spike",
            applicable_dispositions=["CUSTOMER_EXPLAINED", "FALSE_POSITIVE"],
            benign_trigger_type="inheritance",
            evidence_datasets=[D.TRANSACTION, D.CUSTOMER_PERSON, D.ACCOUNT, D.COUNTERPARTY],
            investigation_steps=[
                _step(1, "Identify the large transaction(s) driving the volume anomaly",
                      [_eq(D.TRANSACTION,
                           "Transactions sorted by amount in the alert period",
                           ["txn_id", "amount", "txn_type", "purpose_description",
                            "counterparty_name_raw", "counterparty_country"],
                           "One or few large transactions dominate the volume")],
                      "Volume anomaly is driven by identifiable large one-off transactions",
                      "Single large inflow from estate/insurance/sale source"),
                _step(2, "Verify counterparty is a legitimate estate/insurance/legal entity",
                      [_eq(D.COUNTERPARTY,
                           "Details of the counterparty on the large transaction",
                           ["name", "type", "bank_name", "country"],
                           "Counterparty is a law firm, estate executor, or insurance company")],
                      "Counterparty identity is consistent with claimed source of funds",
                      "Counterparty is verified legal/financial entity"),
            ],
            resolution_criteria="Volume spike is attributable to a documented one-time event "
                               "(inheritance, insurance, asset sale) with verified counterparty",
            weight=0.5,
        ),
    ],

    # ===================================================================
    # ROUND AMOUNTS  (ROUND_001: round_amount_ratio > 0.5 + velocity > 10)
    # ===================================================================
    "round_amounts": [
        FPCategory(
            category_id="ROUND_FP_PAYROLL",
            alert_type="round_amounts",
            triggering_rule="ROUND_001",
            triggering_signals=["round_amount_ratio", "velocity_30d"],
            flag_reason="High proportion of round-number transactions detected with elevated transaction frequency",
            legitimate_explanation="Standard payroll disbursements to salaried employees (fixed round salaries)",
            applicable_dispositions=["NORMAL_BUSINESS", "FALSE_POSITIVE"],
            benign_trigger_type="round_amount_payroll",
            evidence_datasets=[D.TRANSACTION, D.ACCOUNT, D.CUSTOMER_COMPANY, D.TRANSACTION_AGGREGATION],
            investigation_steps=[
                _step(1, "Analyze round-amount transactions for payroll pattern (bi-weekly, same amounts)",
                      [_eq(D.TRANSACTION,
                           "Round-amount transactions grouped by day and amount",
                           ["amount", "value_date", "txn_type", "counterparty_name_raw", "purpose_description"],
                           "Same amounts repeat on regular bi-weekly or monthly schedule")],
                      "Transactions show regular payroll cycle (bi-weekly or monthly, consistent amounts)",
                      "Amounts match standard salary denominations on regular schedule"),
                _step(2, "Confirm account is a business/corporate account with payroll purpose",
                      [_eq(D.ACCOUNT,
                           "Account type and declared purpose",
                           ["account_type", "declared_purpose", "declared_segment"],
                           "Account purpose is business operations or payroll"),
                       _eq(D.CUSTOMER_COMPANY,
                           "Business type and employee count",
                           ["company_type", "employee_count", "industry_description"],
                           "Business has employees consistent with number of payroll transactions")],
                      "Account belongs to a business entity with employees",
                      "Business employee count matches payroll transaction volume"),
            ],
            resolution_criteria="Round amounts are standard payroll disbursements from a verified business "
                               "account with employee count matching transaction frequency",
            weight=1.5,
        ),
        FPCategory(
            category_id="ROUND_FP_FIXED_PAYMENTS",
            alert_type="round_amounts",
            triggering_rule="ROUND_001",
            triggering_signals=["round_amount_ratio", "velocity_30d"],
            flag_reason="High proportion of round-number transactions detected",
            legitimate_explanation="Regular fixed payments (rent, insurance premiums, loan installments, subscriptions)",
            applicable_dispositions=["FALSE_POSITIVE", "NORMAL_BUSINESS"],
            evidence_datasets=[D.TRANSACTION, D.ACCOUNT, D.TRANSACTION_AGGREGATION],
            investigation_steps=[
                _step(1, "Identify recurring same-amount transactions and their counterparties",
                      [_eq(D.TRANSACTION,
                           "Recurring round-amount transactions over 3+ months",
                           ["amount", "value_date", "counterparty_name_raw", "purpose_description"],
                           "Same amounts to same counterparties on predictable schedule")],
                      "Transactions are recurring fixed obligations, not ad-hoc transfers",
                      "Payments match lease/insurance/loan installment schedules"),
                _step(2, "Verify counterparties are legitimate service providers",
                      [_eq(D.COUNTERPARTY_PROFILE,
                           "Counterparty details for recurring payments",
                           ["name", "type", "first_seen_date", "txn_count"],
                           "Counterparties are established landlords, insurers, or lenders")],
                      "All recurring payment recipients are identifiable service providers",
                      "Long-standing relationship with known counterparties"),
            ],
            resolution_criteria="Round amounts are regular fixed obligations (rent, insurance, loan payments) "
                               "to established counterparties with long transaction history",
            weight=1.0,
        ),
        FPCategory(
            category_id="ROUND_FP_VENDOR_INVOICES",
            alert_type="round_amounts",
            triggering_rule="ROUND_001",
            triggering_signals=["round_amount_ratio", "velocity_30d"],
            flag_reason="High proportion of round-number transactions with elevated frequency",
            legitimate_explanation="Business-to-business vendor payments at negotiated contract prices (often round numbers)",
            applicable_dispositions=["NORMAL_BUSINESS"],
            evidence_datasets=[D.TRANSACTION, D.CUSTOMER_COMPANY, D.COUNTERPARTY_PROFILE],
            investigation_steps=[
                _step(1, "Review vendor payment patterns and verify B2B relationship",
                      [_eq(D.TRANSACTION,
                           "Outgoing payments filtered by round amounts",
                           ["amount", "counterparty_name_raw", "purpose_description", "txn_type"],
                           "Payments to identifiable vendors at contract prices"),
                       _eq(D.COUNTERPARTY_PROFILE,
                           "Vendor counterparty history",
                           ["name", "first_seen_date", "total_volume_usd", "txn_count"],
                           "Long-standing vendor relationship")],
                      "Payments are to established suppliers at consistent contract prices",
                      "B2B payment pattern confirmed with documented vendor relationships"),
            ],
            resolution_criteria="Round amounts are standard B2B vendor payments at contractual rates "
                               "to established suppliers",
            weight=0.7,
        ),
    ],

    # ===================================================================
    # HIGH-RISK CORRIDOR  (CORR_001: corridor_risk_score > 40)
    # ===================================================================
    "high_risk_corridor": [
        FPCategory(
            category_id="CORR_FP_TRADE",
            alert_type="high_risk_corridor",
            triggering_rule="CORR_001",
            triggering_signals=["corridor_risk_score"],
            flag_reason="Transaction activity involving high-risk jurisdiction exceeds corridor risk threshold",
            legitimate_explanation="Established international trade relationships with documentation (imports/exports)",
            applicable_dispositions=["FALSE_POSITIVE", "NORMAL_BUSINESS"],
            benign_trigger_type="international_trade",
            evidence_datasets=[D.CORRIDOR_ANALYSIS, D.COUNTERPARTY, D.CUSTOMER_COMPANY, D.TRANSACTION],
            investigation_steps=[
                _step(1, "Review corridor history to determine if this is an established trade route",
                      [_eq(D.CORRIDOR_ANALYSIS,
                           "Historical corridor activity for this account",
                           ["origin_country", "destination_country", "txn_count", "total_volume_usd", "first_seen_date"],
                           "Corridor has been active for 6+ months with consistent volume")],
                      "Corridor is established (not new) with consistent transaction patterns",
                      "Trade corridor active for extended period with predictable volumes"),
                _step(2, "Verify counterparties in the high-risk jurisdiction are known trade partners",
                      [_eq(D.COUNTERPARTY,
                           "Counterparties in the flagged jurisdiction",
                           ["name", "type", "country", "bank_name", "txn_count", "total_volume"],
                           "Counterparties are established suppliers/buyers with long history"),
                       _eq(D.CUSTOMER_COMPANY,
                           "Customer's declared operating countries and industry",
                           ["industry_code", "operational_countries", "annual_revenue"],
                           "Business industry involves international trade to flagged region")],
                      "Counterparties are verified trade partners in customer's declared operating region",
                      "Business model requires trade with this jurisdiction"),
            ],
            resolution_criteria="Corridor activity reflects established trade relationships with documented "
                               "counterparties in customer's declared operating markets",
            weight=1.5,
        ),
        FPCategory(
            category_id="CORR_FP_FAMILY_REMIT",
            alert_type="high_risk_corridor",
            triggering_rule="CORR_001",
            triggering_signals=["corridor_risk_score"],
            flag_reason="Transaction to monitored jurisdiction triggered corridor risk threshold",
            legitimate_explanation="Regular family remittances to country of origin",
            applicable_dispositions=["CUSTOMER_EXPLAINED", "FALSE_POSITIVE"],
            evidence_datasets=[D.TRANSACTION, D.CUSTOMER_PERSON, D.CUSTOMER_RELATIONSHIP, D.COUNTERPARTY],
            investigation_steps=[
                _step(1, "Check customer nationality/origin matches destination country",
                      [_eq(D.CUSTOMER_PERSON,
                           "Customer nationality and country of birth",
                           ["nationality", "country_of_birth", "country_of_residence"],
                           "Customer has ties to the destination country")],
                      "Customer has personal connection to the flagged jurisdiction",
                      "Nationality or birth country matches remittance destination"),
                _step(2, "Verify remittance pattern is regular and consistent",
                      [_eq(D.TRANSACTION,
                           "Outgoing transfers to flagged jurisdiction over 6+ months",
                           ["amount", "value_date", "counterparty_name_raw", "dest_country"],
                           "Regular monthly/quarterly remittances of similar amounts"),
                       _eq(D.CUSTOMER_RELATIONSHIP,
                           "Known family relationships",
                           ["related_customer_id", "relationship_type", "country"],
                           "Family member in destination country")],
                      "Remittance pattern is regular, amounts are consistent, family connection exists",
                      "Documented family remittance pattern"),
            ],
            resolution_criteria="Corridor activity is regular family remittances to customer's country of "
                               "origin/family residence, with consistent amounts and established pattern",
            weight=1.0,
        ),
        FPCategory(
            category_id="CORR_FP_REAL_ESTATE",
            alert_type="high_risk_corridor",
            triggering_rule="CORR_001",
            triggering_signals=["corridor_risk_score"],
            flag_reason="Large transaction to high-risk jurisdiction triggered corridor risk alert",
            legitimate_explanation="Documented real estate purchase or property transaction in destination country",
            applicable_dispositions=["CUSTOMER_EXPLAINED"],
            benign_trigger_type="real_estate_closing",
            evidence_datasets=[D.TRANSACTION, D.ACCOUNT, D.CUSTOMER_PERSON, D.COUNTERPARTY],
            investigation_steps=[
                _step(1, "Identify the large transaction and verify it's a one-time property payment",
                      [_eq(D.TRANSACTION,
                           "Large outgoing wire to flagged jurisdiction",
                           ["amount", "txn_type", "purpose_description", "counterparty_name_raw"],
                           "Single large wire with purpose referencing real estate/property")],
                      "Transaction is a single large payment consistent with property purchase",
                      "One-time wire with real estate purpose description"),
                _step(2, "Verify counterparty is a legitimate real estate/legal entity",
                      [_eq(D.COUNTERPARTY,
                           "Counterparty receiving the large payment",
                           ["name", "type", "country", "bank_name"],
                           "Counterparty is a law firm, escrow agent, or real estate company")],
                      "Payment recipient is a verified real estate professional",
                      "Counterparty is identifiable legal/real estate entity"),
            ],
            resolution_criteria="Large corridor transaction is a documented real estate purchase "
                               "with verified legal/escrow counterparty",
            weight=0.5,
        ),
    ],

    # ===================================================================
    # KYC REFRESH  (KYC_001: kyc_age_days > 365)
    # ===================================================================
    "kyc_refresh": [
        FPCategory(
            category_id="KYC_FP_ADMIN_DELAY",
            alert_type="kyc_refresh",
            triggering_rule="KYC_001",
            triggering_signals=["kyc_age_days"],
            flag_reason="KYC review period exceeded (> 365 days since last refresh)",
            legitimate_explanation="Administrative delay in KYC refresh; no material changes to customer profile",
            applicable_dispositions=["FALSE_POSITIVE"],
            evidence_datasets=[D.CUSTOMER, D.ACCOUNT, D.ACCOUNT_SIGNALS],
            investigation_steps=[
                _step(1, "Verify no material changes to customer profile since last KYC",
                      [_eq(D.CUSTOMER,
                           "Customer profile and last KYC date",
                           ["customer_type", "status", "risk_rating", "kyc_date", "next_review_date"],
                           "Customer profile unchanged, risk rating stable"),
                       _eq(D.ACCOUNT,
                           "Account status and activity level",
                           ["account_status", "declared_monthly_turnover", "declared_purpose"],
                           "Account operating within declared parameters")],
                      "Customer profile is stable with no material changes since last KYC",
                      "No address changes, no new products, risk rating unchanged"),
                _step(2, "Confirm transaction patterns are consistent with pre-KYC behavior",
                      [_eq(D.ACCOUNT_SIGNALS,
                           "Current signals compared to historical baseline",
                           ["volume_30d", "velocity_30d", "counterparty_count_30d"],
                           "All signals within normal range for this account")],
                      "Account behavior has not materially changed",
                      "Transaction patterns match historical norms"),
            ],
            resolution_criteria="KYC is overdue but customer profile shows no material changes; "
                               "schedule KYC refresh and close alert",
            weight=1.5,
        ),
        FPCategory(
            category_id="KYC_FP_LOW_ACTIVITY",
            alert_type="kyc_refresh",
            triggering_rule="KYC_001",
            triggering_signals=["kyc_age_days"],
            flag_reason="KYC review period exceeded for account with minimal activity",
            legitimate_explanation="Low-activity account with no risk indicators; KYC refresh is procedural",
            applicable_dispositions=["FALSE_POSITIVE", "INSUFFICIENT_INFO"],
            evidence_datasets=[D.CUSTOMER, D.ACCOUNT, D.TRANSACTION_AGGREGATION],
            investigation_steps=[
                _step(1, "Review account activity level over past 12 months",
                      [_eq(D.TRANSACTION_AGGREGATION,
                           "Monthly activity summary for past 12 months",
                           ["total_credit_count", "total_debit_count", "total_credit_amount"],
                           "Very low activity (< 5 transactions/month, small amounts)")],
                      "Account has minimal activity, reducing risk exposure",
                      "Low-activity dormant or savings account with small balances"),
            ],
            resolution_criteria="Account has minimal activity and no risk indicators; "
                               "KYC refresh is procedural administrative matter",
            weight=1.0,
        ),
    ],

    # ===================================================================
    # DECLARED MISMATCH  (DECL_001: declared_vs_actual_volume > 2.0)
    # ===================================================================
    "declared_mismatch": [
        FPCategory(
            category_id="DECL_FP_GROWTH",
            alert_type="declared_mismatch",
            triggering_rule="DECL_001",
            triggering_signals=["declared_vs_actual_volume", "volume_30d"],
            flag_reason="Actual transaction volume exceeds declared monthly turnover by more than 2x",
            legitimate_explanation="Business has grown since declaration was made; declared turnover is stale but legitimate",
            applicable_dispositions=["NORMAL_BUSINESS", "CUSTOMER_EXPLAINED"],
            evidence_datasets=[D.ACCOUNT, D.TRANSACTION_AGGREGATION, D.CUSTOMER_COMPANY],
            investigation_steps=[
                _step(1, "Compare declared turnover date to current volume trend",
                      [_eq(D.ACCOUNT,
                           "When turnover was last declared",
                           ["declared_monthly_turnover", "kyc_date", "declared_purpose"],
                           "Declaration date is > 6 months old"),
                       _eq(D.TRANSACTION_AGGREGATION,
                           "Monthly volume trend showing growth trajectory",
                           ["period_start", "total_credit_amount", "total_debit_amount"],
                           "Volume has grown gradually over multiple months")],
                      "Volume growth is gradual and predates the alert by months",
                      "Trend shows organic growth, not sudden unexplained jump"),
                _step(2, "Verify business has growth indicators",
                      [_eq(D.CUSTOMER_COMPANY,
                           "Business growth metrics",
                           ["annual_revenue", "employee_count", "operational_countries"],
                           "Revenue or headcount increased since last declaration")],
                      "Business fundamentals support higher volume",
                      "Documented business expansion"),
            ],
            resolution_criteria="Volume exceeds declaration due to organic business growth; "
                               "recommend updating declared turnover at next KYC refresh",
            weight=1.5,
        ),
        FPCategory(
            category_id="DECL_FP_STALE_DECLARATION",
            alert_type="declared_mismatch",
            triggering_rule="DECL_001",
            triggering_signals=["declared_vs_actual_volume", "volume_30d"],
            flag_reason="Activity exceeds declared turnover significantly",
            legitimate_explanation="Original declaration was conservative or based on projected (not actual) activity",
            applicable_dispositions=["FALSE_POSITIVE", "CUSTOMER_EXPLAINED"],
            evidence_datasets=[D.ACCOUNT, D.CUSTOMER, D.TRANSACTION_AGGREGATION],
            investigation_steps=[
                _step(1, "Review the age of the declaration and compare with actual history",
                      [_eq(D.ACCOUNT,
                           "Declaration date and declared values",
                           ["declared_monthly_turnover", "kyc_date", "opened_date"],
                           "Declaration made at account opening with projected values"),
                       _eq(D.TRANSACTION_AGGREGATION,
                           "Actual monthly volumes since account opening",
                           ["period_start", "total_credit_amount", "total_debit_amount"],
                           "Actual volumes have always exceeded declaration")],
                      "Declaration was conservative from day one; actual volume has been consistent",
                      "Volume has been stable but above declaration since inception"),
            ],
            resolution_criteria="Declaration was conservative; actual volume has been consistently "
                               "above declared amount without any suspicious changes in pattern",
            weight=1.0,
        ),
        FPCategory(
            category_id="DECL_FP_ONE_TIME",
            alert_type="declared_mismatch",
            triggering_rule="DECL_001",
            triggering_signals=["declared_vs_actual_volume", "volume_30d"],
            flag_reason="Monthly volume exceeds declared turnover due to one-time large transaction",
            legitimate_explanation="One-time event (property sale, bonus, business deal) temporarily pushed volume above declaration",
            applicable_dispositions=["CUSTOMER_EXPLAINED"],
            benign_trigger_type="business_acquisition",
            evidence_datasets=[D.TRANSACTION, D.ACCOUNT, D.COUNTERPARTY],
            investigation_steps=[
                _step(1, "Isolate the one-time transaction causing the mismatch",
                      [_eq(D.TRANSACTION,
                           "Largest transactions in the alert period",
                           ["amount", "txn_type", "purpose_description", "counterparty_name_raw"],
                           "Single large transaction accounts for majority of the excess")],
                      "Mismatch is driven by one identifiable large transaction",
                      "One-time event, not a pattern change"),
                _step(2, "Verify the one-time transaction has a legitimate purpose",
                      [_eq(D.COUNTERPARTY,
                           "Counterparty details on the large transaction",
                           ["name", "type", "country"],
                           "Counterparty is identifiable and legitimate")],
                      "Transaction has documented business purpose",
                      "Verified one-time event with legitimate counterparty"),
            ],
            resolution_criteria="Mismatch caused by documented one-time event; "
                               "underlying regular volume remains within declaration",
            weight=0.7,
        ),
    ],

    # ===================================================================
    # NEW COUNTERPARTIES  (NEWCP_001: new_counterparty_rate > 0.5 + velocity > 10)
    # ===================================================================
    "new_counterparties": [
        FPCategory(
            category_id="NEWCP_FP_EXPANSION",
            alert_type="new_counterparties",
            triggering_rule="NEWCP_001",
            triggering_signals=["new_counterparty_rate", "velocity_30d"],
            flag_reason="Unusual surge in new counterparties (> 50% of recent counterparties are new)",
            legitimate_explanation="Business expansion adding new customers or suppliers",
            applicable_dispositions=["NORMAL_BUSINESS", "FALSE_POSITIVE"],
            evidence_datasets=[D.COUNTERPARTY_PROFILE, D.COUNTERPARTY, D.CUSTOMER_COMPANY, D.TRANSACTION],
            investigation_steps=[
                _step(1, "Profile the new counterparties — are they in the same industry/region?",
                      [_eq(D.COUNTERPARTY_PROFILE,
                           "New counterparties in the last 30 days",
                           ["name", "type", "country", "first_seen_date", "txn_count", "total_volume_usd"],
                           "New counterparties are in related industries/geographies"),
                       _eq(D.CUSTOMER_COMPANY,
                           "Customer's industry and operational scope",
                           ["industry_code", "operational_countries", "employee_count"],
                           "Business is in growth phase or expansion")],
                      "New counterparties align with customer's business model and expansion",
                      "New counterparties are credible businesses in related sectors"),
                _step(2, "Verify transaction sizes with new counterparties are reasonable",
                      [_eq(D.TRANSACTION,
                           "Transactions with new counterparties",
                           ["amount", "txn_type", "counterparty_name_raw", "purpose_description"],
                           "Transaction sizes are reasonable for the business type")],
                      "Transaction volumes with new counterparties are proportionate",
                      "No unusually large first-time transactions"),
            ],
            resolution_criteria="New counterparties reflect documented business expansion; "
                               "all are identifiable entities with reasonable transaction volumes",
            weight=1.5,
        ),
        FPCategory(
            category_id="NEWCP_FP_VENDOR_CHANGE",
            alert_type="new_counterparties",
            triggering_rule="NEWCP_001",
            triggering_signals=["new_counterparty_rate", "velocity_30d"],
            flag_reason="High rate of new counterparties detected in recent transaction activity",
            legitimate_explanation="Vendor/supplier changeover — company switched suppliers, causing new counterparty spike",
            applicable_dispositions=["FALSE_POSITIVE", "NORMAL_BUSINESS"],
            evidence_datasets=[D.COUNTERPARTY_PROFILE, D.TRANSACTION, D.COUNTERPARTY],
            investigation_steps=[
                _step(1, "Check if old counterparties stopped and new ones started simultaneously",
                      [_eq(D.COUNTERPARTY_PROFILE,
                           "Counterparty activity timeline",
                           ["name", "first_seen_date", "last_seen_date", "txn_count"],
                           "Old vendors show last activity before new vendors appear")],
                      "Pattern shows replacement, not addition (old vendors stopped, new ones started)",
                      "Vendor changeover pattern with no overlap concerns"),
            ],
            resolution_criteria="New counterparties replace old ones in a vendor changeover; "
                               "total counterparty count remains stable",
            weight=1.0,
        ),
    ],

    # ===================================================================
    # DORMANT REACTIVATION  (DORM_001: dormancy_days > 180 + velocity > 5)
    # ===================================================================
    "dormant_reactivation": [
        FPCategory(
            category_id="DORM_FP_RESUMED_OPS",
            alert_type="dormant_reactivation",
            triggering_rule="DORM_001",
            triggering_signals=["dormancy_days", "velocity_30d"],
            flag_reason="Previously dormant account (180+ days inactive) suddenly showing activity",
            legitimate_explanation="Seasonal business resuming operations after off-season dormancy",
            applicable_dispositions=["FALSE_POSITIVE", "NORMAL_BUSINESS"],
            evidence_datasets=[D.ACCOUNT, D.TRANSACTION, D.TRANSACTION_AGGREGATION, D.CUSTOMER_COMPANY],
            investigation_steps=[
                _step(1, "Check if dormancy pattern is recurring (seasonal business)",
                      [_eq(D.TRANSACTION_AGGREGATION,
                           "Monthly activity over 2+ years to identify seasonal dormancy",
                           ["period_start", "total_credit_count", "total_debit_count"],
                           "Account shows recurring dormancy in same months each year")],
                      "Dormancy is part of a recurring seasonal pattern",
                      "Account has cyclical active/dormant periods"),
                _step(2, "Verify reactivation activity matches pre-dormancy patterns",
                      [_eq(D.TRANSACTION,
                           "Recent transactions compared to last active period",
                           ["amount", "txn_type", "counterparty_name_raw"],
                           "Activity is similar to previous active periods"),
                       _eq(D.CUSTOMER_COMPANY,
                           "Business type supporting seasonal operations",
                           ["industry_code", "industry_description"],
                           "Industry is known seasonal (agriculture, tourism, construction)")],
                      "Current activity matches historical patterns for this account",
                      "Same counterparties, similar amounts, same transaction types"),
            ],
            resolution_criteria="Dormancy is part of established seasonal business cycle; "
                               "reactivation activity mirrors prior active periods",
            weight=1.5,
        ),
        FPCategory(
            category_id="DORM_FP_NEW_PURPOSE",
            alert_type="dormant_reactivation",
            triggering_rule="DORM_001",
            triggering_signals=["dormancy_days", "velocity_30d"],
            flag_reason="Dormant account reactivated with significant transaction volume",
            legitimate_explanation="Account repurposed for new legitimate use (e.g., savings account now used for business)",
            applicable_dispositions=["CUSTOMER_EXPLAINED", "INSUFFICIENT_INFO"],
            evidence_datasets=[D.ACCOUNT, D.CUSTOMER, D.TRANSACTION],
            investigation_steps=[
                _step(1, "Review account purpose and any recent changes",
                      [_eq(D.ACCOUNT,
                           "Account purpose and recent modifications",
                           ["declared_purpose", "declared_monthly_turnover", "kyc_date"],
                           "Account purpose may have been updated recently")],
                      "Account has been repurposed with updated declarations",
                      "Customer updated account purpose to match new activity"),
                _step(2, "Assess whether new activity is consistent with customer profile",
                      [_eq(D.TRANSACTION,
                           "New activity transactions",
                           ["amount", "txn_type", "counterparty_name_raw", "purpose_description"],
                           "Transactions are reasonable for the customer's profile")],
                      "New activity is plausible given customer's overall profile",
                      "Activity is within expected range for this customer type"),
            ],
            resolution_criteria="Account reactivation has plausible legitimate purpose; "
                               "customer profile supports the new activity pattern",
            weight=1.0,
        ),
    ],

    # ===================================================================
    # HIGH CASH  (CASH_001: cash_intensity > 0.3)
    # ===================================================================
    "high_cash": [
        FPCategory(
            category_id="CASH_FP_BUSINESS_OPS",
            alert_type="high_cash",
            triggering_rule="CASH_001",
            triggering_signals=["cash_intensity"],
            flag_reason="Cash transaction ratio exceeds 30% of total transaction volume",
            legitimate_explanation="Cash-intensive business operations (restaurant, retail, convenience store, laundromat)",
            applicable_dispositions=["NORMAL_BUSINESS", "FALSE_POSITIVE"],
            benign_trigger_type="large_cash_business",
            evidence_datasets=[D.CUSTOMER_COMPANY, D.TRANSACTION, D.ACCOUNT_SIGNALS, D.TRANSACTION_AGGREGATION],
            investigation_steps=[
                _step(1, "Verify customer operates in a cash-intensive industry",
                      [_eq(D.CUSTOMER_COMPANY,
                           "Industry and business type",
                           ["industry_code", "industry_description", "company_type"],
                           "Industry is known cash-intensive (retail, F&B, hospitality, laundry)")],
                      "Business type justifies high cash intensity",
                      "Confirmed cash-intensive industry"),
                _step(2, "Analyze cash deposit patterns for consistency",
                      [_eq(D.TRANSACTION,
                           "Cash deposits over 90 days",
                           ["amount", "value_date", "txn_type", "channel"],
                           "Regular daily/weekly cash deposits with expected weekend dips"),
                       _eq(D.TRANSACTION_AGGREGATION,
                           "Monthly cash vs non-cash volume breakdown",
                           ["cash_volume", "total_credit_amount", "total_debit_amount"],
                           "Cash ratio has been stable over time")],
                      "Cash deposit pattern is consistent and matches business operating hours",
                      "Regular deposits with predictable daily/weekly rhythm"),
                _step(3, "Ensure cash amounts align with business scale",
                      [_eq(D.ACCOUNT_SIGNALS,
                           "Cash intensity signal and volume metrics",
                           ["cash_intensity", "volume_30d", "velocity_30d"],
                           "Cash volume proportionate to declared business revenue")],
                      "Cash volume is proportionate to declared turnover and business size",
                      "Cash deposits match expected revenue for business type/size"),
            ],
            resolution_criteria="High cash intensity is explained by documented cash-intensive business "
                               "operations with consistent deposit patterns proportionate to business size",
            weight=1.5,
        ),
        FPCategory(
            category_id="CASH_FP_INDUSTRY_NORM",
            alert_type="high_cash",
            triggering_rule="CASH_001",
            triggering_signals=["cash_intensity"],
            flag_reason="Elevated proportion of cash transactions above monitoring threshold",
            legitimate_explanation="Cash ratio is normal for customer's industry segment even if above general threshold",
            applicable_dispositions=["FALSE_POSITIVE"],
            evidence_datasets=[D.CUSTOMER_COMPANY, D.ACCOUNT, D.ACCOUNT_SIGNALS],
            investigation_steps=[
                _step(1, "Compare cash intensity to industry peer group",
                      [_eq(D.CUSTOMER_COMPANY,
                           "Industry classification for peer comparison",
                           ["industry_code", "industry_description"],
                           "Industry peers typically have 30-70% cash intensity"),
                       _eq(D.ACCOUNT_SIGNALS,
                           "Account's cash intensity metric",
                           ["cash_intensity"],
                           "Cash ratio is within industry norm range")],
                      "Cash intensity falls within expected range for this industry",
                      "Not an outlier relative to industry peers"),
            ],
            resolution_criteria="Cash intensity is within the normal range for the customer's "
                               "industry segment; no other suspicious indicators present",
            weight=1.0,
        ),
    ],

    # ===================================================================
    # STRUCTURING  (STRUCT_001: structuring_score > 3)
    # ===================================================================
    "structuring": [
        FPCategory(
            category_id="STRUCT_FP_CASH_BUSINESS",
            alert_type="structuring",
            triggering_rule="STRUCT_001",
            triggering_signals=["structuring_score", "volume_30d"],
            flag_reason="Multiple transactions near CTR reporting threshold ($10,000) detected",
            legitimate_explanation="Cash-intensive business with daily deposit amounts that naturally fall near threshold",
            applicable_dispositions=["FALSE_POSITIVE", "NORMAL_BUSINESS"],
            benign_trigger_type="large_cash_business",
            evidence_datasets=[D.TRANSACTION, D.ACCOUNT, D.CUSTOMER_COMPANY, D.ACCOUNT_SIGNALS],
            investigation_steps=[
                _step(1, "Analyze near-threshold transactions for intentional splitting pattern",
                      [_eq(D.TRANSACTION,
                           "All transactions between $8,000 and $10,000 in alert period",
                           ["amount", "value_date", "txn_type", "channel"],
                           "Amounts vary naturally (not clustered at exactly $9,900-$9,999)"),
                       _eq(D.ACCOUNT_SIGNALS,
                           "Structuring score details",
                           ["structuring_score", "volume_30d", "velocity_30d"],
                           "Score is borderline, not extreme")],
                      "Amounts show natural variation (not precision-splitting to avoid threshold)",
                      "Amounts range broadly near threshold, not clustered just below"),
                _step(2, "Verify business type generates daily revenue near this amount",
                      [_eq(D.CUSTOMER_COMPANY,
                           "Business type and revenue scale",
                           ["industry_code", "annual_revenue", "employee_count"],
                           "Business daily revenue naturally falls in $5K-$15K range"),
                       _eq(D.ACCOUNT,
                           "Declared purpose and turnover",
                           ["declared_monthly_turnover", "declared_purpose"],
                           "Declared daily deposits align with near-threshold amounts")],
                      "Business revenue scale naturally produces deposits near threshold",
                      "Daily revenue matches deposit patterns"),
            ],
            resolution_criteria="Near-threshold deposits are a natural consequence of business daily revenue, "
                               "not intentional structuring; amounts show variation, not precision splitting",
            weight=1.5,
        ),
        FPCategory(
            category_id="STRUCT_FP_COINCIDENTAL",
            alert_type="structuring",
            triggering_rule="STRUCT_001",
            triggering_signals=["structuring_score"],
            flag_reason="Transactions near reporting threshold triggered structuring alert",
            legitimate_explanation="Coincidental near-threshold amounts not indicative of intentional evasion",
            applicable_dispositions=["FALSE_POSITIVE", "INSUFFICIENT_INFO"],
            benign_trigger_type="just_below_threshold",
            evidence_datasets=[D.TRANSACTION, D.ACCOUNT_SIGNALS, D.ACCOUNT],
            investigation_steps=[
                _step(1, "Examine whether near-threshold transactions are isolated incidents",
                      [_eq(D.TRANSACTION,
                           "Near-threshold transactions and their context",
                           ["amount", "value_date", "txn_type", "purpose_description"],
                           "Only 1-2 near-threshold transactions, not a systematic pattern")],
                      "Near-threshold transactions are infrequent and non-systematic",
                      "Isolated occurrences, not a deliberate pattern"),
                _step(2, "Review overall structuring score relative to account activity",
                      [_eq(D.ACCOUNT_SIGNALS,
                           "Structuring score in context of total transactions",
                           ["structuring_score", "velocity_30d", "volume_30d"],
                           "Low score relative to total transaction count")],
                      "Structuring score is marginal given overall transaction volume",
                      "Score barely crosses threshold with low conviction"),
            ],
            resolution_criteria="Near-threshold amounts are coincidental; no systematic splitting pattern, "
                               "score is borderline, and customer profile does not support structuring intent",
            weight=1.0,
        ),
    ],

    # ===================================================================
    # RAPID MOVEMENT  (RAPID_001: rapid_movement_score > 0.5)
    # ===================================================================
    "rapid_movement": [
        FPCategory(
            category_id="RAPID_FP_TREASURY",
            alert_type="rapid_movement",
            triggering_rule="RAPID_001",
            triggering_signals=["rapid_movement_score", "in_out_ratio"],
            flag_reason="Funds received and moved out quickly (within 48 hours), indicating possible layering",
            legitimate_explanation="Normal corporate treasury / cash management operations (sweep accounts, liquidity pooling)",
            applicable_dispositions=["FALSE_POSITIVE", "NORMAL_BUSINESS"],
            benign_trigger_type="rapid_movement_treasury",
            evidence_datasets=[D.TRANSACTION, D.ACCOUNT_OWNERSHIP, D.ACCOUNT, D.CUSTOMER_COMPANY],
            investigation_steps=[
                _step(1, "Verify account is a corporate/business account with treasury function",
                      [_eq(D.ACCOUNT,
                           "Account type and declared purpose",
                           ["account_type", "declared_purpose", "declared_segment"],
                           "Account purpose includes cash management, treasury, or operating"),
                       _eq(D.CUSTOMER_COMPANY,
                           "Company type and business operations",
                           ["company_type", "industry_code", "annual_revenue"],
                           "Corporate entity with treasury management needs")],
                      "Account serves a legitimate treasury/cash management function",
                      "Confirmed corporate treasury account"),
                _step(2, "Check if rapid movements are between same-owner accounts (internal sweeps)",
                      [_eq(D.ACCOUNT_OWNERSHIP,
                           "All accounts owned by this customer",
                           ["account_id", "customer_id", "ownership_pct"],
                           "Customer owns multiple accounts (sweep source and destination)"),
                       _eq(D.TRANSACTION,
                           "Rapid credit-debit pairs in 48-hour windows",
                           ["amount", "value_date", "txn_type", "counterparty_account_id"],
                           "Debits go to another account owned by the same customer")],
                      "Rapid movements are internal transfers between same-owner accounts",
                      "Sweep pattern between own accounts, not third-party layering"),
            ],
            resolution_criteria="Rapid fund movement is normal treasury operations between "
                               "same-owner accounts; no third-party layering indicators",
            weight=1.5,
        ),
        FPCategory(
            category_id="RAPID_FP_CLOSING",
            alert_type="rapid_movement",
            triggering_rule="RAPID_001",
            triggering_signals=["rapid_movement_score"],
            flag_reason="Rapid in-out fund movement detected within short timeframe",
            legitimate_explanation="Time-sensitive transaction (real estate closing, business deal, urgent vendor payment)",
            applicable_dispositions=["CUSTOMER_EXPLAINED", "FALSE_POSITIVE"],
            benign_trigger_type="real_estate_closing",
            evidence_datasets=[D.TRANSACTION, D.COUNTERPARTY, D.ACCOUNT],
            investigation_steps=[
                _step(1, "Identify the rapid credit-debit pair and verify legitimate purpose",
                      [_eq(D.TRANSACTION,
                           "Credit and subsequent debit within 48 hours",
                           ["amount", "value_date", "txn_type", "purpose_description",
                            "counterparty_name_raw"],
                           "Credit is from a known source, debit is for a documented purpose")],
                      "Both sides of the rapid movement have identifiable legitimate purposes",
                      "Funds received for documented purpose, immediately used for related payment"),
                _step(2, "Verify counterparties on both ends are legitimate entities",
                      [_eq(D.COUNTERPARTY,
                           "Counterparties on the credit and debit legs",
                           ["name", "type", "country", "bank_name"],
                           "Both counterparties are identifiable, legitimate entities")],
                      "Counterparties are verified on both legs of the transaction",
                      "Known entities (e.g., mortgage lender credit, title company debit)"),
            ],
            resolution_criteria="Rapid movement is a time-sensitive legitimate transaction "
                               "with verified counterparties on both sides",
            weight=1.0,
        ),
    ],

    # ===================================================================
    # NETWORK RISK  (NET_001: risk_flow_in > 10K)
    # ===================================================================
    "network_risk": [
        FPCategory(
            category_id="NET_FP_LEGIT_HUB",
            alert_type="network_risk",
            triggering_rule="NET_001",
            triggering_signals=["risk_flow_in", "degree_centrality"],
            flag_reason="High-value fund flows from entities in risk-elevated network cluster",
            legitimate_explanation="Account is a legitimate business hub (payments aggregator, distributor) "
                                  "with naturally high connectivity",
            applicable_dispositions=["FALSE_POSITIVE", "NORMAL_BUSINESS"],
            evidence_datasets=[D.NETWORK_METRICS, D.CUSTOMER_COMPANY, D.COUNTERPARTY, D.TRANSACTION],
            investigation_steps=[
                _step(1, "Review network position and verify business model justifies high connectivity",
                      [_eq(D.NETWORK_METRICS,
                           "Account's network centrality and risk metrics",
                           ["degree_centrality", "betweenness_centrality", "risk_flow_in", "risk_flow_out"],
                           "High centrality is proportionate to business size"),
                       _eq(D.CUSTOMER_COMPANY,
                           "Business model and scale",
                           ["industry_code", "company_type", "annual_revenue", "employee_count"],
                           "Business model involves many counterparty relationships")],
                      "Network position is consistent with legitimate business hub role",
                      "Distributor/aggregator model naturally creates high connectivity"),
                _step(2, "Verify fund flow counterparties are legitimate known entities",
                      [_eq(D.COUNTERPARTY,
                           "Top fund flow counterparties by volume",
                           ["name", "type", "country", "txn_count", "total_volume"],
                           "Counterparties are established business partners")],
                      "Fund flows are with identifiable, legitimate counterparties",
                      "No flows from unknown or shell-like entities"),
            ],
            resolution_criteria="High network connectivity and fund flows are consistent with "
                               "legitimate business hub role; all major counterparties are verified",
            weight=1.5,
        ),
        FPCategory(
            category_id="NET_FP_SHARED_SERVICE",
            alert_type="network_risk",
            triggering_rule="NET_001",
            triggering_signals=["risk_flow_in", "pep_distance", "sanctions_distance"],
            flag_reason="Network proximity to PEP or elevated-risk entity triggered alert",
            legitimate_explanation="Indirect connection through shared service provider (bank, legal firm, accounting firm) "
                                  "— no direct relationship with the flagged entity",
            applicable_dispositions=["FALSE_POSITIVE"],
            evidence_datasets=[D.NETWORK_METRICS, D.CUSTOMER_RELATIONSHIP, D.COUNTERPARTY],
            investigation_steps=[
                _step(1, "Trace the path to the flagged entity and identify intermediary",
                      [_eq(D.NETWORK_METRICS,
                           "Path from account to flagged entity",
                           ["pep_distance", "sanctions_distance", "community_id"],
                           "Connection is 3+ hops through a shared intermediary"),
                       _eq(D.CUSTOMER_RELATIONSHIP,
                           "Direct relationships of this customer",
                           ["related_customer_id", "relationship_type"],
                           "No direct relationship with flagged entity")],
                      "Connection to flagged entity is indirect (3+ hops) through shared service provider",
                      "No direct business or personal relationship with flagged entity"),
            ],
            resolution_criteria="Network flag is due to indirect connection through shared service provider; "
                               "no direct relationship with the elevated-risk entity",
            weight=1.0,
        ),
    ],

    # ===================================================================
    # ADVERSE MEDIA  (MEDIA_001: adverse_media_flag == True)
    # ===================================================================
    "adverse_media": [
        FPCategory(
            category_id="MEDIA_FP_NAME_MATCH",
            alert_type="adverse_media",
            triggering_rule="MEDIA_001",
            triggering_signals=["adverse_media_flag", "adverse_media_count"],
            flag_reason="Adverse media screening returned positive match for customer name",
            legitimate_explanation="Name match is a false hit — different person/entity with same or similar name",
            applicable_dispositions=["FALSE_POSITIVE"],
            evidence_datasets=[D.NEWS_EVENT, D.CUSTOMER_PERSON, D.CUSTOMER_IDENTIFIER, D.CUSTOMER_ADDRESS],
            investigation_steps=[
                _step(1, "Review the adverse media hit and compare identifying details",
                      [_eq(D.NEWS_EVENT,
                           "Adverse media event details",
                           ["event_type", "headline", "severity", "entity_name_matched", "match_confidence"],
                           "Match confidence is low or medium; different identifying details"),
                       _eq(D.CUSTOMER_PERSON,
                           "Customer's identifying information",
                           ["first_name", "last_name", "date_of_birth", "nationality"],
                           "Customer details differ from media subject")],
                      "Identifying details (DOB, nationality, location) do not match media subject",
                      "Different person with same name — false name match"),
                _step(2, "Confirm no geographic or temporal overlap between customer and media subject",
                      [_eq(D.CUSTOMER_ADDRESS,
                           "Customer's current and historical addresses",
                           ["address_type", "city", "state", "country"],
                           "Customer has never been in the jurisdiction mentioned in media")],
                      "Customer has no connection to locations or events in adverse media",
                      "Geographic and temporal mismatch confirms false hit"),
            ],
            resolution_criteria="Adverse media hit is a name-only match; identifying details "
                               "(DOB, nationality, address) confirm different individual/entity",
            weight=1.5,
        ),
        FPCategory(
            category_id="MEDIA_FP_RESOLVED",
            alert_type="adverse_media",
            triggering_rule="MEDIA_001",
            triggering_signals=["adverse_media_flag", "adverse_media_severity"],
            flag_reason="Adverse media screening flagged historical negative coverage",
            legitimate_explanation="Historical media event has been resolved (charges dropped, acquitted, settled)",
            applicable_dispositions=["FALSE_POSITIVE", "INSUFFICIENT_INFO"],
            evidence_datasets=[D.NEWS_EVENT, D.CUSTOMER_PERSON, D.CUSTOMER_COMPANY],
            investigation_steps=[
                _step(1, "Review the adverse media timeline and check for resolution",
                      [_eq(D.NEWS_EVENT,
                           "All media events for this entity, ordered by date",
                           ["event_date", "event_type", "headline", "severity", "credibility"],
                           "Most recent event shows resolution (acquittal, settlement, retraction)")],
                      "Adverse media has subsequent coverage showing resolution",
                      "Matter resolved — charges dropped, case settled, or retracted"),
            ],
            resolution_criteria="Adverse media relates to a matter that has been subsequently resolved; "
                               "no ongoing legal or regulatory risk",
            weight=1.0,
        ),
    ],
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_fp_categories_for_alert(alert_type: str) -> List[FPCategory]:
    """Get all FP categories applicable to a given alert type."""
    return FP_CATEGORIES.get(alert_type, FP_CATEGORIES.get("volume_anomaly", []))


def select_fp_category(
    alert_type: str,
    disposition: str,
    rng: random.Random = None,
) -> FPCategory:
    """Select a random FP category appropriate for the alert type and disposition.

    Filters categories by applicable_dispositions, then selects weighted random.
    Falls back to all categories for the type if no disposition match.
    Falls back to volume_anomaly categories if alert_type is unknown.
    """
    categories = get_fp_categories_for_alert(alert_type)
    if not categories:
        categories = FP_CATEGORIES.get("volume_anomaly", [])

    # Filter by disposition
    matching = [c for c in categories if disposition in c.applicable_dispositions]
    if not matching:
        matching = categories  # Fallback: use all categories for this type

    # Weighted random selection
    _rng = rng or random
    weights = [c.weight for c in matching]
    return _rng.choices(matching, weights=weights, k=1)[0]


def build_fp_investigation_playbooks_summary(
    ground_truth_resolutions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build the fp_investigation_playbooks.json summary from resolved alerts.

    Aggregates all FP categories used in the dataset with counts, distributions,
    and evidence dataset frequency.
    """
    fp_resolutions = [r for r in ground_truth_resolutions if not r.get("is_true_positive")]
    total_fp = len(fp_resolutions)

    # Count by category
    category_counts: Counter = Counter()
    category_dispositions: Dict[str, Counter] = defaultdict(Counter)
    alert_type_counts: Dict[str, Counter] = defaultdict(Counter)
    evidence_frequency: Counter = Counter()

    for r in fp_resolutions:
        cat_id = r.get("fp_category")
        if not cat_id:
            continue
        category_counts[cat_id] += 1
        category_dispositions[cat_id][r.get("disposition", "UNKNOWN")] += 1
        alert_type_counts[r.get("alert_type", "unknown")][cat_id] += 1

        for ds in r.get("fp_evidence_datasets", []):
            evidence_frequency[ds] += 1

    # Build per-category details
    categories_detail = {}
    for cat_id, count in category_counts.most_common():
        # Find the FPCategory definition
        fp_cat = None
        for cats in FP_CATEGORIES.values():
            for c in cats:
                if c.category_id == cat_id:
                    fp_cat = c
                    break
            if fp_cat:
                break

        categories_detail[cat_id] = {
            "alert_type": fp_cat.alert_type if fp_cat else "unknown",
            "flag_reason": fp_cat.flag_reason if fp_cat else "",
            "legitimate_explanation": fp_cat.legitimate_explanation if fp_cat else "",
            "evidence_datasets": [d.value for d in fp_cat.evidence_datasets] if fp_cat else [],
            "investigation_steps_count": len(fp_cat.investigation_steps) if fp_cat else 0,
            "resolution_criteria": fp_cat.resolution_criteria if fp_cat else "",
            "count": count,
            "percentage_of_fp": round(count / max(1, total_fp) * 100, 1),
            "disposition_breakdown": dict(category_dispositions[cat_id]),
        }

    # Build per-alert-type summary
    by_alert_type = {}
    for atype, cat_counter in alert_type_counts.items():
        by_alert_type[atype] = {
            "total": sum(cat_counter.values()),
            "categories": list(cat_counter.keys()),
            "category_counts": dict(cat_counter),
        }

    return {
        "description": "Summary of FP categories and investigation playbooks used in this dataset",
        "total_fp_alerts": total_fp,
        "total_fp_categories_used": len(category_counts),
        "categories": categories_detail,
        "by_alert_type": by_alert_type,
        "evidence_dataset_frequency": dict(evidence_frequency.most_common()),
    }
