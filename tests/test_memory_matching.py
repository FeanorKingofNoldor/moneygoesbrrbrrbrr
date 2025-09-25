#!/usr/bin/env python3
"""
Test memory matching between patterns and TradingAgents
"""

import sys
import os

# Add the parent directory (project root) to Python's path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import src modules
from src.patterns.memory_bridge import TradingAgentsMemoryBridge

def test_memory_matching():
    """Test that pattern memories match TradingAgents format"""
    
    # Test pattern
    test_pattern = {
        'pattern_id': 'mean_reversion_fear_high_oversold',
        'strategy_type': 'mean_reversion',
        'market_regime': 'fear',
        'volume_profile': 'high',
        'technical_setup': 'oversold',
        'win_rate': 0.73,
        'recent_win_rate': 0.80,
        'expectancy': 0.025,
        'confidence_level': 'high',
        'total_trades': 45,
        'fear_greed': 35,
        'vix': 22
    }
    
    test_metrics = {
        'rsi_2': 25,
        'volume_ratio': 1.8,
        'atr': 2.5,
        'price_vs_sma20': 0.97
    }
    
    # Format for TradingAgents
    situation, recommendation = TradingAgentsMemoryBridge.format_pattern_for_tradingagents(
        test_pattern, test_metrics
    )
    
    print("="*60)
    print("PATTERN MEMORY MATCHING TEST")
    print("="*60)
    
    print("\nSITUATION (what TradingAgents will match on):")
    print("-"*40)
    print(situation)
    
    print("\n" + "="*60)
    print("RECOMMENDATION (what agents will recall):")
    print("-"*40)
    print(recommendation)
    
    print("\n" + "="*60)
    print("✅ Test complete - check if format matches TradingAgents expectations")

if __name__ == "__main__":
    test_memory_matching()