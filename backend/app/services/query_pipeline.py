from __future__ import annotations

from app.data.vector_store import initialize_vector_store


def normalize_query(question: str) -> str:
    """
    Normalize user input for consistent matching.

    Rules:
    - lowercase
    - strip leading/trailing whitespace
    - collapse extra internal spaces
    """
    q = (question or "").lower().strip()
    q = " ".join(q.split())
    return q


def _dedupe_sentences(texts: list[str]) -> list[str]:
    """
    Very simple sentence deduplication.

    - Splits on "."
    - Skips repeated sentences (case-insensitive)
    - Returns sentences with trailing "."
    """
    seen: set[str] = set()
    out: list[str] = []
    for t in texts:
        if not t:
            continue
        for part in t.replace("\n", " ").split("."):
            s = part.strip()
            if not s:
                continue
            key = s.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(s + ".")
    return out


def _sentence_tokens(sentence: str) -> set[str]:
    return {w.lower() for w in sentence.replace("\n", " ").split() if w.strip()}


def compress_text(text: str) -> str:
    """
    Simple rule-based compression to reduce token count while preserving meaning.

    - Removes/shortens common filler phrases.
    - Adds compact 'X: ...' style where appropriate.
    - Adds a special compact form for common science patterns (e.g. photosynthesis).
    """
    original = text.strip()
    lower = original.lower()

    # Special photosynthesis pattern compression.
    if "photosynthesis" in lower:
        has_sun = "sunlight" in lower or "light" in lower
        has_water = "water" in lower
        has_co2 = "carbon dioxide" in lower or "co2" in lower or "co₂" in lower
        has_glucose = "glucose" in lower or "food" in lower
        has_oxygen = "oxygen" in lower

        inputs = []
        if has_sun:
            inputs.append("sunlight")
        if has_water:
            inputs.append("water")
        if has_co2:
            inputs.append("CO₂")

        outputs = []
        if has_glucose:
            outputs.append("glucose/food")
        if has_oxygen:
            outputs.append("oxygen")

        if inputs or outputs:
            inputs_str = ", ".join(inputs) if inputs else "materials"
            outputs_str = ", ".join(outputs) if outputs else "food"
            compressed = f"Photosynthesis: inputs ({inputs_str}) → outputs ({outputs_str})."
            print("Compressed text:", compressed)
            return compressed

    # Generic filler phrase compression.
    compressed = original
    replacements = {
        " is the process by which ": ": ",
        " is the process in which ": ": ",
        " allows plants to ": ": ",
        " in order to ": " to ",
        " is known as ": ": ",
    }
    for phrase, repl in replacements.items():
        compressed = compressed.replace(phrase, repl)
        compressed = compressed.replace(phrase.capitalize(), repl)

    compressed = compressed.strip()
    print("Compressed text:", compressed)
    return compressed


def run_query_pipeline(
    *,
    question: str,
    user_id: str | None = None,
    grade: str | None = None,
    subject: str | None = None,
    language: str | None = None,
) -> dict:
    """
    Query pipeline placeholder.

    This is where the real system will eventually do:
    - query normalization (Hindi/English)
    - retrieval from vector DB
    - context pruning
    - LLM generation

    For now it is intentionally simple and runnable:
    User Query -> Embedding Search -> Structured Response
    """
    normalized = normalize_query(question)
    print("Query:", normalized)
    store = initialize_vector_store()
    hits = store.search(normalized, top_k=3)
    print("Top results:", hits)

    threshold = 0.5
    valid = [h for h in hits if float(h.get("score", 0.0)) >= threshold]

    top_score = float(valid[0].get("score", 0.0)) if valid else 0.0
    print("Top score:", top_score)

    if not valid:
        answer = "I could not find relevant information in the textbook."
        citations = [{"source": "demo-textbook", "chapter": "N/A", "page": 0}]
        confidence = "low"
    else:
        # STEP 1: keep only chunks close to the top score (reduce mixed topics).
        keep_floor = top_score * 0.85
        strong = [h for h in valid if float(h.get("score", 0.0)) >= keep_floor]

        # STEP 6: remove topic mixing by majority chapter.
        chapter_counts: dict[str, int] = {}
        for h in strong:
            ch = (h.get("chapter") or "N/A").strip()
            chapter_counts[ch] = chapter_counts.get(ch, 0) + 1
        majority_chapter = max(chapter_counts, key=chapter_counts.get) if chapter_counts else "N/A"
        filtered_strong = [h for h in strong if (h.get("chapter") or "N/A").strip() == majority_chapter]

        mixed_topics = len(chapter_counts) > 1

        if not filtered_strong:
            answer = "I could not find relevant information in the textbook."
            citations = [{"source": "demo-textbook", "chapter": "N/A", "page": 0}]
            confidence = "low"
        else:
            # STEP 2–5: aggregate all strong chunks, then compress into a single structured answer.
            combined_text = " ".join(h["text"] for h in filtered_strong if h.get("text"))
            compressed = compress_text(combined_text)

            # Keep at most 2 sentences/lines in the final answer.
            parts = [p.strip() for p in compressed.split(".") if p.strip()]
            if not parts:
                answer = "I could not find relevant information in the textbook."
            elif len(parts) == 1:
                answer = parts[0] + "."
            else:
                answer = parts[0] + ". " + parts[1] + "."

            # Unique citations only (chapter + page).
            seen_cites: set[tuple[str, int]] = set()
            citations = []
            for doc in filtered_strong:
                chapter = doc.get("chapter") or "N/A"
                page_raw = doc.get("page") or 0
                try:
                    page = int(page_raw)
                except Exception:
                    page = 0
                key = (str(chapter), page)
                if key in seen_cites:
                    continue
                seen_cites.add(key)
                citations.append({"source": "demo-textbook", "chapter": chapter, "page": page})

            # Confidence logic with mixed-topic awareness.
            if mixed_topics:
                confidence = "low"
            elif len(filtered_strong) == 1:
                confidence = "medium"
            else:
                confidence = "high"

    return {
        "answer": answer,
        "citations": citations,
        "meta": {
            "grade": grade,
            "subject": subject,
            "confidence": confidence,
        },
    }

