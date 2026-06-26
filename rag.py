from typing import List, Dict, Any
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from loguru import logger

from config import Config

openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
pc = Pinecone(api_key=Config.PINECONE_API_KEY)


def get_embedding(text: str) -> List[float]:
    response = openai_client.embeddings.create(
        model=Config.OPENAI_EMBEDDING_MODEL,
        input=text
    )
    return response.data[0].embedding


def ensure_index():
    existing_indexes = [idx.name for idx in pc.list_indexes()]

    if Config.PINECONE_INDEX_NAME not in existing_indexes:
        logger.info(f"Creating Pinecone index: {Config.PINECONE_INDEX_NAME}")

        pc.create_index(
            name=Config.PINECONE_INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=Config.PINECONE_CLOUD,
                region=Config.PINECONE_REGION
            )
        )


def search_kb(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    ensure_index()

    index = pc.Index(Config.PINECONE_INDEX_NAME)

    query_vector = get_embedding(query)

    results = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )

    docs = []

    for match in results.matches:
        metadata = match.metadata or {}

        docs.append(
            {
                "score": match.score,
                "source": metadata.get("source"),
                "title": metadata.get("title"),
                "text": metadata.get("text")
            }
        )

    return docs
