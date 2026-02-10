"""
rag_engine/knowledge_base.py
-----------------------------
Manages the ChromaDB Vector Database.

Responsibilities:
1. Initialize ChromaDB (create or load existing)
2. Add documents to the knowledge base
3. Search/retrieve relevant documents for a query (with reranking)
4. Persist data between sessions
"""

import os
import chromadb
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from utils.embeddings import get_embedding_model
from utils.chunker import split_documents

# Path where ChromaDB saves data permanently
CHROMA_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "chroma_db"
)

COLLECTION_NAME = "claim_verifier_kb"


def get_vector_store() -> Chroma:
    embeddings = get_embedding_model()
    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_PATH
    )
    print(f"✅ ChromaDB loaded from: {CHROMA_DB_PATH}")
    return vectorstore


def add_documents_to_kb(documents: list) -> int:
    if not documents:
        print("⚠️ No documents to add.")
        return 0

    chunks = split_documents(documents)
    if not chunks:
        print("⚠️ No chunks generated.")
        return 0

    vectorstore = get_vector_store()
    vectorstore.add_documents(chunks)
    print(f"✅ Added {len(chunks)} chunks to knowledge base")
    return len(chunks)


def search_knowledge_base(query: str, k: int = 3) -> list:
    """
    Searches ChromaDB with reranking for better accuracy.

    Flow:
      1. Fetch k*3 candidates from ChromaDB (wider net)
      2. Rerank by actual relevance to query
      3. Return top k results

    Args:
        query: The claim or search query
        k: Number of results to return after reranking

    Returns:
        Reranked list of most relevant Document chunks
    """
    from utils.reranker import rerank_documents

    vectorstore = get_vector_store()

    # Fetch more candidates than needed for reranker to work with
    fetch_k = min(k * 3, 12)
    raw_results = vectorstore.similarity_search(query, k=fetch_k)

    if not raw_results:
        print(f"🔍 No results found in KB for: '{query}'")
        return []

    print(f"📥 Fetched {len(raw_results)} candidates from ChromaDB")

    # Rerank by actual relevance
    reranked = rerank_documents(query, raw_results, top_k=k)
    print(f"✅ Reranked → returning top {len(reranked)} chunks")
    return reranked


def get_retriever(k: int = 3):
    vectorstore = get_vector_store()
    return vectorstore.as_retriever(search_kwargs={"k": k})


def get_kb_stats() -> dict:
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        collection = client.get_collection(COLLECTION_NAME)
        count = collection.count()
        return {
            "total_chunks": count,
            "collection": COLLECTION_NAME,
            "path": CHROMA_DB_PATH
        }
    except Exception:
        return {
            "total_chunks": 0,
            "collection": COLLECTION_NAME,
            "path": CHROMA_DB_PATH
        }


def clear_knowledge_base():
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        client.delete_collection(COLLECTION_NAME)
        print("🗑️ Knowledge base cleared.")
    except Exception as e:
        print(f"⚠️ Could not clear KB: {e}")