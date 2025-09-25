"""
TradingAgents Client
Handles direct interaction with TradingAgents library
"""

import os
import logging
from typing import Dict, Optional
from datetime import datetime

from tradingagents_lib.tradingagents.graph.trading_graph import TradingAgentsGraph
from config.settings import (
    TRADINGAGENTS_CONFIG,
    TRADINGAGENTS_LIB_PATH,
    ENV_FILE_PATH,
    load_api_keys_from_env
)

logger = logging.getLogger(__name__)


class TradingAgentsClient:
    """Direct interface to TradingAgents library"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize TradingAgents client
        
        Args:
            config: Optional config override
        """
        # Load API keys
        self._load_api_keys()
        
        # Get config
        self.config = config or TRADINGAGENTS_CONFIG.copy()
        self.config['project_dir'] = str(TRADINGAGENTS_LIB_PATH)
        
        # Initialize TradingAgents graph
        self.graph = TradingAgentsGraph(debug=True, config=self.config)
        logger.info(f"TradingAgents initialized with {self.config['llm_provider']}")
    
    def _load_api_keys(self):
        """Load required API keys"""
        try:
            openai_key, finnhub_key = load_api_keys_from_env()
            
            if not openai_key or not finnhub_key:
                # Fallback to manual parsing
                env_path = ENV_FILE_PATH or os.path.join(
                    os.path.dirname(__file__), "../../tradingagents_lib/.env"
                )
                
                if os.path.exists(env_path):
                    with open(env_path, "r") as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith("OPENAI_API_KEY="):
                                openai_key = openai_key or line.split("=", 1)[1]
                            elif line.startswith("FINNHUB_API_KEY="):
                                finnhub_key = finnhub_key or line.split("=", 1)[1]
            
            # Set environment variables
            if openai_key and not os.environ.get("OPENAI_API_KEY"):
                os.environ["OPENAI_API_KEY"] = openai_key
            if finnhub_key and not os.environ.get("FINNHUB_API_KEY"):
                os.environ["FINNHUB_API_KEY"] = finnhub_key
            
            logger.info(f"Loaded API keys (OpenAI ending: ...{openai_key[-10:] if openai_key else 'MISSING'})")
            
        except Exception as e:
            logger.error(f"Error loading API keys: {e}")
            if not os.environ.get("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY not found!")
    
    def analyze(self, symbol: str, date: str = None) -> tuple:
        """
        Run TradingAgents analysis
        
        Args:
            symbol: Stock symbol
            date: Analysis date (optional)
            
        Returns:
            Tuple of (state, decision)
        """
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            state, decision = self.graph.propagate(symbol, date)
            logger.debug(f"TradingAgents decision for {symbol}: {decision}")
            return state, decision
        except Exception as e:
            logger.error(f"TradingAgents analysis failed for {symbol}: {e}")
            raise
    
    def reflect_and_remember(self, position_return: float):
        """Reflect on trade outcome and update memory"""
        try:
            self.graph.reflect_and_remember(position_return)
            logger.info(f"Reflected on position with {position_return:.2%} return")
        except Exception as e:
            logger.error(f"Reflection failed: {e}")