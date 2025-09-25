#!/usr/bin/env python3
"""
Test broker functionality without IBKR
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from brokers.base.mock_broker import MockBroker

def test_mock_broker():
    """Test the mock broker implementation"""
    
    print("="*60)
    print("TESTING MOCK BROKER (No IBKR Required)")
    print("="*60)
    
    # Initialize mock broker
    broker = MockBroker(initial_cash=100000)
    
    # Test 1: Get portfolio data
    print("\n1. Portfolio Data:")
    data = broker.get_portfolio_data()
    print(f"   Cash: ${data['summary']['total_cash']:,.2f}")
    print(f"   Portfolio Value: ${data['summary']['portfolio_value']:,.2f}")
    print(f"   Total: ${data['summary']['net_liquidation']:,.2f}")
    print(f"   Positions: {data['summary']['total_positions']}")
    
    # Test 2: Show positions
    print("\n2. Current Positions:")
    for pos in data['positions']:
        print(f"   {pos['symbol']}: {pos['position']} shares @ ${pos['market_price']:.2f}")
        print(f"      P&L: ${pos['unrealized_pnl']:+,.2f} ({pos['unrealized_pnl_pct']:+.1f}%)")
    
    # Test 3: Place an order
    print("\n3. Placing Test Order:")
    order = broker.place_order('GOOGL', 'BUY', 10, 'MKT')
    print(f"   Order {order['order_id']}: BUY 10 GOOGL @ ${order['fill_price']:.2f}")
    print(f"   Status: {order['status']}")
    
    # Test 4: Updated portfolio
    print("\n4. Updated Portfolio:")
    data = broker.get_portfolio_data()
    print(f"   Cash: ${data['summary']['total_cash']:,.2f}")
    print(f"   Positions: {data['summary']['total_positions']}")
    
    print("\n✅ Mock broker test complete!")
    return broker

if __name__ == "__main__":
    test_mock_broker()