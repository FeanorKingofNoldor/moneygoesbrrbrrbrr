import time
import json


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""As the portfolio manager judging this 3-10 DAY POSITION TRADE debate, evaluate the bull and bear arguments focused on near-term price action, not long-term investment merit.

        Decision Framework for Position Trades:
        - Weight near-term catalysts (next 10 days) heavily
        - Focus on technical setups and momentum
        - Consider regime: Favor bulls in fear (oversold bounces), bears in greed (overbought)
        - Require clear entry/stop/target for any BUY

        Your recommendation—Buy, Sell, or Hold—must be based on:
        1. Technical setup quality for 3-10 day move
        2. Risk/reward with 2.5x ATR stop
        3. Volume confirmation (>1.5x average)
        4. Near-term catalysts or lack thereof
        5. Current regime context

        Your Trading Plan Must Include:
        - Entry price level
        - Stop loss (2.5x ATR)
        - Target (3-5% mean reversion, 7-10% momentum)
        - Expected hold period (max 10 days)
        - Key catalyst/event to watch
        - Exit conditions beyond stop/target

        Learn from past position trading mistakes:
        "{past_memory_str}"

        Common errors to avoid:
        - Holding beyond 10 days
        - No clear stop level
        - Ignoring volume signals
        - Fighting the regime

        Debate History:
        {history}

        Make a decisive call for this TRADE (not investment). Choose Hold only if neither bull nor bear makes a compelling case for movement within 10 days. Present your analysis conversationally without special formatting."""

        response = llm.invoke(prompt)

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": response.content,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
