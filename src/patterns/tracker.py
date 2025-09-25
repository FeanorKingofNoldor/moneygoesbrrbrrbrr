"""
Pattern Performance Tracker
Tracks and updates pattern performance in real-time
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class PatternTracker:
    """
    Tracks pattern performance and provides real-time statistics
    """
    
    def __init__(self, pattern_db):
        """
        Args:
            pattern_db: PatternDatabase instance
        """
        self.db = pattern_db
        
        # Cache for frequently accessed patterns
        self._cache = {}
        self._cache_timeout = 300  # 5 minutes
        self._last_cache_clear = datetime.now()
    
    def track_entry(self, pattern_id: str, entry_data: Dict) -> bool:
        """
        Track when a trade enters based on a pattern
        
        Args:
            pattern_id: Pattern being traded
            entry_data: Entry information including symbol, price, indicators
            
        Returns:
            Success boolean
        """
        try:
            # Record in pattern history
            trade_data = {
                'batch_id': entry_data.get('batch_id'),
                'symbol': entry_data.get('symbol'),
                'entry_date': entry_data.get('entry_date', datetime.now().date()),
                'entry_price': entry_data.get('entry_price'),
                'rsi': entry_data.get('rsi_2'),
                'volume_ratio': entry_data.get('volume_ratio'),
                'atr': entry_data.get('atr'),
                'vix': entry_data.get('vix'),
                'fear_greed': entry_data.get('fear_greed_value'),
                'decision': entry_data.get('decision', 'BUY'),
                'conviction': entry_data.get('conviction_score', 50),
                'position_size_pct': entry_data.get('position_size_pct', 5.0)
            }
            
            success = self.db.record_pattern_trade(pattern_id, trade_data)
            
            if success:
                logger.info(f"Tracking entry for pattern {pattern_id}: {entry_data['symbol']}")
                self._invalidate_cache(pattern_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to track entry: {e}")
            return False
    
    def track_exit(self, pattern_id: str, exit_data: Dict) -> bool:
        """
        Track when a pattern-based trade exits
        
        Args:
            pattern_id: Pattern that was traded
            exit_data: Exit information including pnl, holding period
            
        Returns:
            Success boolean
        """
        try:
            # Update pattern history
            self.db.update_pattern_trade_exit(
                exit_data['batch_id'],
                exit_data['symbol'],
                exit_data
            )
            
            # Update pattern performance
            trade_result = {
                'pnl_percent': exit_data['pnl_percent'],
                'holding_days': exit_data['holding_days'],
                'max_gain_percent': exit_data.get('max_gain_percent', 0),
                'max_drawdown_percent': exit_data.get('max_drawdown_percent', 0)
            }
            
            success = self.db.update_pattern_performance(pattern_id, trade_result)
            
            if success:
                logger.info(f"Pattern {pattern_id} trade closed: {exit_data['pnl_percent']:.2f}%")
                self._invalidate_cache(pattern_id)
                
                # Check for significant events
                self._check_pattern_alerts(pattern_id)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to track exit: {e}")
            return False
    
    def get_pattern_context(self, pattern_id: str) -> Dict:
        """
        Get current pattern context for decision making
        
        Args:
            pattern_id: Pattern to get context for
            
        Returns:
            Dict with pattern statistics and recommendations
        """
        # Check cache first
        if pattern_id in self._cache:
            cached_data, timestamp = self._cache[pattern_id]
            if (datetime.now() - timestamp).seconds < self._cache_timeout:
                return cached_data
        
        # Get fresh data
        stats = self.db.get_pattern_stats(pattern_id)
        
        if not stats:
            return {
                'pattern_id': pattern_id,
                'exists': False,
                'recommendation': 'No historical data for this pattern'
            }
        
        # Build context
        context = {
            'pattern_id': pattern_id,
            'exists': True,
            'total_trades': stats['total_trades'],
            'win_rate': stats['win_rate'],
            'recent_win_rate': stats['recent_win_rate'],
            'expectancy': stats['expectancy'],
            'confidence': stats['confidence_level'],
            'momentum': self._describe_momentum(stats['momentum_score']),
            'recent_trades': stats.get('recent_trades', [])[-5:],  # Last 5
            'recommendation': self._generate_recommendation(stats)
        }
        
        # Cache the result
        self._cache[pattern_id] = (context, datetime.now())
        self._clean_cache()
        
        return context
    
    def _generate_recommendation(self, stats: Dict) -> str:
        """Generate actionable recommendation based on pattern stats"""
        
        if stats['confidence_level'] == 'low':
            return f"Low confidence - only {stats['total_trades']} trades. Use standard position sizing."
        
        if stats['recent_win_rate'] > 0.70 and stats['momentum_score'] > 0.1:
            return f"HOT pattern - {stats['recent_win_rate']:.0%} recent win rate. Consider larger position."
        
        if stats['recent_win_rate'] < 0.35:
            return f"COLD pattern - only {stats['recent_win_rate']:.0%} recent wins. Reduce size or skip."
        
        if stats['expectancy'] > 0.02:
            return f"Profitable pattern - {stats['expectancy']:.2%} expected value. Proceed with confidence."
        
        if stats['expectancy'] < -0.01:
            return f"Losing pattern - {stats['expectancy']:.2%} expected loss. Consider avoiding."
        
        return f"Neutral pattern - {stats['win_rate']:.0%} win rate. Use standard approach."
    
    def _describe_momentum(self, momentum_score: float) -> str:
        """Convert momentum score to description"""
        if momentum_score > 0.15:
            return 'strongly_improving'
        elif momentum_score > 0.05:
            return 'improving'
        elif momentum_score < -0.15:
            return 'strongly_declining'
        elif momentum_score < -0.05:
            return 'declining'
        else:
            return 'stable'
    
    def _check_pattern_alerts(self, pattern_id: str):
        """Check if pattern performance warrants an alert"""
        stats = self.db.get_pattern_stats(pattern_id)
        if not stats:
            return
        
        # Alert on pattern breakdown
        if stats['total_trades'] >= 20 and stats['recent_win_rate'] < 0.30:
            logger.warning(f"PATTERN BREAKDOWN: {pattern_id} win rate collapsed to {stats['recent_win_rate']:.0%}")
        
        # Alert on pattern emergence
        elif stats['total_trades'] >= 10 and stats['recent_win_rate'] > 0.80:
            logger.info(f"HOT PATTERN: {pattern_id} showing {stats['recent_win_rate']:.0%} recent wins")
    
    def get_pattern_report(self, regime: Optional[str] = None) -> Dict:
        """
        Generate comprehensive pattern performance report
        
        Args:
            regime: Optional regime filter
            
        Returns:
            Dict with pattern analysis
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': self.db.get_pattern_summary_stats(),
            'top_patterns': self.db.get_top_patterns(limit=5),
            'breaking_patterns': self.db.get_breaking_patterns(),
            'hot_patterns': self.db.get_hot_patterns(),
            'regime_analysis': {}
        }
        
        # Add regime-specific analysis if requested
        if regime:
            report['regime_analysis'] = {
                'regime': regime,
                'patterns': self.db.get_regime_patterns(regime),
                'best_strategy': self._find_best_strategy_for_regime(regime)
            }
        
        return report
    
    def _find_best_strategy_for_regime(self, regime: str) -> Dict:
        """Find best performing strategy type for a regime"""
        patterns = self.db.get_regime_patterns(regime)
        
        if not patterns:
            return {'error': 'No patterns for this regime'}
        
        # Group by strategy
        strategies = {}
        for pattern in patterns:
            strategy = pattern['strategy_type']
            if strategy not in strategies:
                strategies[strategy] = {
                    'count': 0,
                    'total_expectancy': 0,
                    'total_win_rate': 0
                }
            
            strategies[strategy]['count'] += 1
            strategies[strategy]['total_expectancy'] += pattern['expectancy']
            strategies[strategy]['total_win_rate'] += pattern['win_rate']
        
        # Find best
        best_strategy = None
        best_expectancy = -999
        
        for strategy, data in strategies.items():
            avg_expectancy = data['total_expectancy'] / data['count']
            if avg_expectancy > best_expectancy:
                best_expectancy = avg_expectancy
                best_strategy = {
                    'strategy': strategy,
                    'avg_expectancy': avg_expectancy,
                    'avg_win_rate': data['total_win_rate'] / data['count'],
                    'pattern_count': data['count']
                }
        
        return best_strategy
    
    def _invalidate_cache(self, pattern_id: str):
        """Remove pattern from cache when updated"""
        if pattern_id in self._cache:
            del self._cache[pattern_id]
    
    def _clean_cache(self):
        """Periodically clean old cache entries"""
        now = datetime.now()
        if (now - self._last_cache_clear).seconds > 3600:  # Every hour
            self._cache.clear()
            self._last_cache_clear = now