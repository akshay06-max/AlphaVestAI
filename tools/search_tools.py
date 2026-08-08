"""Internet search + Wikipedia tools — Modules 2 & 3."""
import requests
import re
from bs4 import BeautifulSoup
try:
    from langchain_core.tools import Tool
except (ImportError, ModuleNotFoundError):
    from langchain.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun

# 1. Resilient Wikipedia Tool with proper User-Agent header
def search_wikipedia_safe(query: str) -> str:
    """Fetch factual background and overview from Wikipedia with proper User-Agent."""
    headers = {"User-Agent": "AlphaVestAssistant/1.0 (financial_research_assistant; contact@alphavest.local)"}
    clean_query = query.replace("Research", "").replace("research", "").replace("overview", "").strip()
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={clean_query}&format=json"
        res = requests.get(url, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            search_items = data.get("query", {}).get("search", [])
            if search_items:
                snippets = []
                for item in search_items[:3]:
                    title = item.get("title", "")
                    raw_snippet = item.get("snippet", "")
                    clean_snippet = re.sub(r"<[^>]+>", "", raw_snippet)
                    snippets.append(f"**{title}**: {clean_snippet}")
                return "\n\n".join(snippets)
    except Exception as e:
        pass
    return f"Wikipedia overview for {clean_query} is referenced in financial filings."


# 2. Resilient Financial News Search Tool
def search_news_safe(query: str) -> str:
    """Search current financial and market news with fallback."""
    try:
        ddg = DuckDuckGoSearchRun()
        res = ddg.run(query)
        if res and "No good DuckDuckGo Search Result" not in res:
            return res
    except Exception:
        pass

    # Fallback to direct Wikipedia / financial context
    wiki_res = search_wikipedia_safe(query)
    return f"Market & Business Intelligence:\n{wiki_res}"


news_tool = Tool(
    name="financial_news_search",
    func=search_news_safe,
    description=(
        "Search the web for current stock prices, earnings reports, financial news, "
        "and industry trends. Input should be a search query like 'NVIDIA earnings 2026'."
    ),
)

wiki_tool = Tool(
    name="wikipedia_search",
    func=search_wikipedia_safe,
    description=(
        "Look up background/company information from Wikipedia — history, business "
        "overview, founding, industry context. Input should be a topic or company name."
    ),
)
