"""Evidence-path feedback before adjudication, without changing model judgments."""
import hashlib
import json

from kaji_langgraph.reference_assessment import paragraph_records


def review_source_paths(jev, claim, sources, *, timeout, bind_anchors=False):
    records = paragraph_records(sources)
    supplied = [{k:v for k,v in r.items() if k not in {'visible_text','paragraph_offsets'}} for r in records]
    extra={}
    if bind_anchors:
        from kaji_langgraph.passage_decision import unit_table
        units=unit_table(records,{'C0':claim})
        review,anchors,tokens=jev.review_source_graph(claim,supplied,units,timeout=timeout)
        extra=dict(bound_origins=anchors,
            anchor_catalogue_sha256=hashlib.sha256(json.dumps(units,ensure_ascii=False,sort_keys=True).encode()).hexdigest())
    else:
        review, tokens = jev.check_source_paths(claim, supplied, timeout=timeout)
    return dict(**extra,review=review, model=jev.model, source_ids=[r['id'] for r in records],
        input_sha256=hashlib.sha256(json.dumps(dict(claim=claim,records=supplied),
            ensure_ascii=False,sort_keys=True).encode()).hexdigest(),
        scope='Automated judgment of supplied evidence paths, not authenticated facts, a factual verdict or an acceptance decision.'), tokens
