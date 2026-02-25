"""
tools/research.py — Sprint 3A
───────────────────────────────
Real destination research via Tavily Search API.
Fetches current web content: travel blogs, Reddit posts,
trip reports — then uses GPT-4o to extract structured info.

Falls back to mock data if key missing or call fails.

API docs: https://docs.tavily.com
Free tier: 1,000 searches/month

Key format in .env:
  TAVILY_API_KEY=your_key_here
  USE_REAL_RESEARCH=true
"""

import json
from tavily import TavilyClient
from openai import OpenAI
from app.core.config import config
from app.utils.mock_data import get_mock_destination_info

_tavily_client = None
_openai_client = None


def _tavily() -> TavilyClient:
    global _tavily_client
    if not _tavily_client:
        _tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)
    return _tavily_client


def _openai() -> OpenAI:
    global _openai_client
    if not _openai_client:
        _openai_client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _openai_client


def _search(query: str, max_results: int = 5) -> list[dict]:
    """Run a Tavily search and return list of {title, url, content} dicts."""
    result = _tavily().search(
        query=query,
        search_depth="basic",   # "advanced" uses 2 credits
        max_results=max_results,
        include_answer=False,
    )
    return result.get("results", [])


def _extract_structured_info(destination: str, raw_results: list[dict]) -> dict:
    """
    Use GPT-4o to extract structured destination info from raw search results.
    Returns dict matching mock_data structure so agents need zero changes.
    """
    # Flatten search results into context
    context = "\n\n".join([
        f"SOURCE: {r.get('title','')}\nURL: {r.get('url','')}\nCONTENT:\n{r.get('content','')[:800]}"
        for r in raw_results[:6]
    ])

    system = """You are a travel research assistant. Extract structured destination info from web search results.

Return a JSON object with EXACTLY these fields:
{
  "destination": "city name",
  "overview": "2-3 sentence overview of the destination",
  "best_areas": [
    {"name": "area name", "description": "what it's like", "best_for": ["tag1", "tag2"]}
  ],
  "top_attractions": ["attraction 1", "attraction 2", "attraction 3", "attraction 4", "attraction 5"],
  "local_food_spots": [
    {"name": "place name", "specialty": "what they're known for", "cost": "Rs X-Y"}
  ],
  "cultural_tips": ["tip 1", "tip 2", "tip 3"],
  "safety_notes": ["note 1", "note 2"],
  "best_time_to_visit": "months/season",
  "insider_tips": [
    {"source": "Reddit/Blog/etc", "tip": "actual tip", "upvotes": 0}
  ],
  "activity_tags": ["tag1", "tag2", "tag3"]
}

Rules:
- Extract ONLY from the provided content — don't invent
- Be specific to this destination — real place names, real areas
- insider_tips should be the most useful practical advice from real travelers
- activity_tags should be lowercase single words or short phrases"""

    user = f"""Destination: {destination}

Search results:
{context}

Extract structured destination information:"""

    resp = _openai().chat.completions.create(
        model=config.PRIMARY_MODEL,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return json.loads(resp.choices[0].message.content)


def get_destination_info(destination: str) -> dict:
    """
    Fetch real destination info via Tavily + GPT-4o extraction.
    Returns same structure as get_mock_destination_info().

    Uses 3 Tavily searches:
      1. General destination guide
      2. Reddit travel tips
      3. Best food spots
    """
    if not config.USE_REAL_RESEARCH or not config.TAVILY_API_KEY:
        print(f"   [Research] Using mock data (USE_REAL_RESEARCH=false or key missing)")
        return get_mock_destination_info(destination)

    try:
        print(f"   [Research] Tavily searching for {destination}...")

        from app.agents import _is_indian_city
        suffix = " India" if _is_indian_city(destination) else ""

        results = []
        queries = [
            f"{destination}{suffix} travel guide best things to do attractions 2024",
            f"{destination}{suffix} travel tips reddit hidden gems local advice",
            f"best restaurants local food {destination}{suffix} budget travel",
        ]
        for q in queries:
            try:
                hits = _search(q, max_results=3)
                results.extend(hits)
            except Exception as e:
                print(f"   ⚠️ Search failed for '{q}': {e}")

        if not results:
            raise ValueError("No search results returned")

        # Deduplicate by URL
        seen_urls = set()
        unique    = []
        for r in results:
            if r.get("url") not in seen_urls:
                seen_urls.add(r.get("url"))
                unique.append(r)

        print(f"   [Research] Got {len(unique)} sources, extracting with GPT-4o...")

        info = _extract_structured_info(destination, unique)
        # Ensure destination field is set correctly
        info["destination"] = destination
        info["source"]      = "Tavily + GPT-4o"

        print(f"   ✅ Research: {len(info.get('top_attractions',[]))} attractions, "
              f"{len(info.get('insider_tips',[]))} insider tips")
        return info

    except Exception as e:
        print(f"   ⚠️ Research API failed ({e}) — using mock")
        return get_mock_destination_info(destination)