"""Company Research Agent — Module 3 (combines news + Wikipedia + financial tools)."""
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate

from config import llm
from tools.search_tools import news_tool, wiki_tool
from tools.financial_tools import financial_tools

tools = [news_tool, wiki_tool] + financial_tools

_REACT_PROMPT = PromptTemplate.from_template("""
You are a financial research analyst at AlphaVest Capital.
Use the available tools to gather current, factual information before answering.
When researching a company, aim to cover: business overview, products, competitors,
revenue sources, and recent announcements. Use financial tools whenever the user
asks for a calculation (CAGR, growth %, ROI, comparison table).

You have access to the following tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
{agent_scratchpad}
""")

_agent = create_react_agent(llm, tools, _REACT_PROMPT)

research_executor = AgentExecutor(
    agent=_agent,
    tools=tools,
    verbose=False,
    handle_parsing_errors=True,
    max_iterations=6,
)


def research_company(query: str) -> str:
    """Run the research agent on a single query/company and return plain text output."""
    try:
        result = research_executor.invoke({"input": query})
        return result.get("output", "")
    except Exception as e:
        # Fallback to direct search and LLM synthesis if ReAct loop fails
        try:
            search_context = news_tool.run(query)
            wiki_context = wiki_tool.run(query)
            fallback_prompt = (
                f"You are a financial research analyst at AlphaVest Capital. "
                f"Analyze this query: '{query}'\n\n"
                f"Search Results:\n{search_context}\n\n"
                f"Wikipedia Context:\n{wiki_context}\n\n"
                f"Provide a comprehensive, factual research report covering business overview, "
                f"products, competitors, revenue sources, and recent developments."
            )
            response = llm.invoke(fallback_prompt)
            return response.content if hasattr(response, "content") else str(response)
        except Exception as inner_e:
            return f"Error conducting research for '{query}': {inner_e}"
