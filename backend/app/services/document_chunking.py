from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentTextChunk:
    content: str
    chunk_index: int
    start_char: int
    end_char: int


def chunk_document_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[DocumentTextChunk]:

    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than zero")

    if overlap < 0:
        raise ValueError("Overlap cannot be negative")

    if overlap >= chunk_size:
        raise ValueError("Overlap must be smaller than chunk size")

    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            # Prefer a paragraph boundary.
            boundary = text.rfind("\n\n", start, end)

            # If no paragraph boundary exists, try a sentence boundary.
            if boundary == -1:
                boundary = text.rfind(". ", start, end)

                if boundary != -1:
                    boundary += 1

            # If neither exists, try a word boundary.
            if boundary == -1:
                boundary = text.rfind(" ", start, end)

            # Avoid creating very small chunks from early boundaries.
            minimum_boundary = start + chunk_size // 2

            if boundary >= minimum_boundary:
                end = boundary

        content = text[start:end].strip()

        if content:
            chunks.append(
                DocumentTextChunk(
                    content=content,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end,
                )
            )
            chunk_index += 1

        if end >= len(text):
            break

        next_start = end - overlap

        if next_start <= start:
            raise ValueError("Chunking failed to make progress")

        start = next_start

    return chunks