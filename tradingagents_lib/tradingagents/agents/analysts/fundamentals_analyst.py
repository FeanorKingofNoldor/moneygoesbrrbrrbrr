from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


def create_fundamentals_analyst(llm, toolkit):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        if toolkit.config["online_tools"]:
            tools = [toolkit.get_fundamentals_openai]
        else:
            tools = [
                toolkit.get_finnhub_company_insider_sentiment,
                toolkit.get_finnhub_company_insider_transactions,
                toolkit.get_simfin_balance_sheet,
                toolkit.get_simfin_cashflow,
                toolkit.get_simfin_income_stmt,
            ]
        
        
        system_message = (
            "You are a Catalyst Analyst for 3-10 day position trades. "
            "Your job is to identify near-term catalysts that could move the stock price within your trading window. "
            ""
            "Focus ONLY on: "
            "- Earnings dates within next 10 days (check exact dates and consensus) "
            "- Product launches, FDA approvals, court decisions this week "
            "- Major contract announcements expected soon "
            "- Analyst day presentations or guidance updates scheduled "
            "- Unusual options activity suggesting institutional positioning "
            "- Insider transactions in last 48 hours (especially clusters) "
            "- Recent analyst upgrades/downgrades with price target changes "
            ""
            "IGNORE these long-term factors: "
            "- P/E ratios, book value, DCF valuations "
            "- 5-year growth projections "
            "- Competitive moat analysis "
            "- Management track record discussions "
            ""
            "Rate each catalyst by timing and impact: "
            "- IMMEDIATE (0-3 days): Highest priority for position entry "
            "- NEAR-TERM (4-10 days): Factor into position planning "
            "- IRRELEVANT (>10 days): Mention only if exceptional "
            ""
            "If no meaningful catalyst exists within 10 days, explicitly state 'NO NEAR-TERM CATALYSTS' and recommend HOLD. "
            "Make sure to append a Markdown table at the end of the report to organize key catalysts by date and expected impact."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
