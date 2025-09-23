import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../tradingagents_lib'))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from datetime import datetime

class OdinTradingAgentsWrapper:
    def __init__(self):
        # Manually parse .env file since python-dotenv is acting up
        env_path = os.path.join(os.path.dirname(__file__), '../../tradingagents_lib/.env')
        
        openai_key = None
        finnhub_key = None
        
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('OPENAI_API_KEY='):
                    openai_key = line.split('=', 1)[1]
                elif line.startswith('FINNHUB_API_KEY='):
                    finnhub_key = line.split('=', 1)[1]
        
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not found in .env file!")
        if not finnhub_key:
            raise ValueError("FINNHUB_API_KEY not found in .env file!")
            
        os.environ['OPENAI_API_KEY'] = openai_key
        os.environ['FINNHUB_API_KEY'] = finnhub_key
        
        print(f"Loaded OpenAI key ending in: {openai_key[-10:]}")
        
        # Configure for testing
        self.config = DEFAULT_CONFIG.copy()
        self.config["deep_think_llm"] = "gpt-4o-mini"
        self.config["quick_think_llm"] = "gpt-4o-mini"
        self.config["online_tools"] = True
        
        self.graph = TradingAgentsGraph(debug=True, config=self.config)
    
    def analyze_stock(self, symbol, date=None):
        if date is None:
            date = "2024-12-19"
        
        print(f"Analyzing {symbol} for {date}...")
        result, decision = self.graph.propagate(symbol, date)
        return {
            'symbol': symbol,
            'decision': decision,
            'raw_result': result
        }