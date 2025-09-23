from src.tradingagents.wrapper import OdinTradingAgentsWrapper
from dotenv import load_dotenv

load_dotenv()

# Test with one stock
wrapper = OdinTradingAgentsWrapper()
result = wrapper.analyze_stock("AAPL")

print(f"Analysis complete:")
print(f"Decision: {result['decision']}")