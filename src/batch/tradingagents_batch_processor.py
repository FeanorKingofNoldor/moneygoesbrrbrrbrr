"""
TradingAgents Batch Processor
Processes filtered stocks through TradingAgents and Portfolio Constructor
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))

import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

from src.data.database import OdinDatabase
from src.portfolio.constructor import PortfolioConstructor
from src.portfolio.tracker import PositionTracker
from src.tradingagents.wrapper import OdinTradingAgentsWrapper

logger = logging.getLogger(__name__)


def safe_serialize(obj):
    """Convert non-serializable objects to strings for JSON storage"""
    try:
        return json.dumps(obj)
    except (TypeError, ValueError):
        # Convert to string representation if JSON serialization fails
        try:
            return json.dumps(str(obj))
        except:
            # Last resort - return empty JSON object
            return json.dumps({})


class TradingAgentsBatchProcessor:
    """
    Processes batches of stocks through TradingAgents
    and selects final portfolio
    """

    def __init__(self, odin_database: OdinDatabase):
        self.db = odin_database
        self.tradingagents = OdinTradingAgentsWrapper(
            odin_database=odin_database,
            use_ibkr=False,  # Set to True when IB Gateway is running
            ibkr_port=4002,  # Paper trading port
        )
        self.portfolio_constructor = PortfolioConstructor(self.db.conn)
        self.position_tracker = PositionTracker(self.db.conn)

    def process_batch(
        self,
        candidates: pd.DataFrame,
        regime_data: Dict,
        portfolio_context: Optional[Dict] = None,
    ) -> Dict:
        """
        Process all candidates through TradingAgents and select portfolio

        Args:
            candidates: DataFrame of filtered stocks from ODIN
            regime_data: Current market regime information
            portfolio_context: Current portfolio state

        Returns:
            Dictionary with final selections and analysis results
        """
        # Generate batch ID
        batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        logger.info(f"Starting batch {batch_id} with {len(candidates)} candidates")

        # Step 1: Process each stock through TradingAgents
        analysis_results = []
        failed_count = 0

        for idx, row in candidates.iterrows():
            try:
                logger.info(f"Analyzing {row['symbol']} ({idx+1}/{len(candidates)})")

                # Run TradingAgents analysis
                result = self.tradingagents.analyze_stock(
                    symbol=row["symbol"],
                    date=datetime.now().strftime("%Y-%m-%d"),
                    market_context=regime_data,
                )

                # Check if we got a valid result
                if not result or 'decision' not in result:
                    logger.warning(f"No valid decision for {row['symbol']}, skipping")
                    failed_count += 1
                    continue

                # Parse and store result
                analysis_data = self._parse_tradingagents_result(
                    result, row, regime_data
                )
                analysis_data["batch_id"] = batch_id

                # Save to database
                self._save_analysis_result(analysis_data)
                analysis_results.append(analysis_data)

            except Exception as e:
                logger.error(f"Failed to analyze {row['symbol']}: {e}")
                failed_count += 1
                continue

        logger.info(
            f"Completed TradingAgents analysis: {len(analysis_results)} successful, {failed_count} failed"
        )

        # CRITICAL: Check if we have ANY results
        if len(analysis_results) == 0:
            logger.error("CRITICAL: No stocks were successfully analyzed!")
            logger.error("Check that your LLM backend is running (OpenAI API or local server)")
            return {
                'batch_id': batch_id,
                'total_analyzed': 0,
                'buy_signals': 0,
                'selections': [],
                'excluded': [],
                'error': 'TradingAgents analysis completely failed - no stocks analyzed',
                'timestamp': datetime.now().isoformat()
            }

        # Step 2: Run Portfolio Constructor (only if we have results)
        portfolio_result = self.portfolio_constructor.construct_portfolio(
            batch_id=batch_id,
            max_positions=5,
            portfolio_context=portfolio_context,
            regime_data=regime_data,
        )

        # Step 3: Enter positions for tracking (only if we have selections)
        if portfolio_result.get("selections"):
            self.position_tracker.enter_positions(
                batch_id, portfolio_result["selections"]
            )

        # Step 4: Return complete results
        return {
            "batch_id": batch_id,
            "total_analyzed": len(analysis_results),
            "failed_analyses": failed_count,
            "buy_signals": sum(1 for r in analysis_results if r["decision"] == "BUY"),
            "selections": portfolio_result.get("selections", []),
            "excluded": portfolio_result.get("excluded", []),
            "timestamp": datetime.now().isoformat(),
            "success": len(analysis_results) > 0
        }

    def _parse_tradingagents_result(
        self, result, stock_data: pd.Series, regime_data: Dict
    ) -> Dict:
        """
        Parse TradingAgents output into structured format
        """
        # Handle case where result might be a string instead of dict
        if isinstance(result, str):
            # Convert string result to expected format
            result = {
                'decision': result,
                'raw_result': result,
                'trader_analysis': '',
            }
        
        # Ensure result is a dict at this point
        if not isinstance(result, dict):
            result = {
                'decision': str(result),
                'raw_result': str(result),
                'trader_analysis': '',
            }
        
        # Get the decision text - could be in different places
        decision_text = str(result.get("decision", ""))
        if not decision_text and result.get("raw_result"):
            decision_text = str(result.get("raw_result", ""))

        # Parse decision (BUY/SELL/HOLD)
        decision = "HOLD"  # Default
        if "BUY" in decision_text.upper():
            decision = "BUY"
        elif "SELL" in decision_text.upper():
            decision = "SELL"

        # Extract conviction score (look for number between 0-100)
        import re

        conviction_match = re.search(
            r"conviction[:\s]+(\d+)", decision_text, re.IGNORECASE
        )
        conviction = float(conviction_match.group(1)) if conviction_match else 50.0

        # Helper function to safely extract and convert prices
        def safe_extract_price(pattern, text, default_value):
            """Safely extract price from text, handling N/A and invalid values"""
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    value_str = match.group(1)
                    # Skip N/A or invalid values
                    if value_str.upper() in ['N/A', 'NA', 'NONE', 'NULL']:
                        return default_value
                    return float(value_str)
                except (ValueError, AttributeError):
                    return default_value
            return default_value

        # Get current stock price as baseline
        current_price = stock_data.get("price", 100.0)
        
        # Extract prices with safe conversion
        entry_price = safe_extract_price(
            r"entry[:\s]+\$?([\d.]+|N/?A)", 
            decision_text, 
            current_price
        )
        
        stop_loss = safe_extract_price(
            r"stop[:\s]+\$?([\d.]+|N/?A)", 
            decision_text, 
            entry_price * 0.95
        )
        
        target_price = safe_extract_price(
            r"target[:\s]+\$?([\d.]+|N/?A)", 
            decision_text, 
            entry_price * 1.05
        )

        # Calculate derived metrics with safety checks
        risk = entry_price - stop_loss if entry_price > 0 and stop_loss > 0 else entry_price * 0.05
        reward = target_price - entry_price if target_price > 0 and entry_price > 0 else entry_price * 0.05
        risk_reward_ratio = reward / risk if risk > 0 else 1.0
        expected_return = (target_price - entry_price) / entry_price if entry_price > 0 else 0.05

        return {
            "symbol": stock_data["symbol"],
            "analysis_date": datetime.now().date(),
            "decision": decision,
            "conviction_score": conviction,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "expected_return": expected_return,
            "risk_reward_ratio": risk_reward_ratio,
            "risk_score": 50,  # Default, extract if available
            "regime": regime_data["regime"],
            "fear_greed_value": regime_data["fear_greed_value"],
            "vix": regime_data["vix"],
            "rsi_2": stock_data["rsi_2"],
            "atr": stock_data["atr"],
            "volume_ratio": stock_data["volume_ratio"],
            "filter_score": stock_data["score"],
            "sector": stock_data.get("sector", "Unknown"),
            "trader_analysis": result.get("trader_analysis", ""),
            "risk_manager_analysis": decision_text,
            "full_debate_history": safe_serialize(result.get("raw_result", {})),
        }

    def _save_analysis_result(self, data: Dict):
        """Save TradingAgents analysis to database"""
        try:
            self.db.conn.execute(
                """
            INSERT OR REPLACE INTO tradingagents_analysis_results
            (batch_id, symbol, analysis_date, decision, conviction_score,
             position_size_pct, entry_price, stop_loss, target_price,
             expected_return, risk_reward_ratio, risk_score,
             regime, fear_greed_value, vix, rsi_2, atr, volume_ratio,
             filter_score, sector, trader_analysis, risk_manager_analysis,
             full_debate_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    data["batch_id"],
                    data["symbol"],
                    data["analysis_date"],
                    data["decision"],
                    data["conviction_score"],
                    20,  # Default position size, will be recalculated
                    data["entry_price"],
                    data["stop_loss"],
                    data["target_price"],
                    data["expected_return"],
                    data["risk_reward_ratio"],
                    data["risk_score"],
                    data["regime"],
                    data["fear_greed_value"],
                    data["vix"],
                    data["rsi_2"],
                    data["atr"],
                    data["volume_ratio"],
                    data["filter_score"],
                    data["sector"],
                    data["trader_analysis"],
                    data["risk_manager_analysis"],
                    data["full_debate_history"],
                ),
            )
            self.db.conn.commit()
            logger.info(f"Successfully saved analysis for {data['symbol']}")
        except Exception as e:
            logger.error(f"Failed to save analysis result: {e}")
            logger.error("Make sure you've run: sqlite3 odin_dev.db < src/data/schema_updates.sql")