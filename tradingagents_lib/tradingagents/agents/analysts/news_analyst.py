from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


def create_news_analyst(llm, toolkit):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        if toolkit.config["online_tools"]:
            tools = [toolkit.get_global_news_openai, toolkit.get_google_news]
        else:
            tools = [
                toolkit.get_finnhub_news,
                toolkit.get_reddit_news,
                toolkit.get_google_news,
            ]

        system_message = (
            "You are a news analyst tasked with finding news catalysts relevant to 3-10 DAY POSITION TRADES. "
            "Please write a comprehensive report with focus on price-moving events within the trading window. "
            ""
            "Prioritize news by immediate impact: "
            "- BREAKING (<24 hours old): Earnings surprises, FDA decisions, major contracts "
            "- DEVELOPING (24-48 hours): Analyst changes, guidance updates, sector moves "
            "- UPCOMING (next 10 days): Scheduled events, expected announcements "
            "- BACKGROUND (>48 hours): Only if still actively moving price "
            ""
            "Focus on: "
            "- Surprise elements vs expectations "
            "- Magnitude of guidance changes "
            "- Sector-wide implications affecting the stock "
            "- Regulatory or legal developments with near-term resolution "
            "- Major customer/partnership news "
            ""
            "Rate each news item: "
            "- HIGH IMPACT: Will likely move stock >3% "
            "- MEDIUM IMPACT: Could move stock 1-3% "
            "- LOW IMPACT: Minimal price effect expected "
            "- PRICED IN: Market already adjusted "
            ""
            "Exclude: "
            "- General market commentary "
            "- Long-term strategic plans beyond 2 weeks "
            "- Routine corporate updates "
            ""
            "Focus on actionable intelligence for position traders. Each news item should include expected price impact and timeline. "
            "Make sure to append a Markdown table at the end of the report to organize news by impact level and timing."
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
                    "For your reference, the current date is {current_date}. We are looking at the company {ticker}",
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
            "news_report": report,
        }

    return news_analyst_node
