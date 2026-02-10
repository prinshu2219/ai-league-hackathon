"""
scripts/build_knowledge_base.py
--------------------------------
Run this script ONCE to populate ChromaDB with initial knowledge.

This script:
1. Loads content from trusted fact-check & news websites
2. Chunks the content
3. Creates embeddings
4. Stores everything in ChromaDB

Run with:
    python scripts/build_knowledge_base.py

You can re-run anytime to ADD more sources to the knowledge base.
"""

import sys
import os

# Add project root to path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import WebBaseLoader
from langchain.schema import Document
from rag_engine.knowledge_base import add_documents_to_kb, get_kb_stats
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# TRUSTED SOURCES
# These are reliable fact-check and news sites we pre-load into ChromaDB.
# You can add more URLs here anytime.
# ─────────────────────────────────────────────────────────────────────────────

TRUSTED_SOURCES = [
    # Fact-checking websites
    {
        "url": "https://www.snopes.com/fact-check/",
        "category": "fact-check",
        "name": "Snopes"
    },
    {
        "url": "https://www.factcheck.org/",
        "category": "fact-check",
        "name": "FactCheck.org"
    },
    {
        "url": "https://www.politifact.com/",
        "category": "fact-check",
        "name": "PolitiFact"
    },

    # Wikipedia - General Knowledge
    {
        "url": "https://en.wikipedia.org/wiki/COVID-19_pandemic",
        "category": "encyclopedia",
        "name": "Wikipedia - COVID-19"
    },
    {
        "url": "https://en.wikipedia.org/wiki/Moon_landing",
        "category": "encyclopedia",
        "name": "Wikipedia - Moon Landing"
    },
    {
        "url": "https://en.wikipedia.org/wiki/2024_Indian_general_election",
        "category": "encyclopedia",
        "name": "Wikipedia - 2024 India Election"
    },

    # News sources
    {
        "url": "https://www.bbc.com/news/world",
        "category": "news",
        "name": "BBC News"
    },

    # Sports — Cricket rankings (ICC official)
    {
        "url": "https://www.icc-cricket.com/rankings/mens/player-rankings/odi/batting",
        "category": "sports",
        "name": "ICC ODI Batting Rankings"
    },
    {
        "url": "https://www.icc-cricket.com/rankings/mens/player-rankings/test/batting",
        "category": "sports",
        "name": "ICC Test Batting Rankings"
    },
    {
        "url": "https://www.icc-cricket.com/rankings/mens/player-rankings/t20i/batting",
        "category": "sports",
        "name": "ICC T20I Batting Rankings"
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# STATIC FACTS
# Hard-coded well-known facts that are always useful to have in the KB.
# These act as a reliable baseline and don't require web scraping.
# ─────────────────────────────────────────────────────────────────────────────

STATIC_FACTS = [
    {
        "content": "India banned TikTok and 58 other Chinese apps on June 29, 2020, citing national security and privacy concerns. The Ministry of Electronics and Information Technology (MeitY) issued the ban.",
        "source": "Ministry of Electronics and IT - India",
        "url": "https://meity.gov.in/"
    },
    {
        "content": "Neil Armstrong and Buzz Aldrin became the first humans to land on the Moon on July 20, 1969, during NASA's Apollo 11 mission. This event was broadcast live on television worldwide.",
        "source": "NASA",
        "url": "https://www.nasa.gov/mission/apollo-11/"
    },
    {
        "content": "COVID-19 is caused by the SARS-CoV-2 coronavirus. The World Health Organization (WHO) declared COVID-19 a pandemic on March 11, 2020.",
        "source": "World Health Organization",
        "url": "https://www.who.int/"
    },
    {
        "content": "India surpassed China to become the world's most populous country in 2023, according to United Nations estimates, with a population exceeding 1.4 billion people.",
        "source": "United Nations Population Fund",
        "url": "https://www.unfpa.org/"
    },
    {
        "content": "The Chandrayaan-3 mission successfully landed on the Moon's south pole on August 23, 2023, making India the first country to achieve a soft landing near the lunar south pole.",
        "source": "Indian Space Research Organisation (ISRO)",
        "url": "https://www.isro.gov.in/"
    },
    {
        "content": "Elon Musk acquired Twitter for approximately $44 billion in October 2022 and subsequently rebranded the platform to 'X' in July 2023.",
        "source": "Reuters",
        "url": "https://www.reuters.com/"
    },
    {
        "content": "The 2024 US Presidential election was held on November 5, 2024. Donald Trump won the presidency, defeating Democratic candidate Kamala Harris.",
        "source": "Associated Press",
        "url": "https://apnews.com/"
    },
    {
        "content": "Arvind Kejriwal, Chief Minister of Delhi, was arrested by the Enforcement Directorate (ED) on March 21, 2024, in connection with the Delhi liquor policy case.",
        "source": "The Hindu",
        "url": "https://www.thehindu.com/"
    },
    {
        "content": "Scientific consensus from WHO, CDC, and multiple peer-reviewed studies confirms that COVID-19 vaccines do not cause infertility. The vaccines have been deemed safe and effective.",
        "source": "WHO / CDC",
        "url": "https://www.who.int/news-room/feature-stories/detail/coronavirus-disease-(covid-19)-vaccines"
    },
    {
        "content": "ICC cricket rankings are updated after every match series. The ICC ODI, Test and T20I rankings change frequently. As of early 2025, Babar Azam of Pakistan previously held the top ODI batting ranking but rankings fluctuate. Always check the official ICC website at icc-cricket.com for the most current rankings.",
        "source": "ICC Cricket",
        "url": "https://www.icc-cricket.com/rankings/mens/player-rankings/odi/batting"
    },
    {
        "content": "Climate change and global warming are caused primarily by human activities, particularly the burning of fossil fuels. This is the consensus of over 97% of climate scientists.",
        "source": "NASA Climate",
        "url": "https://climate.nasa.gov/"
    },
]


def load_from_web(sources: list) -> list[Document]:
    """
    Loads content from web URLs using LangChain's WebBaseLoader.

    Args:
        sources: List of source dicts with url, category, name

    Returns:
        List of LangChain Document objects
    """
    all_documents = []

    for source in sources:
        url = source["url"]
        name = source["name"]

        print(f"📥 Loading: {name} ({url})")

        try:
            loader = WebBaseLoader(url)
            docs = loader.load()

            # Add metadata to each document
            for doc in docs:
                doc.metadata["source"] = name
                doc.metadata["url"] = url
                doc.metadata["category"] = source.get("category", "general")

            all_documents.extend(docs)
            print(f"   ✅ Loaded {len(docs)} pages")

        except Exception as e:
            print(f"   ⚠️ Failed to load {name}: {e}")
            continue

    return all_documents


def load_static_facts() -> list[Document]:
    """
    Converts static fact strings into LangChain Document objects.

    Returns:
        List of Document objects from static facts
    """
    documents = []

    for fact in STATIC_FACTS:
        doc = Document(
            page_content=fact["content"],
            metadata={
                "source": fact["source"],
                "url": fact["url"],
                "category": "static_fact"
            }
        )
        documents.append(doc)

    print(f"✅ Loaded {len(documents)} static facts")
    return documents


def build_knowledge_base(include_web: bool = True):
    """
    Main function — builds the complete knowledge base.

    Args:
        include_web: Whether to scrape web sources (True by default)
                     Set to False to only load static facts (faster)
    """
    print("\n" + "="*60)
    print("🏗️  BUILDING KNOWLEDGE BASE")
    print("="*60 + "\n")

    all_documents = []

    # ── Load static facts (always) ───────────────────────────────────
    print("📚 Loading static facts...")
    static_docs = load_static_facts()
    all_documents.extend(static_docs)

    # ── Load web sources (optional) ──────────────────────────────────
    if include_web:
        print("\n🌐 Loading web sources...")
        web_docs = load_from_web(TRUSTED_SOURCES)
        all_documents.extend(web_docs)
    else:
        print("\n⏩ Skipping web sources (include_web=False)")

    # ── Store everything in ChromaDB ─────────────────────────────────
    print(f"\n💾 Storing {len(all_documents)} documents in ChromaDB...")
    chunks_stored = add_documents_to_kb(all_documents)

    # ── Show final stats ─────────────────────────────────────────────
    stats = get_kb_stats()
    print("\n" + "="*60)
    print("✅ KNOWLEDGE BASE BUILT SUCCESSFULLY!")
    print(f"   Total chunks stored: {stats['total_chunks']}")
    print(f"   Location: {stats['path']}")
    print("="*60 + "\n")


if __name__ == "__main__":
    # Run with web sources by default
    # Pass --no-web flag to skip web scraping (faster, for testing)
    import argparse

    parser = argparse.ArgumentParser(description="Build the claim verifier knowledge base")
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Skip web scraping, only load static facts (faster)"
    )
    args = parser.parse_args()

    build_knowledge_base(include_web=not args.no_web)