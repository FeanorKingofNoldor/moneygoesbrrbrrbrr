"""
Pattern Classification System
Classifies trades into patterns based on market conditions and technical indicators
"""

import logging
from typing import Dict, Optional, Tuple
from datetime import datetime
from config.settings import (
    PATTERN_RSI_THRESHOLDS,
    PATTERN_VOLUME_THRESHOLDS,
    PATTERN_FEAR_GREED_THRESHOLDS,
    PATTERN_STRATEGY_TYPES
)

logger = logging.getLogger(__name__)


class PatternClassifier:
    """
    Classifies trades into patterns for tracking and learning
    """
    
    def __init__(self, pattern_db):
        """
        Args:
            pattern_db: PatternDatabase instance for pattern operations
        """
        self.db = pattern_db
        
        # Define classification thresholds
        self.thresholds = {
            'rsi': PATTERN_RSI_THRESHOLDS,
            'volume': PATTERN_VOLUME_THRESHOLDS,
            'fear_greed': PATTERN_FEAR_GREED_THRESHOLDS
        }
    
    def classify_trade(self, stock_metrics: Dict, regime_data: Dict) -> Dict:
        """
        Main classification method - determines pattern for a potential trade
        
        Args:
            stock_metrics: Dict with rsi_2, volume_ratio, sma20_ratio, etc.
            regime_data: Dict with regime, fear_greed_value, vix
            
        Returns:
            Dict with pattern_id and components
        """
        try:
            # Extract components
            strategy = self._classify_strategy(stock_metrics)
            regime = self._classify_regime(regime_data)
            volume = self._classify_volume(stock_metrics)
            technical = self._classify_technical(stock_metrics)
            
            # Generate pattern ID
            pattern_id = f"{strategy}_{regime}_{volume}_{technical}"
            
            components = {
                'strategy_type': strategy,
                'market_regime': regime,
                'volume_profile': volume,
                'technical_setup': technical
            }
            
            # Ensure pattern exists in database
            self.db.create_pattern(pattern_id, components)
            
            # Get current stats
            stats = self.db.get_pattern_stats(pattern_id)
            
            return {
                'pattern_id': pattern_id,
                'components': components,
                'stats': stats,
                'classification_confidence': self._calculate_confidence(stock_metrics)
            }
            
        except Exception as e:
            logger.error(f"Failed to classify trade: {e}")
            return {
                'pattern_id': 'unknown',
                'components': {},
                'stats': None,
                'error': str(e)
            }
    
    def _classify_strategy(self, metrics: Dict) -> str:
        """
        Determine strategy type based on indicators
        
        Returns: 'mean_reversion', 'momentum', 'breakout', or 'bounce'
        """
        rsi = metrics.get('rsi_2', 50)
        volume_ratio = metrics.get('volume_ratio', 1.0)
        price_vs_sma20 = metrics.get('price_vs_sma20', 1.0)
        
        # Mean Reversion: Oversold with price below average
        if rsi < self.thresholds['rsi']['oversold'] and price_vs_sma20 < 0.98:
            return 'mean_reversion'
        
        # Momentum: Overbought with high volume
        elif rsi > self.thresholds['rsi']['overbought'] and volume_ratio > self.thresholds['volume']['high']:
            return 'momentum'
        
        # Breakout: Price crossing above average with volume
        elif 0.99 < price_vs_sma20 < 1.02 and volume_ratio > self.thresholds['volume']['high']:
            return 'breakout'
        
        # Bounce: Recovery from oversold
        elif 30 < rsi < 50 and metrics.get('rsi_change', 0) > 5:
            return 'bounce'
        
        # Default to mean reversion for our strategy
        else:
            return 'mean_reversion'
    
    def _classify_regime(self, regime_data: Dict) -> str:
        """
        Classify market regime based on Fear & Greed
        
        Returns: 'extreme_fear', 'fear', 'neutral', 'greed', or 'extreme_greed'
        """
        # Use the regime directly if provided
        if 'regime' in regime_data:
            regime_text = regime_data['regime'].lower()
            
            # Map to our pattern categories
            if 'extreme fear' in regime_text:
                return 'extreme_fear'
            elif 'fear' in regime_text:
                return 'fear'
            elif 'greed' in regime_text and 'extreme' in regime_text:
                return 'extreme_greed'
            elif 'greed' in regime_text:
                return 'greed'
            else:
                return 'neutral'
        
        # Fallback to F&G value
        fg_value = regime_data.get('fear_greed_value', 50)
        
        if fg_value <= self.thresholds['fear_greed']['extreme_fear']:
            return 'extreme_fear'
        elif fg_value <= self.thresholds['fear_greed']['fear']:
            return 'fear'
        elif fg_value <= self.thresholds['fear_greed']['neutral']:
            return 'neutral'
        elif fg_value <= self.thresholds['fear_greed']['greed']:
            return 'greed'
        else:
            return 'extreme_greed'
    
    def _classify_volume(self, metrics: Dict) -> str:
        """
        Classify volume profile
        
        Returns: 'low', 'normal', 'high', or 'explosive'
        """
        volume_ratio = metrics.get('volume_ratio', 1.0)
        
        if volume_ratio < self.thresholds['volume']['low']:
            return 'low'
        elif volume_ratio < self.thresholds['volume']['high']:
            return 'normal'
        elif volume_ratio < self.thresholds['volume']['explosive']:
            return 'high'
        else:
            return 'explosive'
    
    def _classify_technical(self, metrics: Dict) -> str:
        """
        Classify technical setup based on RSI
        
        Returns: 'oversold', 'neutral', or 'overbought'
        """
        rsi = metrics.get('rsi_2', 50)
        
        if rsi < self.thresholds['rsi']['oversold']:
            return 'oversold'
        elif rsi > self.thresholds['rsi']['overbought']:
            return 'overbought'
        else:
            return 'neutral'
    
    def _calculate_confidence(self, metrics: Dict) -> float:
        """
        Calculate classification confidence based on how clearly metrics match patterns
        
        Returns:
            Confidence score 0-1
        """
        confidence = 1.0
        
        # Reduce confidence for edge cases
        rsi = metrics.get('rsi_2', 50)
        if 25 < rsi < 35 or 65 < rsi < 75:
            confidence *= 0.8  # Near threshold boundaries
        
        volume_ratio = metrics.get('volume_ratio', 1.0)
        if 0.65 < volume_ratio < 0.75 or 1.45 < volume_ratio < 1.55:
            confidence *= 0.8  # Near threshold boundaries
        
        # Boost confidence for extreme readings
        if rsi < 20 or rsi > 80:
            confidence *= 1.2
        if volume_ratio > 3.0:
            confidence *= 1.2
        
        return min(confidence, 1.0)
    
    def classify_batch(self, candidates: list, regime_data: Dict) -> Dict:
        """
        Classify multiple candidates at once
        
        Args:
            candidates: List of stock metrics dicts
            regime_data: Current regime information
            
        Returns:
            Dict mapping symbols to patterns
        """
        results = {}
        
        for candidate in candidates:
            symbol = candidate.get('symbol', 'UNKNOWN')
            pattern = self.classify_trade(candidate, regime_data)
            results[symbol] = pattern
            
            logger.debug(f"Classified {symbol} as {pattern['pattern_id']}")
        
        return results
    
    def get_pattern_distribution(self, regime: Optional[str] = None) -> Dict:
        """
        Get distribution of patterns for analysis
        
        Args:
            regime: Optional regime filter
            
        Returns:
            Dict with pattern counts and performance
        """
        if regime:
            patterns = self.db.get_regime_patterns(regime)
        else:
            patterns = self.db.get_top_patterns(limit=100, min_trades=1)
        
        distribution = {
            'total_patterns': len(patterns),
            'by_strategy': {},
            'by_performance': {
                'winners': 0,
                'losers': 0,
                'neutral': 0
            }
        }
        
        for pattern in patterns:
            strategy = pattern['strategy_type']
            if strategy not in distribution['by_strategy']:
                distribution['by_strategy'][strategy] = {
                    'count': 0,
                    'avg_win_rate': 0,
                    'avg_expectancy': 0
                }
            
            distribution['by_strategy'][strategy]['count'] += 1
            
            # Track performance categories
            if pattern['win_rate'] > 0.55:
                distribution['by_performance']['winners'] += 1
            elif pattern['win_rate'] < 0.45:
                distribution['by_performance']['losers'] += 1
            else:
                distribution['by_performance']['neutral'] += 1
        
        return distribution
    
    def validate_classification(self, pattern_id: str, actual_outcome: Dict) -> Dict:
        """
        Validate if classification was appropriate based on outcome
        
        Args:
            pattern_id: Pattern that was used
            actual_outcome: What actually happened
            
        Returns:
            Validation results
        """
        stats = self.db.get_pattern_stats(pattern_id)
        if not stats:
            return {'valid': False, 'error': 'Pattern not found'}
        
        # Check if outcome aligns with pattern expectations
        expected_win_rate = stats['win_rate']
        actual_win = actual_outcome['pnl_percent'] > 0
        
        # Over many trades, we expect alignment with win rate
        # For single trades, we track for aggregate analysis
        return {
            'valid': True,
            'pattern_id': pattern_id,
            'expected_win_rate': expected_win_rate,
            'actual_win': actual_win,
            'expectancy': stats['expectancy'],
            'actual_return': actual_outcome['pnl_percent'],
            'confidence_level': stats['confidence_level']
        }