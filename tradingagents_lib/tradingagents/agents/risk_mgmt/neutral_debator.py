import time
import json


def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
        current_safe_response = risk_debate_state.get("current_safe_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        prompt = f"""As the Neutral Risk Analyst for 3-10 DAY POSITION TRADES, provide balanced perspective between momentum and mean reversion strategies based on current market conditions. Here is the trader's decision:

        {trader_decision}

        Position Trading Balanced Perspective:
        - Adapt strategy to regime: momentum in trends, reversion at extremes
        - Standard stops at 2.5x ATR with position sizing adjusted for conviction
        - Mix technical and fundamental factors for 3-10 day catalysts
        - Consider both breakout potential and support levels

        Your Balanced Analysis Should:
        - Acknowledge when the risky analyst is right (strong trends with volume)
        - Recognize when the conservative analyst is right (overextended without catalysts)
        - Propose middle-ground solutions (partial positions, scaled entries)
        - Focus on risk/reward rather than direction certainty

        Key Factors for Position Trades:
        - Is the trend strong enough to continue 3-10 days?
        - Are we at a technical inflection point?
        - What catalysts exist in the next 10 days?
        - Does volume confirm the price action?

        Data Sources:
        Market Research Report: {market_research_report}
        Social Media Sentiment Report: {sentiment_report}
        Latest World Affairs Report: {news_report}
        Company Fundamentals Report: {fundamentals_report}

        Current debate: {history}
        Risky response: {current_risky_response}
        Conservative response: {current_safe_response}

        Bridge the gap between aggression and caution with data-driven position trading logic. Output conversationally without special formatting."""

        response = llm.invoke(prompt)

        argument = f"Neutral Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risk_debate_state.get("risky_history", ""),
            "safe_history": risk_debate_state.get("safe_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_risky_response": risk_debate_state.get(
                "current_risky_response", ""
            ),
            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
            "current_neutral_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return neutral_node
