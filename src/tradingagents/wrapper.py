import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../tradingagents_lib'))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
import os
from datetime import datetime

class OdinTradingAgentsWrapper:
    def __init__(self):
        # Set API keys from environment
        os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', 'test-key')
        os.environ['FINNHUB_API_KEY'] = os.getenv('FINNHUB_API_KEY', 'test-key')
        
        # Configure for testing
        self.config = DEFAULT_CONFIG.copy()
        self.config["deep_think_llm"] = "gpt-4o-mini"
        self.config["quick_think_llm"] = "gpt-4o-mini"
        self.config["online_tools"] = True  # Changed to True
        
        self.graph = TradingAgentsGraph(debug=True, config=self.config)
    
    def analyze_stock(self, symbol, date=None):  # Make sure this is indented properly!
        if date is None:
            date = "2024-12-19"  # Use a recent past date
        
        print(f"Analyzing {symbol} for {date}...")
        result, decision = self.graph.propagate(symbol, date)
        return {
            'symbol': symbol,
            'decision': decision,
            'raw_result': result
        }