"""
Transaction Ledger for Adversarial AML System

Provides indexed queries for transactions and pattern detection.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger


@dataclass
class TransactionRecord:
    """Record of a transaction in the ledger"""
    txn_id: str
    from_account_id: str
    to_account_id: str
    amount: float
    currency: str
    txn_type: str
    purpose: str
    timestamp: str
    scenario_id: str
    typology: Optional[str] = None
    is_suspicious: bool = False


class TransactionLedger:
    """
    Ledger for managing transactions across scenarios.

    Features:
    - Indexed queries by account, timestamp, amount
    - Transaction history tracking
    - Pattern detection (velocity, round amounts, etc.)
    - Fast range queries
    """

    def __init__(self):
        # Primary index: txn_id -> TransactionRecord
        self._transactions: Dict[str, TransactionRecord] = {}

        # Secondary indices for fast queries
        self._by_account: Dict[str, List[str]] = defaultdict(list)  # account_id -> [txn_ids]
        self._by_timestamp: List[Tuple[str, str]] = []  # [(timestamp, txn_id)] - sorted
        self._by_amount_range: Dict[int, List[str]] = defaultdict(list)  # amount_bucket -> [txn_ids]

        # Statistics
        self._total_transactions = 0
        self._total_volume = 0.0
        self._suspicious_count = 0

    def record(self, transaction: Dict[str, Any], scenario_id: str) -> TransactionRecord:
        """
        Record a new transaction.

        Args:
            transaction: Transaction dict from generator
            scenario_id: Scenario this transaction belongs to

        Returns:
            TransactionRecord
        """
        txn_id = transaction["txn_id"]

        # Check for duplicates
        if txn_id in self._transactions:
            logger.warning(f"Transaction {txn_id} already exists, skipping")
            return self._transactions[txn_id]

        # Create record
        record = TransactionRecord(
            txn_id=txn_id,
            from_account_id=transaction.get("from_account_id", ""),
            to_account_id=transaction.get("to_account_id", ""),
            amount=transaction.get("amount", 0.0),
            currency=transaction.get("currency", "USD"),
            txn_type=transaction.get("txn_type", "wire"),
            purpose=transaction.get("purpose", ""),
            timestamp=transaction.get("timestamp", datetime.now().isoformat()),
            scenario_id=scenario_id,
            typology=transaction.get("typology"),
            is_suspicious=transaction.get("_ground_truth", {}).get("is_suspicious", False)
        )

        # Add to primary index
        self._transactions[txn_id] = record

        # Update secondary indices
        self._by_account[record.from_account_id].append(txn_id)
        self._by_account[record.to_account_id].append(txn_id)

        # Add to timestamp index (keep sorted)
        self._by_timestamp.append((record.timestamp, txn_id))
        self._by_timestamp.sort()  # TODO: Optimize with bisect

        # Add to amount range index (bucket by $1000)
        amount_bucket = int(record.amount / 1000) * 1000
        self._by_amount_range[amount_bucket].append(txn_id)

        # Update stats
        self._total_transactions += 1
        self._total_volume += record.amount
        if record.is_suspicious:
            self._suspicious_count += 1

        logger.debug(f"Recorded transaction {txn_id}: ${record.amount:.2f} from {record.from_account_id}")

        return record

    def get(self, txn_id: str) -> Optional[TransactionRecord]:
        """Get transaction by ID (O(1) lookup)"""
        return self._transactions.get(txn_id)

    def get_by_account(self, account_id: str, limit: Optional[int] = None) -> List[TransactionRecord]:
        """Get all transactions for an account"""
        txn_ids = self._by_account.get(account_id, [])
        if limit:
            txn_ids = txn_ids[:limit]
        return [self._transactions[tid] for tid in txn_ids]

    def get_by_timerange(
        self,
        start_time: str,
        end_time: str,
        limit: Optional[int] = None
    ) -> List[TransactionRecord]:
        """Get transactions in a time range"""
        # Binary search for start and end indices
        matching_txns = [
            self._transactions[tid]
            for ts, tid in self._by_timestamp
            if start_time <= ts <= end_time
        ]

        if limit:
            matching_txns = matching_txns[:limit]

        return matching_txns

    def get_by_amount_range(
        self,
        min_amount: float,
        max_amount: float,
        limit: Optional[int] = None
    ) -> List[TransactionRecord]:
        """Get transactions in an amount range"""
        # Get relevant buckets
        min_bucket = int(min_amount / 1000) * 1000
        max_bucket = int(max_amount / 1000) * 1000

        txn_ids = []
        for bucket in range(min_bucket, max_bucket + 1000, 1000):
            txn_ids.extend(self._by_amount_range.get(bucket, []))

        # Filter to exact range
        matching_txns = [
            self._transactions[tid]
            for tid in txn_ids
            if min_amount <= self._transactions[tid].amount <= max_amount
        ]

        if limit:
            matching_txns = matching_txns[:limit]

        return matching_txns

    def get_account_velocity(
        self,
        account_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Calculate velocity metrics for an account.

        Args:
            account_id: Account to analyze
            days: Time window in days

        Returns:
            Dict with velocity metrics
        """
        # Get recent transactions
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        all_txns = self.get_by_account(account_id)

        recent_txns = [
            t for t in all_txns
            if t.timestamp >= cutoff_time
        ]

        if not recent_txns:
            return {
                "txn_count": 0,
                "total_volume": 0.0,
                "avg_amount": 0.0,
                "velocity_per_day": 0.0
            }

        total_volume = sum(t.amount for t in recent_txns)
        avg_amount = total_volume / len(recent_txns)

        return {
            "txn_count": len(recent_txns),
            "total_volume": total_volume,
            "avg_amount": avg_amount,
            "velocity_per_day": len(recent_txns) / days
        }

    def detect_round_amounts(self, threshold: float = 0.99) -> List[TransactionRecord]:
        """
        Detect transactions with suspiciously round amounts.

        Args:
            threshold: Percentage of amount that must be round (e.g., 0.99 for 9900 out of 10000)

        Returns:
            List of transactions with round amounts
        """
        round_txns = []

        for txn in self._transactions.values():
            amount = txn.amount
            # Check if amount is close to round thousands
            nearest_thousand = round(amount / 1000) * 1000
            if nearest_thousand > 0:
                roundness = nearest_thousand / amount
                if roundness >= threshold:
                    round_txns.append(txn)

        return round_txns

    def detect_structuring_pattern(
        self,
        account_id: str,
        threshold: float = 10000.0,
        days: int = 30,
        min_count: int = 3
    ) -> bool:
        """
        Detect structuring pattern for an account.

        Args:
            account_id: Account to check
            threshold: Reporting threshold (e.g., $10,000)
            days: Time window
            min_count: Minimum number of transactions to flag

        Returns:
            True if structuring pattern detected
        """
        # Get recent transactions just below threshold
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        all_txns = self.get_by_account(account_id)

        below_threshold = [
            t for t in all_txns
            if t.timestamp >= cutoff_time
            and t.amount < threshold
            and t.amount > threshold * 0.7  # Within 70-100% of threshold
        ]

        return len(below_threshold) >= min_count

    def get_stats(self) -> Dict[str, Any]:
        """Get ledger statistics"""
        return {
            "total_transactions": self._total_transactions,
            "total_volume": self._total_volume,
            "avg_amount": self._total_volume / max(1, self._total_transactions),
            "suspicious_count": self._suspicious_count,
            "suspicious_rate": self._suspicious_count / max(1, self._total_transactions),
            "accounts_with_activity": len(self._by_account),
        }

    def clear(self):
        """Clear all transactions (for testing)"""
        self._transactions.clear()
        self._by_account.clear()
        self._by_timestamp.clear()
        self._by_amount_range.clear()
        self._total_transactions = 0
        self._total_volume = 0.0
        self._suspicious_count = 0
        logger.info("Transaction ledger cleared")
