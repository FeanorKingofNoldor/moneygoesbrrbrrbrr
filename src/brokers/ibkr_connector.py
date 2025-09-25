"""
IBKR Portfolio Connector for ODIN
Fetches real portfolio data from Interactive Brokers account
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import pandas as pd

try:
    from ib_async import IB, Stock, util
    IB_AVAILABLE = True
except ImportError:
    print("Warning: ib_async not installed. Install with: pip install ib_async")
    IB_AVAILABLE = False


class IBKRPortfolioConnector:
    """
    Connects to IBKR and fetches real portfolio data
    """
    
    def __init__(self, host=None, port=None, client_id=None):
        """
        Initialize IBKR connection
        
        Args:
            host: IB Gateway host (None = use config default)
            port: 4001 for live, 4002 for paper trading (None = use config default)
            client_id: Unique client ID 1-32 (None = use config default)
        """
        # Import config settings
        from config.settings import (
            IBKR_HOST,
            IBKR_DEFAULT_PORT,
            IBKR_CLIENT_ID,
            IBKR_CACHE_TIMEOUT
        )
        
        if not IB_AVAILABLE:
            raise ImportError("ib_async library not available. Install with: pip install ib_async")
        
        # Use config defaults if not specified
        self.host = host if host is not None else IBKR_HOST
        self.port = port if port is not None else IBKR_DEFAULT_PORT
        self.client_id = client_id if client_id is not None else IBKR_CLIENT_ID
        
        self.ib = IB()
        self.connected = False
        
        # Cache settings from config
        self._cache = {}
        self._cache_timeout = IBKR_CACHE_TIMEOUT
        self._last_update = None
        
    async def connect(self):
        """Connect to IB Gateway/TWS"""
        try:
            await self.ib.connectAsync(self.host, self.port, self.client_id)
            self.connected = True
            
            # Determine connection type for logging
            connection_type = "LIVE" if self.port == 4001 else "PAPER"
            print(f"✓ Connected to IBKR ({connection_type}) on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect to IBKR on {self.host}:{self.port}: {e}")
            print("Make sure IB Gateway is running and configured properly")
            self.connected = False
            return False
    
    def connect_sync(self):
        """Synchronous wrapper for connect"""
        return asyncio.get_event_loop().run_until_complete(self.connect())
    
    async def disconnect(self):
        """Disconnect from IBKR"""
        if self.connected:
            self.ib.disconnect()
            self.connected = False
            print("✓ Disconnected from IBKR")
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not self._last_update:
            return False
        
        elapsed = (datetime.now() - self._last_update).total_seconds()
        return elapsed < self._cache_timeout
    
    async def get_portfolio_positions(self) -> List[Dict]:
        """
        Get current portfolio positions
        Returns list of position dictionaries
        """
        if not self.connected:
            if not await self.connect():
                return []
        
        # Check cache first
        if self._is_cache_valid() and 'positions' in self._cache:
            return self._cache['positions']
        
        try:
            # Get portfolio positions
            positions = self.ib.portfolio()
            
            position_list = []
            for pos in positions:
                position_dict = {
                    'symbol': pos.contract.symbol,
                    'exchange': pos.contract.exchange,
                    'currency': pos.contract.currency,
                    'position': float(pos.position),
                    'market_price': float(pos.marketPrice) if pos.marketPrice else 0.0,
                    'market_value': float(pos.marketValue) if pos.marketValue else 0.0,
                    'average_cost': float(pos.averageCost) if pos.averageCost else 0.0,
                    'unrealized_pnl': float(pos.unrealizedPNL) if pos.unrealizedPNL else 0.0,
                    'realized_pnl': float(pos.realizedPNL) if pos.realizedPNL else 0.0,
                    'contract_id': pos.contract.conId,
                    'account': pos.account
                }
                
                # Calculate some additional metrics
                if position_dict['position'] != 0 and position_dict['average_cost'] > 0:
                    cost_basis = abs(position_dict['position']) * position_dict['average_cost']
                    if cost_basis > 0:
                        position_dict['unrealized_pnl_pct'] = position_dict['unrealized_pnl'] / cost_basis * 100
                    else:
                        position_dict['unrealized_pnl_pct'] = 0.0
                else:
                    position_dict['unrealized_pnl_pct'] = 0.0
                
                position_list.append(position_dict)
            
            # Cache the results
            self._cache['positions'] = position_list
            self._last_update = datetime.now()
            
            return position_list
            
        except Exception as e:
            print(f"Error fetching portfolio positions: {e}")
            return []
    
    async def get_account_summary(self) -> Dict:
        """
        Get account summary with cash, equity, etc.
        """
        if not self.connected:
            if not await self.connect():
                return {}
        
        # Check cache
        if self._is_cache_valid() and 'account' in self._cache:
            return self._cache['account']
        
        try:
            # Request account summary
            account_tags = [
                'TotalCashValue',
                'NetLiquidation', 
                'GrossPositionValue',
                'BuyingPower',
                'AvailableFunds',
                'Cushion',
                'FullAvailableFunds',
                'FullExcessLiquidity',
                'FullInitMarginReq',
                'FullMaintMarginReq'
            ]
            
            # Get account summary
            summary_items = self.ib.accountSummary()
            
            account_data = {}
            for item in summary_items:
                if item.tag in account_tags:
                    try:
                        account_data[item.tag] = float(item.value)
                    except (ValueError, TypeError):
                        account_data[item.tag] = item.value
            
            # Calculate some derived metrics
            total_cash = account_data.get('TotalCashValue', 0)
            net_liquidation = account_data.get('NetLiquidation', 0)
            gross_position_value = account_data.get('GrossPositionValue', 0)
            
            account_summary = {
                'total_cash': total_cash,
                'net_liquidation': net_liquidation,
                'gross_position_value': gross_position_value,
                'buying_power': account_data.get('BuyingPower', 0),
                'available_funds': account_data.get('AvailableFunds', 0),
                'portfolio_value': net_liquidation - total_cash,
                'cash_percentage': (total_cash / net_liquidation * 100) if net_liquidation > 0 else 0,
                'equity_percentage': ((net_liquidation - total_cash) / net_liquidation * 100) if net_liquidation > 0 else 0,
                'timestamp': datetime.now().isoformat(),
                'raw_data': account_data
            }
            
            # Cache the results
            self._cache['account'] = account_summary
            
            return account_summary
            
        except Exception as e:
            print(f"Error fetching account summary: {e}")
            return {}
    
    async def get_open_orders(self) -> List[Dict]:
        """Get open orders"""
        if not self.connected:
            if not await self.connect():
                return []
        
        try:
            orders = self.ib.orders()
            open_orders = []
            
            for order in orders:
                if order.orderStatus.status in ['PreSubmitted', 'Submitted', 'Filled']:
                    order_dict = {
                        'order_id': order.orderId,
                        'symbol': order.contract.symbol,
                        'action': order.order.action,
                        'total_quantity': order.order.totalQuantity,
                        'order_type': order.order.orderType,
                        'limit_price': order.order.lmtPrice if order.order.lmtPrice else None,
                        'status': order.orderStatus.status,
                        'filled': order.orderStatus.filled,
                        'remaining': order.orderStatus.remaining,
                        'avg_fill_price': order.orderStatus.avgFillPrice,
                        'submit_time': order.orderStatus.permId
                    }
                    open_orders.append(order_dict)
            
            return open_orders
            
        except Exception as e:
            print(f"Error fetching open orders: {e}")
            return []
    
    def get_portfolio_data_sync(self) -> Dict:
        """
        Synchronous method to get complete portfolio data
        This is what ODIN will call
        """
        async def _get_data():
            positions = await self.get_portfolio_positions()
            account = await self.get_account_summary()
            orders = await self.get_open_orders()
            return positions, account, orders
        
        try:
            positions, account, orders = asyncio.get_event_loop().run_until_complete(_get_data())
            
            return {
                'positions': positions,
                'account': account,
                'orders': orders,
                'summary': {
                    'total_positions': len([p for p in positions if p['position'] != 0]),
                    'total_cash': account.get('total_cash', 0),
                    'portfolio_value': account.get('portfolio_value', 0),
                    'net_liquidation': account.get('net_liquidation', 0),
                    'open_orders_count': len(orders),
                    'largest_position': max(positions, key=lambda x: abs(x['market_value']))['symbol'] if positions else None,
                    'total_unrealized_pnl': sum(p['unrealized_pnl'] for p in positions),
                    'risk_utilization': min(len(positions) / 20, 1.0),  # Assume max 20 positions
                    'last_updated': datetime.now().isoformat()
                }
            }
        except Exception as e:
            print(f"Error getting portfolio data: {e}")
            return {
                'positions': [],
                'account': {},
                'orders': [],
                'summary': {
                    'total_positions': 0,
                    'total_cash': 0,
                    'portfolio_value': 0,
                    'net_liquidation': 0,
                    'open_orders_count': 0,
                    'largest_position': None,
                    'total_unrealized_pnl': 0,
                    'risk_utilization': 0.0,
                    'last_updated': datetime.now().isoformat()
                }
            }
    
    def __del__(self):
        """Cleanup on destruction"""
        if self.connected:
            try:
                asyncio.get_event_loop().run_until_complete(self.disconnect())
            except:
                pass


# Convenience function for testing
def test_ibkr_connection():
    """Test IBKR connection and portfolio data retrieval"""
    connector = IBKRPortfolioConnector()
    
    print("Testing IBKR connection...")
    if connector.connect_sync():
        print("\n=== Portfolio Data ===")
        data = connector.get_portfolio_data_sync()
        
        print(f"Total Positions: {data['summary']['total_positions']}")
        print(f"Total Cash: ${data['summary']['total_cash']:,.2f}")
        print(f"Portfolio Value: ${data['summary']['portfolio_value']:,.2f}")
        print(f"Net Liquidation: ${data['summary']['net_liquidation']:,.2f}")
        print(f"Unrealized P&L: ${data['summary']['total_unrealized_pnl']:,.2f}")
        
        if data['positions']:
            print("\nTop 3 Positions:")
            sorted_positions = sorted(data['positions'], key=lambda x: abs(x['market_value']), reverse=True)
            for i, pos in enumerate(sorted_positions[:3]):
                print(f"{i+1}. {pos['symbol']}: {pos['position']:,.0f} shares, "
                      f"${pos['market_value']:,.2f} value, "
                      f"{pos['unrealized_pnl_pct']:+.1f}% P&L")
        
        return data
    else:
        print("Failed to connect to IBKR")
        return None


if __name__ == "__main__":
    test_ibkr_connection()