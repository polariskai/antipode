#!/usr/bin/env python3
"""
CLI Runner for the Adversarial AML Agent System

Provides command-line interface for generating synthetic money laundering
scenarios for AML detection system evaluation.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

# Verify critical environment variables
REQUIRED_ENV_VARS = ["GROQ_API_KEY"]
missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
if missing_vars:
    print(f"\nERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please create a .env file with the following variables:")
    print("  GROQ_API_KEY=your_groq_api_key")
    print("  DATABRICKS_HOST=your_databricks_host (optional)")
    print("  DATABRICKS_TOKEN=your_databricks_token (optional)")
    exit(1)

from .orchestrator import AdversarialOrchestrator
from ..config.config import TypologyType, OrchestratorConfig
from .mixed_orchestrator import MixedScenarioOrchestrator, MixedDatasetConfig


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic money laundering scenarios for AML testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a single structuring scenario
  python -m antipode.adversarial.runner --typology structuring --amount 50000

  # Generate a batch of 10 scenarios with different typologies
  python -m antipode.adversarial.runner --batch 10 --output data/test_scenarios

  # Generate a high-complexity layering scenario
  python -m antipode.adversarial.runner --typology layering --complexity 8 --amount 500000

  # Generate realistic mixed dataset (96% benign, 2% FP, 2% TP)
  python -m antipode.adversarial.runner --mixed --entities 100 --output data/mixed_aml

  # Custom ratios for mixed dataset
  python -m antipode.adversarial.runner --mixed --tn-ratio 0.95 --fp-ratio 0.03 --tp-ratio 0.02
"""
    )
    
    parser.add_argument(
        "--typology", "-t",
        choices=["structuring", "layering", "integration", "mule_network", 
                 "shell_company", "trade_based", "crypto_mixing"],
        default="structuring",
        help="Type of money laundering scenario to generate"
    )
    
    parser.add_argument(
        "--amount", "-a",
        type=float,
        default=100000,
        help="Total amount to launder in USD (default: 100000)"
    )
    
    parser.add_argument(
        "--complexity", "-c",
        type=int,
        choices=range(1, 11),
        default=5,
        help="Complexity level 1-10 (default: 5)"
    )
    
    parser.add_argument(
        "--batch", "-b",
        type=int,
        default=None,
        help="Number of scenarios to generate in batch mode"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="data/adversarial_scenarios",
        help="Output directory for generated scenarios"
    )
    
    parser.add_argument(
        "--no-evasion",
        action="store_true",
        help="Disable evasion techniques"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    # Mixed dataset arguments
    parser.add_argument(
        "--mixed",
        action="store_true",
        help="Generate mixed dataset with realistic TN/FP/TP ratios"
    )
    
    parser.add_argument(
        "--entities",
        type=int,
        default=100,
        help="Number of entities for mixed dataset (default: 100)"
    )
    
    parser.add_argument(
        "--tn-ratio",
        type=float,
        default=0.96,
        help="True negative ratio for mixed dataset (default: 0.96)"
    )
    
    parser.add_argument(
        "--fp-ratio",
        type=float,
        default=0.02,
        help="False positive ratio for mixed dataset (default: 0.02)"
    )
    
    parser.add_argument(
        "--tp-ratio",
        type=float,
        default=0.02,
        help="True positive ratio for mixed dataset (default: 0.02)"
    )
    
    return parser.parse_args()


async def run_single(args, orchestrator: AdversarialOrchestrator):
    """Generate a single scenario"""
    
    print(f"\nGenerating {args.typology} scenario...")
    print(f"  Amount: ${args.amount:,.2f}")
    print(f"  Complexity: {args.complexity}")
    print(f"  Evasion: {'disabled' if args.no_evasion else 'enabled'}")
    
    scenario = await orchestrator.generate_scenario(
        typology=args.typology,
        total_amount=args.amount,
        complexity=args.complexity,
        apply_evasion=not args.no_evasion,
    )
    
    # Save scenario
    scenario.save(args.output)

    print(f"\n[SUCCESS] Scenario generated: {scenario.scenario_id}")
    print(f"  Entities: {len(scenario.entities)}")
    print(f"  Accounts: {len(scenario.accounts)}")
    print(f"  Transactions: {len(scenario.transactions)}")
    print(f"  Relationships: {len(scenario.relationships)}")
    print(f"  Total Amount: ${sum(t['amount'] for t in scenario.transactions):,.2f}")
    
    if scenario.validation:
        print(f"\nValidation:")
        print(f"  Valid: {scenario.validation.get('is_valid', 'N/A')}")
        print(f"  Realistic: {scenario.validation.get('is_realistic', 'N/A')}")
        print(f"  Detection Difficulty: {scenario.validation.get('detection_difficulty', 'N/A')}")
    
    print(f"\nOutput saved to: {args.output}/{scenario.scenario_id}/")
    
    return scenario


async def run_batch(args, orchestrator: AdversarialOrchestrator):
    """Generate multiple scenarios"""
    
    typologies = ["structuring", "layering", "mule_network", "shell_company", "integration"]
    
    print(f"\nGenerating {args.batch} scenarios...")
    print(f"  Typologies: {', '.join(typologies)}")
    print(f"  Output: {args.output}")
    
    scenarios = await orchestrator.generate_batch(
        num_scenarios=args.batch,
        typologies=typologies,
        output_dir=args.output,
    )
    
    print(f"\n[SUCCESS] Generated {len(scenarios)} scenarios")
    
    # Summary statistics
    total_entities = sum(len(s.entities) for s in scenarios)
    total_transactions = sum(len(s.transactions) for s in scenarios)
    total_amount = sum(sum(t['amount'] for t in s.transactions) for s in scenarios)
    
    print(f"\nSummary:")
    print(f"  Total Entities: {total_entities}")
    print(f"  Total Transactions: {total_transactions}")
    print(f"  Total Amount: ${total_amount:,.2f}")
    
    # Breakdown by typology
    typology_counts = {}
    for s in scenarios:
        t = s.typology
        typology_counts[t] = typology_counts.get(t, 0) + 1
    
    print(f"\nBy Typology:")
    for t, count in sorted(typology_counts.items()):
        print(f"  {t}: {count}")
    
    # Save summary
    summary = {
        "generated_at": datetime.now().isoformat(),
        "num_scenarios": len(scenarios),
        "total_entities": total_entities,
        "total_transactions": total_transactions,
        "total_amount": total_amount,
        "typology_distribution": typology_counts,
        "scenarios": [
            {
                "scenario_id": s.scenario_id,
                "typology": s.typology,
                "entities": len(s.entities),
                "transactions": len(s.transactions),
            }
            for s in scenarios
        ],
    }
    
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path / "batch_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"\nSummary saved to: {args.output}/batch_summary.json")
    
    return scenarios


async def run_mixed(args):
    """Generate a mixed dataset with realistic TN/FP/TP ratios"""
    
    # Validate ratios sum to ~1.0
    total_ratio = args.tn_ratio + args.fp_ratio + args.tp_ratio
    if abs(total_ratio - 1.0) > 0.01:
        print(f"Error: Ratios must sum to 1.0, got {total_ratio:.2f}")
        print(f"  TN: {args.tn_ratio}, FP: {args.fp_ratio}, TP: {args.tp_ratio}")
        return None
    
    print(f"\nGenerating mixed AML dataset...")
    print(f"  Entities: {args.entities}")
    print(f"  Ratios: TN={args.tn_ratio:.1%}, FP={args.fp_ratio:.1%}, TP={args.tp_ratio:.1%}")
    print(f"  Output: {args.output}")
    
    config = MixedDatasetConfig(
        true_negative_ratio=args.tn_ratio,
        false_positive_ratio=args.fp_ratio,
        true_positive_ratio=args.tp_ratio,
        num_entities=args.entities,
        output_dir=args.output,
    )
    
    orchestrator = MixedScenarioOrchestrator(config)
    dataset = await orchestrator.generate_mixed_dataset()
    
    # Save dataset
    dataset.save()
    
    # Print evaluation metrics guide
    print("\n" + "="*60)
    print("EVALUATION METRICS GUIDE")
    print("="*60)
    summary = dataset.get_ground_truth_summary()
    
    print(f"\nGround Truth Distribution:")
    print(f"  True Negatives (TN): {summary['counts']['true_negative']} ({summary['percentages']['true_negative']:.2f}%)")
    print(f"  False Positives (FP): {summary['counts']['false_positive']} ({summary['percentages']['false_positive']:.2f}%)")
    print(f"  True Positives (TP): {summary['counts']['true_positive']} ({summary['percentages']['true_positive']:.2f}%)")
    
    print("\nFor AML Detection Evaluation:")
    print("  - Precision = TP / (TP + FP_detected)")
    print("  - Recall = TP_detected / TP")
    print("  - F1 = 2 * (Precision * Recall) / (Precision + Recall)")
    print("  - False Positive Rate = FP_detected / (TN + FP)")
    print("\nKey Challenge: Maximize recall while minimizing false positive rate")
    
    return dataset


async def main():
    args = parse_args()
    
    # Set random seed if provided
    if args.seed:
        import random
        import numpy as np
        random.seed(args.seed)
        np.random.seed(args.seed)
    
    try:
        # Handle mixed dataset generation
        if args.mixed:
            await run_mixed(args)
            return 0
        
        # Initialize orchestrator for adversarial-only generation
        config = OrchestratorConfig(
            ground_truth_output_dir=args.output,
        )
        orchestrator = AdversarialOrchestrator(config)
        
        if args.batch:
            await run_batch(args, orchestrator)
        else:
            await run_single(args, orchestrator)
        
        # Print agent statistics
        if args.verbose:
            print("\nAgent Statistics:")
            stats = orchestrator.get_stats()
            for name, agent_stats in stats.get("agent_stats", {}).items():
                print(f"  {name}:")
                print(f"    Executions: {agent_stats.get('execution_count', 0)}")
                print(f"    Red flags: {agent_stats.get('red_flag_count', 0)}")
                
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
