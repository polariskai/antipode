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
"""

from .tms_generator import TMSAlertGenerator, TMSConfig, TMSOutput
from .alert_packager import AlertPackager, AlertPackage

__all__ = [
    "TMSAlertGenerator",
    "TMSConfig",
    "TMSOutput",
    "AlertPackager",
    "AlertPackage",
]
