# Trading Strategies Package
#
# This package contains different trading strategies for the NATGAS TRADER.
# Strategies define how trades are executed based on signals.

from .mutual_exclusivity_strategy import MutualExclusivityStrategy

__all__ = ['MutualExclusivityStrategy']
