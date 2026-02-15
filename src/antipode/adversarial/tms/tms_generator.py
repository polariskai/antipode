"""
TMS Alert Generator - generates realistic Transaction Monitoring System alerts.

Takes a MixedDataset (entities, accounts, transactions with ground truth) and
produces a full TMS alert queue with >95% false positive rate, rich alert
packages, and separated ground truth resolution files.

This simulates the output of a Tier 1 bank's TMS that the AML detection
agent swarm will consume as input.
"""

import json
import csv
import random
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from uuid import uuid4
from collections import Counter, defaultdict

from .alert_packager import AlertPackager, AlertPackage
from .narrative_templates import (
    generate_investigation_note,
    select_analyst,
    FP_ACTIVITY_TYPES,
)
from ...data.generators.alert_generator import AlertRulesEngine
from ...data.generators.signal_generator import SignalGenerator
from ...data.models.alert import Alert, AlertRiskLevel, AlertStatus


@dataclass
class TMSConfig:
    """Configuration for TMS alert generation."""

    # FP rate target (>95% required)
    target_fp_rate: float = 0.95

    # Alert generation volume
    alerts_per_1000_accounts: int = 50  # How many alerts to generate per 1K accounts

    # Lookback window
    lookback_days: int = 30

    # Prior alert generation
    include_prior_alerts: bool = True
    prior_alert_account_pct: float = 0.30  # 30% of accounts get prior alerts
    prior_alerts_per_account: Tuple[int, int] = (1, 3)  # range

    # Analyst simulation
    analyst_pool_size: int = 10
    investigation_days_range: Tuple[int, int] = (2, 15)

    # SAR filing
    sar_filing_rate: float = 0.03  # 3% of alerts -> SAR (all TPs + some HI risk)

    # FP alert distribution by type
    fp_type_weights: Dict[str, float] = field(default_factory=lambda: {
        "volume_anomaly": 0.25,
        "round_amounts": 0.20,
        "high_risk_corridor": 0.12,
        "kyc_refresh": 0.10,
        "declared_mismatch": 0.10,
        "new_counterparties": 0.08,
        "dormant_reactivation": 0.05,
        "high_cash": 0.05,
        "structuring": 0.03,
        "rapid_movement": 0.02,
    })

    # FP disposition distribution
    fp_disposition_weights: Dict[str, float] = field(default_factory=lambda: {
        "FALSE_POSITIVE": 0.60,
        "NORMAL_BUSINESS": 0.25,
        "CUSTOMER_EXPLAINED": 0.10,
        "INSUFFICIENT_INFO": 0.05,
    })

    def validate(self):
        if self.target_fp_rate < 0.90 or self.target_fp_rate > 0.999:
            raise ValueError(f"target_fp_rate must be between 0.90 and 0.999, got {self.target_fp_rate}")


