from __future__ import annotations

from pathlib import Path


def load_textbook_file(path: str) -> str:
    """
    Load a plain-text textbook file from disk.

    Why plain text first:
    - It keeps ingestion beginner-friendly for an MVP.
    - It proves the end-to-end flow (ingest -> embed -> retrieve -> cite) without
      needing PDF parsing or OCR yet.

    Later upgrade path:
    - Replace this with a PDF extraction pipeline that produces the same structured
      plain text (or directly produces docs). Keeping the output schema stable
      makes upgrades safe.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Textbook file not found: {p}")

    # UTF-8 is the safest default for modern text. Use errors="replace" so the
    # system keeps running even if there are a few bad characters.
    return p.read_text(encoding="utf-8", errors="replace")


def parse_textbook(raw_text: str) -> list[dict]:
    """
    Parse a simple structured plain-text textbook into documents.

    Format rules (MVP):
    - Lines starting with "Chapter:" set the current chapter
    - Lines starting with "Page:" set the current page number
    - Following non-empty lines are content lines for that chapter/page
      until the next Chapter/Page block

    Why chapter/page metadata matters:
    - We keep citations stable and explainable for students and teachers.
    - When we later add real PDFs, these map back to actual page ranges.
    """
    docs: list[dict] = []

    chapter: str | None = None
    page: int | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if chapter and page is not None and buffer:
            docs.append(
                {
                    "text": " ".join(buffer).strip(),
                    "chapter": chapter,
                    "page": page,
                }
            )
        buffer = []

    for raw_line in (raw_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.lower().startswith("chapter:"):
            flush()
            chapter = line.split(":", 1)[1].strip() or None
            continue

        if line.lower().startswith("page:"):
            flush()
            page_str = line.split(":", 1)[1].strip()
            try:
                page = int(page_str)
            except ValueError:
                page = None
            continue

        # Content line
        buffer.append(line)

    flush()
    return docs


def parse_textbook_text(text: str) -> list[dict]:
    """
    Backward-compatible alias.
    Prefer `parse_textbook()` going forward.
    """
    return parse_textbook(text)

