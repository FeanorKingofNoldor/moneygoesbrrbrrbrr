"""
Abstract base class for all broker implementations
Pure API interface - no business logic
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Position:
    """Standard position data structure"""
    symbol: str
    shares: float
    avg_cost: float
    market_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float


@dataclass
class Order:
    """Standard order data structure"""
    order_id: str
    symbol: str
    action: str  # BUY/SELL
    quantity: int
    order_type: str  # MKT/LMT/STP
    status: str
    fill_price: Optional[float] = None
    timestamp: Optional[datetime] = None


class BrokerInterface(ABC):
    """Abstract interface for all brokers"""
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to broker"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Close broker connection"""
        pass
    
    @abstractmethod
    async def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary data"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all current positions"""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, action: str, quantity: int, 
                         order_type: str = 'MKT', **kwargs) -> Order:
        """Place an order"""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        pass