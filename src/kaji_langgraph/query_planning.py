"""Build initial evidence queries using only the supplied claim."""

import re


_ATTRIBUTION = re.compile(r"^(.+?)\s+(?:said|stated|claimed|wrote)\s*[:,]?\s+(.+)$", re.I)
_SHARED_PREDICATE = re.compile(
    r"^((?:the )?(?:majority|minority) of .+?) and "
    r"((?:the )?(?:majority|minority) of .+?) "
    r"((?:now )?(?:support|oppose|favor|want|have|are)\b.+)$", re.I,
)


def evidence_queries(claim: str) -> list[str]:
    """Search for the underlying records and a separately scoped lead."""
    claim = " ".join(claim.split()).rstrip(".")
    attribution = _ATTRIBUTION.fullmatch(claim)
    if attribution:
        _, statement = attribution.groups()
        statement = statement.strip('"')
        return [f"{claim} original transcript", f"{statement} official record chronology"]
    groups = _SHARED_PREDICATE.fullmatch(claim)
    if groups:
        first, second, predicate = groups.groups()
        return [f"{first} {predicate} original survey results",
                f"{second} {predicate} original survey results"]
    if re.search(r"\b(?:opposed|supported|voted)\b", claim, re.I):
        return [f"{claim} official vote record",
                f"{claim} contemporaneous public statement timeline"]
    if re.search(r"\b(?:(?:more|less)(?: \w+){0,2} than|as .* as|easier than)\b", claim, re.I):
        return [f"{claim} original data methodology",
                f"{claim} underlying measurements scope"]
    return [f"{claim} primary record", f"{claim} original evidence timeline counterevidence"]
