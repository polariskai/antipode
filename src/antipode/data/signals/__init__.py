"""Signal generation modules for synthetic data."""

from .definitions import SIGNAL_DEFINITIONS
from .generator import SignalGenerator

__all__ = [
    "SIGNAL_DEFINITIONS",
    "SignalGenerator",
]
