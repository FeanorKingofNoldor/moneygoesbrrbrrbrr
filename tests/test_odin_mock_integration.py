#!/usr/bin/env python3
"""
Test ODIN pipeline with mock broker
Simulates complete trading flow
"""

import sys
import os
# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from datetime import datetime

from src.brokers.base.mock_broker import MockBroker
from src.data.database import OdinDatabase
from src.tradingagents.portfolio_context import PortfolioContextProvider


def test_odin_pipeline_with_mock():
    """Test complete ODIN pipeline with mock broker"""
    
    print("\n" + "="*60)
    print("ODIN PIPELINE WITH MOCK BROKER TEST")
    print("="*60)
    
    # Initialize components
    db = OdinDatabase()
    mock_broker = MockBroker(initial_cash=100000)
    
    # Create mock portfolio context provider
    class MockPortfolioProvider:
        def __init__(self, broker):
            self.broker = broker
        
        def get_portfolio_context(self):
            data = self.broker.get_portfolio_data()
            return {
                'cash_available': data['summary']['total_cash'],
                'portfolio_value': data['summary']['net_liquidation'],
                'total_positions': data['summary']['total_positions'],
                'current_positions': data['positions'],
                'data_source': 'MOCK_BROKER'
            }
    
    portfolio_provider = MockPortfolioProvider(mock_broker)
    
    # Test 1: Get initial context
    print("\n1. Initial Portfolio Context:")
    context = portfolio_provider.get_portfolio_context()
    print(f"   Cash: ${context['cash_available']:,.2f}")
    print(f"   Value: ${context['portfolio_value']:,.2f}")
    print(f"   Positions: {context['total_positions']}")
    
    # Test 2: Simulate TradingAgents decisions
    print("\n2. Simulating TradingAgents Decisions:")
    
    decisions = [
        {'symbol': 'GOOGL', 'decision': 'BUY', 'conviction': 80, 'size_pct': 15},
        {'symbol': 'AMZN', 'decision': 'BUY', 'conviction': 65, 'size_pct': 10},
        {'symbol': 'AAPL', 'decision': 'SELL', 'conviction': 70, 'size_pct': 50},  # Sell half
    ]
    
    for dec in decisions:
        print(f"   {dec['decision']} {dec['symbol']} - Conviction: {dec['conviction']}")
    
    # Test 3: Execute decisions
    print("\n3. Executing Trades:")
    
    for dec in decisions:
        if dec['decision'] == 'BUY':
            # Calculate shares
            position_value = context['portfolio_value'] * (dec['size_pct'] / 100)
            price = mock_broker._get_mock_price(dec['symbol'])
            shares = int(position_value / price)
            
            if shares > 0:
                order = mock_broker.place_order(dec['symbol'], 'BUY', shares, 'MKT')
                print(f"   ✓ Bought {shares} {dec['symbol']} @ ${order['fill_price']:.2f}")
        
        elif dec['decision'] == 'SELL':
            # Find position
            position = next((p for p in context['current_positions'] 
                           if p['symbol'] == dec['symbol']), None)
            if position:
                shares = int(position['position'] * (dec['size_pct'] / 100))
                if shares > 0:
                    order = mock_broker.place_order(dec['symbol'], 'SELL', shares, 'MKT')
                    print(f"   ✓ Sold {shares} {dec['symbol']} @ ${order['fill_price']:.2f}")
    
    # Test 4: Verify final state
    print("\n4. Final Portfolio State:")
    final_context = portfolio_provider.get_portfolio_context()
    print(f"   Cash: ${final_context['cash_available']:,.2f}")
    print(f"   Value: ${final_context['portfolio_value']:,.2f}")
    print(f"   Positions: {final_context['total_positions']}")
    
    print("\n5. Position Details:")
    for pos in final_context['current_positions']:
        print(f"   {pos['symbol']}: {pos['position']} shares, "
              f"P&L: ${pos['unrealized_pnl']:+,.2f} ({pos['unrealized_pnl_pct']:+.1f}%)")
    
    print("\n✅ ODIN Pipeline Mock Test Complete!")


if __name__ == "__main__":
    test_odin_pipeline_with_mock()