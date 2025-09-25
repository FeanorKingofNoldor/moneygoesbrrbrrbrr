#!/usr/bin/env python3
"""
Run weekly pattern learning
Schedule this with cron for Sunday nights
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.database import OdinDatabase
from src.batch.tradingagents_batch_processor import TradingAgentsBatchProcessor

def run_weekly_learning():
    print("\n" + "="*60)
    print("WEEKLY PATTERN LEARNING")
    print("="*60)
    
    db = OdinDatabase()
    processor = TradingAgentsBatchProcessor(db)
    
    results = processor.run_weekly_pattern_analysis()
    
    if 'error' not in results:
        print(f"✓ Analyzed {results.get('patterns_analyzed', 0)} patterns")
        print(f"✓ Injected {results.get('memories_injected', 0)} memories")
    else:
        print(f"✗ Error: {results['error']}")

if __name__ == "__main__":
    run_weekly_learning()