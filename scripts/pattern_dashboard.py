#!/usr/bin/env python3
"""
Display pattern performance dashboard
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.database import OdinDatabase
from src.patterns import PatternDatabase

def show_dashboard():
    db = OdinDatabase()
    pattern_db = PatternDatabase(db.conn)
    
    print("\n" + "="*60)
    print("PATTERN PERFORMANCE DASHBOARD")
    print("="*60)
    
    # Summary stats
    stats = pattern_db.get_pattern_summary_stats()
    print(f"\nTotal Patterns: {stats['total_patterns']}")
    print(f"Total Trades: {stats['total_trades']}")
    print(f"Avg Win Rate: {stats['avg_win_rate']:.1%}")
    print(f"Avg Expectancy: {stats['avg_expectancy']:.2%}")
    
    # Top patterns
    print("\n🏆 TOP PERFORMING PATTERNS:")
    top = pattern_db.get_top_patterns(limit=5)
    for i, p in enumerate(top, 1):
        print(f"{i}. {p['pattern_id']}")
        print(f"   Win Rate: {p['win_rate']:.1%} ({p['total_trades']} trades)")
        print(f"   Expectancy: {p['expectancy']:.2%}")
    
    # Breaking patterns
    print("\n⚠️ BREAKING PATTERNS:")
    breaking = pattern_db.get_breaking_patterns()
    for p in breaking[:3]:
        print(f"- {p['pattern_id']}")
        print(f"  Was: {p['win_rate']:.1%} → Now: {p['recent_win_rate']:.1%}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    show_dashboard()