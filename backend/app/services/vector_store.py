import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import Optional

from app.config import get_settings

settings = get_settings()

_chroma_client: Optional[chromadb.ClientAPI] = None


def get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        persist_dir = settings.chroma_persist_directory
        os.makedirs(persist_dir, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _chroma_client


def get_or_create_collection(resolution_id: int) -> chromadb.Collection:
    client = get_chroma_client()
    collection_name = f"resolution_{resolution_id}"
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


async def add_documents_to_collection(
    resolution_id: int,
    documents: list[str],
    metadatas: list[dict],
    ids: list[str],
) -> None:
    collection = get_or_create_collection(resolution_id)
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids,
    )


async def query_collection(
    resolution_id: int,
    query_text: str,
    n_results: int = 5,
) -> dict:
    collection = get_or_create_collection(resolution_id)
    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
    )
    return results


async def delete_collection(resolution_id: int) -> None:
    client = get_chroma_client()
    collection_name = f"resolution_{resolution_id}"
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
