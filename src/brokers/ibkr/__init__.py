"""
IBKR Broker Implementation
Combines all IBKR components
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

from ..base.broker_interface import BrokerInterface, Position, Order
from .connection import IBKRConnection
from .portfolio import IBKRPortfolio
from .orders import IBKROrders

logger = logging.getLogger(__name__)


class IBKRBroker(BrokerInterface):
    """Complete IBKR broker implementation"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 4002, 
                 client_id: int = 1):
        """
        Initialize IBKR broker
        
        Args:
            host: IB Gateway host
            port: IB Gateway port
            client_id: Client ID
        """
        self.connection = IBKRConnection(host, port, client_id)
        self.portfolio = IBKRPortfolio(self.connection)
        self.orders = IBKROrders(self.connection)
    
    async def connect(self) -> bool:
        """Connect to IBKR"""
        return await self.connection.connect()
    
    async def disconnect(self) -> None:
        """Disconnect from IBKR"""
        await self.connection.disconnect()
    
    async def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary"""
        return await self.portfolio.get_account_summary()
    
    async def get_positions(self) -> List[Position]:
        """Get all positions"""
        positions_data = await self.portfolio.get_positions()
        
        return [
            Position(
                symbol=p['symbol'],
                shares=p['position'],
                avg_cost=p['avg_cost'],
                market_price=p['market_price'],
                market_value=p['market_value'],
                unrealized_pnl=p['unrealized_pnl'],
                unrealized_pnl_pct=p['unrealized_pnl_pct']
            )
            for p in positions_data
        ]
    
    async def place_order(self, symbol: str, action: str, quantity: int,
                         order_type: str = 'MKT', **kwargs) -> Order:
        """Place an order"""
        if order_type == 'MKT':
            result = await self.orders.place_market_order(symbol, action, quantity)
        elif order_type == 'LMT':
            limit_price = kwargs.get('limit_price')
            if not limit_price:
                raise ValueError("Limit price required for limit order")
            result = await self.orders.place_limit_order(symbol, action, quantity, limit_price)
        elif order_type == 'STP':
            stop_price = kwargs.get('stop_price')
            if not stop_price:
                raise ValueError("Stop price required for stop order")
            result = await self.orders.place_stop_order(symbol, action, quantity, stop_price)
        else:
            raise ValueError(f"Unsupported order type: {order_type}")
        
        return Order(
            order_id=str(result['order_id']),
            symbol=result['symbol'],
            action=result['action'],
            quantity=result['quantity'],
            order_type=result['order_type'],
            status=result['status'],
            fill_price=result.get('avg_fill_price'),
            timestamp=result.get('timestamp')
        )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        return await self.orders.cancel_order(int(order_id))
    
    async def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        # Would need to track orders internally
        raise NotImplementedError("Order tracking not implemented")
    
    # Synchronous wrapper methods for compatibility
    def connect_sync(self) -> bool:
        """Synchronous connect"""
        return asyncio.get_event_loop().run_until_complete(self.connect())
    
    def get_portfolio_data_sync(self) -> Dict[str, Any]:
        """Synchronous portfolio data"""
        return asyncio.get_event_loop().run_until_complete(
            self.portfolio.get_portfolio_data()
        )