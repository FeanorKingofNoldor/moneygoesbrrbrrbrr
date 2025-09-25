"""
Test script for Portfolio Constructor
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), './'))

import json
from datetime import datetime
from src.data.database import OdinDatabase
from src.portfolio.constructor import PortfolioConstructor

# Create test data
def create_test_data(db):
    """Insert test TradingAgents results"""
    
    batch_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    test_stocks = [
        {"symbol": "AAPL", "decision": "BUY", "conviction": 92, "sector": "Tech", "return": 0.04},
        {"symbol": "MSFT", "decision": "BUY", "conviction": 88, "sector": "Tech", "return": 0.035},
        {"symbol": "JPM", "decision": "BUY", "conviction": 85, "sector": "Finance", "return": 0.045},
        {"symbol": "AMZN", "decision": "BUY", "conviction": 83, "sector": "Tech", "return": 0.038},
        {"symbol": "BAC", "decision": "BUY", "conviction": 80, "sector": "Finance", "return": 0.042},
        {"symbol": "GOOGL", "decision": "BUY", "conviction": 79, "sector": "Tech", "return": 0.033},
        {"symbol": "V", "decision": "BUY", "conviction": 77, "sector": "Finance", "return": 0.028},
        {"symbol": "TSLA", "decision": "BUY", "conviction": 75, "sector": "Auto", "return": 0.055},
        {"symbol": "NVDA", "decision": "HOLD", "conviction": 60, "sector": "Tech", "return": 0.02},
        {"symbol": "META", "decision": "HOLD", "conviction": 55, "sector": "Tech", "return": 0.015},
    ]
    
    for stock in test_stocks:
        db.conn.execute("""
        INSERT INTO tradingagents_analysis_results
        (batch_id, symbol, decision, conviction_score, expected_return,
         entry_price, stop_loss, target_price, risk_reward_ratio,
         volume_ratio, rsi_2, atr, sector, regime)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            batch_id,
            stock['symbol'],
            stock['decision'],
            stock['conviction'],
            stock['return'],
            100,  # entry_price
            95,   # stop_loss
            105,  # target_price
            2.0,  # risk_reward_ratio
            1.5,  # volume_ratio
            30,   # rsi_2
            2.5,  # atr
            stock['sector'],
            'fear'  # regime
        ))
    
    db.conn.commit()
    return batch_id


def test_portfolio_constructor():
    """Test the Portfolio Constructor"""
    
    print("Testing Portfolio Constructor...")
    
    # Setup database
    db = OdinDatabase()
    
    # Run schema updates
    with open('src/data/schema_updates.sql', 'r') as f:
        schema_sql = f.read()
        db.conn.executescript(schema_sql)
    
    # Create test data
    batch_id = create_test_data(db)
    print(f"Created test batch: {batch_id}")
    
    # Initialize Portfolio Constructor
    constructor = PortfolioConstructor(db.conn)
    
    # Test portfolio construction
    result = constructor.construct_portfolio(
        batch_id=batch_id,
        max_positions=5,
        portfolio_context={
            'cash_available': 100000,
            'total_positions': 2,
            'unrealized_pnl_pct': 5.2
        },
        regime_data={
            'regime': 'fear',
            'fear_greed_value': 35,
            'vix': 22,
            'strategy': 'mean_reversion',
            'expected_win_rate': 0.70
        }
    )
    
    # Display results
    print(f"\n{'='*60}")
    print("PORTFOLIO CONSTRUCTION RESULTS")
    print(f"{'='*60}")
    
    print(f"\nSELECTED ({len(result['selections'])}):")
    for i, stock in enumerate(result['selections'], 1):
        print(f"  {i}. {stock['symbol']}: {stock['position_size_pct']}% (${stock['position_size_dollars']:,.0f})")
        print(f"     Conviction: {stock['conviction_score']}")
        print(f"     Reason: {stock.get('selection_reason', 'N/A')}")
    
    print(f"\nEXCLUDED ({len(result['excluded'])}):")
    for stock in result['excluded'][:5]:  # Show first 5
        print(f"  - {stock['symbol']}: {stock.get('exclusion_reason', 'Not selected')}")
    
    print("\n✓ Test completed successfully!")


if __name__ == "__main__":
    test_portfolio_constructor()