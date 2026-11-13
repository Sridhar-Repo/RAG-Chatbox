from app.ingest import chunk_text


def test_short_text_is_one_chunk():
    assert chunk_text("Hello world.", size=100, overlap=10) == ["Hello world."]


def test_paragraphs_are_packed_not_split():
    text = "\n\n".join(["a" * 40, "b" * 40, "c" * 40])
    chunks = chunk_text(text, size=100, overlap=10)
    assert len(chunks) == 2
    assert chunks[0].startswith("a") and "b" * 40 in chunks[0]


def test_long_paragraph_is_hard_split_with_overlap():
    chunks = chunk_text("x" * 250, size=100, overlap=20)
    assert all(len(c) <= 100 for c in chunks)
    assert len(chunks) >= 3


def test_empty_text():
    assert chunk_text("   \n\n  ") == []
