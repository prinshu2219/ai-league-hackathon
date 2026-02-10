"""
utils/reranker.py
-----------------
Reranks retrieved documents by actual relevance to the query.

WHY RERANKING:
ChromaDB retrieves by vector similarity (fast but imprecise).
Reranking does a second pass — scoring each chunk by how
relevant it ACTUALLY is to the specific claim.

Result: Top chunks are genuinely relevant, not just similar.

We use FlashRank — free, runs locally, no API needed.
Model: ms-marco-MiniLM-L-12-v2 (fast + accurate)
"""

from flashrank import Ranker, RerankRequest
from langchain.schema import Document


# Initialize ranker once (loads model into memory)
# ms-marco is trained specifically for passage relevance scoring
_ranker = None


def get_ranker() -> Ranker:
    """
    Returns the FlashRank ranker instance (singleton).
    Loads the model once and reuses it.
    """
    global _ranker
    if _ranker is None:
        print("⏳ Loading reranker model...")
        _ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2")
        print("✅ Reranker model loaded")
    return _ranker


def rerank_documents(
    query: str,
    documents: list[Document],
    top_k: int = 3
) -> list[Document]:
    """
    Reranks a list of documents by relevance to the query.
    Returns top_k most relevant documents.

    Args:
        query:     The claim or question being verified
        documents: List of LangChain Document objects from ChromaDB
        top_k:     How many top documents to return (default 3)

    Returns:
        Reranked list of Document objects, most relevant first

    Example:
        # Without reranking — returns by vector similarity
        raw_results = search_knowledge_base("Babar ODI ranking", k=6)

        # With reranking — returns by actual relevance
        reranked = rerank_documents("Babar ODI ranking", raw_results, top_k=3)
        # Now chunk 1 is genuinely the most relevant
    """
    if not documents:
        return []

    # FlashRank needs (id, text) pairs
    passages = [
        {"id": i, "text": doc.page_content}
        for i, doc in enumerate(documents)
    ]

    try:
        ranker = get_ranker()

        request = RerankRequest(
            query=query,
            passages=passages
        )

        results = ranker.rerank(request)

        # Sort by relevance score descending
        results_sorted = sorted(
            results,
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        # Return top_k documents in reranked order
        reranked_docs = []
        for result in results_sorted[:top_k]:
            original_doc = documents[result["id"]]
            # Add rerank score to metadata for transparency
            original_doc.metadata["rerank_score"] = round(result.get("score", 0), 4)
            reranked_docs.append(original_doc)

        print(f"✅ Reranked {len(documents)} chunks → kept top {len(reranked_docs)}")
        return reranked_docs

    except Exception as e:
        print(f"⚠️ Reranking failed: {e}. Returning original order.")
        return documents[:top_k]