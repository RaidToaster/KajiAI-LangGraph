"""Retain explicit source publication datelines without guessing document roles.

This English-label extractor deliberately leaves unlabeled/ambiguous dates
unknown. It records source-reported metadata, not an authenticated publishing time.
"""
import re


MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
DATE = rf"(?:\d{{4}}-\d{{2}}-\d{{2}}|{MONTH}\s+\d{{1,2}},?\s+\d{{4}}|\d{{1,2}}\s+{MONTH}\s+\d{{4}})"
DATELINE = re.compile(rf"^\s*(?:#{{1,6}}\s*)?(?:Published|Publication date)(?:\s+on)?\s*[:\-–]?\s*(?P<value>{DATE}[^\n]*)$", re.IGNORECASE)
DATE_MENTION = re.compile(rf"\b(?:{DATE}|(?:19|20)\d{{2}})\b", re.IGNORECASE)


def source_date_mentions(records):
    """Literal candidates with complete paragraph context; no event-role inference."""
    result = {}
    for record in records:
        matches = []
        offsets = record.get("paragraph_offsets")
        for pid, text in record["passages"].items():
            if offsets is not None and pid not in offsets:
                continue
            for match in DATE_MENTION.finditer(text):
                matches.append({"text": match.group(), "paragraph": pid,
                    "paragraph_character_span": list(match.span()), "literal_context": text,
                    "role": "unassigned", "source_url": record["url"],
                    "content_hash": record.get("content_hash")})
        result[record["id"]] = matches
    return result


def source_publications(records):
    result = {}
    for record in records:
        matches = []
        offsets = record.get("paragraph_offsets")
        for pid, text in record["passages"].items():
            if offsets is not None and pid not in offsets:
                continue  # Exclude compiled range aliases of the same paragraphs.
            for line in text.splitlines():
                match = DATELINE.fullmatch(line)
                if match:
                    value = match.group("value").strip()
                    matches.append({"text": value, "literal_dateline": line,
                        "reference": {"source": record["id"], "first_paragraph": pid, "last_paragraph": pid},
                        "literal_quote": text})
        values = {m["text"] for m in matches}
        result[record["id"]] = {"text": next(iter(values)) if len(values) == 1 else None,
            "status": "explicit_source_dateline" if len(values) == 1 else ("ambiguous_datelines" if values else "no_explicit_publication_label"),
            "matches": matches, "source_url": record["url"], "content_hash": record.get("content_hash"),
            "authenticated_publication_time": False}
    return result
