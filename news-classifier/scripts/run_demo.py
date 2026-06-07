#!/usr/bin/env python3
"""
Demo script — classify sample articles.
Requires OPENAI_API_KEY in .env (ANTHROPIC_API_KEY optional for fallback demo).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.secrets import load_secrets
from app.config import config
from app.rate_limiter import rate_limiter
from app.llm.classifier import classify_news

SAMPLES = [
    ("India wins cricket series", "The team scored 350 runs in the final test match at Melbourne."),
    ("OpenAI launches GPT-4o-mini", "The AI startup released a faster, cheaper model for developers."),
    ("Election results announced", "The ruling party secured 290 seats in parliament."),
    ("Stock market hits record", "Nifty 50 crossed 25000 as IT stocks rallied on earnings."),
]


def main():
    load_secrets()
    missing = config.validate()
    if missing:
        print(f"❌ Missing keys: {missing}")
        print("Copy .env.example to .env and add your keys.")
        sys.exit(1)

    print("=" * 60)
    print("NEWS CLASSIFIER DEMO")
    print(f"Primary: {config.PRIMARY_MODEL} | Fallback: {config.FALLBACK_MODEL}")
    print("=" * 60)

    for headline, body in SAMPLES:
        allowed, remaining = rate_limiter.check("demo-user", "free")
        if not allowed:
            print("\n⚠️  Rate limit hit — demo stopped")
            break

        print(f"\n📰 {headline}")
        try:
            resp = classify_news(headline, body, use_chain=True)
            r = resp.result
            print(f"   → {r.category.upper()} ({r.confidence:.0%}) via {r.provider}/{r.method}")
            print(f"   → {r.summary}")
            if resp.article_compacted:
                print("   ⚠️  Article was compacted for context window")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("Done. Extraction paths:")
    print("  OpenAI:    response.choices[0].message.content")
    print("  Anthropic: message.content[0].text")
    print("  LangChain: result.content (internal)")


if __name__ == "__main__":
    main()
