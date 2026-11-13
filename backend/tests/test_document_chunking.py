import pytest

from app.services.document_chunking import chunk_document_text


def test_chunk_short_document():
    text = "This is a short document."

    chunks = chunk_document_text(text)

    assert len(chunks) == 1
    assert chunks[0].content == text
    assert chunks[0].chunk_index == 0
    assert chunks[0].start_char == 0
    assert chunks[0].end_char == len(text)


def test_chunk_long_document_with_overlap():
    text = "a" * 2500

    chunks = chunk_document_text(
        text,
        chunk_size=1000,
        overlap=150,
    )

    assert len(chunks) == 3

    assert chunks[0].start_char == 0
    assert chunks[1].start_char == 850
    assert chunks[2].start_char == 1700

    assert chunks[0].content == "a" * 1000
    assert chunks[1].content == "a" * 1000
    assert chunks[2].content == "a" * 800


def test_chunk_indexes_are_sequential():
    text = "a" * 2500

    chunks = chunk_document_text(text)

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]


def test_chunk_prefers_paragraph_boundary():
    text = "a" * 600 + "\n\n" + "b" * 600

    chunks = chunk_document_text(
        text,
        chunk_size=1000,
        overlap=150,
    )

    assert len(chunks) == 2
    assert chunks[0].content == "a" * 600
    assert chunks[1].start_char == 450
    assert chunks[1].content.startswith("a" * 150 + "\n\n")


def test_empty_document_returns_no_chunks():
    assert chunk_document_text("") == []
    assert chunk_document_text("   \n  ") == []


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [
        (0, 0),
        (-1, 0),
        (100, -1),
        (100, 100),
        (100, 150),
    ],
)
def test_invalid_chunk_configuration(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_document_text(
            "Some document content",
            chunk_size=chunk_size,
            overlap=overlap,
        )