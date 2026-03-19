from __future__ import annotations

import copy

from app.data.vector_store import initialize_vector_store

_QUERY_CACHE: dict[tuple[str, str | None, str | None, str | None, str | None, str | None, str | None, str | None], dict] = {}
"""
Simple in-memory cache for MVP.

Why caching:
- Many tutoring queries repeat (same question asked by multiple students, or the same student retries).
- Avoids repeated embedding search + scoring + pruning + formatting.
- Reduces latency and cost (important for low-bandwidth, low-cost systems).

Why in-memory is OK for MVP (but not production):
- Works for a single process and resets on restart.
- In production you’d use a shared cache (e.g., Redis) with TTLs and size limits.
"""


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


def detect_intent(query: str) -> str:
    """
    Very simple intent detection for an MVP.

    Why this is useful:
    - Different questions need different answer shapes (definition vs process vs inputs/outputs).
    - We keep this separate from retrieval so we can improve UX without touching embeddings,
      pruning, or model logic (and without increasing token cost much).
    """
    q = (query or "").lower()

    # Definition-style questions.
    if any(k in q for k in ["what is", "define", "meaning"]):
        return "definition"
    # Inputs/outputs / reactants vs products.
    if any(k in q for k in ["inputs and outputs", "reactants and products"]) or (
        "inputs" in q and "outputs" in q
    ):
        return "inputs_outputs"
    # Process / "how" questions.
    if any(k in q for k in ["how does", "how do", "how is", "how are", "process", "steps of"]):
        return "process"
    # Explanations / "why" questions.
    if any(k in q for k in ["explain", "in simple terms", "why ", "why is", "why are"]):
        return "explanation"
    # Very short factual questions -> factoid.
    tokens = [t for t in q.replace("?", " ").split() if t]
    if len(tokens) <= 6 and q.endswith("?"):
        return "factoid"
    # Fallback intent.
    return "unknown"


def _remove_fillers(text: str) -> str:
    """
    Small helper to shorten common filler phrases while preserving meaning.
    """
    s = (text or "").strip()
    replacements = {
        " is the process by which ": " is how ",
        " is the process in which ": " is how ",
        " is known as ": " is called ",
        " in order to ": " to ",
    }
    for phrase, repl in replacements.items():
        s = s.replace(phrase, repl).replace(phrase.capitalize(), repl)
    return " ".join(s.split())


