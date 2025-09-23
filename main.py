#!/usr/bin/env python3
"""
ODIN - Optimized Data Intelligence Network
Main entry point for the trading system
"""

import sys
import time
from datetime import datetime

from src.regime.detector import OdinRegimeDetector
from src.data.database import OdinDatabase
from src.data.fetcher import OdinDataFetcher
from src.filtering.filter import OdinFilter


# Initialize components
print("Initializing ODIN components...")
regime_detector = OdinRegimeDetector()
database = OdinDatabase()

def main():
    """
    Main ODIN workflow
    """
    print(
        """
    ╔═══════════════════════════════════╗
    ║           ODIN SYSTEM             ║
    ║  Optimized Data Intelligence      ║
    ║          Network v1.0             ║
    ╚═══════════════════════════════════╝
    """
    )

    # Get current market regime
    print("\n1. Detecting Market Regime...")
    regime = regime_detector.get_current_regime()

    print(f"   Regime: {regime['regime'].upper()}")
    print(f"   CNN Fear & Greed: {regime['fear_greed_value']}")
    print(f"   VIX: {regime['vix']:.2f}")
    print(f"   Strategy: {regime['strategy']}")
    print(f"   Expected Win Rate: {regime['expected_win_rate']:.1%}")
    print(f"   Position Size Multiplier: {regime['position_multiplier']}x")

    # Log regime to database
    database.log_regime(regime)
    print("   ✓ Regime logged to database")


def main():
    """
    Main ODIN workflow
    """
    print(
        """
    ╔═══════════════════════════════════╗
    ║           ODIN SYSTEM             ║
    ║  Optimized Data Intelligence      ║
    ║          Network v1.0             ║
    ╚═══════════════════════════════════════╝
    """
    )

    # Get current market regime
    print("\n1. Detecting Market Regime...")
    regime = regime_detector.get_current_regime()

    print(f"   Regime: {regime['regime'].upper()}")
    print(f"   CNN Fear & Greed: {regime['fear_greed_value']}")
    print(f"   VIX: {regime['vix']:.2f}")
    print(f"   Strategy: {regime['strategy']}")
    print(f"   Expected Win Rate: {regime['expected_win_rate']:.1%}")
    print(f"   Position Size Multiplier: {regime['position_multiplier']}x")

    # Log regime to database
    database.log_regime(regime)
    print("   ✓ Regime logged to database")

    # Fetch market data
    print("\n2. Fetching Market Data...")
    fetcher = OdinDataFetcher()
    metrics = fetcher.fetch_all_sp500()  # Gets ALL S&P 500

    if not metrics.empty:
        print(f"   ✓ Fetched data for {len(metrics)} stocks")
        database.insert_stock_metrics(metrics)
        print("   ✓ Saved to database")
    else:
        print("   ⚠ No data fetched")

    # Run 3-layer filter
    print("\n3. Applying 3-Layer Filter...")
    filter = OdinFilter(database)
    candidates = filter.run_full_filter(regime)

    if not candidates.empty:
        print(f"\n   Selected Candidates (Regime: {regime['regime'].upper()}):")
        for _, stock in candidates.head(10).iterrows():
            print(
                f"   - {stock['symbol']}: Score={stock['score']:.3f}, "
                f"RSI={stock['rsi_2']:.1f}, Volume={stock['volume_ratio']:.1f}x"
            )

    print("\n4. Next Steps:")
    print("   - Send filtered stocks to TradingAgents")
    print("   - Execute trades based on signals")

    print("\nODIN initialized successfully!")


if __name__ == "__main__":
    main()
