import os
import uuid
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-small"
)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "hybrid-kb")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

KB_DIR = Path("data/kb_docs")

openai_client = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> List[str]:
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


def get_embedding(text: str) -> List[float]:
    response = openai_client.embeddings.create(
        model=OPENAI_EMBEDDING_MODEL,
        input=text
    )

    return response.data[0].embedding


def ensure_index():
    existing_indexes = [idx.name for idx in pc.list_indexes()]

    if PINECONE_INDEX_NAME not in existing_indexes:
        print(f"Creating Pinecone index: {PINECONE_INDEX_NAME}")

        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=PINECONE_CLOUD,
                region=PINECONE_REGION
            )
        )


def ingest():
    ensure_index()

    index = pc.Index(PINECONE_INDEX_NAME)

    vectors = []

    for file_path in KB_DIR.glob("**/*"):
        if file_path.suffix.lower() not in [".txt", ".md"]:
            continue

        text = file_path.read_text(encoding="utf-8")
        chunks = chunk_text(text)

        for chunk_index, chunk in enumerate(chunks):
            embedding = get_embedding(chunk)

            vectors.append(
                {
                    "id": str(uuid.uuid4()),
                    "values": embedding,
                    "metadata": {
                        "source": str(file_path),
                        "title": file_path.stem,
                        "chunk_index": chunk_index,
                        "text": chunk
                    }
                }
            )

    batch_size = 100

    for i in range(0, len(vectors), batch_size):
        batch = vectors[i:i + batch_size]
        index.upsert(vectors=batch)
        print(f"Uploaded {i + len(batch)} / {len(vectors)}")

    print("KB ingestion completed successfully.")


if __name__ == "__main__":
    ingest()
