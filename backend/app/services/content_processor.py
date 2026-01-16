import io
import hashlib
from typing import Optional
from pypdf import PdfReader
from bs4 import BeautifulSoup

from app.services.vector_store import add_documents_to_collection


async def process_pdf(file_content: bytes, resolution_id: int) -> dict:
    pdf_reader = PdfReader(io.BytesIO(file_content))
    
    full_text = ""
    chunks = []
    
    for page_num, page in enumerate(pdf_reader.pages):
        page_text = page.extract_text() or ""
        full_text += page_text + "\n"
        
        if page_text.strip():
            chunks.append({
                "text": page_text,
                "page": page_num + 1,
                "source": "pdf",
            })
    
    await _store_chunks(resolution_id, chunks)
    
    return {
        "total_pages": len(pdf_reader.pages),
        "total_chunks": len(chunks),
        "total_characters": len(full_text),
    }


async def process_epub(file_content: bytes, resolution_id: int) -> dict:
    try:
        import ebooklib
        from ebooklib import epub
        
        book = epub.read_epub(io.BytesIO(file_content))
        
        full_text = ""
        chunks = []
        chapter_num = 0
        
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                chapter_text = soup.get_text(separator="\n", strip=True)
                
                if chapter_text.strip():
                    chapter_num += 1
                    full_text += chapter_text + "\n"
                    
                    chapter_chunks = _split_text_into_chunks(chapter_text, 1000)
                    for i, chunk in enumerate(chapter_chunks):
                        chunks.append({
                            "text": chunk,
                            "chapter": chapter_num,
                            "chunk_index": i,
                            "source": "epub",
                        })
        
        await _store_chunks(resolution_id, chunks)
        
        return {
            "total_chapters": chapter_num,
            "total_chunks": len(chunks),
            "total_characters": len(full_text),
        }
    except ImportError:
        return {"error": "EPUB support not available"}


async def process_text(text_content: str, resolution_id: int, source: str = "text") -> dict:
    chunks = _split_text_into_chunks(text_content, 1000)
    
    chunk_data = []
    for i, chunk in enumerate(chunks):
        chunk_data.append({
            "text": chunk,
            "chunk_index": i,
            "source": source,
        })
    
    await _store_chunks(resolution_id, chunk_data)
    
    return {
        "total_chunks": len(chunks),
        "total_characters": len(text_content),
    }


def _split_text_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        if end < len(text):
            last_period = text.rfind(".", start, end)
            last_newline = text.rfind("\n", start, end)
            break_point = max(last_period, last_newline)
            
            if break_point > start:
                end = break_point + 1
        
        chunks.append(text[start:end].strip())
        start = end - overlap
    
    return [c for c in chunks if c]


async def _store_chunks(resolution_id: int, chunks: list[dict]) -> None:
    if not chunks:
        return
    
    documents = []
    metadatas = []
    ids = []
    
    for i, chunk in enumerate(chunks):
        text = chunk.pop("text")
        doc_id = hashlib.md5(f"{resolution_id}_{i}_{text[:50]}".encode()).hexdigest()
        
        documents.append(text)
        metadatas.append(chunk)
        ids.append(doc_id)
    
    await add_documents_to_collection(resolution_id, documents, metadatas, ids)


def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    word_count = len(text.split())
    return max(1, round(word_count / words_per_minute))


def get_approximate_pages(text: str, words_per_page: int = 250) -> int:
    word_count = len(text.split())
    return max(1, round(word_count / words_per_page))
