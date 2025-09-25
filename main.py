#!/usr/bin/env python3
"""
Main script with Portfolio Constructor integration and Performance Observer
"""

import sys
import os
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from src.regime.detector import OdinRegimeDetector
from src.data.database import OdinDatabase
from src.data.fetcher import OdinDataFetcher
from src.filtering.filter import OdinFilter
from src.batch.tradingagents_batch_processor import TradingAgentsBatchProcessor
from src.portfolio.tracker import PositionTracker
from src.feedback.observer import PerformanceObserver


def main():
    """
    Complete ODIN workflow with Portfolio Construction and Observation
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

    # Initialize components
    print("\nInitializing components...")
    database = OdinDatabase()
    regime_detector = OdinRegimeDetector()
    fetcher = OdinDataFetcher()
    filter_engine = OdinFilter(database)
    batch_processor = TradingAgentsBatchProcessor(database)
    position_tracker = PositionTracker(database.conn)

    # Initialize observer for feedback loop
    observer = PerformanceObserver(database.conn)

    # Step 1: Detect regime
    print("\n1. Detecting Market Regime...")
    regime = regime_detector.get_current_regime()
    print(f"   Regime: {regime['regime']}")
    print(f"   CNN F&G: {regime['fear_greed_value']}")
    print(f"   Strategy: {regime['strategy']}")

    # Step 2: Fetch data
    print("\n2. Fetching S&P 500 Data...")
    metrics = fetcher.fetch_all_sp500()
    print(f"   ✓ Fetched {len(metrics)} stocks")
    database.insert_stock_metrics(metrics)

    # Step 3: Filter
    print("\n3. Running 3-Layer Filter...")
    candidates = filter_engine.run_full_filter(regime)
    print(f"   ✓ Selected {len(candidates)} candidates")

    if not candidates.empty:
        # Generate batch ID for this run
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Record filter decisions in observer
        for _, row in candidates.iterrows():
            observer.record_pipeline_decision(
                batch_id=batch_id,
                symbol=row["symbol"],
                stage="filter",
                data={
                    "passed": True,
                    "score": row["score"],
                    "layer": "final",
                    "rsi_2": row["rsi_2"],
                    "volume_ratio": row["volume_ratio"],
                    "regime": regime["regime"],
                },
            )

        # Step 4: Get portfolio context
        print("\n4. Getting Portfolio Context...")
        portfolio_context = {
            "cash_available": 100000,  # Replace with IBKR data
            "total_positions": 0,
            "unrealized_pnl_pct": 0,
        }

        # Step 5: Process through TradingAgents and Portfolio Constructor
        print("\n5. Running TradingAgents Analysis...")
        result = batch_processor.process_batch(
            candidates=candidates,
            regime_data=regime,
            portfolio_context=portfolio_context,
        )

        # Record TradingAgents decisions in observer
        if result.get("success"):
            # Get the actual analysis results from database
            analysis_results = database.conn.execute(
                """
                SELECT symbol, decision, conviction_score
                FROM tradingagents_analysis_results
                WHERE batch_id = ?
            """,
                (result["batch_id"],),
            ).fetchall()

            for symbol, decision, conviction in analysis_results:
                observer.record_pipeline_decision(
                    batch_id=batch_id,
                    symbol=symbol,
                    stage="tradingagents",
                    data={"decision": decision, "conviction": conviction},
                )

            # Record portfolio constructor selections
            for stock in result.get("selections", []):
                observer.record_pipeline_decision(
                    batch_id=batch_id,
                    symbol=stock["symbol"],
                    stage="portfolio_constructor",
                    data={"selected": True},
                )

            for stock in result.get("excluded", []):
                observer.record_pipeline_decision(
                    batch_id=batch_id,
                    symbol=stock["symbol"],
                    stage="portfolio_constructor",
                    data={"selected": False},
                )

        # Step 6: Display results
        print(f"\n{'='*60}")
        print("PORTFOLIO CONSTRUCTION COMPLETE")
        print(f"{'='*60}")
        print(f"Batch ID: {result['batch_id']}")
        print(f"Total Analyzed: {result['total_analyzed']}")
        print(f"BUY Signals: {result['buy_signals']}")
        print(f"\nFINAL SELECTIONS ({len(result['selections'])}):")

        for i, stock in enumerate(result["selections"], 1):
            print(f"   {i}. {stock['symbol']}")
            print(
                f"      Position: {stock['position_size_pct']}% (${stock['position_size_dollars']:,.0f})"
            )
            print(f"      Conviction: {stock['conviction_score']:.1f}")
            print(f"      Entry: ${stock['entry_price']:.2f}")
            print(f"      Stop: ${stock['stop_loss']:.2f}")
            print(f"      Target: ${stock['target_price']:.2f}")
            print(f"      Reason: {stock.get('selection_reason', 'N/A')}")

            # Record execution intent
            observer.record_pipeline_decision(
                batch_id=batch_id,
                symbol=stock["symbol"],
                stage="execution",
                data={"entry_price": stock["entry_price"], "regime": regime["regime"]},
            )

        # Step 7: Update existing positions
        print("\n6. Updating Open Positions...")
        position_tracker.update_positions(check_exits=True)

        # Step 8: Analyze feedback (if we have history)
        print("\n7. Analyzing Performance Feedback...")
        feedback = position_tracker.analyze_feedback(lookback_days=30)

        if "selected_avg_return" in feedback:
            print(f"   Selected Avg Return: {feedback['selected_avg_return']:.2f}%")
            print(f"   Excluded Avg Return: {feedback['excluded_avg_return']:.2f}%")
            print(f"   Selection Edge: {feedback['selection_edge']:.2f}%")

        # Step 9: Show observation summary
        print("\n8. Observation Summary...")
        observer.print_observation_summary()

    print("\n✓ ODIN Portfolio Construction Complete!")


if __name__ == "__main__":
    main()
