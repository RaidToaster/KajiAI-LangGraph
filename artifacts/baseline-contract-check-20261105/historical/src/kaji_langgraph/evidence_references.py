"""Build candidate searches from dated citations listed on a retrieved page."""

from datetime import date, datetime
import re

from kaji_langgraph.linked_evidence import _terms


_HEADING = re.compile(r"(?im)^#{1,6}[ \t]+\**(?:our sources|references|sources)\**[ \t]*$")
_DATE = re.compile(r"\b([A-Z][a-z]+)\.? (\d{1,2}), (\d{4})\.?$")
_PRIMARY = re.compile(r"\b(?:roll call|court order|official record|survey data)\b", re.I)


def reference_queries(claim: str, cutoff: date, page_text: str) -> list[str]:
    """Return dated public citation leads, ordered by topic and record type."""
    heading = _HEADING.search(page_text)
    if heading is None:
        return []
    terms = _terms(claim)
    candidates = {}
    for line in page_text[heading.end():].splitlines():
        line = line.strip()
        if line.startswith("#"):
            break
        match = _DATE.search(line)
        if (not match or len(line) > 240 or "@" in line
                or line.lower().startswith(("email ", "interview ", "telephone "))):
            continue
        month, day, year = match.groups()
        try:
            month_number = datetime.strptime(month[:3], "%b").month
            published = date(int(year), month_number, int(day))
        except ValueError:
            continue
        if published > cutoff:
            continue
        overlap = len(terms & _terms(line))
        primary = bool(_PRIMARY.search(line))
        if overlap or primary:
            recent = (cutoff - published).days <= 90
            candidates[line] = (3 * overlap + 12 * primary + 8 * recent, published)
    return sorted(candidates, key=candidates.get, reverse=True)
