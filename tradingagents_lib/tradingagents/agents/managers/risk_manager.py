import time
import json


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:

        company_name = state["company_of_interest"]

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        fundamentals_report = state["news_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""As the Risk Management Judge and Debate Facilitator for 3-10 DAY POSITION TRADES, evaluate the debate between three risk analysts—Risky, Neutral, and Safe/Conservative—and determine the best course of action. Your decision must result in a clear recommendation: Buy, Sell, or Hold.

        Position Trading Specific Guidelines:
        1. **Time Horizon Focus**: All risk assessments should be for 3-10 day holds, not long-term investments
        2. **Stop Loss Requirement**: Every BUY must have a clear stop at 2.5x ATR
        3. **Volume Confirmation**: Positions require 1.5x average daily volume
        4. **Maximum Hold**: Any position held 10 days should be flagged for exit

        Decision Framework for Position Trades:
        - In GREED regimes (F&G > 55): Favor the Risky analyst for momentum plays
        - In FEAR regimes (F&G < 45): Favor the Conservative analyst for mean reversion
        - In NEUTRAL regimes: Balance all three perspectives

        Guidelines for Decision-Making:
        1. **Summarize Key Arguments**: Extract points relevant to 3-10 day price movement
        2. **Provide Rationale**: Focus on near-term catalysts and technical setups
        3. **Refine the Trader's Plan**: Adjust **{trader_plan}** with specific entry/exit levels
        4. **Learn from Past Mistakes**: Use **{past_memory_str}** to avoid repeated errors, especially:
        - Holding beyond 10 days
        - Ignoring stop losses
        - Trading without volume confirmation

        Deliverables:
        - Clear recommendation: Buy, Sell, or Hold
        - Entry price, stop loss (2.5x ATR), and target
        - Expected holding period (must be <10 days)
        - Risk/reward ratio

        **Analysts Debate History:**  
        {history}

        Focus on position trading setups, not long-term investment merit."""

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": risk_debate_state["history"],
            "risky_history": risk_debate_state["risky_history"],
            "safe_history": risk_debate_state["safe_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_risky_response": risk_debate_state["current_risky_response"],
            "current_safe_response": risk_debate_state["current_safe_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response.content,
        }

    return risk_manager_node
