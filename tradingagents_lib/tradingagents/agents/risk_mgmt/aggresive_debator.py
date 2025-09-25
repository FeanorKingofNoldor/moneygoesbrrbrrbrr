import time
import json


def create_risky_debator(llm):
    def risky_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        risky_history = risk_debate_state.get("risky_history", "")

        current_safe_response = risk_debate_state.get("current_safe_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        prompt = f"""As the Risky Risk Analyst for 3-10 DAY MOMENTUM TRADES, champion high-reward opportunities that can move quickly. Focus on momentum continuation in greed regimes and sharp reversals in fear regimes. Here is the trader's decision:

        {trader_decision}

        Position Trading Momentum Perspective:
        - In GREED markets: Look for breakouts with volume, ride momentum with trailing stops
        - In FEAR markets: Look for panic selling climaxes that could snap back violently
        - Focus on stocks with high ATR that can move 5-10% in days
        - Accept wider stops (3x ATR) for higher targets (10%+ moves)

        Your Arguments Should Include:
        - Why waiting for "perfect" setups means missing the best moves
        - How momentum begets momentum in the short term
        - Why the conservative analyst will miss the meat of the move
        - Volume surge patterns that signal institutional accumulation

        Data Sources:
        Market Research Report: {market_research_report}
        Social Media Sentiment Report: {sentiment_report}
        Latest World Affairs Report: {news_report}
        Company Fundamentals Report: {fundamentals_report}

        Current debate: {history}
        Conservative response: {current_safe_response}
        Neutral response: {current_neutral_response}

        Challenge their caution by showing how 3-10 day momentum trades require different risk tolerance than investing. Output conversationally without special formatting."""

        response = llm.invoke(prompt)

        argument = f"Risky Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risky_history + "\n" + argument,
            "safe_history": risk_debate_state.get("safe_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Risky",
            "current_risky_response": argument,
            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return risky_node
