from langchain_core.messages import AIMessage
import time
import json


def create_safe_debator(llm):
    def safe_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        safe_history = risk_debate_state.get("safe_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        prompt = f"""As the Safe/Conservative Risk Analyst for 3-10 DAY POSITION TRADES, prioritize capital preservation while seeking mean reversion opportunities in oversold conditions. Here is the trader's decision:

        {trader_decision}

        Position Trading Conservative Perspective:
        - Only buy extreme oversold (RSI(2) < 10) with clear support
        - Require tight stops (2x ATR maximum) to preserve capital
        - Target modest gains (3-5%) with high probability
        - Avoid momentum chasing in extended markets
        - Wait for fear regimes where risk/reward improves dramatically

        Your Arguments Should Focus On:
        - Why the risky analyst ignores that most breakouts fail
        - How chasing momentum in greed regimes leads to buying tops
        - Why waiting for extreme oversold provides 65%+ win rates
        - Volume exhaustion patterns that signal reversals

        Counter their optimism by emphasizing:
        - Current extension from moving averages
        - Declining breadth despite price rises
        - Overhead resistance levels
        - Upcoming catalysts that could gap against position

        Data Sources:
        Market Research Report: {market_research_report}
        Social Media Sentiment Report: {sentiment_report}
        Latest World Affairs Report: {news_report}
        Company Fundamentals Report: {fundamentals_report}

        Current debate: {history}
        Risky response: {current_risky_response}
        Neutral response: {current_neutral_response}

        Show why patience and discipline beat aggression in position trading. Output conversationally without special formatting."""

        response = llm.invoke(prompt)

        argument = f"Safe Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risk_debate_state.get("risky_history", ""),
            "safe_history": safe_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Safe",
            "current_risky_response": risk_debate_state.get(
                "current_risky_response", ""
            ),
            "current_safe_response": argument,
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return safe_node
