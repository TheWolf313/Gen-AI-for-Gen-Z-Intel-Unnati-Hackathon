from __future__ import annotations

import json
from pathlib import Path

"""
Plain-text ingestion (MVP).

Goal:
- Convert a raw, easy-to-edit textbook text file into the structured JSON dataset
  used by the app's vector store loader.

Why this exists:
- Beginner-friendly first step before PDF parsing/OCR.
- Keeps ingestion separate from retrieval so the /chat API stays stable while the
  ingestion pipeline evolves.

Raw format (data/raw/demo_textbook.txt):
Each entry is a block separated by blank lines. Example:

Chapter: Plant Biology
Topic: Photosynthesis
Page: 12
Text: Photosynthesis is how green plants make food using sunlight, carbon dioxide, and water.

Notes:
- "Text:" can be multi-line; subsequent lines are appended until the next blank line
  (or until another field line starts).
"""


REQUIRED_FIELDS = ("chapter", "topic", "page", "text")

DEFAULT_SOURCE = "demo-textbook"
DEFAULT_SUBJECT = "Science"
DEFAULT_GRADE = "9"
DEFAULT_BOOK_ID = "science_foundation_book_1"
DEFAULT_BOARD = "State Board"
DEFAULT_CLASS_LEVEL = "9"

def _repo_root() -> Path:
    # backend/app/ingestion/textbook_ingestor.py -> backend/app/ingestion -> backend/app -> backend -> repo
    return Path(__file__).resolve().parents[3]


def read_raw_textbook(path: Path) -> str:
    """
    Read raw textbook source file safely.
    """
    return path.read_text(encoding="utf-8", errors="replace")


def parse_raw_textbook(raw_text: str) -> list[dict]:
    """
    Parse raw text blocks into structured documents.

    Returns list of dicts with keys:
    - text, chapter, topic, page
    (metadata defaults are added later)

    Validation:
    - Skips incomplete blocks (no crashes)
    - Ignores blank lines
    """
    docs: list[dict] = []

    current: dict[str, object] = {}
    text_lines: list[str] = []
    in_text = False

    def flush(block_idx: int) -> None:
        nonlocal current, text_lines, in_text

        if text_lines and "text" not in current:
            current["text"] = " ".join(text_lines).strip()

        missing = [k for k in REQUIRED_FIELDS if not str(current.get(k, "")).strip()]
        if missing:
            if any(str(current.get(k, "")).strip() for k in ("chapter", "topic", "page", "text")):
                print(f"[ingest] Skipping block #{block_idx}: missing {missing}")
        else:
            # Normalize types
            try:
                page = int(str(current["page"]).strip())
            except Exception:
                print(f"[ingest] Skipping block #{block_idx}: invalid page={current.get('page')}")
                current, text_lines, in_text = {}, [], False
                return

            docs.append(
                {
                    "chapter": str(current["chapter"]).strip(),
                    "topic": str(current["topic"]).strip(),
                    "page": page,
                    "text": str(current["text"]).strip(),
                }
            )

        current, text_lines, in_text = {}, [], False

    block_idx = 0
    for raw_line in (raw_text or "").splitlines():
        line = raw_line.strip()

        if not line:
            if current or text_lines:
                block_idx += 1
                flush(block_idx)
            continue

        lower = line.lower()

        def is_field(prefix: str) -> bool:
            return lower.startswith(prefix)

        if is_field("chapter:"):
            current["chapter"] = line.split(":", 1)[1].strip()
            in_text = False
            continue

        if is_field("topic:"):
            current["topic"] = line.split(":", 1)[1].strip()
            in_text = False
            continue

        if is_field("page:"):
            current["page"] = line.split(":", 1)[1].strip()
            in_text = False
            continue

        if is_field("text:"):
            in_text = True
            text_value = line.split(":", 1)[1].strip()
            if text_value:
                text_lines.append(text_value)
            continue

        # If we are in a Text section, treat additional lines as continuation.
        if in_text:
            text_lines.append(line)
            continue

        # Unknown line outside Text: ignore safely (but visible to devs)
        print(f"[ingest] Ignoring line outside Text/fields: {line}")

    if current or text_lines:
        block_idx += 1
        flush(block_idx)

    return docs


def add_default_metadata(
    docs: list[dict],
    *,
    source: str,
    subject: str,
    grade: str,
    book_id: str,
    board: str,
    class_level: str,
) -> list[dict]:
    """
    Attach default metadata used by the app (beginner-friendly MVP).

    Preserving chapter/topic/page is important for citations and future expansion.
    """
    out: list[dict] = []
    for d in docs:
        out.append(
            {
                "source": source,
                "subject": subject,
                "grade": grade,
                "book_id": book_id,
                "board": board,
                "class_level": class_level,
                "chapter": d.get("chapter"),
                "topic": d.get("topic"),
                "page": d.get("page"),
                "text": d.get("text"),
            }
        )
    return out


def write_processed_json(docs: list[dict], path: Path) -> None:
    """
    Write the processed JSON dataset used by the vector store loader.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(docs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    """
    CLI entry point:
    Run from repo root (recommended):
      python -m app.ingestion.textbook_ingestor
    """
    root = _repo_root()
    raw_path = root / "data" / "raw" / "demo_textbook.txt"
    out_path = root / "data" / "processed" / "demo_textbook.json"

    if not raw_path.exists():
        print(f"[ingest] Raw textbook file not found: {raw_path}")
        print("[ingest] Create it at data/raw/demo_textbook.txt and re-run.")
        return 1

    raw_text = read_raw_textbook(raw_path)
    docs = parse_raw_textbook(raw_text)
    print(f"[ingest] Parsed {len(docs)} valid blocks from {raw_path.name}")

    processed = add_default_metadata(
        docs,
        source=DEFAULT_SOURCE,
        subject=DEFAULT_SUBJECT,
        grade=DEFAULT_GRADE,
        book_id=DEFAULT_BOOK_ID,
        board=DEFAULT_BOARD,
        class_level=DEFAULT_CLASS_LEVEL,
    )
    write_processed_json(processed, out_path)
    print(f"[ingest] Wrote {len(processed)} entries to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

