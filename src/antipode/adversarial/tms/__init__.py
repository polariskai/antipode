"""
TMS (Transaction Monitoring System) Alert Generation Module.

Generates realistic TMS alerts from synthetic bank data, simulating
the output of a Tier 1 bank's transaction monitoring system.

Key components:
- TMSAlertGenerator: Main pipeline that produces alert datasets
- AlertPackager: Builds rich alert packages with investigation context
- AlertPackage: The rich alert format consumed by AML detection agents
- TMSConfig: Configuration for alert generation parameters
- TMSOutput: Complete output with alerts, bank data, and ground truth
- FPCategory: Data class describing a false-positive category
- FP_CATEGORIES: Full taxonomy of FP categories by alert type
- select_fp_category: Helper to pick a weighted FP category for an alert
"""

from .tms_generator import TMSAlertGenerator, TMSConfig, TMSOutput
from .alert_packager import AlertPackager, AlertPackage
from .fp_taxonomy import FPCategory, FP_CATEGORIES, select_fp_category

__all__ = [
    "TMSAlertGenerator",
    "TMSConfig",
    "TMSOutput",
    "AlertPackager",
    "AlertPackage",
    "FPCategory",
    "FP_CATEGORIES",
    "select_fp_category",
]
