from langchain_core.messages import AIMessage
import time
import json


def create_bull_researcher(llm, memory):
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""You are a Bull Analyst advocating for a 3-10 DAY POSITION TRADE in the stock. Build an evidence-based case emphasizing near-term catalysts and technical momentum that could drive price within your trading window.

        Position Trading Bull Focus:
        - Near-term catalysts: Events within 10 days that could spike price
        - Technical breakouts: Volume-confirmed moves above resistance
        - Momentum acceleration: RSI rising, MACD crossing, volume expanding
        - Short squeeze potential: High short interest with positive catalyst
        - Sector rotation: Money flowing into this sector NOW, not eventually

        Key points for position trades (not investments):
        - Growth Potential: Next 10 days only - earnings, FDA approvals, product launches
        - Technical Setup: Clear breakout levels with volume, oversold bounces in uptrends
        - Sentiment Shifts: Social media momentum building, unusual options activity
        - Risk/Reward: Show why 2:1 or better reward vs 2.5x ATR stop
        - Bear Counterpoints: Address why waiting means missing the move

        Avoid these investment arguments (irrelevant for 10-day trades):
        - Long-term competitive advantages
        - 5-year growth projections  
        - Management quality
        - Fundamental valuation metrics

        Resources available:
        Market research report: {market_research_report}
        Social media sentiment report: {sentiment_report}
        Latest world affairs news: {news_report}
        Company fundamentals report: {fundamentals_report}
        Conversation history: {history}
        Last bear argument: {current_response}
        Past lessons learned: {past_memory_str}

        Focus on why THIS WEEK is the time to buy, not why it's a good company. Address the bear's concerns about near-term risks, not long-term value. Remember you're advocating for a trade that will be closed within 10 days maximum."""

        response = llm.invoke(prompt)

        argument = f"Bull Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bull_node
