"""
IBKR Order Execution System for ODIN
Automatically places trades based on TradingAgents decisions
"""

import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import pandas as pd

try:
    from ib_async import IB, Stock, MarketOrder, LimitOrder, StopOrder, OrderStatus, Trade
    IB_AVAILABLE = True
except ImportError:
    print("Warning: ib_async not installed. Install with: pip install ib_async")
    IB_AVAILABLE = False


class OrderType(Enum):
    MARKET = "MKT"
    LIMIT = "LMT" 
    STOP = "STP"
    STOP_LIMIT = "STP LMT"


class OrderAction(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderResult:
    """Container for order execution results"""
    def __init__(self, success: bool, order_id: Optional[int] = None, 
                 message: str = "", trade_object: Optional[Trade] = None):
        self.success = success
        self.order_id = order_id
        self.message = message
        self.trade_object = trade_object
        self.timestamp = datetime.now()


class IBKROrderExecutor:
    """
    Automated order execution for ODIN system
    Handles order placement, tracking, and confirmation
    """
    
    def __init__(self, host='127.0.0.1', port=4002, client_id=2, 
                 max_position_size_pct=5.0, max_total_exposure_pct=95.0):
        """
        Initialize order executor
        
        Args:
            host: IB Gateway host
            port: IB Gateway port (4002 for paper, 4001 for live)
            client_id: Unique client ID (different from portfolio connector)
            max_position_size_pct: Maximum % of portfolio per position
            max_total_exposure_pct: Maximum % of portfolio invested
        """
        if not IB_AVAILABLE:
            raise ImportError("ib_async library not available")
        
        self.host = host
        self.port = port  
        self.client_id = client_id
        self.ib = IB()
        self.connected = False
        
        # Risk management settings
        self.max_position_size_pct = max_position_size_pct / 100
        self.max_total_exposure_pct = max_total_exposure_pct / 100
        
        # Order tracking
        self.pending_orders = {}
        self.executed_orders = []
        self.failed_orders = []
        
        # Safety settings
        self.is_paper_trading = port == 4002
        self.orders_enabled = True
        self.dry_run = False  # Set to True to simulate orders
        
        print(f"Order Executor initialized:")
        print(f"  Mode: {'PAPER' if self.is_paper_trading else 'LIVE'}")
        print(f"  Max position: {max_position_size_pct}%")
        print(f"  Max exposure: {max_total_exposure_pct}%")
    
    async def connect(self):
        """Connect to IB Gateway for order execution"""
        try:
            await self.ib.connectAsync(self.host, self.port, self.client_id)
            self.connected = True
            
            # Set up event handlers
            self.ib.orderStatusEvent += self._on_order_status
            self.ib.execDetailsEvent += self._on_execution
            
            print(f"✓ Order executor connected to IBKR on {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Failed to connect order executor: {e}")
            self.connected = False
            return False
    
    def connect_sync(self):
        """Synchronous wrapper for connect"""
        return asyncio.get_event_loop().run_until_complete(self.connect())
    
    def _on_order_status(self, trade):
        """Handle order status updates"""
        order_id = trade.order.orderId
        status = trade.orderStatus.status
        
        print(f"Order {order_id} status: {status}")
        
        if order_id in self.pending_orders:
            self.pending_orders[order_id]['status'] = status
            self.pending_orders[order_id]['last_update'] = datetime.now()
            
            if status in ['Filled', 'Cancelled', 'ApiCancelled']:
                # Move to completed orders
                completed_order = self.pending_orders.pop(order_id)
                if status == 'Filled':
                    self.executed_orders.append(completed_order)
                else:
                    self.failed_orders.append(completed_order)
    
    def _on_execution(self, trade, fill):
        """Handle trade executions"""
        print(f"Execution: {fill.execution.shares} shares of {trade.contract.symbol} "
              f"at ${fill.execution.price}")
    
    def calculate_position_size(self, symbol: str, regime_multiplier: float, 
                              account_value: float, current_price: float,
                              atr: float) -> int:
        """
        Calculate optimal position size based on regime and risk management
        
        Args:
            symbol: Stock symbol
            regime_multiplier: Multiplier based on market regime (0.5x to 1.5x)
            account_value: Total account value
            current_price: Current stock price
            atr: Average True Range for stop loss calculation
            
        Returns:
            Number of shares to buy
        """
        # Base risk per trade (1% of account)
        base_risk_amount = account_value * 0.01
        
        # Adjust for regime (more aggressive in fear, conservative in greed)
        risk_amount = base_risk_amount * regime_multiplier
        
        # Calculate stop loss distance (2.5x ATR from research)
        stop_distance = atr * 2.5
        
        # Position size based on stop loss
        shares_by_risk = int(risk_amount / stop_distance)
        
        # Limit by maximum position size (e.g., 5% of account)
        max_position_value = account_value * self.max_position_size_pct
        max_shares_by_value = int(max_position_value / current_price)
        
        # Take the smaller of the two
        shares = min(shares_by_risk, max_shares_by_value)
        
        # Ensure at least 1 share if we can afford it
        if shares == 0 and current_price <= max_position_value:
            shares = 1
        
        return shares
    
    def calculate_stop_loss_price(self, entry_price: float, atr: float, 
                                 vix: float) -> float:
        """
        Calculate stop loss price based on ATR and VIX
        From research: 2.5x ATR optimal, adjust for volatility
        """
        if vix < 15:
            multiplier = 1.5  # Low volatility
        elif vix < 30:
            multiplier = 2.5  # Normal volatility (research optimal)
        else:
            multiplier = 3.0  # High volatility
        
        stop_distance = atr * multiplier
        stop_price = entry_price - stop_distance
        
        # Ensure stop is reasonable (max 10% loss)
        max_loss = entry_price * 0.10
        if stop_distance > max_loss:
            stop_price = entry_price - max_loss
        
        return round(stop_price, 2)
    
    def validate_order(self, symbol: str, action: OrderAction, shares: int,
                      account_value: float, current_positions: List[Dict]) -> Tuple[bool, str]:
        """
        Validate order before placement
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not self.orders_enabled:
            return False, "Order execution disabled"
        
        if shares <= 0:
            return False, "Invalid share quantity"
        
        # Check if we already have a position
        existing_position = next((p for p in current_positions if p['symbol'] == symbol), None)
        if existing_position and action == OrderAction.BUY:
            return False, f"Already have position in {symbol}"
        
        # Check total exposure
        current_exposure = sum(abs(p['market_value']) for p in current_positions) / account_value
        if current_exposure > self.max_total_exposure_pct:
            return False, f"Total exposure {current_exposure:.1%} exceeds limit {self.max_total_exposure_pct:.1%}"
        
        # Check for duplicate pending orders
        for order_data in self.pending_orders.values():
            if order_data['symbol'] == symbol and order_data['action'] == action.value:
                return False, f"Pending order already exists for {symbol}"
        
        # Paper trading validation
        if not self.is_paper_trading:
            return False, "Live trading not enabled - safety check"
        
        return True, "Order validated"
    
    async def place_market_order(self, symbol: str, action: OrderAction, shares: int,
                               stop_loss_price: Optional[float] = None) -> OrderResult:
        """
        Place a market order with optional stop loss
        """
        if not self.connected:
            if not await self.connect():
                return OrderResult(False, message="Not connected to IBKR")
        
        try:
            # Create stock contract
            contract = Stock(symbol, 'SMART', 'USD')
            await self.ib.qualifyContractsAsync(contract)
            
            # Create market order
            order = MarketOrder(action.value, shares)
            
            if self.dry_run:
                # Simulate order for testing
                fake_order_id = len(self.executed_orders) + 1000
                print(f"DRY RUN: {action.value} {shares} shares of {symbol}")
                return OrderResult(True, fake_order_id, "Dry run successful")
            
            # Place the order
            trade = self.ib.placeOrder(contract, order)
            order_id = trade.order.orderId
            
            # Track the order
            self.pending_orders[order_id] = {
                'symbol': symbol,
                'action': action.value,
                'shares': shares,
                'order_type': 'MARKET',
                'trade': trade,
                'timestamp': datetime.now(),
                'status': 'Submitted',
                'stop_loss_price': stop_loss_price
            }
            
            print(f"✓ Market order placed: {action.value} {shares} shares of {symbol} (ID: {order_id})")
            
            # Place stop loss order if specified
            if stop_loss_price and action == OrderAction.BUY:
                await self._place_stop_loss_order(symbol, shares, stop_loss_price)
            
            return OrderResult(True, order_id, "Market order placed successfully", trade)
            
        except Exception as e:
            error_msg = f"Failed to place market order for {symbol}: {e}"
            print(f"✗ {error_msg}")
            return OrderResult(False, message=error_msg)
    
    async def _place_stop_loss_order(self, symbol: str, shares: int, stop_price: float):
        """Place a stop loss order"""
        try:
            contract = Stock(symbol, 'SMART', 'USD')
            stop_order = StopOrder('SELL', shares, stop_price)
            
            trade = self.ib.placeOrder(contract, stop_order)
            order_id = trade.order.orderId
            
            self.pending_orders[order_id] = {
                'symbol': symbol,
                'action': 'SELL',
                'shares': shares,
                'order_type': 'STOP',
                'stop_price': stop_price,
                'trade': trade,
                'timestamp': datetime.now(),
                'status': 'Submitted'
            }
            
            print(f"✓ Stop loss order placed: SELL {shares} shares of {symbol} at ${stop_price}")
            
        except Exception as e:
            print(f"✗ Failed to place stop loss for {symbol}: {e}")
    
    def place_order_sync(self, symbol: str, action: OrderAction, shares: int,
                        stop_loss_price: Optional[float] = None) -> OrderResult:
        """Synchronous wrapper for order placement"""
        return asyncio.get_event_loop().run_until_complete(
            self.place_market_order(symbol, action, shares, stop_loss_price)
        )
    
    def get_order_status(self, order_id: int) -> Optional[Dict]:
        """Get status of a specific order"""
        if order_id in self.pending_orders:
            return self.pending_orders[order_id]
        
        # Check completed orders
        for order in self.executed_orders + self.failed_orders:
            if order.get('trade') and order['trade'].order.orderId == order_id:
                return order
        
        return None
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders"""
        return list(self.pending_orders.values())
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel a pending order"""
        if order_id in self.pending_orders:
            try:
                trade = self.pending_orders[order_id]['trade']
                self.ib.cancelOrder(trade.order)
                print(f"✓ Cancelled order {order_id}")
                return True
            except Exception as e:
                print(f"✗ Failed to cancel order {order_id}: {e}")
                return False
        return False
    
    def get_execution_summary(self) -> Dict:
        """Get summary of order executions"""
        total_orders = len(self.executed_orders) + len(self.failed_orders) + len(self.pending_orders)
        
        return {
            'total_orders': total_orders,
            'executed': len(self.executed_orders),
            'failed': len(self.failed_orders),
            'pending': len(self.pending_orders),
            'success_rate': len(self.executed_orders) / total_orders * 100 if total_orders > 0 else 0,
            'last_update': datetime.now()
        }
    
    def enable_live_trading(self, confirmation_code: str = ""):
        """
        Enable live trading (safety mechanism)
        Requires confirmation code to prevent accidental live trading
        """
        if confirmation_code != "ENABLE_LIVE_TRADING_ODIN":
            print("⚠ Invalid confirmation code for live trading")
            return False
        
        if self.port == 4001:  # Live trading port
            self.orders_enabled = True
            print("🚨 LIVE TRADING ENABLED - REAL MONEY AT RISK!")
            return True
        else:
            print("✓ Paper trading mode - live trading flag set")
            return True
    
    def disable_orders(self):
        """Disable all order placement (emergency stop)"""
        self.orders_enabled = False
        print("🛑 Order placement DISABLED")
    
    def set_dry_run(self, enabled: bool):
        """Enable/disable dry run mode for testing"""
        self.dry_run = enabled
        print(f"Dry run mode: {'ENABLED' if enabled else 'DISABLED'}")


# Convenience function for testing
async def test_order_system():
    """Test the order execution system"""
    print("Testing IBKR Order Execution System")
    print("=" * 40)
    
    executor = IBKROrderExecutor(port=4002)  # Paper trading
    
    if await executor.connect():
        print("✓ Connected to IBKR for order execution")
        
        # Enable dry run for testing
        executor.set_dry_run(True)
        
        # Test order validation
        is_valid, message = executor.validate_order(
            "AAPL", OrderAction.BUY, 10, 100000, []
        )
        print(f"Order validation: {is_valid} - {message}")
        
        if is_valid:
            # Test order placement (dry run)
            result = await executor.place_market_order(
                "AAPL", OrderAction.BUY, 10, stop_loss_price=200.0
            )
            print(f"Order result: {result.success} - {result.message}")
        
        # Get summary
        summary = executor.get_execution_summary()
        print(f"Execution summary: {summary}")
        
    else:
        print("✗ Failed to connect to IBKR")


if __name__ == "__main__":
    asyncio.run(test_order_system())