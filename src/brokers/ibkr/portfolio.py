"""
IBKR Portfolio Data Fetching
Pure data retrieval - no business logic
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .connection import IBKRConnection

logger = logging.getLogger(__name__)


class IBKRPortfolio:
    """Fetches portfolio data from IBKR"""
    
    def __init__(self, connection: IBKRConnection):
        """
        Initialize with connection
        
        Args:
            connection: IBKRConnection instance
        """
        self.conn = connection
        self._cache = {}
        self._cache_time = None
        self._cache_timeout = 60  # seconds
    
    async def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary from IBKR"""
        if not self.conn.is_connected():
            raise ConnectionError("Not connected to IBKR")
        
        try:
            # Get account values
            account_values = self.conn.ib.accountValues()
            
            # Parse into summary dict
            summary = {
                'net_liquidation': 0,
                'total_cash': 0,
                'buying_power': 0,
                'gross_position_value': 0,
                'maintenance_margin': 0,
                'available_funds': 0
            }
            
            for av in account_values:
                if av.tag == 'NetLiquidation':
                    summary['net_liquidation'] = float(av.value)
                elif av.tag == 'TotalCashBalance':
                    summary['total_cash'] = float(av.value)
                elif av.tag == 'BuyingPower':
                    summary['buying_power'] = float(av.value)
                elif av.tag == 'GrossPositionValue':
                    summary['gross_position_value'] = float(av.value)
                elif av.tag == 'MaintMarginReq':
                    summary['maintenance_margin'] = float(av.value)
                elif av.tag == 'AvailableFunds':
                    summary['available_funds'] = float(av.value)
            
            summary['timestamp'] = datetime.now().isoformat()
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get account summary: {e}")
            raise
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get all positions from IBKR"""
        if not self.conn.is_connected():
            raise ConnectionError("Not connected to IBKR")
        
        try:
            positions = []
            ib_positions = self.conn.ib.positions()
            
            for pos in ib_positions:
                position_data = {
                    'symbol': pos.contract.symbol,
                    'exchange': pos.contract.exchange,
                    'position': float(pos.position),
                    'avg_cost': float(pos.avgCost),
                    'market_price': 0,  # Will be updated with market data
                    'market_value': 0,
                    'unrealized_pnl': 0,
                    'unrealized_pnl_pct': 0
                }
                
                # Try to get market price
                try:
                    ticker = self.conn.ib.reqMktData(pos.contract)
                    await asyncio.sleep(0.5)  # Wait for data
                    
                    if ticker.marketPrice():
                        position_data['market_price'] = float(ticker.marketPrice())
                        position_data['market_value'] = (
                            position_data['position'] * position_data['market_price']
                        )
                        position_data['unrealized_pnl'] = (
                            position_data['market_value'] - 
                            (position_data['position'] * position_data['avg_cost'])
                        )
                        position_data['unrealized_pnl_pct'] = (
                            position_data['unrealized_pnl'] / 
                            (position_data['position'] * position_data['avg_cost']) * 100
                        )
                    
                    self.conn.ib.cancelMktData(ticker)
                    
                except Exception as e:
                    logger.warning(f"Could not get market data for {pos.contract.symbol}: {e}")
                
                positions.append(position_data)
            
            return positions
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    async def get_portfolio_data(self) -> Dict[str, Any]:
        """Get complete portfolio data"""
        summary = await self.get_account_summary()
        positions = await self.get_positions()
        
        # Calculate totals
        total_value = sum(p['market_value'] for p in positions)
        total_pnl = sum(p['unrealized_pnl'] for p in positions)
        
        return {
            'summary': {
                **summary,
                'portfolio_value': total_value,
                'total_positions': len(positions),
                'total_unrealized_pnl': total_pnl
            },
            'positions': positions,
            'timestamp': datetime.now().isoformat()
        }