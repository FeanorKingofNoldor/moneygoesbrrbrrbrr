"""
Memory Bridge for TradingAgents
Enhanced to create both pattern and trade-specific memories
"""

import logging
from typing import Dict, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)


class TradingAgentsMemoryBridge:
    """
    Bridges pattern statistics and specific trades into TradingAgents memory format
    """
    
    @staticmethod
    def create_pattern_memory(pattern_data: Dict, 
                             current_metrics: Dict,
                             symbol: str = "[ANALYZING STOCK]") -> Tuple[str, str]:
        """
        Create pattern-based memory entry with company placeholder
        
        Args:
            pattern_data: Pattern statistics
            current_metrics: Current market metrics
            symbol: Stock symbol (or placeholder for general patterns)
        """
        
        # Build situation with company context
        market_report = f"""Analyzing {symbol}
Technical Analysis Report:
RSI(2): {current_metrics.get('rsi_2', 'N/A')}
Volume Ratio: {current_metrics.get('volume_ratio', 1.0):.2f}x average
ATR: {current_metrics.get('atr', 'N/A')}
Price vs SMA20: {current_metrics.get('price_vs_sma20', 1.0):.2%}
Market Regime: {pattern_data.get('market_regime', 'neutral').replace('_', ' ').title()}"""

        sentiment_report = f"""Market Sentiment:
Fear & Greed Index: {pattern_data.get('fear_greed', 50)}
VIX Level: {pattern_data.get('vix', 20):.1f}
Overall Sentiment: {pattern_data.get('market_regime', 'neutral').replace('_', ' ').title()}"""

        news_report = f"""Market Context:
Pattern Classification: {pattern_data['pattern_id']}
Strategy Type: {pattern_data['strategy_type'].replace('_', ' ')}
Volume Profile: {pattern_data['volume_profile']}
Technical Setup: {pattern_data['technical_setup']}
Pattern Confidence: {pattern_data.get('confidence_level', 'medium')}"""

        fundamentals_report = f"""Pattern Statistics:
Historical Win Rate: {pattern_data.get('win_rate', 0):.1%}
Recent Performance: {pattern_data.get('recent_win_rate', 0):.1%}
Expected Value: {pattern_data.get('expectancy', 0):.2%}
Sample Size: {pattern_data.get('total_trades', 0)} trades"""

        situation = f"{market_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        
        # Build recommendation based on pattern statistics
        recommendation = TradingAgentsMemoryBridge._build_pattern_recommendation(pattern_data)
        
        return (situation, recommendation)
    
    @staticmethod
    def create_trade_memory(position_data: Dict, pattern_data: Dict) -> Tuple[str, str]:
        """
        Create specific trade memory when position closes
        
        Args:
            position_data: Actual trade details with P&L
            pattern_data: Pattern that was traded
        """
        
        # Build situation for specific trade
        market_report = f"""Completed trade in {position_data['symbol']}
Technical Analysis at Entry:
RSI(2): {position_data.get('rsi_at_entry', 'N/A')}
Volume Ratio: {position_data.get('volume_ratio_at_entry', 1.0):.2f}x average
ATR: {position_data.get('atr', 'N/A')}
Entry Price: ${position_data.get('entry_price', 0):.2f}
Market Regime: {position_data.get('regime_at_entry', 'unknown')}"""

        sentiment_report = f"""Market Sentiment at Entry:
Fear & Greed Index: {position_data.get('fear_greed_at_entry', 'N/A')}
VIX Level: {position_data.get('vix_at_entry', 'N/A')}
Pattern Matched: {position_data.get('pattern_id', 'unknown')}"""

        news_report = f"""Trade Execution Details:
Entry Date: {position_data.get('entry_date')}
Exit Date: {position_data.get('exit_date')}
Holding Period: {position_data.get('holding_days')} days
Exit Reason: {position_data.get('exit_reason', 'unknown')}"""

        fundamentals_report = f"""Trade Outcome:
P&L: {position_data.get('pnl_percent', 0):.2%}
Max Gain: {position_data.get('max_gain_percent', 0):.2%}
Max Drawdown: {position_data.get('max_drawdown_percent', 0):.2%}
Pattern Win Rate: {pattern_data.get('win_rate', 0):.1%} (historical)"""

        situation = f"{market_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        
        # Build recommendation based on actual outcome
        recommendation = TradingAgentsMemoryBridge._build_trade_recommendation(
            position_data, pattern_data
        )
        
        return (situation, recommendation)
    
    @staticmethod
    def create_hybrid_memories(position_data: Dict, pattern_data: Dict) -> List[Tuple[str, str]]:
        """
        Create both pattern update and specific trade memories
        
        Returns:
            List of (situation, recommendation) tuples
        """
        memories = []
        
        # 1. Create specific trade memory
        trade_memory = TradingAgentsMemoryBridge.create_trade_memory(
            position_data, pattern_data
        )
        memories.append(trade_memory)
        
        # 2. Create updated pattern memory (with new statistics)
        current_metrics = {
            'rsi_2': position_data.get('rsi_at_entry'),
            'volume_ratio': position_data.get('volume_ratio_at_entry', 1.0),
            'atr': position_data.get('atr'),
            'vix': position_data.get('vix_at_entry'),
            'fear_greed': position_data.get('fear_greed_at_entry')
        }
        
        pattern_memory = TradingAgentsMemoryBridge.create_pattern_memory(
            pattern_data, 
            current_metrics,
            position_data['symbol']
        )
        memories.append(pattern_memory)
        
        return memories
    
    @staticmethod
    def _build_pattern_recommendation(pattern: Dict) -> str:
        """Build recommendation from pattern statistics"""
        win_rate = pattern.get('win_rate', 0)
        recent_win_rate = pattern.get('recent_win_rate', win_rate)
        expectancy = pattern.get('expectancy', 0)
        confidence = pattern.get('confidence_level', 'low')
        total_trades = pattern.get('total_trades', 0)
        
        if win_rate > 0.65 and confidence == 'high':
            return f"""STRONG BUY PATTERN: Statistical analysis of {total_trades} similar trades shows {win_rate:.1%} win rate.
Recent performance even stronger at {recent_win_rate:.1%}. Expected return: {expectancy:.2%}.
RECOMMENDATION: Increase position size to 1.5x normal. Set stop at 2.5x ATR.
This pattern has proven highly reliable. Take position with high conviction."""
            
        elif win_rate > 0.55:
            return f"""MODERATE BUY PATTERN: {total_trades} historical trades show {win_rate:.1%} success rate.
Recent trend: {recent_win_rate:.1%}. Expected value: {expectancy:.2%}.
RECOMMENDATION: Use standard position sizing with normal conviction.
Pattern shows positive edge but not exceptional. Proceed with standard risk management."""
            
        elif win_rate < 0.45:
            return f"""WEAK/AVOID PATTERN: Only {win_rate:.1%} historical win rate across {total_trades} trades.
Recent performance worse at {recent_win_rate:.1%}. Negative expectancy: {expectancy:.2%}.
RECOMMENDATION: Consider HOLDING or reduce position to 50% if entering.
Pattern has been consistently underperforming. Extra caution warranted."""
            
        else:
            return f"""NEUTRAL PATTERN: {win_rate:.1%} win rate with {expectancy:.2%} expectancy over {total_trades} trades.
No significant statistical edge detected. Recent performance: {recent_win_rate:.1%}.
RECOMMENDATION: Use standard approach. No pattern-based adjustment needed."""
    
    @staticmethod
    def _build_trade_recommendation(position: Dict, pattern: Dict) -> str:
        """Build recommendation from specific trade outcome"""
        pnl = position.get('pnl_percent', 0)
        symbol = position.get('symbol', 'UNKNOWN')
        pattern_id = position.get('pattern_id', 'unknown')
        exit_reason = position.get('exit_reason', 'unknown')
        
        if pnl > 3.0:
            return f"""SUCCESSFUL TRADE: {symbol} gained {pnl:.2%} following pattern {pattern_id}.
Pattern continues to perform as expected with {pattern.get('win_rate', 0):.1%} historical win rate.
Exit trigger: {exit_reason}. Maximum gain reached {position.get('max_gain_percent', pnl):.2%}.
LESSON: This pattern remains reliable. Continue using with confidence.
Similar setups should be taken with full or increased position size."""
            
        elif pnl > 0:
            return f"""WINNING TRADE: {symbol} gained {pnl:.2%} as pattern predicted.
Pattern {pattern_id} performed within expectations. Exit: {exit_reason}.
LESSON: Pattern working normally. Maintain current approach.
No adjustments needed to pattern confidence or position sizing."""
            
        elif pnl < -2.0:
            return f"""LOSING TRADE: {symbol} lost {abs(pnl):.2%} despite pattern {pattern_id}.
Pattern historical win rate: {pattern.get('win_rate', 0):.1%}. Exit: {exit_reason}.
Maximum drawdown: {position.get('max_drawdown_percent', pnl):.2%}.
LESSON: Monitor this pattern for potential breakdown. If pattern continues failing,
reduce position size or avoid until it stabilizes."""
            
        else:
            return f"""SMALL LOSS: {symbol} lost {abs(pnl):.2%}. Pattern {pattern_id} didn't work this time.
Within normal variance for {pattern.get('win_rate', 0):.1%} win rate pattern.
LESSON: Small losses are expected. No pattern adjustment needed yet.
Continue monitoring performance over larger sample."""