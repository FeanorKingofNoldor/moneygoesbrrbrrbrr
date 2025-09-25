#!/usr/bin/env python3
"""
Main script with Portfolio Constructor integration and Performance Observer
ENHANCED with optional Pattern-Based Feedback System
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
    (Enhanced with optional pattern learning)
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

    # Initialize components (all original)
    print("\nInitializing components...")
    database = OdinDatabase()
    regime_detector = OdinRegimeDetector()
    fetcher = OdinDataFetcher()
    filter_engine = OdinFilter(database)
    batch_processor = TradingAgentsBatchProcessor(database)  # Now MAY include patterns if available
    position_tracker = PositionTracker(database.conn)
    observer = PerformanceObserver(database.conn)

    # Step 1: Detect regime (original)
    print("\n1. Detecting Market Regime...")
    regime = regime_detector.get_current_regime()
    print(f"   Regime: {regime['regime']}")
    print(f"   CNN F&G: {regime['fear_greed_value']}")
    print(f"   Strategy: {regime['strategy']}")

    # Step 2: Fetch data (original)
    print("\n2. Fetching S&P 500 Data...")
    metrics = fetcher.fetch_all_sp500()
    print(f"   ✓ Fetched {len(metrics)} stocks")
    database.insert_stock_metrics(metrics)

    # Step 3: Filter (original)
    print("\n3. Running 3-Layer Filter...")
    candidates = filter_engine.run_full_filter(regime)
    print(f"   ✓ Selected {len(candidates)} candidates")

    if not candidates.empty:
        # Generate batch ID for this run (original)
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Record filter decisions in observer (original)
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

        # Step 4: Get portfolio context (original)
        print("\n4. Getting Portfolio Context...")
        portfolio_context = {
            "cash_available": 100000,  # Replace with IBKR data
            "total_positions": 0,
            "unrealized_pnl_pct": 0,
        }

        # Step 5: Process through TradingAgents and Portfolio Constructor (original)
        print("\n5. Running TradingAgents Analysis...")
        result = batch_processor.process_batch(
            candidates=candidates,
            regime_data=regime,
            portfolio_context=portfolio_context,
        )
        
        # ADD: Note if patterns are enabled
        if result.get("patterns_enabled"):
            print("   ✓ Pattern-based feedback enabled")

        # Record TradingAgents decisions in observer (original)
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

            # Record portfolio constructor selections (original)
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

        # Step 6: Display results (original)
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

            # Record execution intent (original)
            observer.record_pipeline_decision(
                batch_id=batch_id,
                symbol=stock["symbol"],
                stage="execution",
                data={"entry_price": stock["entry_price"], "regime": regime["regime"]},
            )

        # Step 7: Update existing positions (original + pattern enhancement)
        print("\n6. Updating Open Positions...")
        position_tracker.update_positions(check_exits=True)
        
        # ADD: Close positions with pattern learning if available
        try:
            closed_positions = database.conn.execute("""
                SELECT * FROM position_tracking 
                WHERE exit_date = date('now') AND pattern_id IS NOT NULL
            """).fetchall()
            
            for pos in closed_positions:
                batch_processor.close_position_with_learning(dict(pos))
        except:
            pass  # Pattern fields might not exist
        
        # Check for recently closed positions
        closed_today = database.conn.execute("""
            SELECT * FROM position_tracking 
            WHERE exit_date = date('now') 
            AND pattern_id IS NOT NULL
        """).fetchall()

        if closed_today:
            print(f"\n   Processing {len(closed_today)} closed positions...")
            memories_injected = batch_processor.process_closed_positions(
                [dict(pos) for pos in closed_today]
            )
            print(f"   ✓ Injected {memories_injected} memories from closed trades")

        # Step 8: Analyze feedback (original)
        print("\n7. Analyzing Performance Feedback...")
        feedback = position_tracker.analyze_feedback(lookback_days=30)

        if "selected_avg_return" in feedback:
            print(f"   Selected Avg Return: {feedback['selected_avg_return']:.2f}%")
            print(f"   Excluded Avg Return: {feedback['excluded_avg_return']:.2f}%")
            print(f"   Selection Edge: {feedback['selection_edge']:.2f}%")

        # Step 9: Show observation summary (original)
        print("\n8. Observation Summary...")
        observer.print_observation_summary()
        
        # ADD: Weekly pattern analysis on Sundays (if available)
        if datetime.now().weekday() == 6:  # Sunday
            print("\n9. Weekly Pattern Analysis...")
            try:
                pattern_results = batch_processor.run_weekly_pattern_analysis()
                if 'error' not in pattern_results:
                    print(f"   ✓ Pattern analysis complete")
            except Exception as e:
                logger.debug(f"Weekly pattern analysis not available: {e}")

    print("\n✓ ODIN Portfolio Construction Complete!")


if __name__ == "__main__":
    main()