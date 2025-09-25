"""
TradingAgents Batch Processor
Processes filtered stocks through TradingAgents and Portfolio Constructor
ENHANCED with Pattern-Based Feedback System (preserving existing functionality)
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
from src.tradingagents.coordinator import OdinTradingAgentsCoordinator
from config.settings import (
    IBKR_ENABLED,
    IBKR_DEFAULT_PORT,
    PATTERN_LEARNING_TRIGGER,
)

# ADD: Pattern system imports (only if they exist)
try:
    from src.integrations.pattern_wrapper import PatternEnhancedWrapper
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False
    logging.info("Pattern system not available - continuing without patterns")

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
    
    # Add this method to TradingAgentsBatchProcessor class:

    def process_closed_positions(self, closed_positions: List[Dict]):
        """
        Process closed positions for pattern learning and memory injection
        """
        if not self.pattern_wrapper:
            return 0
        
        memories_injected = 0
        
        for position in closed_positions:
            try:
                # Skip if no pattern
                if not position.get('pattern_id'):
                    continue
                
                # Update pattern stats
                self.pattern_wrapper.tracker.track_exit(
                    position['pattern_id'],
                    position
                )
                
                # Get updated pattern stats
                pattern_stats = self.pattern_wrapper.pattern_db.get_pattern_stats(
                    position['pattern_id']
                )
                
                if pattern_stats:
                    # Inject hybrid memories
                    count = self.pattern_wrapper.memory_injector.inject_closed_position_memories(
                        position, pattern_stats
                    )
                    memories_injected += count
                    
            except Exception as e:
                logger.warning(f"Failed to process closed position: {e}")
        
        if memories_injected > 0:
            logger.info(f"Injected {memories_injected} memories from {len(closed_positions)} closed positions")
        
        return memories_injected

    def __init__(self, odin_database: OdinDatabase):
        self.db = odin_database
        
        # Use settings instead of hardcoding
        self.tradingagents = OdinTradingAgentsWrapper(
            odin_database=odin_database,
            use_ibkr=IBKR_ENABLED,      # From settings (True)
            ibkr_port=IBKR_DEFAULT_PORT  # From settings (4002 for paper)
        )
        
        self.portfolio_constructor = PortfolioConstructor(self.db.conn)
        self.position_tracker = PositionTracker(self.db.conn)
        
        # ADD: Pattern system if available (won't break if not installed)
        self.pattern_wrapper = None
        if PATTERNS_AVAILABLE:
            try:
                self.pattern_wrapper = PatternEnhancedWrapper(
                    self.tradingagents,
                    self.db.conn
                )
                logger.info("Pattern-based feedback system initialized")
                # Initialize with historical patterns
                self.pattern_wrapper.initialize_pattern_memories(min_trades=10)
            except Exception as e:
                logger.warning(f"Pattern system initialization failed: {e}")
                self.pattern_wrapper = None

    def process_batch(
        self,
        candidates: pd.DataFrame,
        regime_data: Dict,
        portfolio_context: Optional[Dict] = None,
    ) -> Dict:
        """
        Process all candidates through TradingAgents and select portfolio
        (Enhanced with optional pattern tracking)

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

                # ENHANCED: Use pattern-aware analysis if available
                if self.pattern_wrapper:
                    try:
                        result = self.pattern_wrapper.analyze_with_patterns(
                            symbol=row["symbol"],
                            stock_metrics=row.to_dict(),
                            regime_data=regime_data,
                            batch_id=batch_id
                        )
                    except Exception as e:
                        logger.warning(f"Pattern analysis failed, using standard: {e}")
                        # Fallback to standard analysis
                        result = self.tradingagents.analyze_stock(
                            symbol=row["symbol"],
                            date=datetime.now().strftime("%Y-%m-%d"),
                            market_context=regime_data,
                        )
                else:
                    # Standard TradingAgents analysis (original code)
                    result = self.tradingagents.analyze_stock(
                        symbol=row["symbol"],
                        date=datetime.now().strftime("%Y-%m-%d"),
                        market_context=regime_data,
                    )

                # Check if we got a valid result (original validation)
                if not result or 'decision' not in result:
                    logger.warning(f"No valid decision for {row['symbol']}, skipping")
                    failed_count += 1
                    continue

                # Parse and store result (using original method)
                analysis_data = self._parse_tradingagents_result(
                    result, row, regime_data
                )
                analysis_data["batch_id"] = batch_id
                
                # ADD: Pattern data if available
                if self.pattern_wrapper and 'pattern_id' in result:
                    analysis_data["pattern_id"] = result.get("pattern_id")
                    analysis_data["pattern_win_rate"] = result.get("pattern_context", {}).get("win_rate", 0)
                    analysis_data["pattern_expectancy"] = result.get("pattern_context", {}).get("expectancy", 0)

                # Save to database (will work with or without pattern fields)
                self._save_analysis_result(analysis_data)
                analysis_results.append(analysis_data)

            except Exception as e:
                logger.error(f"Failed to analyze {row['symbol']}: {e}")
                failed_count += 1
                continue

        logger.info(
            f"Completed TradingAgents analysis: {len(analysis_results)} successful, {failed_count} failed"
        )

        # CRITICAL: Check if we have ANY results (original validation)
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

        # Step 2: Run Portfolio Constructor (original code)
        portfolio_result = self.portfolio_constructor.construct_portfolio(
            batch_id=batch_id,
            max_positions=5,
            portfolio_context=portfolio_context,
            regime_data=regime_data,
        )

        # Step 3: Enter positions for tracking (enhanced with patterns)
        if portfolio_result.get("selections"):
            # Original position tracking
            self.position_tracker.enter_positions(
                batch_id, portfolio_result["selections"]
            )
            
            # ADD: Pattern tracking for selected positions
            if self.pattern_wrapper:
                for selection in portfolio_result["selections"]:
                    # Find pattern data for this selection
                    for result in analysis_results:
                        if result["symbol"] == selection["symbol"] and "pattern_id" in result:
                            # Update position with pattern data
                            try:
                                self.db.conn.execute("""
                                    UPDATE position_tracking 
                                    SET pattern_id = ?, pattern_confidence = ?
                                    WHERE batch_id = ? AND symbol = ?
                                """, (
                                    result["pattern_id"],
                                    result.get("pattern_context", {}).get("confidence", "low"),
                                    batch_id,
                                    selection["symbol"]
                                ))
                                self.db.conn.commit()
                            except:
                                pass  # Pattern fields might not exist in DB

        # ADD: Trigger pattern learning if applicable
        if self.pattern_wrapper:
            try:
                completed_trades = self._get_completed_trade_count()
                if completed_trades > 0 and completed_trades % PATTERN_LEARNING_TRIGGER == 0:
                    logger.info(f"Triggering pattern learning after {completed_trades} trades")
                    self.pattern_wrapper.run_pattern_learning(frequency='daily')
            except Exception as e:
                logger.warning(f"Pattern learning check failed: {e}")

        # Step 4: Return complete results (original structure preserved)
        return {
            "batch_id": batch_id,
            "total_analyzed": len(analysis_results),
            "failed_analyses": failed_count,
            "buy_signals": sum(1 for r in analysis_results if r["decision"] == "BUY"),
            "selections": portfolio_result.get("selections", []),
            "excluded": portfolio_result.get("excluded", []),
            "timestamp": datetime.now().isoformat(),
            "success": len(analysis_results) > 0,
            # ADD: Pattern info if available
            "patterns_enabled": self.pattern_wrapper is not None
        }
    
    # ADD: New methods for pattern system (won't affect existing functionality)
    def close_position_with_learning(self, position_data: Dict):
        """Close position and trigger pattern learning if available"""
        if self.pattern_wrapper:
            try:
                return self.pattern_wrapper.close_position_with_pattern(position_data)
            except Exception as e:
                logger.warning(f"Pattern close failed: {e}")
        return {'pattern_tracked': False}
    
    def run_weekly_pattern_analysis(self):
        """Run weekly pattern analysis if available"""
        if self.pattern_wrapper:
            try:
                return self.pattern_wrapper.run_pattern_learning(frequency='weekly')
            except Exception as e:
                logger.error(f"Weekly pattern analysis failed: {e}")
                return {'error': str(e)}
        return {'error': 'Pattern system not available'}
    
    def _get_completed_trade_count(self) -> int:
        """Get count of completed trades for learning trigger"""
        try:
            query = "SELECT COUNT(*) as count FROM position_tracking WHERE exit_date IS NOT NULL"
            result = self.db.conn.execute(query).fetchone()
            return result[0] if result else 0
        except:
            return 0

    # ALL ORIGINAL METHODS REMAIN UNCHANGED
    def _parse_tradingagents_result(
        self, result, stock_data: pd.Series, regime_data: Dict
    ) -> Dict:
        """
        Parse TradingAgents output into structured format
        (Original implementation preserved)
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
        """Save TradingAgents analysis to database (handles pattern fields gracefully)"""
        try:
            # Try to save with pattern fields if they exist
            if "pattern_id" in data:
                try:
                    self.db.conn.execute(
                        """
                    INSERT OR REPLACE INTO tradingagents_analysis_results
                    (batch_id, symbol, analysis_date, decision, conviction_score,
                     position_size_pct, entry_price, stop_loss, target_price,
                     expected_return, risk_reward_ratio, risk_score,
                     regime, fear_greed_value, vix, rsi_2, atr, volume_ratio,
                     filter_score, sector, trader_analysis, risk_manager_analysis,
                     full_debate_history, pattern_id, pattern_components)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            data.get("pattern_id", None),
                            json.dumps(data.get("pattern_components", {}))
                        ),
                    )
                except:
                    # Pattern fields don't exist, use original query
                    raise
            else:
                # Original save without pattern fields
                raise  # Go to original save
                
        except:
            # Fallback to original save query
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