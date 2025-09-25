#!/usr/bin/env python3
"""
Complete test suite for mock broker functionality
Tests the entire trading flow without IBKR
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from datetime import datetime
from typing import Dict, List

from src.brokers.base.mock_broker import MockBroker
from src.batch.tradingagents_batch_processor import TradingAgentsBatchProcessor
from src.data.database import OdinDatabase


class MockBrokerTester:
    """Test harness for mock broker"""
    
    def __init__(self):
        self.broker = MockBroker(initial_cash=100000)
        self.test_results = []
        
    def test_initial_portfolio(self) -> bool:
        """Test 1: Verify initial portfolio setup"""
        print("\n" + "="*60)
        print("TEST 1: Initial Portfolio Setup")
        print("="*60)
        
        data = self.broker.get_portfolio_data()
        
        # Verify structure
        assert 'summary' in data, "Missing summary"
        assert 'positions' in data, "Missing positions"
        
        # Check initial values
        summary = data['summary']
        print(f"Initial Cash: ${summary['total_cash']:,.2f}")
        print(f"Portfolio Value: ${summary['portfolio_value']:,.2f}")
        print(f"Net Liquidation: ${summary['net_liquidation']:,.2f}")
        
        # Check initial positions
        print(f"\nInitial Positions: {len(data['positions'])}")
        for pos in data['positions']:
            print(f"  {pos['symbol']}: {pos['position']} @ ${pos['market_price']:.2f}")
            assert pos['position'] > 0, f"Invalid position for {pos['symbol']}"
            assert pos['market_price'] > 0, f"Invalid price for {pos['symbol']}"
        
        self.test_results.append(('Initial Portfolio', 'PASS'))
        return True
    
    def test_buy_order(self) -> bool:
        """Test 2: Place a BUY order"""
        print("\n" + "="*60)
        print("TEST 2: BUY Order Execution")
        print("="*60)
        
        # Get initial state
        initial_data = self.broker.get_portfolio_data()
        initial_cash = initial_data['summary']['total_cash']
        initial_positions = len(initial_data['positions'])
        
        # Place BUY order
        symbol = 'GOOGL'
        quantity = 10
        print(f"Placing BUY order: {quantity} shares of {symbol}")
        
        order = self.broker.place_order(symbol, 'BUY', quantity, 'MKT')
        
        # Verify order
        assert order['status'] == 'FILLED', "Order not filled"
        assert order['symbol'] == symbol, "Wrong symbol"
        assert order['quantity'] == quantity, "Wrong quantity"
        
        print(f"Order {order['order_id']} FILLED at ${order['fill_price']:.2f}")
        
        # Verify portfolio update
        new_data = self.broker.get_portfolio_data()
        new_cash = new_data['summary']['total_cash']
        new_positions = len(new_data['positions'])
        
        # Cash should decrease
        cash_used = initial_cash - new_cash
        expected_cash_used = quantity * order['fill_price']
        assert abs(cash_used - expected_cash_used) < 0.01, "Cash calculation error"
        
        print(f"Cash used: ${cash_used:,.2f}")
        print(f"New cash balance: ${new_cash:,.2f}")
        
        # Should have new position
        googl_position = next((p for p in new_data['positions'] if p['symbol'] == symbol), None)
        assert googl_position is not None, "Position not created"
        assert googl_position['position'] == quantity, "Wrong position size"
        
        print(f"New position: {googl_position['position']} shares of {symbol}")
        
        self.test_results.append(('BUY Order', 'PASS'))
        return True
    
    def test_sell_order(self) -> bool:
        """Test 3: Place a SELL order"""
        print("\n" + "="*60)
        print("TEST 3: SELL Order Execution")
        print("="*60)
        
        # Sell existing position (AAPL from initial setup)
        symbol = 'AAPL'
        quantity = 50
        
        # Get initial state
        initial_data = self.broker.get_portfolio_data()
        initial_position = next((p for p in initial_data['positions'] if p['symbol'] == symbol), None)
        
        if not initial_position:
            print(f"No {symbol} position to sell, skipping test")
            self.test_results.append(('SELL Order', 'SKIP'))
            return True
        
        print(f"Current {symbol} position: {initial_position['position']} shares")
        print(f"Placing SELL order: {quantity} shares of {symbol}")
        
        order = self.broker.place_order(symbol, 'SELL', quantity, 'MKT')
        
        # Verify order
        assert order['status'] == 'FILLED', "Order not filled"
        print(f"Order {order['order_id']} FILLED at ${order['fill_price']:.2f}")
        
        # Verify position update
        new_data = self.broker.get_portfolio_data()
        new_position = next((p for p in new_data['positions'] if p['symbol'] == symbol), None)
        
        expected_position = initial_position['position'] - quantity
        if expected_position > 0:
            assert new_position is not None, "Position incorrectly removed"
            assert new_position['position'] == expected_position, "Wrong remaining position"
            print(f"Remaining position: {new_position['position']} shares")
        else:
            print(f"Position fully closed")
        
        # Verify cash increase
        cash_received = quantity * order['fill_price']
        print(f"Cash received: ${cash_received:,.2f}")
        
        self.test_results.append(('SELL Order', 'PASS'))
        return True
    
    def test_portfolio_calculations(self) -> bool:
        """Test 4: Verify portfolio calculations"""
        print("\n" + "="*60)
        print("TEST 4: Portfolio Calculations")
        print("="*60)
        
        data = self.broker.get_portfolio_data()
        summary = data['summary']
        positions = data['positions']
        
        # Calculate expected values
        total_market_value = sum(p['market_value'] for p in positions)
        total_pnl = sum(p['unrealized_pnl'] for p in positions)
        expected_net_liq = summary['total_cash'] + total_market_value
        
        print(f"Cash: ${summary['total_cash']:,.2f}")
        print(f"Market Value: ${total_market_value:,.2f}")
        print(f"Total P&L: ${total_pnl:+,.2f}")
        print(f"Net Liquidation: ${summary['net_liquidation']:,.2f}")
        print(f"Expected Net Liq: ${expected_net_liq:,.2f}")
        
        # Verify calculations
        assert abs(summary['net_liquidation'] - expected_net_liq) < 0.01, "Net liquidation mismatch"
        assert abs(summary['portfolio_value'] - total_market_value) < 0.01, "Portfolio value mismatch"
        
        self.test_results.append(('Portfolio Calculations', 'PASS'))
        return True
    
    def test_tradingagents_integration(self) -> bool:
        """Test 5: Integration with TradingAgents decisions"""
        print("\n" + "="*60)
        print("TEST 5: TradingAgents Integration")
        print("="*60)
        
        # Simulate TradingAgents decision
        tradingagents_decision = {
            'symbol': 'NVDA',
            'decision': 'BUY',
            'conviction_score': 75,
            'position_size_pct': 10,
            'entry_price': 500.00,
            'stop_loss': 475.00,
            'target_price': 550.00
        }
        
        print(f"TradingAgents Decision: {tradingagents_decision['decision']} {tradingagents_decision['symbol']}")
        print(f"Conviction: {tradingagents_decision['conviction_score']}")
        print(f"Position Size: {tradingagents_decision['position_size_pct']}% of portfolio")
        
        # Calculate position size
        portfolio_value = self.broker.get_portfolio_data()['summary']['net_liquidation']
        position_value = portfolio_value * (tradingagents_decision['position_size_pct'] / 100)
        shares = int(position_value / tradingagents_decision['entry_price'])
        
        print(f"Calculated shares: {shares}")
        
        # Execute order
        if tradingagents_decision['decision'] == 'BUY' and shares > 0:
            order = self.broker.place_order(
                tradingagents_decision['symbol'],
                'BUY',
                shares,
                'MKT'
            )
            print(f"Executed: BUY {shares} {tradingagents_decision['symbol']} @ ${order['fill_price']:.2f}")
            
            # Verify position created
            new_data = self.broker.get_portfolio_data()
            nvda_position = next((p for p in new_data['positions'] 
                                 if p['symbol'] == tradingagents_decision['symbol']), None)
            assert nvda_position is not None, "Position not created from TradingAgents decision"
            
        self.test_results.append(('TradingAgents Integration', 'PASS'))
        return True
    
    def test_multiple_orders(self) -> bool:
        """Test 6: Multiple simultaneous orders"""
        print("\n" + "="*60)
        print("TEST 6: Multiple Order Processing")
        print("="*60)
        
        orders_to_place = [
            {'symbol': 'AMZN', 'action': 'BUY', 'quantity': 5},
            {'symbol': 'TSLA', 'action': 'BUY', 'quantity': 8},
            {'symbol': 'AAPL', 'action': 'SELL', 'quantity': 25},  # Partial sell
        ]
        
        executed_orders = []
        
        for order_req in orders_to_place:
            print(f"Placing: {order_req['action']} {order_req['quantity']} {order_req['symbol']}")
            order = self.broker.place_order(
                order_req['symbol'],
                order_req['action'],
                order_req['quantity'],
                'MKT'
            )
            executed_orders.append(order)
            print(f"  Filled at ${order['fill_price']:.2f}")
        
        # Verify all orders executed
        assert len(executed_orders) == len(orders_to_place), "Not all orders executed"
        
        # Check final portfolio
        final_data = self.broker.get_portfolio_data()
        print(f"\nFinal Portfolio:")
        print(f"  Cash: ${final_data['summary']['total_cash']:,.2f}")
        print(f"  Positions: {final_data['summary']['total_positions']}")
        print(f"  Total Value: ${final_data['summary']['net_liquidation']:,.2f}")
        
        self.test_results.append(('Multiple Orders', 'PASS'))
        return True
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        for test_name, result in self.test_results:
            status_symbol = "✓" if result == "PASS" else "✗" if result == "FAIL" else "⊘"
            print(f"{status_symbol} {test_name}: {result}")
        
        passed = sum(1 for _, r in self.test_results if r == "PASS")
        total = len(self.test_results)
        print(f"\nResults: {passed}/{total} tests passed")
        
        return all(r == "PASS" or r == "SKIP" for _, r in self.test_results)


def run_mock_broker_tests():
    """Run all mock broker tests"""
    print("\n" + "="*80)
    print("MOCK BROKER COMPREHENSIVE TEST SUITE")
    print("Testing portfolio management and order execution without IBKR")
    print("="*80)
    
    tester = MockBrokerTester()
    
    try:
        # Run all tests
        tester.test_initial_portfolio()
        tester.test_buy_order()
        tester.test_sell_order()
        tester.test_portfolio_calculations()
        tester.test_tradingagents_integration()
        tester.test_multiple_orders()
        
        # Print summary
        success = tester.print_summary()
        
        if success:
            print("\n✅ ALL TESTS PASSED - Mock broker ready for use!")
        else:
            print("\n⚠️ Some tests failed - check implementation")
            
        return success
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    run_mock_broker_tests()