"""
Mixed Scenario Orchestrator

Generates realistic datasets with the proper ratio of:
- True Negatives (TN): Normal, benign transactions (~95-98%)
- False Positives (FP): Look suspicious but legitimate (~1-3%)
- True Positives (TP): Actual money laundering (~1-2%)

This creates realistic test data for evaluating AML detection systems
where the key challenge is maximizing TP detection while minimizing FP.
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
import json
import csv
import random
import asyncio
from ..agents.base.base_agent import BaseAgent
from ..agents.benign.benign_agents import BenignPatternAgent, FalsePositiveAgent
from .orchestrator import AdversarialOrchestrator, GeneratedScenario, OrchestratorConfig
from ..config.config import AgentConfig
from ...tracking import tracker
from ..agents.benign.benign_agents import (
    BenignPatternAgent,
    FalsePositiveAgent,
    BenignPatternType,
    FalsePositiveTrigger,
    BENIGN_PATTERNS,
    FALSE_POSITIVE_PATTERNS,
)
from ..tools import create_entity, create_account


@dataclass
class MixedDatasetConfig:
    """Configuration for mixed dataset generation"""
    # Ratio configuration (should sum to 1.0)
    true_negative_ratio: float = 0.96  # Normal transactions
    false_positive_ratio: float = 0.02  # Look suspicious but legitimate
    true_positive_ratio: float = 0.02  # Actual money laundering
    
    # Volume configuration
    num_entities: int = 100  # Total entities to generate
    transactions_per_entity: int = 50  # Average transactions per entity
    time_span_months: int = 12  # Time span for transaction history
    
    # Entity mix
    individual_ratio: float = 0.7  # Individuals vs businesses
    
    # Typology mix for true positives
    typology_weights: Dict[str, float] = field(default_factory=lambda: {
        "structuring": 0.30,
        "layering": 0.20,
        "mule_network": 0.20,
        "shell_company": 0.10,
        "trade_based": 0.10,
        "crypto_mixing": 0.10,
    })
    
    # False positive trigger mix
    fp_trigger_weights: Dict[str, float] = field(default_factory=lambda: {
        "large_cash_business": 0.20,
        "just_below_threshold": 0.25,
        "high_volume_seasonal": 0.15,
        "round_amount_payroll": 0.15,
        "real_estate_closing": 0.10,
        "international_trade": 0.10,
        "inheritance": 0.05,
    })
    
    # Output configuration
    output_dir: str = "data/mixed_aml_dataset"
    
    def validate(self):
        """Validate configuration"""
        total_ratio = self.true_negative_ratio + self.false_positive_ratio + self.true_positive_ratio
        if abs(total_ratio - 1.0) > 0.01:
            raise ValueError(f"Ratios must sum to 1.0, got {total_ratio}")


@dataclass 
class MixedDataset:
    """Complete mixed dataset with ground truth"""
    dataset_id: str
    entities: List[Dict[str, Any]]
    accounts: List[Dict[str, Any]]
    transactions: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    
    # Ground truth statistics
    stats: Dict[str, Any] = field(default_factory=dict)
    
    # Configuration used
    config: MixedDatasetConfig = None
    
    def _write_csv(self, filepath: Path, data: List[Dict[str, Any]]):
        """Write list of dicts to CSV file"""
        if not data:
            # Write empty file with no headers for empty data
            with open(filepath, "w", newline="") as f:
                pass
            return

        # Get all unique keys across all records (for nested dicts)
        fieldnames = set()
        for record in data:
            for key, value in record.items():
                if isinstance(value, dict):
                    # Flatten nested dicts with dot notation
                    for subkey in value.keys():
                        fieldnames.add(f"{key}.{subkey}")
                else:
                    fieldnames.add(key)

        fieldnames = sorted(list(fieldnames))

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for record in data:
                # Flatten nested dicts
                flat_record = {}
                for key, value in record.items():
                    if isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            flat_record[f"{key}.{subkey}"] = subvalue
                    else:
                        flat_record[key] = value

                writer.writerow(flat_record)

    def get_ground_truth_summary(self) -> Dict[str, Any]:
        """Get summary of ground truth labels"""
        labels = {"true_negative": 0, "false_positive": 0, "true_positive": 0}
        
        for txn in self.transactions:
            gt = txn.get("_ground_truth", {})
            label = gt.get("label", "true_negative")
            labels[label] = labels.get(label, 0) + 1
        
        total = sum(labels.values())
        return {
            "counts": labels,
            "percentages": {k: v/total*100 if total > 0 else 0 for k, v in labels.items()},
            "total_transactions": total,
        }
    
    def save(self, output_dir: Optional[str] = None):
        """Save dataset with proper separation of raw data and ground truth"""
        output_path = Path(output_dir or self.config.output_dir) / self.dataset_id
        output_path.mkdir(parents=True, exist_ok=True)
        
        # === RAW DATA (for AI agent) ===
        raw_path = output_path / "raw_data"
        raw_path.mkdir(exist_ok=True)
        
        # Strip ground truth from raw data
        raw_entities = [{k: v for k, v in e.items() if not k.startswith("_")} for e in self.entities]
        raw_accounts = [{k: v for k, v in a.items() if not k.startswith("_")} for a in self.accounts]
        raw_transactions = [{k: v for k, v in t.items() if not k.startswith("_")} for t in self.transactions]
        raw_relationships = [{k: v for k, v in r.items() if not k.startswith("_")} for r in self.relationships]
        
        # Save as JSON (for compatibility)
        with open(raw_path / "entities.json", "w") as f:
            json.dump(raw_entities, f, indent=2, default=str)
        with open(raw_path / "accounts.json", "w") as f:
            json.dump(raw_accounts, f, indent=2, default=str)
        with open(raw_path / "transactions.json", "w") as f:
            json.dump(raw_transactions, f, indent=2, default=str)
        with open(raw_path / "relationships.json", "w") as f:
            json.dump(raw_relationships, f, indent=2, default=str)

        # Save as CSV (for performance at scale)
        self._write_csv(raw_path / "entities.csv", raw_entities)
        self._write_csv(raw_path / "accounts.csv", raw_accounts)
        self._write_csv(raw_path / "transactions.csv", raw_transactions)
        self._write_csv(raw_path / "relationships.csv", raw_relationships)
        
        # === GROUND TRUTH (for evaluation) ===
        gt_path = output_path / "ground_truth"
        gt_path.mkdir(exist_ok=True)
        
        # Transaction labels
        transaction_labels = [
            {
                "txn_id": t["txn_id"],
                **t.get("_ground_truth", {"label": "true_negative", "is_suspicious": False})
            }
            for t in self.transactions
        ]
        with open(gt_path / "transaction_labels.json", "w") as f:
            json.dump(transaction_labels, f, indent=2, default=str)
        self._write_csv(gt_path / "transaction_labels.csv", transaction_labels)

        # Entity labels
        entity_labels = [
            {
                "entity_id": e.get("entity_id"),
                **e.get("_ground_truth", {"is_suspicious": False})
            }
            for e in self.entities
        ]
        with open(gt_path / "entity_labels.json", "w") as f:
            json.dump(entity_labels, f, indent=2, default=str)
        self._write_csv(gt_path / "entity_labels.csv", entity_labels)
        
        # Summary statistics
        summary = self.get_ground_truth_summary()
        summary["dataset_id"] = self.dataset_id
        summary["generated_at"] = datetime.now().isoformat()
        summary["config"] = {
            "true_negative_ratio": self.config.true_negative_ratio,
            "false_positive_ratio": self.config.false_positive_ratio,
            "true_positive_ratio": self.config.true_positive_ratio,
            "num_entities": self.config.num_entities,
        }
        
        with open(gt_path / "summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)
        
        # Full stats
        with open(gt_path / "detailed_stats.json", "w") as f:
            json.dump(self.stats, f, indent=2, default=str)
        
        print(f"Dataset saved to: {output_path}")
        print(f"  Raw data: {raw_path}")
        print(f"  Ground truth: {gt_path}")
        
        return output_path


class MixedScenarioOrchestrator:
    """
    Orchestrator for generating mixed datasets with realistic ratios.
    
    Combines:
    - Adversarial agents (for true positives)
    - Benign agents (for true negatives)
    - False positive agents (for false positives)
    """
    
    def __init__(self, config: Optional[MixedDatasetConfig] = None):
        self.config = config or MixedDatasetConfig()
        self.config.validate()
        
        # Initialize sub-orchestrators and agents
        self.adversarial_orchestrator = AdversarialOrchestrator(
            OrchestratorConfig(ground_truth_output_dir=self.config.output_dir)
        )
        self.benign_agent = BenignPatternAgent()
        self.fp_agent = FalsePositiveAgent()
        
        # Statistics
        self.datasets_generated = 0
    
    def _weighted_choice(self, weights: Dict[str, float]) -> str:
        """Select an item based on weights"""
        items = list(weights.keys())
        probs = list(weights.values())
        # Normalize
        total = sum(probs)
        probs = [p/total for p in probs]
        return random.choices(items, weights=probs, k=1)[0]
    
    def _generate_entity(self, entity_type: str, is_suspicious: bool = False) -> Dict[str, Any]:
        """Generate an entity"""
        if entity_type == "individual":
            name = f"Person_{uuid4().hex[:8]}"
            country = random.choice(["US", "US", "US", "CA", "UK", "DE"])  # US-heavy
        else:
            name = f"Company_{uuid4().hex[:8]}"
            country = random.choice(["US", "US", "CA", "UK", "DE", "SG"])
        
        return create_entity.invoke({
            "entity_type": entity_type,
            "name": name,
            "country": country,
            "risk_indicators": [] if not is_suspicious else ["high_risk_jurisdiction"],
            "is_shell": False,
            "is_nominee": False,
        })
    
    def _generate_account(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Generate an account for an entity"""
        return create_account.invoke({
            "entity_id": entity["entity_id"],
            "account_type": random.choice(["checking", "savings"]),
            "currency": "USD",
            "country": entity.get("country", "US"),
            "is_offshore": False,
        })
    
    async def generate_mixed_dataset(
        self,
        config: Optional[MixedDatasetConfig] = None,
    ) -> MixedDataset:
        """
        Generate a complete mixed dataset with realistic ratios.
        """
        start_time = datetime.now()
        
        config = config or self.config
        config.validate()
        
        dataset_id = f"MIXED_{uuid4().hex[:12]}"
        print(f"\nGenerating mixed dataset: {dataset_id}")
        print(f"  Target ratios: TN={config.true_negative_ratio:.1%}, FP={config.false_positive_ratio:.1%}, TP={config.true_positive_ratio:.1%}")
        print(f"  Entities: {config.num_entities}")
        
        # Start MLflow run
        run_id = tracker.start_run(
            run_name=f"{tracker.run_name_prefix}_{dataset_id}",
            tags={"dataset_type": "mixed_aml", "llm_provider": "groq"}
        )
        
        all_entities = []
        all_accounts = []
        all_transactions = []
        all_relationships = []
        
        stats = {
            "true_negative_entities": 0,
            "false_positive_entities": 0,
            "true_positive_entities": 0,
            "by_pattern": {},
            "by_typology": {},
            "by_fp_trigger": {},
        }
        
        # Determine entity distribution
        num_tn_entities = int(config.num_entities * config.true_negative_ratio)
        num_fp_entities = int(config.num_entities * config.false_positive_ratio)
        num_tp_entities = config.num_entities - num_tn_entities - num_fp_entities
        
        print(f"  Entities: TN={num_tn_entities}, FP={num_fp_entities}, TP={num_tp_entities}")
        
        # === Generate True Negative Entities ===
        print("  [1/3] Generating true negative (benign) entities...")
        
        for i in range(num_tn_entities):
            # Determine entity type
            is_individual = random.random() < config.individual_ratio
            entity_type = "individual" if is_individual else "company"
            
            entity = self._generate_entity(entity_type, is_suspicious=False)
            entity["_ground_truth"] = {
                "is_suspicious": False,
                "label": "true_negative",
            }
            all_entities.append(entity)
            
            account = self._generate_account(entity)
            account["_ground_truth"] = {"is_suspicious": False}
            all_accounts.append(account)
            
            # Generate benign transactions
            pattern_types = list(BENIGN_PATTERNS.keys())
            if entity_type == "company":
                pattern_types = [BenignPatternType.BUSINESS_PAYROLL, BenignPatternType.BUSINESS_VENDOR, 
                               BenignPatternType.BUSINESS_REVENUE]
            else:
                pattern_types = [BenignPatternType.SALARY, BenignPatternType.RENT_MORTGAGE,
                               BenignPatternType.RETAIL, BenignPatternType.GROCERY]
            
            # Mix of patterns for this entity
            for pattern in random.sample(pattern_types, min(2, len(pattern_types))):
                txns = self.benign_agent.generate_pattern(
                    pattern_type=pattern,
                    entity_id=entity["entity_id"],
                    account_id=account["account_id"],
                    num_months=config.time_span_months,
                    scenario_id=dataset_id,
                )
                all_transactions.extend(txns)
                
                stats["by_pattern"][pattern] = stats["by_pattern"].get(pattern, 0) + len(txns)
        
        stats["true_negative_entities"] = num_tn_entities
        
        # === Generate False Positive Entities ===
        print("  [2/3] Generating false positive entities...")
        
        for i in range(num_fp_entities):
            # Select FP trigger type
            trigger_type = self._weighted_choice(config.fp_trigger_weights)
            trigger_config = FALSE_POSITIVE_PATTERNS.get(trigger_type, {})
            
            # Entity type based on trigger
            entity_type = trigger_config.get("entity_type", "individual")
            if entity_type == "business":
                entity_type = "company"
            
            entity = self._generate_entity(entity_type, is_suspicious=False)
            entity["_ground_truth"] = {
                "is_suspicious": False,
                "is_false_positive": True,
                "trigger_type": trigger_type,
                "label": "false_positive",
            }
            all_entities.append(entity)
            
            account = self._generate_account(entity)
            account["_ground_truth"] = {"is_suspicious": False, "is_false_positive": True}
            all_accounts.append(account)
            
            # Generate false positive scenario
            fp_result = self.fp_agent.generate_false_positive(
                trigger_type=trigger_type,
                entity_id=entity["entity_id"],
                account_id=account["account_id"],
                scenario_id=dataset_id,
            )
            all_transactions.extend(fp_result["transactions"])
            
            stats["by_fp_trigger"][trigger_type] = stats["by_fp_trigger"].get(trigger_type, 0) + 1
        
        stats["false_positive_entities"] = num_fp_entities
        
        # === Generate True Positive Entities ===
        print("  [3/3] Generating true positive (suspicious) entities...")
        
        for i in range(num_tp_entities):
            # Select typology
            typology = self._weighted_choice(config.typology_weights)
            
            try:
                # Use adversarial orchestrator to generate suspicious scenario
                scenario = await self.adversarial_orchestrator.generate_scenario(
                    typology=typology,
                    total_amount=random.uniform(50000, 500000),
                    complexity=random.randint(3, 7),
                )

                # Check if scenario generation actually succeeded
                if not scenario.entities or not scenario.transactions:
                    raise ValueError(f"Scenario generation failed - no entities or transactions generated. Metadata: {scenario.metadata.get('error', 'Unknown error')}")

                # Mark all entities/transactions as true positives
                for entity in scenario.entities:
                    entity["_ground_truth"]["label"] = "true_positive"
                    entity["_ground_truth"]["typology"] = typology
                all_entities.extend(scenario.entities)
                
                for account in scenario.accounts:
                    account["_ground_truth"]["label"] = "true_positive"
                all_accounts.extend(scenario.accounts)
                
                for txn in scenario.transactions:
                    txn["_ground_truth"]["label"] = "true_positive"
                    txn["_ground_truth"]["is_suspicious"] = True
                all_transactions.extend(scenario.transactions)
                
                all_relationships.extend(scenario.relationships)
                
                stats["by_typology"][typology] = stats["by_typology"].get(typology, 0) + 1
                
            except Exception as e:
                import traceback
                import sys
                print(f"    Warning: Failed to generate {typology} scenario: {e}", flush=True)
                print(f"    Stack trace: {traceback.format_exc()}", flush=True)
                sys.stdout.flush()
                # Generate simple suspicious entity as fallback
                entity = self._generate_entity("individual", is_suspicious=True)
                entity["_ground_truth"] = {
                    "is_suspicious": True,
                    "label": "true_positive",
                    "typology": typology,
                }
                all_entities.append(entity)
                
                account = self._generate_account(entity)
                account["_ground_truth"] = {"is_suspicious": True}
                all_accounts.append(account)
        
        stats["true_positive_entities"] = num_tp_entities
        
        # Shuffle transactions to mix them up
        random.shuffle(all_transactions)
        
        # Create dataset
        dataset = MixedDataset(
            dataset_id=dataset_id,
            entities=all_entities,
            accounts=all_accounts,
            transactions=all_transactions,
            relationships=all_relationships,
            stats=stats,
            config=config,
        )
        
        # Print summary
        summary = dataset.get_ground_truth_summary()
        print(f"\nDataset generated: {dataset_id}")
        print(f"  Entities: {len(all_entities)}")
        print(f"  Accounts: {len(all_accounts)}")
        print(f"  Transactions: {summary['total_transactions']}")
        print(f"  Label distribution:")
        for label, count in summary["counts"].items():
            pct = summary["percentages"][label]
            print(f"    {label}: {count} ({pct:.2f}%)")
        
        self.datasets_generated += 1
        
        # Log to MLflow
        try:
            generation_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            tracker.log_mixed_dataset(
                dataset_id=dataset_id,
                num_entities=len(all_entities),
                num_accounts=len(all_accounts),
                num_transactions=summary['total_transactions'],
                label_distribution=summary["counts"],
                generation_time_ms=generation_time_ms
            )
            
            # Log dataset as artifact
            output_path = dataset.save()
            tracker.log_dataset_artifact(str(output_path), f"mixed_dataset_{dataset_id}")
            
            # End MLflow run
            tracker.end_run()
            
        except Exception as e:
            print(f"    Warning: Failed to log to MLflow: {e}")
        
        return dataset
    
    def generate_dataset_sync(
        self,
        config: Optional[MixedDatasetConfig] = None,
    ) -> MixedDataset:
        """Synchronous wrapper for generate_mixed_dataset"""
        return asyncio.run(self.generate_mixed_dataset(config))


async def main():
    """Example usage"""
    
    config = MixedDatasetConfig(
        true_negative_ratio=0.96,
        false_positive_ratio=0.02,
        true_positive_ratio=0.02,
        num_entities=50,  # Smaller for demo
        output_dir="data/mixed_aml_test",
    )
    
    orchestrator = MixedScenarioOrchestrator(config)
    dataset = await orchestrator.generate_mixed_dataset()
    
    # Save dataset
    dataset.save()
    
    return dataset


if __name__ == "__main__":
    asyncio.run(main())
