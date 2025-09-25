#!/usr/bin/env python3
"""
Test complete pattern system integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.database import OdinDatabase
from src.patterns import PatternDatabase, PatternClassifier, PatternTracker
from src.patterns.memory_injector import PatternMemoryInjector
from src.patterns.memory_bridge import TradingAgentsMemoryBridge

def test_full_pattern_flow():
    """Test the complete pattern flow from classification to memory injection"""
    
    print("="*60)
    print("TESTING COMPLETE PATTERN SYSTEM")
    print("="*60)
    
    # FIX: Use test database or ensure we're in the right directory
    # Option 1: Use a test database
    test_db_path = "test_patterns.db"
    
    # Option 2: Use the actual database if it exists
    if os.path.exists("odin.db"):
        db = OdinDatabase()  # Uses default
    else:
        # Create OdinDatabase with specific path
        db = OdinDatabase()
        # Or manually set the path
        db.db_path = test_db_path
        db.setup_database()
    
    pattern_db = PatternDatabase(db.conn)
    classifier = PatternClassifier(pattern_db)
    tracker = PatternTracker(pattern_db)
    
    # Test 1: Classification
    print("\n1. Testing Pattern Classification...")
    test_trade = {
        'symbol': 'AAPL',
        'rsi_2': 25,
        'volume_ratio': 1.8,
        'price_vs_sma20': 0.97
    }
    test_regime = {'regime': 'fear', 'fear_greed_value': 35}
    
    pattern = classifier.classify_trade(test_trade, test_regime)
    print(f"   ✓ Pattern classified: {pattern['pattern_id']}")
    
    # Test 2: Track Entry
    print("\n2. Testing Pattern Entry Tracking...")
    entry_data = {
        'batch_id': 'test_batch',
        'symbol': 'AAPL',
        'entry_price': 150.00,
        'rsi_2': 25,
        'volume_ratio': 1.8,
        'fear_greed_value': 35
    }
    tracker.track_entry(pattern['pattern_id'], entry_data)
    print(f"   ✓ Entry tracked for pattern")
    
    # Test 3: Track Exit and Update
    print("\n3. Testing Pattern Exit Tracking...")
    exit_data = {
        'batch_id': 'test_batch',
        'symbol': 'AAPL',
        'exit_date': '2024-01-15',
        'exit_price': 155.00,
        'pnl_percent': 3.33,
        'holding_days': 5
    }
    tracker.track_exit(pattern['pattern_id'], exit_data)
    print(f"   ✓ Exit tracked and pattern updated")
    
    # Test 4: Get Pattern Context
    print("\n4. Testing Pattern Context Retrieval...")
    context = tracker.get_pattern_context(pattern['pattern_id'])
    print(f"   ✓ Pattern context: {context['recommendation'][:50]}...")
    
    # Test 5: Memory Creation
    print("\n5. Testing Memory Creation...")
    position_data = {
        'symbol': 'AAPL',
        'entry_price': 150.00,
        'exit_price': 155.00,
        'pnl_percent': 3.33,
        'pattern_id': pattern['pattern_id'],
        'regime_at_entry': 'fear',
        'rsi_at_entry': 25,
        'volume_ratio_at_entry': 1.8
    }
    
    pattern_stats = pattern_db.get_pattern_stats(pattern['pattern_id'])
    if pattern_stats:
        memories = TradingAgentsMemoryBridge.create_hybrid_memories(
            position_data, pattern_stats
        )
        print(f"   ✓ Created {len(memories)} hybrid memories")
    
    print("\n" + "="*60)
    print("✅ ALL PATTERN SYSTEM TESTS PASSED!")
    print("="*60)

if __name__ == "__main__":
    test_full_pattern_flow()