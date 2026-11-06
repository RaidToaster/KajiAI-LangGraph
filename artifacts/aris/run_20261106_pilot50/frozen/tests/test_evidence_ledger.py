from kaji_langgraph.evidence_ledger import ComponentLedger, PassageLink, audit_ledger
from kaji_langgraph.models import SourceRecord


def source(text="Registry: on 2024-06-01 the council voted 7 to 2.", hash="old"):
    return SourceRecord(url="https://example.test/record", retrieved_at="2026-11-04",
                        content_hash=hash, query="", provider="authored-control", page_text=text)


def test_exact_link_is_audited_without_certifying_support():
    row = ComponentLedger(component="original claim", passages=[PassageLink(
        source_url=source().url, source_hash="old", quote="the council voted 7 to 2",
        event_date="2024-06-01", origin="Registry")])
    audit = audit_ledger([row], [source()], ["original claim"])
    assert audit["literal_references_valid"]
    assert not audit["semantic_support_verified"] and not audit["independence_verified"]
    assert audit["components"][0]["passages"][0]["quote_start"] == 24


def test_wrong_version_fabricated_metadata_and_missing_whole_claim_are_retained():
    row = ComponentLedger(component="subclaim", passages=[PassageLink(
        source_url=source().url, source_hash="old", quote="the council voted 7 to 2",
        event_date="2025-06-01", origin="independent audit")],
        unresolved_material_questions=["Did the proposal become law?"])
    audit = audit_ledger([row], [source(hash="new")], ["original claim"])
    assert not audit["literal_references_valid"]
    assert {i["issue"] for i in audit["issues"]} == {"missing_component", "unanchored_reference"}
    assert audit["components"][0]["unresolved_material_questions"]
    audit = audit_ledger([row], [source()], ["subclaim"])
    assert not audit["components"][0]["passages"][0]["literal_metadata_checks"]["event_date"]


def test_question_does_not_resolve_component_or_supply_evidence():
    row = ComponentLedger(component="whole claim", questions=["Was it approved?"],
                          unresolved_material_questions=["Was it approved?"])
    audit = audit_ledger([row], [], ["whole claim"])
    assert audit["components"][0]["passages"] == []
    assert not audit["semantic_support_verified"]
