#!/usr/bin/env python3
"""
Example: Generate synthetic AML banking data using Antipode.

Produces a complete dataset of customers, companies, accounts,
transactions, news events, signals, alerts, and investigation
scenarios with embedded money laundering typologies.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from antipode.data.generators import AMLDataGenerator


def main():
    """Generate a sample synthetic AML dataset."""

    print("=" * 60)
    print("  ANTIPODE - Adversarial AML Synthetic Data Generator")
    print("=" * 60)

    generator = AMLDataGenerator(seed=42)

    dataset = generator.generate_full_dataset(
        num_customers=500,
        num_companies=100,
        typology_rate=0.05,
        adverse_media_rate=0.05,
    )

    # Save to files (JSON + CSV)
    output_dir = "data/synthetic_aml"
    generator.save_dataset(dataset, output_dir)

    # Print summary
    stats = dataset["statistics"]
    meta = dataset["metadata"]

    print(f"\nDataset Summary:")
    print(f"  Customers:              {meta['num_customers']}")
    print(f"  Companies:              {meta['num_companies']}")
    print(f"  Accounts:               {len(dataset['accounts'])}")
    print(f"  Transactions:           {stats['total_transactions']}")
    print(f"  Suspicious Txns:        {stats['suspicious_transactions']}")
    print(f"  Scenarios (typologies): {stats['scenarios']}")
    print(f"  News Events:            {len(dataset['news_events'])}")
    print(f"  Alerts:                 {stats['alerts'].get('total', 0)}")
    print(f"  Date Range:             {meta['start_date']} to {meta['end_date']}")
    print(f"  Output:                 {output_dir}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