@dataclass
class TMSOutput:
    """Complete TMS output with alert packages and ground truth."""

    dataset_id: str
    alert_packages: List[AlertPackage]
    ground_truth_resolutions: List[Dict[str, Any]]
    bank_data: Dict[str, List[Dict[str, Any]]]  # customers, accounts, txns, signals
    summary: Dict[str, Any]
    config: TMSConfig

    def save(self, output_dir: str) -> Path:
        """Save TMS output with proper separation."""
        output_path = Path(output_dir) / self.dataset_id
        output_path.mkdir(parents=True, exist_ok=True)

        # === ALERTS (what AML agents see) ===
        alerts_path = output_path / "alerts"
        alerts_path.mkdir(exist_ok=True)

        # Full alert queue
        alert_queue = [pkg.to_dict() for pkg in self.alert_packages]
        with open(alerts_path / "alert_queue.json", "w") as f:
            json.dump(alert_queue, f, indent=2, default=str)

        # Individual alert files
        for pkg in self.alert_packages:
            with open(alerts_path / f"{pkg.alert_id}.json", "w") as f:
                json.dump(pkg.to_dict(), f, indent=2, default=str)

        # Alert index CSV
        index_data = [pkg.to_summary_dict() for pkg in self.alert_packages]
        if index_data:
            fieldnames = list(index_data[0].keys())
            with open(alerts_path / "alert_index.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(index_data)

        # === BANK DATA (queryable by agents) ===
        bank_path = output_path / "bank_data"
        bank_path.mkdir(exist_ok=True)

        for data_type, records in self.bank_data.items():
            # Strip ground truth from bank data
            clean_records = [
                {k: v for k, v in r.items() if not k.startswith("_")}
                for r in records
            ]
            with open(bank_path / f"{data_type}.json", "w") as f:
                json.dump(clean_records, f, indent=2, default=str)

            # Also save CSV
            if clean_records:
                # Flatten nested dicts for CSV
                flat_records = []
                all_keys = set()
                for r in clean_records:
                    flat = {}
                    for k, v in r.items():
                        if isinstance(v, dict):
                            for sk, sv in v.items():
                                flat[f"{k}.{sk}"] = sv
                                all_keys.add(f"{k}.{sk}")
                        elif isinstance(v, (list, set)):
                            flat[k] = json.dumps(v) if v else ""
                            all_keys.add(k)
                        else:
                            flat[k] = v
                            all_keys.add(k)
                    flat_records.append(flat)

                fieldnames = sorted(all_keys)
                with open(bank_path / f"{data_type}.csv", "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(flat_records)

        # === GROUND TRUTH (for evaluation) ===
        gt_path = output_path / "ground_truth"
        gt_path.mkdir(exist_ok=True)

        # Alert resolutions
        with open(gt_path / "alert_resolutions.json", "w") as f:
            json.dump(self.ground_truth_resolutions, f, indent=2, default=str)

        # Alert resolutions CSV
        if self.ground_truth_resolutions:
            fieldnames = list(self.ground_truth_resolutions[0].keys())
            with open(gt_path / "alert_resolutions.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(self.ground_truth_resolutions)

        # Summary
        with open(gt_path / "summary.json", "w") as f:
            json.dump(self.summary, f, indent=2, default=str)

        # Evaluation guide
        evaluation_guide = self._build_evaluation_guide()
        with open(gt_path / "evaluation_guide.json", "w") as f:
            json.dump(evaluation_guide, f, indent=2, default=str)

        print(f"\nTMS output saved to: {output_path}")
        print(f"  Alerts: {alerts_path} ({len(self.alert_packages)} alert packages)")
        print(f"  Bank data: {bank_path}")
        print(f"  Ground truth: {gt_path}")

        return output_path

    def _build_evaluation_guide(self) -> Dict[str, Any]:
        """Build evaluation guide for scoring agent performance."""
        tp_count = sum(1 for r in self.ground_truth_resolutions if r.get("is_true_positive"))
        fp_count = sum(1 for r in self.ground_truth_resolutions if not r.get("is_true_positive"))
        total = len(self.ground_truth_resolutions)

        return {
            "description": "Guide for evaluating AML detection agent performance",
            "total_alerts": total,
            "true_positives": tp_count,
            "false_positives": fp_count,
            "fp_rate": round(fp_count / total, 4) if total > 0 else 0,
            "metrics": {
                "precision": "TP_correctly_identified / (TP_correctly_identified + FP_incorrectly_escalated)",
                "recall": "TP_correctly_identified / total_true_positives",
                "specificity": "FP_correctly_dismissed / total_false_positives",
                "f1_score": "2 * (precision * recall) / (precision + recall)",
                "time_to_decision": "Average time agent takes per alert (seconds)",
                "escalation_accuracy": "Proportion of escalated alerts that are true SAR-able cases",
            },
            "scoring_rubric": {
                "excellent": "Recall > 0.95 AND Precision > 0.30",
                "good": "Recall > 0.90 AND Precision > 0.20",
                "acceptable": "Recall > 0.80 AND Precision > 0.10",
                "poor": "Recall < 0.80 OR Precision < 0.10",
            },
            "notes": [
                "In real AML operations, recall (catching all TPs) is more important than precision",
                "A 5% false negative rate (missing 1 in 20 suspicious cases) is considered unacceptable",
                "Agents should provide clear reasoning for each disposition decision",
                "SAR-able cases (CRITICAL risk) must always be escalated",
            ],
        }


class TMSAlertGenerator:
    """
    Generates realistic TMS alert datasets from mixed bank data.

    Pipeline:
    1. Index dataset (entities, accounts, transactions)
    2. Compute signals from transactions (reuses SignalGenerator)
    3. Generate rule-based alerts (reuses AlertRulesEngine)
    4. Pad with FP alerts to achieve >95% FP rate
    5. Package alerts with rich context (AlertPackager)
    6. Simulate investigation lifecycle (ground truth)
    7. Save with proper separation
    """

    def __init__(self, config: Optional[TMSConfig] = None):
        self.config = config or TMSConfig()
        self.config.validate()

        self.signal_generator = SignalGenerator()
        self.alert_engine = AlertRulesEngine(seed=42)
        self.packager = AlertPackager(lookback_days=self.config.lookback_days)

    def generate_tms_alerts(
        self,
        entities: List[Dict[str, Any]],
        accounts: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]],
        relationships: Optional[List[Dict[str, Any]]] = None,
    ) -> TMSOutput:
        """
        Generate complete TMS alert dataset.

        Pipeline:
        1. Index dataset and identify TP entities/accounts from ground truth
        2. Compute signals from transactions
        3. Generate rule-based alerts (may catch some TPs)
        4. Force-generate TP alerts for every TP account not already caught
        5. Pad with FP alerts to achieve target FP rate (>95%)
        6. Generate prior alerts for account history
        7. Package alerts with rich investigation context
        8. Simulate investigation lifecycle (ground truth)

        Args:
            entities: All entities (customers/companies)
            accounts: All accounts
            transactions: All transactions (with _ground_truth labels)
            relationships: Optional entity relationships

        Returns:
            TMSOutput with alert packages, ground truth, and bank data
        """
        dataset_id = f"TMS_{uuid4().hex[:12]}"
        print(f"\nGenerating TMS alerts: {dataset_id}")
        print(f"  Input: {len(entities)} entities, {len(accounts)} accounts, {len(transactions)} transactions")
        print(f"  Target FP rate: {self.config.target_fp_rate:.1%}")

        # Step 1: Build indices and identify TP entities
        print("  [1/8] Indexing dataset...")
        entity_by_id = {e.get("entity_id", e.get("customer_id", "")): e for e in entities}
        account_by_id = {a.get("account_id", ""): a for a in accounts}
        txns_by_account = defaultdict(list)
        for t in transactions:
            acct = t.get("account_id") or t.get("from_account_id", "")
            if acct:
                txns_by_account[acct].append(t)

        # Map accounts to entities
        account_to_entity = {}
        for a in accounts:
            eid = a.get("entity_id") or a.get("customer_id", "")
            account_to_entity[a.get("account_id", "")] = eid

        # Identify TP entities and their accounts from ground truth
        tp_entity_ids = set()
        tp_entity_typology = {}  # entity_id -> typology
        tp_entity_scenario = {}  # entity_id -> scenario_id
        for e in entities:
            gt = e.get("_ground_truth", {})
            if gt.get("is_suspicious") or gt.get("label") == "true_positive":
                eid = e.get("entity_id", e.get("customer_id", ""))
                tp_entity_ids.add(eid)
                tp_entity_typology[eid] = gt.get("typology", "unknown")
                tp_entity_scenario[eid] = gt.get("scenario_id", f"TP_{uuid4().hex[:8]}")

        # Build TP account set and scenario lookup for AlertRulesEngine
        tp_account_ids = set()
        gt_scenarios = []
        for a in accounts:
            eid = a.get("entity_id") or a.get("customer_id", "")
            acct_gt = a.get("_ground_truth", {})
            if eid in tp_entity_ids or acct_gt.get("is_suspicious") or acct_gt.get("label") == "true_positive":
                acct_id = a.get("account_id", "")
                tp_account_ids.add(acct_id)
                gt_scenarios.append({
                    "primary_account": acct_id,
                    "scenario_id": tp_entity_scenario.get(eid, f"TP_{uuid4().hex[:8]}"),
                    "typology": tp_entity_typology.get(eid, "unknown"),
                })

        print(f"         TP entities: {len(tp_entity_ids)}, TP accounts: {len(tp_account_ids)}")

        # Step 2: Compute signals
        print("  [2/8] Computing signals...")
        account_signals = self._compute_signals(accounts, transactions, entities)
        signals_by_account = {s.get("account_id", ""): s for s in account_signals}
        print(f"         Computed signals for {len(account_signals)} accounts")

        # Step 3: Generate rule-based alerts (may catch some TPs)
        print("  [3/8] Generating rule-based alerts...")
        raw_alerts = self.alert_engine.generate_alerts(
            account_signals=account_signals,
            scenarios=gt_scenarios,
            as_of_date=date.today(),
        )
        rule_tp_alerts = [a for a in raw_alerts if a.get("_true_positive")]
        fp_alerts_initial = [a for a in raw_alerts if not a.get("_true_positive")]

        # Track which TP accounts already have alerts from the rules engine
        covered_tp_accounts = set()
        for a in rule_tp_alerts:
            covered_tp_accounts.add(a.get("account_id", ""))

        print(f"         Generated {len(raw_alerts)} raw alerts (TP={len(rule_tp_alerts)}, FP={len(fp_alerts_initial)})")
        print(f"         TP accounts covered by rules: {len(covered_tp_accounts)} / {len(tp_account_ids)}")

        # Step 4: Force-generate TP alerts for uncovered TP accounts
        print("  [4/8] Generating TP alerts for uncovered suspicious accounts...")
        forced_tp_alerts = self._generate_forced_tp_alerts(
            tp_account_ids=tp_account_ids,
            covered_tp_accounts=covered_tp_accounts,
            tp_entity_typology=tp_entity_typology,
            tp_entity_scenario=tp_entity_scenario,
            account_to_entity=account_to_entity,
            signals_by_account=signals_by_account,
            txns_by_account=txns_by_account,
        )
        all_tp_alerts = rule_tp_alerts + forced_tp_alerts
        print(f"         Forced {len(forced_tp_alerts)} additional TP alerts")
        print(f"         Total TP alerts: {len(all_tp_alerts)}")

        # Step 5: Pad FP alerts to achieve target FP rate
        print("  [5/8] Padding FP alerts to reach target rate...")
        all_alerts = self._pad_fp_alerts(
            tp_alerts=all_tp_alerts,
            fp_alerts=fp_alerts_initial,
            account_signals=account_signals,
            entities=entities,
            accounts=accounts,
            transactions=transactions,
        )
        total = len(all_alerts)
        tp_count = sum(1 for a in all_alerts if a.get("_true_positive"))
        fp_count = total - tp_count
        actual_fp_rate = fp_count / total if total > 0 else 0
        print(f"         Total alerts: {total} (TP={tp_count}, FP={fp_count}, FP rate={actual_fp_rate:.1%})")

        # Step 6: Generate prior alerts
        prior_alerts_map = {}
        if self.config.include_prior_alerts:
            print("  [6/8] Generating prior alerts...")
            prior_alerts_map = self._generate_prior_alerts(accounts, account_signals)
            print(f"         Generated prior alerts for {len(prior_alerts_map)} accounts")
        else:
            print("  [6/8] Skipping prior alerts (disabled)")

        # Step 7: Package alerts
        print("  [7/8] Packaging alerts...")
        alert_packages = []
        for alert in all_alerts:
            account_id = alert.get("account_id", "")
            entity_id = account_to_entity.get(account_id, "")
            entity = entity_by_id.get(entity_id)
            account = account_by_id.get(account_id)

            # Get signals for this account
            signals = signals_by_account.get(account_id, {})

            # Get prior alerts
            prior = prior_alerts_map.get(account_id, [])

            pkg = self.packager.package_alert(
                alert=alert,
                entity=entity,
                account=account,
                all_transactions=txns_by_account.get(account_id, []),
                signals=signals,
                prior_alerts=prior,
            )
            alert_packages.append(pkg)

        # Step 8: Simulate lifecycle and build ground truth
        print("  [8/8] Simulating investigation lifecycle...")
        ground_truth = []
        for alert, pkg in zip(all_alerts, alert_packages):
            resolution = self._simulate_lifecycle(alert, pkg)
            ground_truth.append(resolution)

        # Build summary
        summary = self._build_summary(
            dataset_id=dataset_id,
            alert_packages=alert_packages,
            ground_truth=ground_truth,
            entities=entities,
            accounts=accounts,
            transactions=transactions,
        )

        # Build bank data for output
        bank_data = {
            "customers": entities,
            "accounts": accounts,
            "transactions": transactions,
            "signals": account_signals,
        }
        if relationships:
            bank_data["relationships"] = relationships

        output = TMSOutput(
            dataset_id=dataset_id,
            alert_packages=alert_packages,
            ground_truth_resolutions=ground_truth,
            bank_data=bank_data,
            summary=summary,
            config=self.config,
        )

        # Print summary
        print(f"\n{'='*60}")
        print(f"TMS ALERT GENERATION COMPLETE: {dataset_id}")
        print(f"{'='*60}")
        print(f"  Total Alerts: {total}")
        print(f"  True Positives: {tp_count} ({tp_count/total*100:.1f}%)")
        print(f"  False Positives: {fp_count} ({fp_count/total*100:.1f}%)")
        print(f"  FP Rate: {actual_fp_rate:.2%}")
        print(f"  Risk Distribution:")
        risk_dist = Counter(pkg.risk_level for pkg in alert_packages)
        for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL", "low", "medium", "high", "critical"]:
            if level in risk_dist:
                print(f"    {level.upper()}: {risk_dist[level]} ({risk_dist[level]/total*100:.1f}%)")
        print(f"  Alert Types:")
        type_dist = Counter(pkg.alert_type for pkg in alert_packages)
        for atype, count in type_dist.most_common():
            print(f"    {atype}: {count} ({count/total*100:.1f}%)")

        return output

    def _compute_signals(
        self,
        accounts: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Compute signals for all accounts using existing SignalGenerator."""
        try:
            # Ensure accounts have customer_id field (SignalGenerator expects it)
            # Adversarial-generated accounts may have entity_id but not customer_id,
            # or customer_id may be None
            prepared_accounts = []
            for a in accounts:
                acct = dict(a)
                if not acct.get("customer_id"):
                    acct["customer_id"] = acct.get("entity_id", "")
                prepared_accounts.append(acct)

            result = self.signal_generator.generate_signals(
                accounts=prepared_accounts,
                transactions=transactions,
                news_events=[],
                as_of_date=date.today(),
            )
            # SignalGenerator returns {'account_signals': [...]}
            if isinstance(result, dict):
                return result.get("account_signals", [])
            return result
        except Exception as e:
            print(f"    Warning: SignalGenerator failed ({e}), computing basic signals...")
            return self._compute_basic_signals(accounts, transactions, entities)

    def _compute_basic_signals(
        self,
        accounts: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Fallback: compute basic signals when SignalGenerator fails."""
        txns_by_account = defaultdict(list)
        for t in transactions:
            acct = t.get("account_id") or t.get("from_account_id", "")
            if acct:
                txns_by_account[acct].append(t)

        entity_by_id = {e.get("entity_id", e.get("customer_id", "")): e for e in entities}

        signals_list = []
        for account in accounts:
            account_id = account.get("account_id", "")
            entity_id = account.get("entity_id") or account.get("customer_id", "")
            entity = entity_by_id.get(entity_id, {})
            acct_txns = txns_by_account.get(account_id, [])

            # Basic behavioral signals
            amounts = [t.get("amount", 0) for t in acct_txns]
            total_volume = sum(amounts)
            txn_count = len(acct_txns)

            # Structuring score (count of txns near 10K threshold)
            threshold = 10000
            near_threshold = sum(1 for a in amounts if threshold * 0.9 <= a < threshold)

            # Cash intensity
            cash_txns = [t for t in acct_txns if t.get("txn_type", "").upper() in
                         ("CASH_DEPOSIT", "CASH_WITHDRAWAL", "CASH")]
            cash_intensity = len(cash_txns) / max(1, txn_count)

            # Round amount ratio
            round_txns = sum(1 for a in amounts if a > 0 and a == round(a, -2))
            round_ratio = round_txns / max(1, txn_count)

            # Counterparty analysis
            counterparties = set()
            for t in acct_txns:
                cp = t.get("counterparty_name_raw") or t.get("counterparty_id", "")
                if cp:
                    counterparties.add(cp)

            # Volume z-score (simplified)
            mean_vol = total_volume / max(1, 12)  # rough monthly average
            declared = account.get("declared_monthly_turnover", mean_vol)

            # Track contributing transactions
            contributing_txns = {
                "volume_30d": [t.get("txn_id", "") for t in acct_txns[:100]],
                "velocity_30d": [t.get("txn_id", "") for t in acct_txns[:100]],
                "structuring_score": [
                    t.get("txn_id", "") for t in acct_txns
                    if threshold * 0.9 <= t.get("amount", 0) < threshold
                ],
                "round_amount_ratio": [
                    t.get("txn_id", "") for t in acct_txns
                    if t.get("amount", 0) > 0 and t.get("amount", 0) == round(t.get("amount", 0), -2)
                ],
            }

            signals = {
                "account_id": account_id,
                "customer_id": entity_id,
                "velocity_30d": txn_count,
                "volume_30d": total_volume,
                "volume_90d": total_volume,
                "volume_zscore": abs(total_volume - declared * 12) / max(1, declared * 3) if declared else 1.0,
                "structuring_score": near_threshold,
                "rapid_movement_score": random.uniform(0, 0.3),
                "cash_intensity": cash_intensity,
                "round_amount_ratio": round_ratio,
                "corridor_risk_score": random.uniform(0, 30),
                "counterparty_concentration": 1.0 / max(1, len(counterparties)),
                "new_counterparty_rate": random.uniform(0, 0.3),
                "in_out_ratio": random.uniform(0.8, 1.2),
                "declared_vs_actual_volume": (total_volume / 12) / max(1, declared) if declared else 1.0,
                "dormancy_days": 0,
                # Network signals (synthetic)
                "degree_centrality": random.uniform(0, 0.1),
                "betweenness_centrality": random.uniform(0, 0.05),
                "risk_flow_in": random.uniform(0, 5000),
                "risk_flow_out": random.uniform(0, 5000),
                "pep_distance": random.randint(3, 10),
                "sanctions_distance": random.randint(4, 10),
                "cluster_risk_score": random.uniform(0, 20),
                # Entity signals
                "pep_flag": entity.get("pep_type", "none") != "none",
                "sanctions_flag": entity.get("sanctions_status", False),
                "adverse_media_flag": entity.get("adverse_media", False),
                "adverse_media_count": 0,
                "adverse_media_severity": 0.0,
                "jurisdiction_risk": random.uniform(0, 30),
                "kyc_age_days": random.randint(30, 500),
                "account_age_days": random.randint(30, 1000),
                # Contributing transactions for alert linkage
                "_contributing_txns": contributing_txns,
            }
            signals_list.append(signals)

        return signals_list

    # ---- Typology-to-alert-type mapping for realistic TP alerts ----
    TYPOLOGY_ALERT_MAP = {
        "structuring": [
            {"rule_id": "STRUCT_001", "rule_name": "Structuring Pattern", "alert_type": "structuring",
             "description": "Transactions structured to avoid reporting thresholds",
             "risk": AlertRiskLevel.HIGH},
            {"rule_id": "CASH_001", "rule_name": "High Cash Activity", "alert_type": "high_cash",
             "description": "Unusual proportion of cash transactions",
             "risk": AlertRiskLevel.MEDIUM},
        ],
        "layering": [
            {"rule_id": "RAPID_001", "rule_name": "Rapid Movement", "alert_type": "rapid_movement",
             "description": "Funds received and moved out quickly (layering pattern)",
             "risk": AlertRiskLevel.HIGH},
            {"rule_id": "NET_001", "rule_name": "Network Risk", "alert_type": "network_risk",
             "description": "Connected to high-risk entities in network",
             "risk": AlertRiskLevel.HIGH},
        ],
        "mule_network": [
            {"rule_id": "NET_001", "rule_name": "Network Risk", "alert_type": "network_risk",
             "description": "Connected to high-risk entities in network",
             "risk": AlertRiskLevel.HIGH},
            {"rule_id": "RAPID_001", "rule_name": "Rapid Movement", "alert_type": "rapid_movement",
             "description": "Funds flow through account rapidly — possible mule activity",
             "risk": AlertRiskLevel.CRITICAL},
        ],
        "shell_company": [
            {"rule_id": "DECL_001", "rule_name": "Declared vs Actual Mismatch", "alert_type": "declared_mismatch",
             "description": "Activity significantly exceeds declared turnover for shell entity",
             "risk": AlertRiskLevel.HIGH},
            {"rule_id": "NET_001", "rule_name": "Network Risk", "alert_type": "network_risk",
             "description": "Entity linked to complex ownership network",
             "risk": AlertRiskLevel.HIGH},
        ],
        "trade_based": [
            {"rule_id": "CORR_001", "rule_name": "High-Risk Corridor", "alert_type": "high_risk_corridor",
             "description": "Cross-border transactions to high-risk trade corridor",
             "risk": AlertRiskLevel.HIGH},
            {"rule_id": "VOL_ANOM_001", "rule_name": "Volume Anomaly", "alert_type": "volume_anomaly",
             "description": "Unusual transaction volumes inconsistent with declared trade activity",
             "risk": AlertRiskLevel.MEDIUM},
        ],
        "integration": [
            {"rule_id": "VOL_ANOM_001", "rule_name": "Volume Anomaly", "alert_type": "volume_anomaly",
             "description": "Large value transactions with unclear economic purpose",
             "risk": AlertRiskLevel.HIGH},
            {"rule_id": "DECL_001", "rule_name": "Declared vs Actual Mismatch", "alert_type": "declared_mismatch",
             "description": "Activity pattern inconsistent with declared business",
             "risk": AlertRiskLevel.MEDIUM},
        ],
        "crypto_mixing": [
            {"rule_id": "RAPID_001", "rule_name": "Rapid Movement", "alert_type": "rapid_movement",
             "description": "Rapid fund movement pattern consistent with crypto mixing",
             "risk": AlertRiskLevel.HIGH},
            {"rule_id": "CORR_001", "rule_name": "High-Risk Corridor", "alert_type": "high_risk_corridor",
             "description": "Funds routed through crypto-friendly jurisdictions",
             "risk": AlertRiskLevel.MEDIUM},
        ],
    }

    # Risk factors per typology
    TYPOLOGY_RISK_FACTORS = {
        "structuring": [
            "Multiple transactions near CTR threshold ($10,000)",
            "Transactions split across short time windows",
            "Cash deposits structured to avoid reporting",
            "Pattern of just-below-threshold activity",
        ],
        "layering": [
            "Rapid in-out fund movement across multiple accounts",
            "Complex chain of intermediary transfers",
            "No economic rationale for transfer pattern",
            "Funds layered through multiple entities",
        ],
        "mule_network": [
            "Account used as pass-through for third-party funds",
            "Multiple unrelated sources depositing to account",
            "Funds forwarded rapidly to unrelated beneficiaries",
            "Pattern consistent with money mule recruitment",
        ],
        "shell_company": [
            "Entity with minimal operational footprint",
            "Nominal registered office with no real operations",
            "Circular fund flow between related entities",
            "Complex ownership structure obscures beneficial owner",
        ],
        "trade_based": [
            "Invoice values inconsistent with market prices",
            "Cross-border payments to high-risk trade zones",
            "Goods descriptions vague or inconsistent",
            "Multiple payments for same shipment reference",
        ],
        "integration": [
            "Large-value asset purchase with unclear fund source",
            "Funds integrated through real estate or business acquisition",
            "Transaction amounts inconsistent with customer profile",
            "Layered ownership used to obscure proceeds",
        ],
        "crypto_mixing": [
            "Fund flow pattern consistent with crypto mixer output",
            "Rapid conversion between fiat and crypto channels",
            "Structured withdrawals after crypto on-ramp",
            "Links to known crypto mixing service patterns",
        ],
    }

    def _generate_forced_tp_alerts(
        self,
        tp_account_ids: set,
        covered_tp_accounts: set,
        tp_entity_typology: Dict[str, str],
        tp_entity_scenario: Dict[str, str],
        account_to_entity: Dict[str, str],
        signals_by_account: Dict[str, Dict[str, Any]],
        txns_by_account: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """
        Force-generate TP alerts for every TP account that wasn't caught
        by the rules engine.

        In real TMS systems, adversarial launderers try to evade detection,
        but the TMS still generates SOME alerts on suspicious accounts —
        that's the point of this simulation. Every TP account must have at
        least one alert so AML agents can be evaluated on whether they
        correctly escalate it.

        For each uncovered TP account, we generate 1-3 alerts with:
        - Alert type matched to the underlying typology
        - HIGH or CRITICAL risk level (these are real suspicious cases)
        - Proper ground truth labels (_true_positive, _typology, _scenario_id)
        """
        uncovered = tp_account_ids - covered_tp_accounts
        if not uncovered:
            return []

        forced_alerts = []
        as_of_date = date.today()

        for account_id in uncovered:
            entity_id = account_to_entity.get(account_id, "")
            typology = tp_entity_typology.get(entity_id, "unknown")
            scenario_id = tp_entity_scenario.get(entity_id, f"TP_{uuid4().hex[:8]}")
            signals = signals_by_account.get(account_id, {})
            acct_txns = txns_by_account.get(account_id, [])

            # Get typology-specific alert templates (fall back to generic)
            alert_templates = self.TYPOLOGY_ALERT_MAP.get(
                typology,
                [{"rule_id": "VOL_ANOM_001", "rule_name": "Volume Anomaly",
                  "alert_type": "volume_anomaly",
                  "description": "Unusual transaction pattern detected",
                  "risk": AlertRiskLevel.HIGH}],
            )

            # Generate 1-3 alerts per TP account (primary alert always generated)
            num_alerts = random.choices([1, 2, 3], weights=[0.3, 0.5, 0.2], k=1)[0]
            num_alerts = min(num_alerts, len(alert_templates))

            # Select alert templates (always include primary + optional secondary)
            selected_templates = alert_templates[:num_alerts]

            for tmpl in selected_templates:
                risk_level = tmpl["risk"]

                # Possibly escalate to CRITICAL for high-severity scenarios
                if typology in ("mule_network", "structuring") and random.random() < 0.3:
                    risk_level = AlertRiskLevel.CRITICAL

                # Compute score (TP alerts should score 65-95)
                base_scores = {
                    AlertRiskLevel.LOW: 40,
                    AlertRiskLevel.MEDIUM: 55,
                    AlertRiskLevel.HIGH: 75,
                    AlertRiskLevel.CRITICAL: 90,
                }
                score = base_scores.get(risk_level, 75) + random.uniform(-5, 10)
                score = max(40, min(100, score))

                # Get risk factors for this typology
                all_factors = self.TYPOLOGY_RISK_FACTORS.get(typology, ["Suspicious activity pattern detected"])
                risk_factors = random.sample(all_factors, min(3, len(all_factors)))

                # Get contributing transaction IDs
                txn_ids = [t.get("txn_id", "") for t in acct_txns[:50] if t.get("txn_id")]

                # Compute amount involved
                amounts = [t.get("amount", 0) for t in acct_txns]
                amount_involved = sum(amounts) if amounts else 0

                # Build triggering signals
                triggering_signals = {}
                signal_keys = {
                    "structuring": ["structuring_score", "cash_intensity", "volume_30d"],
                    "layering": ["rapid_movement_score", "in_out_ratio", "volume_30d"],
                    "mule_network": ["risk_flow_in", "risk_flow_out", "velocity_30d"],
                    "shell_company": ["declared_vs_actual_volume", "volume_30d"],
                    "trade_based": ["corridor_risk_score", "volume_30d"],
                    "integration": ["volume_zscore", "volume_30d"],
                    "crypto_mixing": ["rapid_movement_score", "corridor_risk_score"],
                }
                for key in signal_keys.get(typology, ["volume_30d"]):
                    val = signals.get(key)
                    if val is not None and isinstance(val, (int, float)):
                        triggering_signals[key] = val

                # Vary the created timestamp
                days_ago = random.randint(0, 14)
                created_ts = datetime.combine(
                    as_of_date - timedelta(days=days_ago),
                    datetime.min.time().replace(
                        hour=random.randint(6, 22),
                        minute=random.randint(0, 59),
                    ),
                )

                alert = Alert(
                    alert_id=f"ALERT_{uuid4().hex[:12]}",
                    created_ts=created_ts,
                    rule_id=tmpl["rule_id"],
                    rule_name=tmpl["rule_name"],
                    account_id=account_id,
                    customer_id=signals.get("customer_id", entity_id),
                    risk_level=risk_level,
                    score=score,
                    risk_factors=risk_factors,
                    transaction_ids=txn_ids,
                    triggering_signals=triggering_signals,
                    alert_type=tmpl["alert_type"],
                    description=tmpl["description"],
                    amount_involved=amount_involved,
                    lookback_start=as_of_date - timedelta(days=self.config.lookback_days),
                    lookback_end=as_of_date,
                    status=AlertStatus.NEW,
                    _true_positive=True,
                    _scenario_id=scenario_id,
                    _typology=typology,
                )
                forced_alerts.append(alert.to_dict())

        return forced_alerts

    def _pad_fp_alerts(
        self,
        tp_alerts: List[Dict[str, Any]],
        fp_alerts: List[Dict[str, Any]],
        account_signals: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        accounts: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Pad false positive alerts to achieve target FP rate."""
        tp_count = len(tp_alerts)
        current_fp = len(fp_alerts)

        if tp_count == 0:
            # No TPs, generate some FP alerts anyway
            target_total = max(20, len(accounts) * self.config.alerts_per_1000_accounts // 1000)
            needed_fp = target_total
        else:
            # Calculate FP needed for target rate
            # fp_rate = fp / (tp + fp)  =>  fp = tp * fp_rate / (1 - fp_rate)
            needed_fp = int(tp_count * self.config.target_fp_rate / (1 - self.config.target_fp_rate))
            needed_fp = max(needed_fp, current_fp)  # Don't remove existing FPs

        additional_needed = needed_fp - current_fp
        if additional_needed <= 0:
            return tp_alerts + fp_alerts

        print(f"         Need {additional_needed} additional FP alerts (have {current_fp}, need {needed_fp})")

        # Identify TN/FP entity accounts (never generate FP alerts for TP accounts)
        tp_entity_ids = set()
        for e in entities:
            gt = e.get("_ground_truth", {})
            if gt.get("is_suspicious") or gt.get("label") == "true_positive":
                tp_entity_ids.add(e.get("entity_id", e.get("customer_id", "")))

        benign_signals = [
            s for s in account_signals
            if s.get("customer_id", "") not in tp_entity_ids
            and s.get("account_id", "") not in {a.get("account_id") for a in tp_alerts}
        ]

        if not benign_signals:
            benign_signals = [s for s in account_signals if s.get("customer_id", "") not in tp_entity_ids]

        additional_fp = self._generate_bulk_fp_alerts(
            benign_signals=benign_signals,
            count=additional_needed,
            transactions=transactions,
        )

        all_alerts = tp_alerts + fp_alerts + additional_fp
        random.shuffle(all_alerts)
        return all_alerts

    def _generate_bulk_fp_alerts(
        self,
        benign_signals: List[Dict[str, Any]],
        count: int,
        transactions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate a large volume of false positive alerts."""
        if not benign_signals:
            return []

        fp_alerts = []
        as_of_date = date.today()

        # FP alert type templates
        fp_rules = {
            "volume_anomaly": {
                "rule_id": "VOL_ANOM_001",
                "rule_name": "Volume Anomaly",
                "alert_type": "volume_anomaly",
                "description": "Unusual transaction volume detected",
                "base_risk": AlertRiskLevel.LOW,
            },
            "round_amounts": {
                "rule_id": "ROUND_001",
                "rule_name": "Round Amount Pattern",
                "alert_type": "round_amounts",
                "description": "Pattern of round-number transactions",
                "base_risk": AlertRiskLevel.LOW,
            },
            "high_risk_corridor": {
                "rule_id": "CORR_001",
                "rule_name": "High-Risk Corridor Activity",
                "alert_type": "high_risk_corridor",
                "description": "Transaction involving monitored jurisdiction",
                "base_risk": AlertRiskLevel.LOW,
            },
            "kyc_refresh": {
                "rule_id": "KYC_001",
                "rule_name": "KYC Refresh Due",
                "alert_type": "kyc_refresh",
                "description": "KYC review period exceeded",
                "base_risk": AlertRiskLevel.LOW,
            },
            "declared_mismatch": {
                "rule_id": "DECL_001",
                "rule_name": "Declared vs Actual Mismatch",
                "alert_type": "declared_mismatch",
                "description": "Activity exceeds declared turnover",
                "base_risk": AlertRiskLevel.LOW,
            },
            "new_counterparties": {
                "rule_id": "NEWCP_001",
                "rule_name": "New Counterparty Surge",
                "alert_type": "new_counterparties",
                "description": "Unusual number of new counterparties",
                "base_risk": AlertRiskLevel.LOW,
            },
            "dormant_reactivation": {
                "rule_id": "DORM_001",
                "rule_name": "Dormant Account Reactivation",
                "alert_type": "dormant_reactivation",
                "description": "Previously dormant account showing activity",
                "base_risk": AlertRiskLevel.MEDIUM,
            },
            "high_cash": {
                "rule_id": "CASH_001",
                "rule_name": "High Cash Activity",
                "alert_type": "high_cash",
                "description": "Elevated cash transaction ratio",
                "base_risk": AlertRiskLevel.LOW,
            },
            "structuring": {
                "rule_id": "STRUCT_FP",
                "rule_name": "Potential Structuring",
                "alert_type": "structuring",
                "description": "Transactions near reporting threshold",
                "base_risk": AlertRiskLevel.MEDIUM,
            },
            "rapid_movement": {
                "rule_id": "RAPID_FP",
                "rule_name": "Rapid Fund Movement",
                "alert_type": "rapid_movement",
                "description": "Quick in-out fund movement detected",
                "base_risk": AlertRiskLevel.MEDIUM,
            },
        }

        # Select alert types based on weights
        type_weights = self.config.fp_type_weights
        types = list(type_weights.keys())
        weights = [type_weights.get(t, 0.1) for t in types]
        total_w = sum(weights)
        weights = [w / total_w for w in weights]

        # Risk level distribution for FP alerts
        # Most FPs are LOW risk, some MEDIUM, very few HIGH
        risk_weights = {"LOW": 0.70, "MEDIUM": 0.22, "HIGH": 0.07, "CRITICAL": 0.01}

        for i in range(count):
            # Select signal source (account)
            signals = random.choice(benign_signals)

            # Select alert type
            alert_type = random.choices(types, weights=weights, k=1)[0]
            rule = fp_rules.get(alert_type, fp_rules["volume_anomaly"])

            # Select risk level
            risk_level_str = random.choices(
                list(risk_weights.keys()),
                weights=list(risk_weights.values()),
                k=1,
            )[0]
            risk_level = AlertRiskLevel(risk_level_str.lower())

            # Compute score
            base_scores = {"LOW": 25, "MEDIUM": 50, "HIGH": 75, "CRITICAL": 90}
            score = base_scores.get(risk_level_str, 25) + random.uniform(-10, 10)
            score = max(0, min(100, score))

            # Get contributing transactions
            contributing_txns = signals.get("_contributing_txns", {})
            txn_ids = contributing_txns.get("volume_30d", [])[:20]

            # Vary the created timestamp over the past 30 days
            days_ago = random.randint(0, 30)
            created_ts = datetime.combine(
                as_of_date - timedelta(days=days_ago),
                datetime.min.time().replace(
                    hour=random.randint(6, 22),
                    minute=random.randint(0, 59),
                ),
            )

            alert = Alert(
                alert_id=f"ALERT_{uuid4().hex[:12]}",
                created_ts=created_ts,
                rule_id=rule["rule_id"],
                rule_name=rule["rule_name"],
                account_id=signals.get("account_id", ""),
                customer_id=signals.get("customer_id", ""),
                risk_level=risk_level,
                score=score,
                risk_factors=self._generate_fp_risk_factors(alert_type, signals),
                transaction_ids=txn_ids,
                triggering_signals=self._extract_triggering_signals(alert_type, signals),
                alert_type=alert_type,
                description=rule["description"],
                status=AlertStatus.NEW,
                _true_positive=False,
                _scenario_id=None,
                _typology=None,
            )
            fp_alerts.append(alert.to_dict())

        return fp_alerts

    def _generate_fp_risk_factors(self, alert_type: str, signals: Dict) -> List[str]:
        """Generate realistic risk factors for FP alerts."""
        factor_pools = {
            "volume_anomaly": [
                "Transaction volume exceeds historical average",
                "Monthly volume increased significantly",
                "Unusual number of transactions for account profile",
            ],
            "round_amounts": [
                "Multiple round-number transactions detected",
                "Round amount pattern in recent activity",
                "Consistent round-dollar transactions",
            ],
            "high_risk_corridor": [
                "Transaction to monitored jurisdiction",
                "Cross-border activity to elevated-risk country",
                "Geographic risk flag triggered",
            ],
            "structuring": [
                "Transactions near reporting threshold",
                "Multiple sub-threshold deposits",
                "Pattern suggestive of structuring",
            ],
            "high_cash": [
                "Elevated cash deposit ratio",
                "Cash intensity above threshold",
                "Unusual cash activity for account type",
            ],
            "rapid_movement": [
                "Funds moved rapidly through account",
                "Short holding period detected",
                "Quick credit-debit pattern",
            ],
        }

        factors = factor_pools.get(alert_type, ["Minor pattern detected"])
        return random.sample(factors, min(2, len(factors)))

    def _extract_triggering_signals(self, alert_type: str, signals: Dict) -> Dict[str, float]:
        """Extract relevant signal values for a given alert type."""
        signal_map = {
            "volume_anomaly": ["volume_zscore", "volume_30d", "velocity_30d"],
            "round_amounts": ["round_amount_ratio", "velocity_30d"],
            "high_risk_corridor": ["corridor_risk_score"],
            "structuring": ["structuring_score", "volume_30d"],
            "high_cash": ["cash_intensity"],
            "rapid_movement": ["rapid_movement_score", "in_out_ratio"],
            "kyc_refresh": ["kyc_age_days"],
            "declared_mismatch": ["declared_vs_actual_volume", "volume_30d"],
            "new_counterparties": ["new_counterparty_rate", "velocity_30d"],
            "dormant_reactivation": ["dormancy_days", "velocity_30d"],
        }

        signal_names = signal_map.get(alert_type, [])
        result = {}
        for name in signal_names:
            val = signals.get(name)
            if val is not None and isinstance(val, (int, float)):
                result[name] = val
        return result

    def _generate_prior_alerts(
        self,
        accounts: List[Dict[str, Any]],
        account_signals: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Generate historical (closed) alerts for some accounts."""
        prior_map = {}
        num_accounts_with_prior = int(len(accounts) * self.config.prior_alert_account_pct)
        selected_accounts = random.sample(accounts, min(num_accounts_with_prior, len(accounts)))

        as_of_date = date.today()

        for account in selected_accounts:
            account_id = account.get("account_id", "")
            num_prior = random.randint(*self.config.prior_alerts_per_account)

            priors = []
            for _ in range(num_prior):
                days_ago = random.randint(30, 365)
                created = datetime.combine(
                    as_of_date - timedelta(days=days_ago),
                    datetime.min.time(),
                )

                prior = {
                    "alert_id": f"HIST_{uuid4().hex[:12]}",
                    "created_ts": created.isoformat(),
                    "alert_type": random.choice([
                        "volume_anomaly", "round_amounts", "kyc_refresh",
                        "high_risk_corridor", "declared_mismatch",
                    ]),
                    "risk_level": random.choices(
                        ["LOW", "MEDIUM", "HIGH"],
                        weights=[0.70, 0.25, 0.05],
                        k=1,
                    )[0],
                    "status": "CLOSED_NO_ISSUE",
                    "disposition": random.choices(
                        ["FALSE_POSITIVE", "NORMAL_BUSINESS", "CUSTOMER_EXPLAINED"],
                        weights=[0.65, 0.25, 0.10],
                        k=1,
                    )[0],
                    "score": round(random.uniform(15, 50), 1),
                }
                priors.append(prior)

            if priors:
                prior_map[account_id] = priors

        return prior_map

    def _simulate_lifecycle(
        self,
        alert: Dict[str, Any],
        pkg: AlertPackage,
    ) -> Dict[str, Any]:
        """Simulate investigation lifecycle for ground truth."""
        is_tp = alert.get("_true_positive", False)
        typology = alert.get("_typology")
        risk_level = alert.get("risk_level", "LOW").upper()

        # Select analyst
        analyst = select_analyst(risk_level)

        # Investigation timeline
        min_days, max_days = self.config.investigation_days_range
        if risk_level in ("CRITICAL", "HIGH"):
            investigation_days = random.randint(min_days, min_days + 3)
        else:
            investigation_days = random.randint(min_days, max_days)

        created_ts = alert.get("created_ts", datetime.now())
        if isinstance(created_ts, str):
            try:
                created_ts = datetime.fromisoformat(created_ts)
            except ValueError:
                created_ts = datetime.now()

        closed_ts = created_ts + timedelta(days=investigation_days)

        # Determine disposition
        if is_tp:
            if risk_level == "CRITICAL":
                disposition = "CONFIRMED_FRAUD"
            else:
                disposition = random.choices(
                    ["SUSPICIOUS_ACTIVITY", "CONFIRMED_FRAUD"],
                    weights=[0.7, 0.3],
                    k=1,
                )[0]
            # SAR filing: guaranteed for CRITICAL/HIGH, probabilistic for others
            # Real TPs should have meaningful SAR filing rate even at lower risk
            if risk_level in ("CRITICAL", "HIGH"):
                sar_filed = True
            elif risk_level == "MEDIUM":
                sar_filed = random.random() < 0.60  # 60% chance for medium TP
            else:
                sar_filed = random.random() < 0.30  # 30% chance for low TP
            final_status = "SAR_FILED" if sar_filed else "ESCALATED"
        else:
            # FP disposition
            disp_choices = list(self.config.fp_disposition_weights.keys())
            disp_weights = list(self.config.fp_disposition_weights.values())
            disposition = random.choices(disp_choices, weights=disp_weights, k=1)[0]
            sar_filed = False
            final_status = "CLOSED_NO_ISSUE"

        # Generate investigation note
        note_data = {
            "alert_id": alert.get("alert_id", ""),
            "account_id": alert.get("account_id", ""),
            "customer_name": pkg.customer_summary.get("name", "Unknown"),
            "segment": pkg.customer_summary.get("segment", "retail"),
            "txn_count": len(pkg.triggering_transactions),
            "total_amount": pkg.amount_involved,
            "alert_type": alert.get("alert_type", ""),
            "declared_purpose": pkg.account_summary.get("declared_purpose", "general banking"),
            "risk_factors": ", ".join(pkg.risk_factors) if pkg.risk_factors else "N/A",
            "suspicious_amount": pkg.amount_involved,
        }

        if is_tp and sar_filed:
            note_data["sar_id"] = f"SAR-{uuid4().hex[:8].upper()}"
            note_data["filing_date"] = str(closed_ts.date())

        investigation_note = generate_investigation_note(
            is_true_positive=is_tp,
            disposition=disposition,
            alert_data=note_data,
            typology=typology,
        )

        return {
            "alert_id": alert.get("alert_id", ""),
            "is_true_positive": is_tp,
            "typology": typology,
            "scenario_id": alert.get("_scenario_id"),
            "disposition": disposition,
            "final_status": final_status,
            "assigned_analyst": analyst,
            "investigation_started": str(created_ts),
            "investigation_closed": str(closed_ts),
            "investigation_days": investigation_days,
            "sar_filed": sar_filed,
            "sar_id": note_data.get("sar_id"),
            "investigation_notes": investigation_note,
            "risk_level": risk_level,
            "score": alert.get("score", 0),
            "alert_type": alert.get("alert_type", ""),
            "account_id": alert.get("account_id", ""),
            "customer_id": alert.get("customer_id", ""),
        }

    def _build_summary(
        self,
        dataset_id: str,
        alert_packages: List[AlertPackage],
        ground_truth: List[Dict[str, Any]],
        entities: List[Dict[str, Any]],
        accounts: List[Dict[str, Any]],
        transactions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build summary statistics."""
        total = len(alert_packages)
        tp_count = sum(1 for r in ground_truth if r.get("is_true_positive"))
        fp_count = total - tp_count

        risk_dist = Counter(pkg.risk_level.upper() if isinstance(pkg.risk_level, str) else pkg.risk_level for pkg in alert_packages)
        type_dist = Counter(pkg.alert_type for pkg in alert_packages)
        disposition_dist = Counter(r.get("disposition") for r in ground_truth)

        sar_count = sum(1 for r in ground_truth if r.get("sar_filed"))
        avg_investigation_days = (
            sum(r.get("investigation_days", 0) for r in ground_truth) / max(1, total)
        )

        return {
            "dataset_id": dataset_id,
            "generated_at": datetime.now().isoformat(),
            "total_alerts": total,
            "true_positives": tp_count,
            "false_positives": fp_count,
            "fp_rate": round(fp_count / max(1, total), 4),
            "target_fp_rate": self.config.target_fp_rate,
            "bank_data_stats": {
                "entities": len(entities),
                "accounts": len(accounts),
                "transactions": len(transactions),
            },
            "risk_distribution": dict(risk_dist),
            "alert_type_distribution": dict(type_dist),
            "disposition_distribution": dict(disposition_dist),
            "sar_filings": sar_count,
            "avg_investigation_days": round(avg_investigation_days, 1),
        }
