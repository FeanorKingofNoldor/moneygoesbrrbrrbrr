"""
IBKR Utility Functions
Helper functions for IBKR operations
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, time


def is_market_open() -> bool:
    """Check if US market is open"""
    now = datetime.now()
    market_open = time(9, 30)
    market_close = time(16, 0)
    
    # Check if weekday
    if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
    
    # Check time
    current_time = now.time()
    return market_open <= current_time <= market_close


def format_contract_details(contract: Any) -> Dict[str, Any]:
    """Format IB contract to dict"""
    return {
        'symbol': contract.symbol,
        'exchange': contract.exchange,
        'currency': contract.currency,
        'contract_id': contract.conId,
        'local_symbol': contract.localSymbol,
        'trading_class': contract.tradingClass
    }


def calculate_position_size(account_value: float, risk_pct: float, 
                           stop_distance: float, entry_price: float) -> int:
    """
    Calculate position size (pure math, no business logic)
    
    Args:
        account_value: Total account value
        risk_pct: Risk percentage (e.g., 0.01 for 1%)
        stop_distance: Distance to stop in points
        entry_price: Entry price
        
    Returns:
        Number of shares
    """
    risk_amount = account_value * risk_pct
    shares = int(risk_amount / stop_distance)
    
    # Ensure we can afford it
    max_affordable = int(account_value * 0.95 / entry_price)
    
    return min(shares, max_affordable)


async def wait_for_fill(trade: Any, timeout: int = 30) -> bool:
    """Wait for order to fill with timeout"""
    try:
        await asyncio.wait_for(trade.fillEvent, timeout=timeout)
        return True
    except asyncio.TimeoutError:
        return False