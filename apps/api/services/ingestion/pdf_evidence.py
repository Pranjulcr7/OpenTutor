"""Native PDF text with page provenance and explicit extraction limitations.

No OCR or semantic layout reconstruction is performed. Original PDFs remain
the authority for equations, tables, diagrams and scanned pages.
"""

import json
import re
import uuid
from pathlib import Path

import tiktoken
from pypdf import PdfReader

PREFIX = "<!-- study-pdf-page: "
MARKER = re.compile(r"^<!-- study-pdf-page: (\{[^\n]+\}) -->\n", re.MULTILINE)


def extract_pdf_pages(path: str) -> tuple[str, str]:
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs must be decrypted before upload.")
    if len(reader.pages) > 1000:
        raise ValueError("PDF exceeds the 1000-page extraction limit; split the file.")
    pages = []
    enc = tiktoken.get_encoding("cl100k_base")
    for number, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip().replace(PREFIX, "[source marker] ")
        flags = ["native_text"]
        if len(re.sub(r"\s", "", text)) < 40:
            flags.append("sparse_text")
        resources = page.get("/Resources")
        if resources and resources.get_object().get("/XObject"):
            flags.append("visual_objects")
        meta = {
            "page_number": number,
            "extraction_method": "pypdf_native",
            "quality_flags": flags,
            "page_text_tokens": len(enc.encode(text, disallowed_special=())),
            "visual_review_required": len(flags) > 1,
        }
        if not text:
            text = (
                "[No native text extracted. Inspect the original page; "
                "OCR may be needed.]"
            )
        pages.append(f"{PREFIX}{json.dumps(meta)} -->\n{text}")
    return Path(path).stem, "\n\n".join(pages)


def split_text(text: str, max_tokens: int = 450) -> list[str]:
    """Split on Unicode character boundaries without dropping any text."""
    enc = tiktoken.get_encoding("cl100k_base")
    chunks = []
    while text:
        lo, hi = 1, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if len(enc.encode(text[:mid], disallowed_special=())) <= max_tokens:
                lo = mid
            else:
                hi = mid - 1
        end = lo
        if end < len(text):
            boundary = text.rfind(" ", end // 2, end)
            if boundary > 0:
                end = boundary + 1
        chunks.append(text[:end])
        text = text[end:]
    return chunks


def page_nodes(markdown: str, course_id: uuid.UUID, source_file: str) -> list:
    from models.content import CourseContentTree

    markers = list(MARKER.finditer(markdown))
    nodes = []
    for i, marker in enumerate(markers):
        meta = json.loads(marker.group(1))
        text = markdown[
            marker.end() : markers[i + 1].start()
            if i + 1 < len(markers)
            else len(markdown)
        ].strip()
        for part, chunk in enumerate(split_text(text), 1):
            warning = (
                "[Native PDF text only; inspect original figures/tables/equations.]\n"
            )
            nodes.append(
                CourseContentTree(
                    id=uuid.uuid4(),
                    course_id=course_id,
                    parent_id=None,
                    title=f"{source_file} · page {meta['page_number']} · part {part}",
                    level=0,
                    order_index=len(nodes),
                    content=warning + chunk,
                    source_file=source_file,
                    source_type="pdf",
                    metadata_={**meta, "part": part},
                )
            )
    return nodes
