
import asyncio

import httpx
import pytest

from app.services import embedding_service
from app.services.embedding_service import (
    EmbeddingGenerationError,
    generate_embedding,
)


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


class FakeAsyncClient:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def post(self, url, json):
        return self.response


def test_generate_embedding_success(monkeypatch):
    expected_embedding = [0.1] * 768

    monkeypatch.setattr(
        embedding_service.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(
            FakeResponse({"embeddings": [expected_embedding]})
        ),
    )

    result = asyncio.run(generate_embedding("SupportPilot AI"))

    assert len(result) == 768
    assert all(isinstance(value, float) for value in result)
    assert result == expected_embedding


def test_generate_embedding_rejects_empty_text():
    with pytest.raises(ValueError):
        asyncio.run(generate_embedding("   "))


def test_generate_embedding_rejects_invalid_response(monkeypatch):
    monkeypatch.setattr(
        embedding_service.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(
            FakeResponse({"embeddings": []})
        ),
    )

    with pytest.raises(EmbeddingGenerationError):
        asyncio.run(generate_embedding("SupportPilot AI"))


def test_generate_embedding_rejects_wrong_dimensions(monkeypatch):
    monkeypatch.setattr(
        embedding_service.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(
            FakeResponse({"embeddings": [[0.1] * 512]})
        ),
    )

    with pytest.raises(EmbeddingGenerationError):
        asyncio.run(generate_embedding("SupportPilot AI"))


def test_generate_embedding_handles_connection_error(monkeypatch):
    class FailingAsyncClient:
        async def __aenter__(self):
            raise httpx.ConnectError("Ollama unavailable")

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(
        embedding_service.httpx,
        "AsyncClient",
        lambda **kwargs: FailingAsyncClient(),
    )

    with pytest.raises(EmbeddingGenerationError):
        asyncio.run(generate_embedding("SupportPilot AI"))
