"""
utils/web_result_parser.py
---------------------------
Parses the formatted string returned by the search_web tool (Tavily)
into a list of structured results for harvesting into the knowledge base.

Format: blocks like [Web Result i] or [Web Summary] separated by \\n---\\n.
Only [Web Result i] blocks are returned (they have URL); [Web Summary] is skipped.
"""

import re


def parse_web_observation(observation: str) -> list[dict]:
    """
    Parse a web search observation string into a list of result dicts.

    Input format (from tools._search_web_tool):
        [Web Summary]\\n...\\n\\n---\\n[Web Result 1]\\nTitle: ...\\nURL: ...\\nContent: ...\\n---\\n...

    Output: list of {"title": str, "url": str, "content": str}.
    Skips blocks without URL (e.g. Web Summary). Empty URL => skip.
    """
    if not observation or not observation.strip():
        return []

    results = []
    blocks = observation.split("\n---\n")

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Skip [Web Summary] (no URL to store)
        if block.startswith("[Web Summary]"):
            continue
        # Parse [Web Result i]\nTitle: ...\nURL: ...\nContent: ...
        if not block.startswith("[Web Result"):
            continue

        title = ""
        url = ""
        content = ""

        lines = block.split("\n")
        for line in lines:
            if line.startswith("Title:"):
                title = line[6:].strip()
            elif line.startswith("URL:"):
                url = line[4:].strip()
            elif line.startswith("Content:"):
                content = line[8:].strip()

        if not url:
            continue

        results.append({
            "title": title or "Unknown",
            "url": url,
            "content": content or "",
        })

    return results
