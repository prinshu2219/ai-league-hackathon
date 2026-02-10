"""
utils/chunker.py
----------------
Handles splitting large documents into smaller chunks
before storing in ChromaDB.

Why we chunk:
- One article covers many topics → embedding would be confused
- Smaller chunks = more precise retrieval
- Overlap ensures context isn't lost at boundaries

Strategy: RecursiveCharacterTextSplitter
- Tries to split on paragraphs first
- Then sentences, then words
- Keeps chunks as meaningful as possible
"""

from langchain.text_splitter import RecursiveCharacterTextSplitter


def get_text_splitter(chunk_size: int = 500, chunk_overlap: int = 50):
    """
    Returns a text splitter configured for news articles.

    Args:
        chunk_size: Max characters per chunk (default 500)
        chunk_overlap: Overlap between chunks (default 50)
                       Prevents losing context at boundaries

    Example:
        splitter = get_text_splitter()
        chunks = splitter.split_documents(documents)
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # Try splitting on these characters in order:
        # paragraph → sentence → word → character
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len
    )


def split_documents(documents, chunk_size: int = 500, chunk_overlap: int = 50):
    """
    Convenience function: splits a list of documents into chunks.

    Args:
        documents: List of LangChain Document objects
        chunk_size: Max characters per chunk
        chunk_overlap: Characters of overlap between chunks

    Returns:
        List of chunked Document objects with metadata preserved

    Example:
        chunks = split_documents(loaded_docs)
        print(f"Split {len(documents)} docs into {len(chunks)} chunks")
    """
    splitter = get_text_splitter(chunk_size, chunk_overlap)
    chunks = splitter.split_documents(documents)
    print(f"✅ Split {len(documents)} documents → {len(chunks)} chunks")
    return chunks