def _extract_facts(raw_context: str) -> dict:
    """
    Extract simple facts from retrieved context (no hardcoded full answers).

    We only detect:
    - concept name (best-effort, based on terms present)
    - inputs/outputs for common science phrasing
    """
    text = (raw_context or "").strip()
    lower = text.lower()

    concept = None
    if "photosynthesis" in lower:
        concept = "Photosynthesis"
    elif "gravity" in lower:
        concept = "Gravity"

    # Inputs/outputs for the photosynthesis-style pattern.
    inputs: list[str] = []
    outputs: list[str] = []

    if "sunlight" in lower or "light" in lower:
        inputs.append("sunlight")
    if "water" in lower:
        inputs.append("water")
    if "carbon dioxide" in lower or "co2" in lower or "co₂" in lower:
        inputs.append("CO₂")

    if "glucose" in lower:
        outputs.append("glucose")
    if "oxygen" in lower:
        outputs.append("oxygen")
    if "food" in lower and "glucose" not in lower:
        outputs.append("food")

    # Deduplicate while preserving order.
    def _uniq(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for it in items:
            if it in seen:
                continue
            seen.add(it)
            out.append(it)
        return out

    return {
        "concept": concept,
        "inputs": _uniq(inputs),
        "outputs": _uniq(outputs),
        "raw_context": text,
    }


def _shape_answer(*, raw_context: str, intent: str) -> str:
    """
    Shape a short, query-aware answer using extracted facts.
    Keeps output to 1–2 lines and avoids repeating the same template for every query.
    """
    facts = _extract_facts(raw_context)
    concept = facts["concept"] or "This concept"
    inputs: list[str] = facts["inputs"]
    outputs: list[str] = facts["outputs"]

    # If we have a clean IO set, we can produce a dense IO format.
    has_complete_io = (len(inputs) >= 2) and (len(outputs) >= 1)

    # "inputs_outputs" is the new explicit intent; keep 'io' for backward compatibility.
    if intent in {"inputs_outputs", "io"} and has_complete_io:
        return f"{concept}: inputs ({', '.join(inputs)}) → outputs ({', '.join(outputs)})."

    # Use the first sentence of the retrieved context as a grounding line.
    first_sentence = (raw_context.split(".")[0] if raw_context else "").strip()
    first_sentence = _remove_fillers(first_sentence)
    if first_sentence and not first_sentence.endswith("."):
        first_sentence += "."

    if intent == "definition":
        # Prefer a natural "X is ..." definition when possible.
        if first_sentence:
            return first_sentence
        if has_complete_io:
            return f"{concept}: uses {', '.join(inputs)} to produce {', '.join(outputs)}."
        return f"{concept}: short definition not found in context."

    if intent == "process":
        if has_complete_io:
            return f"{concept} process: uses {', '.join(inputs)} → {', '.join(outputs)}."
        return first_sentence or f"{concept}: process details not found in context."

    if intent == "explanation":
        # Two-sentence explanatory mode when possible.
        if has_complete_io:
            return f"{concept}: uses {', '.join(inputs)} to produce {', '.join(outputs)}. This helps explain the process in simple terms."
        if first_sentence:
            return first_sentence
        return f"{concept}: explanation not clearly found in context."

    if intent == "factoid":
        # Short factual answer; rely on first sentence or IO summary.
        if first_sentence:
            return first_sentence
        if has_complete_io:
            return f"{concept}: uses {', '.join(inputs)} to produce {', '.join(outputs)}."
        return f"{concept}: key fact not clearly found in context."

    # "unknown" or general intent: best-effort concise answer.
    if has_complete_io:
        return f"{concept}: uses {', '.join(inputs)} to produce {', '.join(outputs)}."
    return first_sentence or f"{concept}: relevant details not found in context."


def adjust_answer_for_grade(answer: str, grade: str | None) -> str:
    """
    Grade-aware personalization (deterministic, no LLM).

    Why this matters in an education tutor:
    - The *same* concept needs different vocabulary and density for different grades.
    - Younger learners benefit from simpler words and fewer symbols.
    - Older learners benefit from standard academic terms (glucose, carbon dioxide, oxygen).

    Why deterministic first:
    - Safe, predictable, and easy to test.
    - A good baseline before adding any generative model.

    Important for token tracking:
    - Personalization is applied *before* token counting so we measure the final
      user-visible output cost/size accurately.
    """
    a = " ".join((answer or "").split()).strip()
    if not a:
        return a

    # Best-effort grade parsing.
    try:
        g = int(str(grade).strip()) if grade is not None else None
    except Exception:
        g = None

    # If we can't parse grade, keep the original answer.
    if g is None:
        return a

    # Try to parse the compact IO pattern, if present:
    # "Concept: inputs (a, b, c) → outputs (x, y)."
    concept = None
    inputs: list[str] = []
    outputs: list[str] = []
    if ":" in a and "inputs" in a.lower() and "outputs" in a.lower():
        try:
            concept = a.split(":", 1)[0].strip()
            after = a.split(":", 1)[1]
            if "inputs" in after and "outputs" in after:
                inputs_part = after.split("inputs", 1)[1].split("outputs", 1)[0]
                outputs_part = after.split("outputs", 1)[1]

                def _parse_list(s: str) -> list[str]:
                    s = s.replace("→", " ")
                    s = s.replace("(", " ").replace(")", " ")
                    s = s.replace(".", " ")
                    s = " ".join(s.split())
                    # Keep comma-separated items if present
                    if "," in s:
                        items = [x.strip() for x in s.split(",") if x.strip()]
                    else:
                        items = [x.strip() for x in s.split() if x.strip()]
                    # Remove label words
                    drop = {"inputs", "outputs"}
                    items = [it for it in items if it.lower() not in drop]
                    # Deduplicate
                    seen: set[str] = set()
                    out: list[str] = []
                    for it in items:
                        key = it.lower()
                        if key in seen:
                            continue
                        seen.add(key)
                        out.append(it)
                    return out

                inputs = _parse_list(inputs_part)
                outputs = _parse_list(outputs_part)
        except Exception:
            concept = None
            inputs = []
            outputs = []

    # Grade buckets:
    # - 1–5: simplified, shorter, fewer technical terms/symbols
    # - 6–10: balanced (keep current)
    # - 11–12: advanced, slightly more academic/precise

    if 1 <= g <= 5:
        # Visible simplification:
        # - remove symbols/technical terms where possible
        # - prefer "plants make food using sunlight"
        simplified = a
        simplified = simplified.replace("CO₂", "carbon dioxide")
        simplified = simplified.replace("carbon dioxide (CO₂)", "carbon dioxide")
        simplified = simplified.replace("glucose/food", "food")
        simplified = simplified.replace("glucose (food)", "food")
        simplified = simplified.replace("glucose", "food")

        # If we have IO facts and it's photosynthesis-like, rewrite into a kid-friendly sentence.
        if (concept or "").lower() == "photosynthesis":
            return "Photosynthesis is how plants make their food using sunlight."

        # Generic simplification: keep only first sentence and remove heavy clauses after commas.
        first = (simplified.split(".")[0]).strip()
        if "," in first:
            first = first.split(",", 1)[0].strip()
        if not first.endswith("."):
            first += "."
        return first

    if 6 <= g <= 10:
        # Balanced: keep current style (still visible vs grade 5 and 12 due to the other buckets).
        return a

    if 11 <= g <= 12:
        advanced = a
        advanced = advanced.replace("CO₂", "carbon dioxide (CO₂)")
        advanced = advanced.replace("glucose/food", "glucose (food)")

        # If we have parsed IO facts, try a more academic process sentence.
        if concept and inputs and outputs:
            # Prefer "produce X from Y using Z" when possible.
            inputs_lower = [x.lower() for x in inputs]
            outputs_lower = [x.lower() for x in outputs]

            has_sun = any("sun" in x or "light" in x for x in inputs_lower)
            has_water = any("water" in x for x in inputs_lower)
            has_co2 = any("co" in x or "carbon" in x for x in inputs_lower)
            has_oxygen = any("oxygen" in x for x in outputs_lower)
            has_glucose = any("glucose" in x or "food" in x for x in outputs_lower)

            if has_glucose and (has_water or has_co2) and has_sun:
                base = f"{concept} is the process by which plants produce glucose from "
                parts = []
                if has_co2:
                    parts.append("carbon dioxide")
                if has_water:
                    parts.append("water")
                base += " and ".join(parts) if parts else "materials"
                base += " using sunlight"
                if has_oxygen:
                    base += ", releasing oxygen"
                return base + "."

        # Generic enrichment: add "process" wording if absent, keep up to 2 sentences.
        if "process" not in advanced.lower() and "is how" in advanced.lower():
            advanced = advanced.replace(" is how ", " is the process by which ")
        parts = [p.strip() for p in advanced.split(".") if p.strip()]
        if len(parts) >= 2:
            return parts[0] + ". " + parts[1] + "."
        if len(parts) == 1:
            return parts[0] + "."
        return advanced

    return a


def render_answer_for_language(answer: str, language: str | None) -> str:
    """
    Language-aware rendering (MVP).

    For stability:
    - We currently return only English answers.
    - Non-English language codes are accepted but fall back to English.
    - This avoids unreliable mixed-language output until proper translation is added.
    """
    lang = (language or "en").strip().lower()
    # Currently we ignore `lang` and always return a clean English answer.
    # This keeps behavior predictable while still allowing the API to evolve later.
    return " ".join((answer or "").split()).strip()


def dedupe_citations(citations: list[dict]) -> list[dict]:
    """
    Deduplicate citations by (source, chapter, page), preserving order.
    """
    seen: set[tuple[str, str, int]] = set()
    out: list[dict] = []
    for c in citations or []:
        source = str(c.get("source") or "demo-textbook")
        chapter = str(c.get("chapter") or "N/A")
        page_raw = c.get("page") or 0
        try:
            page = int(page_raw)
        except Exception:
            page = 0
        key = (source, chapter, page)
        if key in seen:
            continue
        seen.add(key)
        out.append({"source": source, "chapter": chapter, "page": page})
    return out


def clean_final_answer(answer: str) -> str:
    """
    Final answer cleanup (MVP):
    - remove repeated sentences
    - keep the answer short and non-contradictory by preferring earliest unique sentences
    """
    a = " ".join((answer or "").split()).strip()
    if not a:
        return a
    sentences = _dedupe_sentences([a])
    # Keep it compact (1–2 sentences) to reduce mixing and contradictions.
    return " ".join(sentences[:2]).strip()


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using a simple approximation.

    Why this is approximate:
    - Real LLM tokenizers split text into subword tokens, not characters.
    - Token counts vary by language (Hindi/English), punctuation, and formatting.

    Why this still helps:
    - We mainly need a consistent metric to compare "before vs after" compression.
    - Lower tokens typically means lower API cost, faster responses, and less data
      transfer—important for low-bandwidth environments.

    Rule of thumb:
    - 1 token ≈ 4 characters (rough average for English-like text)
    """
    return int(len(text) / 4)


def run_query_pipeline(
    *,
    question: str,
    user_id: str | None = None,
    grade: str | None = None,
    subject: str | None = None,
    language: str | None = None,
    chapter: str | None = None,
    topic: str | None = None,
    book_id: str | None = None,
    board: str | None = None,
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
    intent = detect_intent(normalized)

    # Cache key includes query + personalization knobs.
    # Chapter/topic are included so filtered queries don't reuse unfiltered answers.
    cache_key = (normalized, grade, subject, language, chapter, topic, book_id, board)
    cached = _QUERY_CACHE.get(cache_key)
    if cached is not None:
        # Use a deep copy so callers can't accidentally mutate the cached value.
        result = copy.deepcopy(cached)
        result.setdefault("meta", {})
        result["meta"]["cache_hit"] = True
        return result

    store = initialize_vector_store()

    # Optional filters enter the flow here (chapter/topic + future-proof multi-book hints).
    # We prefer/restrict when possible, but always fall back to normal retrieval.
    wants_filter = bool((chapter or "").strip() or (topic or "").strip() or (book_id or "").strip() or (board or "").strip())
    # Always keep a true "normal retrieval" fallback for safety.
    fallback_hits = store.search(normalized, top_k=3)
    initial_k = 12 if wants_filter else 3
    hits = store.search(normalized, top_k=initial_k)
    print("Top results:", hits)

    if wants_filter:
        # Keep the original unfiltered hits so we can gracefully fall back without
        # re-running retrieval (and without risking different results).
        unfiltered_hits = hits

        ch = (chapter or "").strip().lower()
        tp = (topic or "").strip().lower()
        bid = (book_id or "").strip().lower()
        brd = (board or "").strip().lower()

        # Prefer matching book_id/board when provided, but never hard-fail.
        def _prefer_book(h: dict) -> bool:
            if not bid:
                return True
            hb = str(h.get("book_id") or "").strip().lower()
            return hb == bid

        def _prefer_board(h: dict) -> bool:
            if not brd:
                return True
            hb = str(h.get("board") or "").strip().lower()
            return hb == brd

        def _match_chapter(h: dict) -> bool:
            if not ch:
                return True
            hc = str(h.get("chapter") or "").strip().lower()
            return (ch in hc) or (hc in ch)

        def _match_topic(h: dict) -> bool:
            if not tp:
                return True
            ht = str(h.get("text") or "").lower()
            htopic = str(h.get("topic") or "").strip().lower()
            return (tp in ht) or (tp in htopic) or (htopic and (htopic in tp))

        # Step 1: apply chapter/topic restrictions (if provided).
        filtered_hits = [h for h in hits if _match_chapter(h) and _match_topic(h)]

        # Step 2: within the restricted set, prefer book_id/board matches if possible.
        if (bid or brd) and filtered_hits:
            preferred = [h for h in filtered_hits if _prefer_book(h) and _prefer_board(h)]
            if preferred:
                filtered_hits = preferred + [h for h in filtered_hits if h not in preferred]

        # Fallback logic: if filters match nothing, revert to normal top-3 retrieval.
        if filtered_hits:
            hits = filtered_hits[:3]
        else:
            hits = fallback_hits
    else:
        # No filters: use the default top-3 retrieval.
        hits = fallback_hits

    threshold = 0.5
    valid = [h for h in hits if float(h.get("score", 0.0)) >= threshold]

    top_score = float(valid[0].get("score", 0.0)) if valid else 0.0
    print("Top score:", top_score)

    if not valid:
        tokens_before = 0
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
            tokens_before = 0
            answer = "I could not find relevant information in the textbook."
            citations = [{"source": "demo-textbook", "chapter": "N/A", "page": 0}]
            confidence = "low"
        else:
            # STEP 2–5: aggregate all strong chunks, then compress into a single structured answer.
            raw_context = " ".join(h["text"] for h in filtered_strong if h.get("text"))
            tokens_before = estimate_tokens(raw_context)
            print("Tokens before:", tokens_before)

            # Answer shaping is intentionally separate from retrieval:
            # - Retrieval decides "what content is relevant"
            # - Shaping decides "how to present it" based on the user's intent
            answer = _shape_answer(raw_context=raw_context, intent=intent)
            answer = " ".join(answer.split())  # keep compact
            print("Shaped answer (pre-grade):", answer)
            print("Grade value:", grade)

            # Grade-aware personalization is applied after shaping (so it is query-aware),
            # and before token counting (so token usage reflects the final output).
            answer = adjust_answer_for_grade(answer, grade)
            print("Adjusted answer (post-grade):", answer)

            # Keep at most 2 lines by limiting to 2 sentences.
            parts = [p.strip() for p in answer.split(".") if p.strip()]
            if len(parts) >= 2:
                answer = parts[0] + ". " + parts[1] + "."
            elif len(parts) == 1:
                answer = parts[0] + "."
            else:
                answer = "I could not find relevant information in the textbook."

            # Unique citations only (chapter + page).
            citations = []
            for doc in filtered_strong:
                citations.append(
                    {
                        "source": doc.get("source") or "demo-textbook",
                        "chapter": doc.get("chapter") or "N/A",
                        "page": doc.get("page") or 0,
                    }
                )
            citations = dedupe_citations(citations)

            # If only one citation is needed for the final answer, keep it short.
            if intent in {"definition", "factoid"} and citations:
                citations = citations[:1]
            elif intent in {"inputs_outputs", "process", "explanation"} and len(citations) > 2:
                citations = citations[:2]

            # Confidence estimation combines multiple factors:
            # - top_score: how strong is the best match
            # - score gap: how clearly it stands out
            # - mixed_topics: whether chapters disagree
            # - filters: if we applied filters and they collapsed the set heavily
            second_score = float(valid[1].get("score", 0.0)) if len(valid) > 1 else 0.0
            gap = max(0.0, top_score - second_score)

            if top_score < 0.55 or mixed_topics:
                confidence = "low"
            elif top_score >= 0.8 and gap >= 0.15 and len(filtered_strong) >= 1:
                confidence = "high"
            else:
                confidence = "medium"

    # Final cleanup to avoid repetition / mixed fragments.
    answer = clean_final_answer(answer)

    # Render the final answer in the requested language (lightweight MVP).
    answer = render_answer_for_language(answer, language)

    # Token tracking must happen after personalization (including language rendering).
    tokens_after = estimate_tokens(answer)
    reduction_percent = int(((tokens_before - tokens_after) / tokens_before) * 100) if tokens_before > 0 else 0
    print("Tokens after:", tokens_after)
    print("Reduction %:", reduction_percent)

    # If we fall back or the confidence is low, avoid exposing a misleading intent.
    public_intent = intent
    if confidence == "low" or answer in {
        "I could not find relevant information in the textbook.",
        "मुझे पाठ्यपुस्तक में इससे संबंधित जानकारी नहीं मिली।",
    }:
        public_intent = "unknown"

    result = {
        "answer": answer,
        "citations": dedupe_citations(citations),
        "meta": {
            "grade": grade,
            "subject": subject,
            "confidence": confidence,
            "intent": public_intent,
            "token_usage": {
                "before": tokens_before,
                "after": tokens_after,
                "reduction_percent": reduction_percent,
            },
            "cache_hit": False,
        },
    }

    # Store final response in cache for identical future requests.
    _QUERY_CACHE[cache_key] = copy.deepcopy(result)
    return result

