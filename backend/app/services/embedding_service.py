import httpx


EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIMENSIONS = 768
OLLAMA_BASE_URL = "http://localhost:11434"


class EmbeddingGenerationError(Exception):
    """Raised when an embedding cannot be generated."""


async def generate_embedding(text: str) -> list[float]:
    """Generate a vector embedding for the supplied text using Ollama."""

    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    payload = {
        "model": EMBEDDING_MODEL,
        "input": text,
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json=payload,
            )
            response.raise_for_status()

        data = response.json()
        embeddings = data.get("embeddings")

        if not embeddings or len(embeddings) != 1:
            raise EmbeddingGenerationError(
                "Ollama returned an invalid embedding response"
            )

        embedding = embeddings[0]

        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise EmbeddingGenerationError(
                f"Expected {EMBEDDING_DIMENSIONS} dimensions, "
                f"received {len(embedding)}"
            )

        return [float(value) for value in embedding]

    except httpx.HTTPError as exc:
        raise EmbeddingGenerationError(
            "Could not communicate with Ollama"
        ) from exc
