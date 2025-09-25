"""
IBKR Order Execution
Pure order API - no risk logic (handled by agents)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from ib_async import Stock, MarketOrder, LimitOrder, StopOrder, Trade
except ImportError:
    Stock = MarketOrder = LimitOrder = StopOrder = Trade = None

from .connection import IBKRConnection

logger = logging.getLogger(__name__)


class IBKROrders:
    """Handles order execution through IBKR API"""
    
    def __init__(self, connection: IBKRConnection):
        """
        Initialize with connection
        
        Args:
            connection: IBKRConnection instance
        """
        self.conn = connection
        self.pending_orders = {}
    
    async def place_market_order(self, symbol: str, action: str, 
                                 quantity: int) -> Dict[str, Any]:
        """
        Place a market order
        
        Args:
            symbol: Stock symbol
            action: 'BUY' or 'SELL'
            quantity: Number of shares
            
        Returns:
            Order details dict
        """
        if not self.conn.is_connected():
            raise ConnectionError("Not connected to IBKR")
        
        try:
            # Create contract
            contract = Stock(symbol, 'SMART', 'USD')
            
            # Create order
            order = MarketOrder(action, quantity)
            
            # Place order
            trade = self.conn.ib.placeOrder(contract, order)
            
            # Store in pending
            self.pending_orders[trade.order.orderId] = trade
            
            # Wait for fill (with timeout)
            await asyncio.wait_for(trade.fillEvent, timeout=10)
            
            return self._format_trade(trade)
            
        except asyncio.TimeoutError:
            logger.warning(f"Order timeout for {symbol}")
            return self._format_trade(trade)
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    async def place_limit_order(self, symbol: str, action: str, 
                               quantity: int, limit_price: float) -> Dict[str, Any]:
        """Place a limit order"""
        if not self.conn.is_connected():
            raise ConnectionError("Not connected to IBKR")
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            order = LimitOrder(action, quantity, limit_price)
            trade = self.conn.ib.placeOrder(contract, order)
            
            self.pending_orders[trade.order.orderId] = trade
            
            return self._format_trade(trade)
            
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            raise
    
    async def place_stop_order(self, symbol: str, action: str, 
                              quantity: int, stop_price: float) -> Dict[str, Any]:
        """Place a stop order"""
        if not self.conn.is_connected():
            raise ConnectionError("Not connected to IBKR")
        
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            order = StopOrder(action, quantity, stop_price)
            trade = self.conn.ib.placeOrder(contract, order)
            
            self.pending_orders[trade.order.orderId] = trade
            
            return self._format_trade(trade)
            
        except Exception as e:
            logger.error(f"Failed to place stop order: {e}")
            raise
    
    async def cancel_order(self, order_id: int) -> bool:
        """Cancel an order"""
        if not self.conn.is_connected():
            raise ConnectionError("Not connected to IBKR")
        
        try:
            if order_id in self.pending_orders:
                trade = self.pending_orders[order_id]
                self.conn.ib.cancelOrder(trade.order)
                del self.pending_orders[order_id]
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            return False
    
    async def get_open_orders(self) -> List[Dict[str, Any]]:
        """Get all open orders"""
        if not self.conn.is_connected():
            raise ConnectionError("Not connected to IBKR")
        
        try:
            trades = self.conn.ib.openTrades()
            return [self._format_trade(trade) for trade in trades]
            
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            raise
    
    def _format_trade(self, trade: Trade) -> Dict[str, Any]:
        """Format trade object to dict"""
        fills = []
        for fill in trade.fills:
            fills.append({
                'time': fill.time.isoformat() if fill.time else None,
                'shares': fill.execution.shares,
                'price': fill.execution.price,
                'commission': fill.commissionReport.commission if fill.commissionReport else 0
            })
        
        return {
            'order_id': trade.order.orderId,
            'symbol': trade.contract.symbol,
            'action': trade.order.action,
            'quantity': trade.order.totalQuantity,
            'order_type': trade.order.orderType,
            'limit_price': trade.order.lmtPrice if hasattr(trade.order, 'lmtPrice') else None,
            'stop_price': trade.order.auxPrice if hasattr(trade.order, 'auxPrice') else None,
            'status': trade.orderStatus.status,
            'filled': trade.orderStatus.filled,
            'remaining': trade.orderStatus.remaining,
            'avg_fill_price': trade.orderStatus.avgFillPrice,
            'fills': fills,
            'timestamp': datetime.now().isoformat()
        }