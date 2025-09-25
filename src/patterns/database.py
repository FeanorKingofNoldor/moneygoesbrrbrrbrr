"""
Pattern Database Operations
Handles all database interactions for the pattern-based feedback system
"""

import sqlite3
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


class PatternDatabase:
    """
    Single responsibility: All pattern-related database operations
    """
    
    def __init__(self, db_connection: sqlite3.Connection):
        """
        Args:
            db_connection: Existing database connection from OdinDatabase
        """
        self.conn = db_connection
        self.conn.row_factory = sqlite3.Row  # Return dict-like rows
        
    # ==========================================
    # Pattern CRUD Operations
    # ==========================================
    
    def create_pattern(self, pattern_id: str, components: Dict) -> bool:
        """
        Create a new pattern entry
        
        Args:
            pattern_id: Unique pattern identifier
            components: Dict with strategy_type, market_regime, volume_profile, technical_setup
        """
        try:
            query = """
            INSERT OR IGNORE INTO trade_patterns (
                pattern_id, strategy_type, market_regime, 
                volume_profile, technical_setup, first_seen_date
            ) VALUES (?, ?, ?, ?, ?, date('now'))
            """
            
            self.conn.execute(query, (
                pattern_id,
                components['strategy_type'],
                components['market_regime'],
                components['volume_profile'],
                components['technical_setup']
            ))
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to create pattern {pattern_id}: {e}")
            return False
    
    def get_pattern_stats(self, pattern_id: str) -> Optional[Dict]:
        """
        Get current performance statistics for a pattern
        
        Returns:
            Dict with pattern performance metrics or None
        """
        query = """
        SELECT 
            pattern_id,
            strategy_type,
            market_regime,
            volume_profile,
            technical_setup,
            total_trades,
            winning_trades,
            losing_trades,
            win_rate,
            avg_win_percent,
            avg_loss_percent,
            expectancy,
            recent_win_rate,
            recent_avg_return,
            momentum_score,
            confidence_level,
            recent_trades,
            last_traded_date
        FROM trade_patterns
        WHERE pattern_id = ?
        """
        
        cursor = self.conn.execute(query, (pattern_id,))
        row = cursor.fetchone()
        
        if row:
            result = dict(row)
            # Parse JSON fields
            if result['recent_trades']:
                result['recent_trades'] = json.loads(result['recent_trades'])
            return result
        return None
    
    def update_pattern_performance(self, pattern_id: str, trade_result: Dict) -> bool:
        """
        Update pattern metrics with a new trade result
        
        Args:
            pattern_id: Pattern to update
            trade_result: Dict with pnl_percent, holding_days, max_gain, max_drawdown
        """
        try:
            # Get current stats
            current = self.get_pattern_stats(pattern_id)
            if not current:
                logger.warning(f"Pattern {pattern_id} not found")
                return False
            
            # Update totals
            total_trades = current['total_trades'] + 1
            winning_trades = current['winning_trades'] + (1 if trade_result['pnl_percent'] > 0 else 0)
            losing_trades = current['losing_trades'] + (1 if trade_result['pnl_percent'] <= 0 else 0)
            
            # Update averages
            if trade_result['pnl_percent'] > 0:
                avg_win = ((current['avg_win_percent'] * current['winning_trades']) + 
                          trade_result['pnl_percent']) / (winning_trades or 1)
            else:
                avg_win = current['avg_win_percent']
                
            if trade_result['pnl_percent'] <= 0:
                avg_loss = ((current['avg_loss_percent'] * current['losing_trades']) + 
                           abs(trade_result['pnl_percent'])) / (losing_trades or 1)
            else:
                avg_loss = current['avg_loss_percent']
            
            # Calculate new metrics
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
            
            # Update recent trades (rolling 20)
            recent_trades = current['recent_trades'] or []
            recent_trades.append(trade_result['pnl_percent'])
            if len(recent_trades) > 20:
                recent_trades = recent_trades[-20:]
            
            # Calculate recent metrics
            recent_wins = sum(1 for t in recent_trades if t > 0)
            recent_win_rate = recent_wins / len(recent_trades) if recent_trades else 0
            recent_avg_return = sum(recent_trades) / len(recent_trades) if recent_trades else 0
            
            # Calculate momentum (recent vs overall performance)
            momentum_score = recent_win_rate - win_rate
            
            # Determine confidence level
            if total_trades >= 50:
                confidence_level = 'high'
            elif total_trades >= 20:
                confidence_level = 'medium'
            else:
                confidence_level = 'low'
            
            # Update database
            update_query = """
            UPDATE trade_patterns SET
                total_trades = ?,
                winning_trades = ?,
                losing_trades = ?,
                win_rate = ?,
                avg_win_percent = ?,
                avg_loss_percent = ?,
                expectancy = ?,
                recent_trades = ?,
                recent_win_rate = ?,
                recent_avg_return = ?,
                momentum_score = ?,
                confidence_level = ?,
                last_traded_date = date('now'),
                last_updated = datetime('now')
            WHERE pattern_id = ?
            """
            
            self.conn.execute(update_query, (
                total_trades, winning_trades, losing_trades, win_rate,
                avg_win, avg_loss, expectancy, json.dumps(recent_trades),
                recent_win_rate, recent_avg_return, momentum_score,
                confidence_level, pattern_id
            ))
            
            self.conn.commit()
            
            # Log significant changes
            if abs(momentum_score) > 0.15:
                logger.info(f"Pattern {pattern_id} showing significant momentum: {momentum_score:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update pattern {pattern_id}: {e}")
            return False
    
    # ==========================================
    # Pattern Analysis Queries
    # ==========================================
    
    def get_top_patterns(self, limit: int = 10, min_trades: int = 20) -> List[Dict]:
        """Get best performing patterns"""
        query = """
        SELECT * FROM trade_patterns
        WHERE total_trades >= ? AND is_active = 1
        ORDER BY expectancy DESC
        LIMIT ?
        """
        
        cursor = self.conn.execute(query, (min_trades, limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_breaking_patterns(self, threshold: float = 0.40, min_trades: int = 20) -> List[Dict]:
        """Get patterns that are breaking down"""
        query = """
        SELECT *,
               (recent_win_rate - win_rate) as performance_delta
        FROM trade_patterns
        WHERE total_trades >= ?
          AND recent_win_rate < ?
          AND win_rate > 0.50
          AND is_active = 1
        ORDER BY performance_delta ASC
        """
        
        cursor = self.conn.execute(query, (min_trades, threshold))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_regime_patterns(self, regime: str) -> List[Dict]:
        """Get all patterns for a specific regime"""
        query = """
        SELECT * FROM trade_patterns
        WHERE market_regime = ? AND is_active = 1
        ORDER BY expectancy DESC
        """
        
        cursor = self.conn.execute(query, (regime.lower().replace(' ', '_'),))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_hot_patterns(self, min_improvement: float = 0.10) -> List[Dict]:
        """Get patterns showing strong recent improvement"""
        query = """
        SELECT *,
               (recent_win_rate - win_rate) as improvement
        FROM trade_patterns
        WHERE total_trades >= 10
          AND recent_win_rate > win_rate + ?
          AND is_active = 1
        ORDER BY improvement DESC
        """
        
        cursor = self.conn.execute(query, (min_improvement,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ==========================================
    # Pattern History Tracking
    # ==========================================
    
    def record_pattern_trade(self, pattern_id: str, trade_data: Dict) -> bool:
        """
        Record a new trade for pattern history
        
        Args:
            pattern_id: Pattern identifier
            trade_data: Complete trade information
        """
        try:
            query = """
            INSERT INTO pattern_trade_history (
                pattern_id, batch_id, symbol,
                entry_date, entry_price, entry_rsi,
                entry_volume_ratio, entry_atr, entry_vix,
                entry_fear_greed, tradingagents_decision,
                tradingagents_conviction, position_size_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self.conn.execute(query, (
                pattern_id,
                trade_data['batch_id'],
                trade_data['symbol'],
                trade_data['entry_date'],
                trade_data['entry_price'],
                trade_data.get('rsi', None),
                trade_data.get('volume_ratio', None),
                trade_data.get('atr', None),
                trade_data.get('vix', None),
                trade_data.get('fear_greed', None),
                trade_data.get('decision', 'HOLD'),
                trade_data.get('conviction', 0),
                trade_data.get('position_size_pct', 0)
            ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to record pattern trade: {e}")
            return False
    
    def update_pattern_trade_exit(self, batch_id: str, symbol: str, exit_data: Dict) -> bool:
        """Update pattern trade with exit information"""
        try:
            query = """
            UPDATE pattern_trade_history SET
                exit_date = ?,
                exit_price = ?,
                exit_reason = ?,
                holding_days = ?,
                pnl_percent = ?,
                max_gain_percent = ?,
                max_drawdown_percent = ?
            WHERE batch_id = ? AND symbol = ?
            """
            
            self.conn.execute(query, (
                exit_data.get('exit_date'),
                exit_data.get('exit_price'),
                exit_data.get('exit_reason', 'unknown'),  # Default if missing
                exit_data.get('holding_days'),
                exit_data.get('pnl_percent'),
                exit_data.get('max_gain_percent', 0),
                exit_data.get('max_drawdown_percent', 0),
                batch_id, symbol
            ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update pattern trade exit: {e}")
            return False
    
    # ==========================================
    # Learning and Memory Operations
    # ==========================================
    
    def record_learning_event(self, lesson_type: str, patterns: List[str], 
                             situation: str, recommendation: str,
                             memory_systems: List[str]) -> bool:
        """Record when a lesson is learned and injected into memory"""
        try:
            query = """
            INSERT INTO pattern_learning_log (
                learning_date, lesson_type, pattern_ids_affected,
                situation, recommendation, injected_to_memories
            ) VALUES (date('now'), ?, ?, ?, ?, ?)
            """
            
            self.conn.execute(query, (
                lesson_type,
                json.dumps(patterns),
                situation,
                recommendation,
                json.dumps(memory_systems)
            ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to record learning event: {e}")
            return False
    
    def get_recent_lessons(self, days: int = 7) -> List[Dict]:
        """Get recently learned lessons"""
        query = """
        SELECT * FROM pattern_learning_log
        WHERE learning_date > date('now', '-' || ? || ' days')
        ORDER BY learning_date DESC
        """
        
        cursor = self.conn.execute(query, (days,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ==========================================
    # Regime Transition Detection
    # ==========================================
    
    def detect_regime_transition(self, from_regime: str, to_regime: str, 
                                transition_date: str) -> Dict:
        """
        Analyze pattern performance changes during regime transition
        
        Returns:
            Dict with patterns that broke and patterns that emerged
        """
        # Get patterns performance before transition
        before_query = """
        SELECT pattern_id, win_rate, expectancy
        FROM trade_patterns
        WHERE market_regime = ? AND total_trades >= 10
        """
        
        before_patterns = pd.read_sql(before_query, self.conn, params=[from_regime])
        
        # This would need actual trade history to determine post-transition performance
        # For now, return structure
        return {
            'from_regime': from_regime,
            'to_regime': to_regime,
            'transition_date': transition_date,
            'patterns_affected': len(before_patterns),
            'analysis_pending': True
        }
    
    # ==========================================
    # Utility Methods
    # ==========================================
    
    def get_pattern_summary_stats(self) -> Dict:
        """Get overall pattern system statistics"""
        query = """
        SELECT 
            COUNT(DISTINCT pattern_id) as total_patterns,
            SUM(total_trades) as total_trades,
            AVG(win_rate) as avg_win_rate,
            AVG(expectancy) as avg_expectancy,
            COUNT(CASE WHEN confidence_level = 'high' THEN 1 END) as high_confidence_patterns,
            COUNT(CASE WHEN momentum_score > 0.1 THEN 1 END) as improving_patterns,
            COUNT(CASE WHEN momentum_score < -0.1 THEN 1 END) as declining_patterns
        FROM trade_patterns
        WHERE is_active = 1
        """
        
        cursor = self.conn.execute(query)
        return dict(cursor.fetchone())
    
    def deactivate_stale_patterns(self, days_inactive: int = 30) -> int:
        """Deactivate patterns that haven't been traded recently"""
        query = """
        UPDATE trade_patterns
        SET is_active = 0
        WHERE last_traded_date < date('now', '-' || ? || ' days')
          AND is_active = 1
        """
        
        cursor = self.conn.execute(query, (days_inactive,))
        self.conn.commit()
        
        deactivated = cursor.rowcount
        if deactivated > 0:
            logger.info(f"Deactivated {deactivated} stale patterns")
        
        return deactivated