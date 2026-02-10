"""
utils/embeddings.py
-------------------
Sets up the OpenAI Embedding model.
This converts text → numbers (vectors) for storage in ChromaDB.

Model: text-embedding-3-small
- Fast, cheap, high quality
- Same OpenAI API key works for this
"""

import os
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()


def get_embedding_model():
    """
    Returns the OpenAI embedding model instance.
    
    Usage:
        embeddings = get_embedding_model()
        vector = embeddings.embed_query("some text")
    """
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
