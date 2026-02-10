"""
rag_engine/tools.py
--------------------
Defines the tools available to the LangChain ReAct Agent.

The agent can CHOOSE which tool to use based on the situation.

Tools:
1. search_knowledge_base → Searches ChromaDB (stored facts)
2. search_web            → Searches live web via Tavily
"""

import os
from langchain.tools import Tool
from tavily import TavilyClient
from dotenv import load_dotenv
from rag_engine.knowledge_base import search_knowledge_base as kb_search

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1: Knowledge Base Search
# Searches our pre-built ChromaDB for stored facts
# ─────────────────────────────────────────────────────────────────────────────

def _search_knowledge_base_tool(query: str) -> str:
    """
    Internal function that searches ChromaDB and returns
    results as a formatted string for the agent to read.
    """
    results = kb_search(query, k=4)

    if not results:
        return "No relevant information found in the knowledge base."

    # Format results as readable text for the agent
    formatted = []
    for i, doc in enumerate(results, 1):
        source = doc.metadata.get("source", "Unknown source")
        url = doc.metadata.get("url", "")
        content = doc.page_content.strip()

        entry = f"[Result {i}]\n"
        entry += f"Source: {source}\n"
        if url:
            entry += f"URL: {url}\n"
        entry += f"Content: {content}\n"
        formatted.append(entry)

    return "\n---\n".join(formatted)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 2: Web Search
# Searches live web via Tavily for current news
# ─────────────────────────────────────────────────────────────────────────────

def _search_web_tool(query: str) -> str:
    """
    Internal function that searches the live web via Tavily
    and returns formatted results for the agent.
    """
    try:
        tavily_key = os.getenv("TAVILY_API_KEY")

        if not tavily_key:
            return "Web search unavailable: TAVILY_API_KEY not set."

        client = TavilyClient(api_key=tavily_key)

        # Search with focus on news and factual content
        response = client.search(
            query=query,
            search_depth="advanced",   # deeper search
            max_results=5,
            include_answer=True,       # Tavily's own AI summary
            include_raw_content=False  # just snippets, not full pages
        )

        if not response or "results" not in response:
            return "No web results found."

        formatted = []

        # Include Tavily's own answer summary if available
        if response.get("answer"):
            formatted.append(f"[Web Summary]\n{response['answer']}\n")

        # Include individual search results
        for i, result in enumerate(response["results"], 1):
            entry = f"[Web Result {i}]\n"
            entry += f"Title: {result.get('title', 'No title')}\n"
            entry += f"URL: {result.get('url', '')}\n"
            entry += f"Content: {result.get('content', 'No content')}\n"
            formatted.append(entry)

        return "\n---\n".join(formatted)

    except Exception as e:
        return f"Web search error: {str(e)}"


# ─────────────────────────────────────────────────────────────────────────────
# LANGCHAIN TOOL WRAPPERS
# Wraps the above functions into LangChain Tool objects the agent can use
# ─────────────────────────────────────────────────────────────────────────────

knowledge_base_tool = Tool(
    name="search_knowledge_base",
    func=_search_knowledge_base_tool,
    description=(
        "Search the local knowledge base of stored fact-check articles, "
        "news archives, and Wikipedia summaries. "
        "Use this FIRST before searching the web. "
        "Input should be a clear search query related to the claim."
    )
)

web_search_tool = Tool(
    name="search_web",
    func=_search_web_tool,
    description=(
        "Search the live web for current news articles and recent information. "
        "Use this when the knowledge base doesn't have enough information, "
        "or when you need the latest news. "
        "Input should be a clear search query related to the claim."
    )
)


def get_agent_tools() -> list:
    """
    Returns the list of tools available to the agent.

    Returns:
        List of LangChain Tool objects

    Example:
        tools = get_agent_tools()
        agent = create_react_agent(llm, tools, prompt)
    """
    return [knowledge_base_tool, web_search_tool]
