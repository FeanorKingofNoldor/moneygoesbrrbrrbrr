import functools
import time
import json


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        
        # Get the risk debate result if available
        risk_manager_result = state.get("final_trade_decision", "")

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        context = {
            "role": "user",
            "content": f"Based on a comprehensive analysis by a team of analysts for {company_name}, here are the reports for your 3-10 day position trading decision:\n\nProposed Investment Plan from Bull/Bear Debate: {investment_plan}\n\nRisk Management Assessment: {risk_manager_result}\n\nUse these insights to make a specific position trading decision with entry, stop, and target levels.",
        }

        messages = [
            {
                "role": "system",
                "content": f"""You are a Position Trader making the FINAL 3-10 day swing trade decision. Synthesize all reports into an actionable trading decision with specific parameters.

                POSITION TRADING RULES (STRICT):
                1. Maximum hold period: 10 days then exit regardless
                2. Stop loss: ALWAYS set at 2.5x ATR from entry
                3. Volume requirement: Current volume must exceed 1.5x 20-day average
                4. Risk/Reward: Minimum 2:1 (target vs stop distance)
                5. Position exits: Stop hit, target reached, 10 days elapsed, or volume divergence

                Decision Criteria for BUY:
                ✓ Clear technical setup (breakout or oversold bounce)
                ✓ Catalyst within 10 days or strong momentum
                ✓ Volume confirmation (>1.5x average today)
                ✓ Risk/reward exceeds 2:1
                ✓ Regime alignment (momentum in greed, reversion in fear)

                Decision Criteria for SELL/AVOID:
                ✗ Already extended (>7% above 10-day MA)
                ✗ Major resistance overhead within target range
                ✗ Declining volume on recent advance
                ✗ Binary event risk without edge

                Learn from past position trading mistakes: {past_memory_str}

                Required Output Format:
                Entry Price: $XX.XX
                Stop Loss: $XX.XX (2.5x ATR = $X.XX move)
                Target Price: $XX.XX (X% gain)
                Risk/Reward Ratio: 1:X.X
                Conviction Score: XX/100
                Volume Confirmation: Yes/No
                Expected Hold: X days
                Primary Catalyst: [specific]
                Exit Plan: [stop/target/time/volume]

                Always end with: FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**""",
            },
            context,
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")