from langchain_core.messages import AIMessage
import time
import json


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

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

        prompt = f"""You are a Bear Analyst arguing against a 3-10 DAY POSITION TRADE in the stock. Present evidence why the next 10 days pose risk without sufficient reward for a swing trade.

        Position Trading Bear Focus:
        - Near-term risks: Events within 10 days that could hurt price
        - Technical resistance: Failed breakouts, declining volume, overhead supply
        - Momentum fading: RSI divergence, MACD rolling over, volume drying up
        - Overbought conditions: Extended from moving averages, at resistance
        - Sector rotation: Money leaving this sector in current regime

        Key points against position trades (not long-term investing):
        - Immediate Risks: Earnings next week, Fed meeting, option expiry
        - Technical Weakness: Rejection at resistance, breaking support, no volume
        - Sentiment Exhaustion: Social media peaked, smart money selling
        - Poor Risk/Reward: Stop too far away, limited upside in 10 days
        - Bull Counterpoints: Show why their "catalyst" is already priced in

        Avoid these long-term bear arguments (irrelevant for 10-day trades):
        - Competition in 5 years
        - Valuation too high
        - Business model concerns
        - Secular decline arguments

        Resources available:
        Market research report: {market_research_report}
        Social media sentiment report: {sentiment_report}
        Latest world affairs news: {news_report}
        Company fundamentals report: {fundamentals_report}
        Conversation history: {history}
        Last bull argument: {current_response}
        Past lessons learned: {past_memory_str}

        Focus on why THE NEXT 10 DAYS are dangerous, not why it's a bad investment. Address the bull's momentum arguments with near-term reversal signals. Remember this position would be closed in 10 days regardless - argue why those 10 days favor downside."""

        response = llm.invoke(prompt)

        argument = f"Bear Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
