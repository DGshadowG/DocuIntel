"""Text segmentation into overlapping chunks with page mapping."""
from typing import List, Tuple

from app.core.config import get_settings


def chunk_text(
    text: str,
    page_offsets: List[Tuple[int, int]],
    chunk_size: int = None,
    overlap: int = None,
) -> List[dict]:
    """Split text into overlapping chunks, breaking on paragraph/sentence
    boundaries when possible. Returns dicts with content, index, page, offsets."""
    settings = get_settings()
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap if overlap is not None else settings.CHUNK_OVERLAP

    chunks = []
    start = 0
    index = 0
    length = len(text)
    while start < length:
        end = min(start + chunk_size, length)
        if end < length:
            # Prefer to cut on a paragraph break, then sentence end, then space
            window = text[start:end]
            cut = window.rfind("\n\n")
            if cut < chunk_size // 2:
                cut = max(window.rfind(". "), window.rfind(".\n"))
            if cut < chunk_size // 2:
                cut = window.rfind(" ")
            if cut > chunk_size // 2:
                end = start + cut + 1
        content = text[start:end].strip()
        if content:
            chunks.append(
                {
                    "index": index,
                    "content": content,
                    "start_char": start,
                    "end_char": end,
                    "page_number": _page_for_offset(start, page_offsets),
                }
            )
            index += 1
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def _page_for_offset(offset: int, page_offsets: List[Tuple[int, int]]) -> int:
    page = 1
    for page_number, start_char in page_offsets:
        if offset >= start_char:
            page = page_number
        else:
            break
    return page
