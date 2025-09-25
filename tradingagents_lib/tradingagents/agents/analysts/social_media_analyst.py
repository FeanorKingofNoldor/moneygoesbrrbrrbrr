from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


def create_social_media_analyst(llm, toolkit):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        if toolkit.config["online_tools"]:
            tools = [toolkit.get_stock_news_openai]
        else:
            tools = [
                toolkit.get_reddit_stock_info,
            ]

        system_message = (
            "You are a social media analyst tasked with gauging retail and institutional sentiment FOR 3-10 DAY POSITION TRADES. "
            "Please write a comprehensive report that analyzes recent social media activity including momentum shifts that could impact price within 10 days. "
            ""
            "Focus on: "
            "- Volume of mentions: Compare last 48 hours to 30-day average "
            "- Momentum acceleration: Is buzz building or fading? "
            "- Quality of discussion: Technical breakout talk vs meme hype "
            "- Institutional flow indicators: UnusualWhales, FlowAlgo alerts "
            "- WSB/FinTwit sentiment: Bullish/bearish ratio and change rate "
            "- Smart money signals: Large option sweeps, dark pool prints "
            ""
            "Rate sentiment momentum for position trading: "
            "- ACCELERATING BULLISH: Momentum building, good for 3-5 day momentum trades "
            "- STEADY BULLISH: Sustained interest but not explosive "
            "- TURNING BEARISH: Sentiment shifting, consider exits "
            "- CAPITULATION: Extreme bearish, potential reversal setup "
            ""
            "Ignore: "
            "- Fundamental debates about long-term value "
            "- Political discussions unless directly affecting near-term price "
            "- Bot activity and obvious pump attempts "
            ""
            "Make sure to include specific metrics (mention %, volume changes) and assess whether social momentum aligns with technical setup. "
            "Do not simply state the trends are mixed, provide detailed and finegrained analysis and insights that may help traders make decisions. "
            "Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
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
                    "For your reference, the current date is {current_date}. The current company we want to analyze is {ticker}",
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
            "sentiment_report": report,
        }

    return social_media_analyst_node
