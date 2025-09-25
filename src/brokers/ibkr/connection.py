"""
IBKR Connection Management
Handles connection lifecycle only
"""

import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

try:
    from ib_async import IB
    IB_AVAILABLE = True
except ImportError:
    IB_AVAILABLE = False

logger = logging.getLogger(__name__)


class IBKRConnection:
    """Manages IBKR connection lifecycle"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 4002, 
                 client_id: int = 1):
        """
        Initialize connection parameters
        
        Args:
            host: IB Gateway host
            port: IB Gateway port (4001=live, 4002=paper)
            client_id: Unique client ID (1-32)
        """
        if not IB_AVAILABLE:
            raise ImportError("ib_async not installed")
            
        self.host = host
        self.port = port
        self.client_id = client_id
        self.ib: Optional[IB] = None
        self.connected = False
    
    async def connect(self) -> bool:
        """Connect to IB Gateway"""
        try:
            self.ib = IB()
            await self.ib.connectAsync(self.host, self.port, self.client_id)
            self.connected = True
            logger.info(f"Connected to IBKR {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"IBKR connection failed: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from IB Gateway"""
        if self.ib and self.connected:
            self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self.connected and self.ib is not None
    
    @asynccontextmanager
    async def session(self):
        """Context manager for connection"""
        try:
            await self.connect()
            yield self.ib
        finally:
            await self.disconnect()