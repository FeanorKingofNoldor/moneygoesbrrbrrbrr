"""
Mock Broker for Testing Without IBKR
"""

import random
from datetime import datetime
from typing import Dict, List, Optional

class MockBroker:
    """Mock broker that simulates IBKR responses"""
    
    def __init__(self, initial_cash: float = 100000):
        self.cash = initial_cash
        self.positions = {}
        self.orders = []
        self.connected = True
        
        # Add some fake positions for testing
        self._init_test_positions()
    
    def _init_test_positions(self):
        """Initialize with some test positions"""
        test_positions = [
            {'symbol': 'AAPL', 'shares': 100, 'avg_cost': 145.00},
            {'symbol': 'MSFT', 'shares': 50, 'avg_cost': 380.00},
            {'symbol': 'NVDA', 'shares': 25, 'avg_cost': 450.00}
        ]
        
        for pos in test_positions:
            self.positions[pos['symbol']] = {
                'position': pos['shares'],
                'avg_cost': pos['avg_cost'],
                'market_price': pos['avg_cost'] * (1 + random.uniform(-0.1, 0.1)),
                'market_value': 0,
                'unrealized_pnl': 0
            }
            
            # Calculate values
            self.positions[pos['symbol']]['market_value'] = (
                pos['shares'] * self.positions[pos['symbol']]['market_price']
            )
            self.positions[pos['symbol']]['unrealized_pnl'] = (
                self.positions[pos['symbol']]['market_value'] - 
                (pos['shares'] * pos['avg_cost'])
            )
    
    def get_portfolio_data(self) -> Dict:
        """Mock portfolio data matching IBKR format"""
        total_value = sum(p['market_value'] for p in self.positions.values())
        total_pnl = sum(p['unrealized_pnl'] for p in self.positions.values())
        
        return {
            'summary': {
                'total_cash': self.cash,
                'portfolio_value': total_value,
                'net_liquidation': self.cash + total_value,
                'total_positions': len(self.positions),
                'total_unrealized_pnl': total_pnl,
                'buying_power': self.cash * 4  # Simulate margin
            },
            'positions': [
                {
                    'symbol': symbol,
                    'position': data['position'],
                    'market_price': data['market_price'],
                    'market_value': data['market_value'],
                    'avg_cost': data['avg_cost'],
                    'unrealized_pnl': data['unrealized_pnl'],
                    'unrealized_pnl_pct': (data['unrealized_pnl'] / 
                                          (data['position'] * data['avg_cost']) * 100)
                }
                for symbol, data in self.positions.items()
            ],
            'orders': self.orders,
            'timestamp': datetime.now().isoformat()
        }
    
    def place_order(self, symbol: str, action: str, quantity: int, 
                   order_type: str = 'MKT') -> Dict:
        """Simulate order placement"""
        order = {
            'order_id': f"MOCK_{len(self.orders) + 1}",
            'symbol': symbol,
            'action': action,
            'quantity': quantity,
            'order_type': order_type,
            'status': 'FILLED',  # Mock fills immediately
            'fill_price': self._get_mock_price(symbol),
            'timestamp': datetime.now().isoformat()
        }
        
        self.orders.append(order)
        
        # Update positions
        if action == 'BUY':
            if symbol in self.positions:
                self.positions[symbol]['position'] += quantity
            else:
                self.positions[symbol] = {
                    'position': quantity,
                    'avg_cost': order['fill_price'],
                    'market_price': order['fill_price'],
                    'market_value': quantity * order['fill_price'],
                    'unrealized_pnl': 0
                }
            self.cash -= quantity * order['fill_price']
            
        elif action == 'SELL':
            if symbol in self.positions:
                self.positions[symbol]['position'] -= quantity
                if self.positions[symbol]['position'] == 0:
                    del self.positions[symbol]
            self.cash += quantity * order['fill_price']
        
        return order
    
    def _get_mock_price(self, symbol: str) -> float:
        """Generate mock price for symbol"""
        base_prices = {
            'AAPL': 150.00, 'MSFT': 400.00, 'NVDA': 500.00,
            'GOOGL': 140.00, 'AMZN': 180.00, 'TSLA': 250.00
        }
        base = base_prices.get(symbol, 100.00)
        return base * (1 + random.uniform(-0.02, 0.02))