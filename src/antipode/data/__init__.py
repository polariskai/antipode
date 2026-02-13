"""
Data ingestion, normalization, and synthetic data generation layer.

Structure:
- models/: Pure data classes (Account, Transaction, Alert, NewsEvent)
- config/: Configuration (regions, segments)
- generators/: Synthetic data generation logic
- signals/: Signal definitions
- alerts/: Alert rule definitions
- typologies/: Typology definitions
"""

# Import from generators package (generation logic)
from .generators import (
    AMLDataGenerator,
    generate_sample_dataset,
    NewsEventGenerator,
    SignalGenerator,
    AlertRulesEngine,
    TypologyInjector,
)

# Import from config package
from .config import REGIONS, CUSTOMER_SEGMENTS

# Import signal/alert/typology definitions
from .signals import SIGNAL_DEFINITIONS
from .alerts import ALERT_RULES
from .typologies import TYPOLOGIES

__all__ = [
    # Generators
    "AMLDataGenerator",
    "generate_sample_dataset",
    "NewsEventGenerator",
    "SignalGenerator",
    "AlertRulesEngine",
    "TypologyInjector",
    # Config
    "REGIONS",
    "CUSTOMER_SEGMENTS",
    # Definitions
    "SIGNAL_DEFINITIONS",
    "ALERT_RULES",
    "TYPOLOGIES",
]



