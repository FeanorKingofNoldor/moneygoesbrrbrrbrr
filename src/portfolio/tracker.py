"""
Position Tracking Module
Tracks actual performance for feedback loop
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import logging

logger = logging.getLogger(__name__)


class PositionTracker:
    """
    Tracks positions after entry for performance analysis
    """
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def enter_positions(self, batch_id: str, selections: List[Dict]):
        """
        Record position entries in tracking table
        """
        for stock in selections:
            self.db.execute("""
            INSERT INTO position_tracking
            (batch_id, symbol, entry_date, entry_price, shares, 
             position_value, was_selected, tradingagents_conviction, regime_at_entry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                stock['symbol'],
                datetime.now().date(),
                stock['entry_price'],
                stock.get('shares', 0),
                stock['position_size_dollars'],
                1,  # was_selected = True
                stock['conviction_score'],
                stock.get('regime', 'Unknown')
            ))
        
        # Also track excluded BUY signals for comparison
        self._track_excluded_positions(batch_id)
        
        self.db.commit()
        logger.info(f"Entered {len(selections)} positions for tracking")
    
    def _track_excluded_positions(self, batch_id: str):
        """Track excluded BUY signals for regret analysis"""
        query = """
        SELECT symbol, conviction_score, entry_price, regime
        FROM tradingagents_analysis_results
        WHERE batch_id = ? AND decision = 'BUY'
        AND symbol NOT IN (
            SELECT symbol FROM portfolio_selections
            WHERE batch_id = ? AND selected = 1
        )
        """
        
        df = pd.read_sql(query, self.db, params=[batch_id, batch_id])
        
        for _, row in df.iterrows():
            self.db.execute("""
            INSERT INTO position_tracking
            (batch_id, symbol, entry_date, entry_price, 
             was_selected, tradingagents_conviction, regime_at_entry)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id,
                row['symbol'],
                datetime.now().date(),
                row['entry_price'],
                0,  # was_selected = False
                row['conviction_score'],
                row['regime']
            ))
    
    def update_positions(self, check_exits: bool = True):
        """
        Update all open positions with current prices
        Check for exit conditions if requested
        """
        # Get open positions
        query = """
        SELECT * FROM position_tracking
        WHERE exit_date IS NULL
        """
        
        positions = pd.read_sql(query, self.db)
        
        if positions.empty:
            logger.info("No open positions to update")
            return
        
        for _, pos in positions.iterrows():
            try:
                # Get current data
                ticker = yf.Ticker(pos['symbol'])
                current_price = ticker.history(period='1d')['Close'].iloc[-1]
                
                # Calculate performance
                pnl_pct = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                holding_days = (datetime.now().date() - pos['entry_date']).days
                
                # Check exit conditions
                exit_triggered = False
                exit_reason = None
                
                if check_exits:
                    # Get stop loss and target from original analysis
                    targets = self._get_exit_targets(pos['batch_id'], pos['symbol'])
                    
                    if current_price <= targets['stop_loss']:
                        exit_triggered = True
                        exit_reason = 'stop_loss'
                    elif current_price >= targets['target_price']:
                        exit_triggered = True
                        exit_reason = 'target'
                    elif holding_days >= 10:  # Max holding period
                        exit_triggered = True
                        exit_reason = 'time_limit'
                
                if exit_triggered:
                    self._exit_position(
                        pos['batch_id'],
                        pos['symbol'],
                        current_price,
                        exit_reason
                    )
                    logger.info(f"Exited {pos['symbol']}: {exit_reason} at ${current_price:.2f}")
                else:
                    # Just update metrics
                    self._update_position_metrics(
                        pos['batch_id'],
                        pos['symbol'],
                        pnl_pct,
                        holding_days
                    )
                    
            except Exception as e:
                logger.error(f"Failed to update {pos['symbol']}: {e}")
    
    def _get_exit_targets(self, batch_id: str, symbol: str) -> Dict:
        """Get stop loss and target price from original analysis"""
        query = """
        SELECT stop_loss, target_price
        FROM tradingagents_analysis_results
        WHERE batch_id = ? AND symbol = ?
        """
        
        result = self.db.execute(query, (batch_id, symbol)).fetchone()
        if result:
            return {'stop_loss': result[0], 'target_price': result[1]}
        else:
            # Default fallback
            return {'stop_loss': 0, 'target_price': float('inf')}
    
    def _exit_position(
        self,
        batch_id: str,
        symbol: str,
        exit_price: float,
        exit_reason: str
    ):
        """Record position exit"""
        # Get entry data
        query = """
        SELECT entry_price, entry_date, shares, position_value
        FROM position_tracking
        WHERE batch_id = ? AND symbol = ?
        """
        
        entry_data = self.db.execute(query, (batch_id, symbol)).fetchone()
        
        if entry_data:
            entry_price, entry_date, shares, position_value = entry_data
            holding_days = (datetime.now().date() - entry_date).days
            pnl_dollars = (exit_price - entry_price) * (shares or 0)
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
            
            # Determine performance category
            if pnl_percent > 3:
                category = 'winner'
            elif pnl_percent < -2:
                category = 'loser'
            else:
                category = 'neutral'
            
            # Update record
            self.db.execute("""
            UPDATE position_tracking
            SET exit_date = ?, exit_price = ?, exit_reason = ?,
                holding_days = ?, pnl_dollars = ?, pnl_percent = ?,
                actual_performance_category = ?, closed_at = ?
            WHERE batch_id = ? AND symbol = ?
            """, (
                datetime.now().date(),
                exit_price,
                exit_reason,
                holding_days,
                pnl_dollars,
                pnl_percent,
                category,
                datetime.now(),
                batch_id,
                symbol
            ))
            
            self.db.commit()
    
    def _update_position_metrics(
        self,
        batch_id: str,
        symbol: str,
        current_pnl_pct: float,
        holding_days: int
    ):
        """Update position metrics without exiting"""
        # Track max gain/drawdown
        query = """
        SELECT max_gain_percent, max_drawdown_percent
        FROM position_tracking
        WHERE batch_id = ? AND symbol = ?
        """
        
        result = self.db.execute(query, (batch_id, symbol)).fetchone()
        if result:
            max_gain = max(result[0] or 0, current_pnl_pct)
            max_drawdown = min(result[1] or 0, current_pnl_pct)
            
            self.db.execute("""
            UPDATE position_tracking
            SET max_gain_percent = ?, max_drawdown_percent = ?, holding_days = ?
            WHERE batch_id = ? AND symbol = ?
            """, (max_gain, max_drawdown, holding_days, batch_id, symbol))
            
            self.db.commit()
    
    def analyze_feedback(self, lookback_days: int = 30) -> Dict:
        """
        Analyze performance for feedback loop
        Compare selected vs excluded stocks
        """
        cutoff_date = datetime.now().date() - timedelta(days=lookback_days)
        
        # Get closed positions
        query = """
        SELECT 
            symbol,
            was_selected,
            tradingagents_conviction,
            pnl_percent,
            actual_performance_category,
            exit_reason
        FROM position_tracking
        WHERE exit_date >= ? AND exit_date IS NOT NULL
        """
        
        df = pd.read_sql(query, self.db, params=[cutoff_date])
        
        if df.empty:
            return {"message": "No closed positions to analyze"}
        
        # Calculate metrics
        selected = df[df['was_selected'] == 1]
        excluded = df[df['was_selected'] == 0]
        
        analysis = {
            "period_days": lookback_days,
            "total_positions": len(df),
            
            # Selected performance
            "selected_count": len(selected),
            "selected_avg_return": selected['pnl_percent'].mean() if len(selected) > 0 else 0,
            "selected_win_rate": (selected['actual_performance_category'] == 'winner').mean() if len(selected) > 0 else 0,
            
            # Excluded performance (what we missed)
            "excluded_count": len(excluded),
            "excluded_avg_return": excluded['pnl_percent'].mean() if len(excluded) > 0 else 0,
            "excluded_win_rate": (excluded['actual_performance_category'] == 'winner').mean() if len(excluded) > 0 else 0,
            
            # Regret analysis
            "selection_edge": (selected['pnl_percent'].mean() - excluded['pnl_percent'].mean()) if len(selected) > 0 and len(excluded) > 0 else 0
        }
        
        # Find best missed opportunity
        if len(excluded) > 0:
            best_excluded = excluded.nlargest(1, 'pnl_percent').iloc[0]
            analysis['best_missed'] = {
                "symbol": best_excluded['symbol'],
                "return": best_excluded['pnl_percent'],
                "conviction": best_excluded['tradingagents_conviction']
            }
        
        # Find worst selection
        if len(selected) > 0:
            worst_selected = selected.nsmallest(1, 'pnl_percent').iloc[0]
            analysis['worst_selected'] = {
                "symbol": worst_selected['symbol'],
                "return": worst_selected['pnl_percent'],
                "conviction": worst_selected['tradingagents_conviction']
            }
        
        # Save to feedback_analysis table
        self._save_feedback_analysis(analysis)
        
        return analysis
    
    def _save_feedback_analysis(self, analysis: Dict):
        """Save feedback analysis to database"""
        self.db.execute("""
        INSERT INTO feedback_analysis
        (analysis_date, selected_stocks_performance, excluded_buys_performance,
         selection_accuracy, tradingagents_accuracy, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().date(),
            analysis.get('selected_avg_return', 0),
            analysis.get('excluded_avg_return', 0),
            analysis.get('selected_win_rate', 0),
            analysis.get('selection_edge', 0),
            json.dumps(analysis)
        ))
        
        self.db.commit()

    def close_position_with_pattern_learning(self, position_id: int, exit_price: float, 
                                            exit_reason: str, pattern_wrapper=None):
        """
        Close position and trigger pattern learning
        Enhanced to inject both trade and pattern memories
        """
        # Get position data
        position = self.conn.execute("""
            SELECT * FROM position_tracking WHERE id = ?
        """, (position_id,)).fetchone()
        
        if not position:
            return False
        
        # Calculate P&L
        position_data = dict(position)
        position_data['exit_price'] = exit_price
        position_data['exit_reason'] = exit_reason
        position_data['exit_date'] = datetime.now().date()
        position_data['pnl_percent'] = ((exit_price - position_data['entry_price']) / 
                                        position_data['entry_price'] * 100)
        position_data['holding_days'] = (position_data['exit_date'] - 
                                        position_data['entry_date']).days
        
        # Update database
        self.conn.execute("""
            UPDATE position_tracking 
            SET exit_date = ?, exit_price = ?, exit_reason = ?,
                holding_days = ?, pnl_percent = ?, pnl_dollars = ?
            WHERE id = ?
        """, (
            position_data['exit_date'],
            exit_price,
            exit_reason,
            position_data['holding_days'],
            position_data['pnl_percent'],
            position_data['pnl_percent'] * position_data['position_value'] / 100,
            position_id
        ))
        self.conn.commit()
        
        # ENHANCED: Inject memories if pattern system available
        if pattern_wrapper and position_data.get('pattern_id'):
            try:
                # Update pattern performance
                pattern_wrapper.tracker.track_exit(
                    position_data['pattern_id'],
                    position_data
                )
                
                # Get updated pattern stats
                pattern_stats = pattern_wrapper.pattern_db.get_pattern_stats(
                    position_data['pattern_id']
                )
                
                # Inject both trade and pattern memories
                if pattern_stats:
                    pattern_wrapper.memory_injector.inject_closed_position_memories(
                        position_data, pattern_stats
                    )
                    logger.info(f"Injected hybrid memories for {position_data['symbol']}")
                    
            except Exception as e:
                logger.warning(f"Pattern memory injection failed: {e}")
        
        return True