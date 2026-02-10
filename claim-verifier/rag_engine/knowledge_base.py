"""
rag_engine/knowledge_base.py
-----------------------------
Manages the ChromaDB Vector Database.

Responsibilities:
1. Initialize ChromaDB (create or load existing)
2. Add documents to the knowledge base
3. Search/retrieve relevant documents for a query
4. Persist data between sessions

The knowledge base stores:
- Pre-loaded fact-check articles
- News articles
- Wikipedia summaries
- Any documents added via the build script
"""

import os
from typing import Optional
import chromadb
from langchain_community.vectorstores import Chroma
from langchain.schema import Document
from utils.embeddings import get_embedding_model
from utils.chunker import split_documents

# Path where ChromaDB will save its data permanently on disk
CHROMA_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "chroma_db"
)

# Collection name inside ChromaDB
COLLECTION_NAME = "claim_verifier_kb"


def get_vector_store() -> Chroma:
    """
    Returns the ChromaDB vector store instance.
    Creates it if it doesn't exist, loads it if it does.

    Returns:
        Chroma vectorstore instance ready for use

    Example:
        vectorstore = get_vector_store()
        results = vectorstore.similarity_search("some query", k=3)
    """
    embeddings = get_embedding_model()

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_PATH
    )

    print(f"✅ ChromaDB loaded from: {CHROMA_DB_PATH}")
    return vectorstore


def add_documents_to_kb(documents: list[Document]) -> int:
    """
    Adds a list of LangChain Documents to ChromaDB after chunking.

    Args:
        documents: List of LangChain Document objects to add

    Returns:
        Number of chunks actually stored

    Example:
        from langchain.schema import Document
        docs = [Document(page_content="Some news text", metadata={"source": "bbc.com"})]
        count = add_documents_to_kb(docs)
        print(f"Stored {count} chunks")
    """
    if not documents:
        print("⚠️ No documents to add.")
        return 0

    # Split into chunks first
    chunks = split_documents(documents)

    if not chunks:
        print("⚠️ No chunks generated.")
        return 0

    # Get or create the vectorstore
    vectorstore = get_vector_store()

    # Add chunks to ChromaDB
    vectorstore.add_documents(chunks)

    print(f"✅ Added {len(chunks)} chunks to knowledge base")
    return len(chunks)


def search_knowledge_base(query: str, k: int = 4) -> list[Document]:
    """
    Searches ChromaDB for the most relevant documents to a query.
    This is the core retrieval function used by the agent.

    Args:
        query: The search query (claim or question)
        k: Number of top results to return (default 4)

    Returns:
        List of most relevant Document chunks with metadata

    Example:
        results = search_knowledge_base("India banned TikTok", k=3)
        for doc in results:
            print(doc.page_content)
            print(doc.metadata.get("source"))
    """
    vectorstore = get_vector_store()

    # Similarity search finds closest vectors to the query
    results = vectorstore.similarity_search(query, k=k)

    if not results:
        print(f"🔍 No results found in knowledge base for: '{query}'")
    else:
        print(f"✅ Found {len(results)} relevant chunks from knowledge base")

    return results


def get_retriever(k: int = 4):
    """
    Returns a LangChain Retriever object (used in chains).
    Alternative to search_knowledge_base() when using LangChain chains.

    Args:
        k: Number of documents to retrieve

    Returns:
        LangChain BaseRetriever instance
    """
    vectorstore = get_vector_store()
    return vectorstore.as_retriever(
        search_kwargs={"k": k}
    )


def get_kb_stats() -> dict:
    """
    Returns stats about what's in the knowledge base.
    Useful for debugging and UI display.

    Returns:
        Dict with document count info
    """
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
    """
    Clears all documents from the knowledge base.
    Use with caution — this is irreversible!
    """
    try:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        client.delete_collection(COLLECTION_NAME)
        print("🗑️ Knowledge base cleared.")
    except Exception as e:
        print(f"⚠️ Could not clear KB: {e}")
