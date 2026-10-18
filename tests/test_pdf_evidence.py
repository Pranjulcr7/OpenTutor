import uuid

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject
from services.ingestion.pdf_evidence import extract_pdf_pages, split_text
from services.parser.pdf import _markdown_to_tree


def sample_pdf(path):
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {
            NameObject("/Font"): DictionaryObject(
                {NameObject("/F1"): writer._add_object(font)}
            )
        }
    )
    stream = DecodedStreamObject()
    stream.set_data(
        b"BT /F1 12 Tf 20 250 Td (Attention uses queries, keys and values to compute weighted outputs.) Tj ET"
    )
    page[NameObject("/Contents")] = writer._add_object(stream)
    writer.add_blank_page(width=300, height=300)
    writer.write(path)


def test_real_pdf_text_and_page_boundaries(tmp_path):
    path = tmp_path / "sample.pdf"
    sample_pdf(path)
    _, text = extract_pdf_pages(str(path))
    nodes = _markdown_to_tree(text, uuid.uuid4(), path.name)
    assert {n.metadata_["page_number"] for n in nodes} == {1, 2}
    assert "Attention uses queries" in nodes[0].content
    assert "sparse_text" in nodes[-1].metadata_["quality_flags"]
    assert nodes[-1].metadata_["visual_review_required"]


def test_unicode_chunks_preserve_all_text():
    text = "中文🙂 special <|endoftext|> values " * 300
    chunks = split_text(text)
    assert "".join(chunks) == text
    assert all("\ufffd" not in part for part in chunks)


def test_encrypted_pdf_is_explicit_error(tmp_path):
    path = tmp_path / "locked.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    writer.encrypt("secret")
    writer.write(path)
    with pytest.raises(ValueError, match="Encrypted"):
        extract_pdf_pages(str(path))
