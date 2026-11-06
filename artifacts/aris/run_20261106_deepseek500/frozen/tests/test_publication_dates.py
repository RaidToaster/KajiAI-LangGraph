from kaji_langgraph.publication_dates import source_publications


def record(text):
    return {'id':'S1','url':'https://a.test/record','content_hash':'v1','passages':{'P1':text}}


def test_transcript_event_date_is_not_promoted_to_publication_date():
    text='Interview transcript, 2024-02-02. Mayor Imani said the statistic.'
    result=source_publications([record(text)])['S1']
    assert result['text'] is None and result['status']=='no_explicit_publication_label'


def test_explicit_publication_dateline_retains_exact_precision_and_quote():
    text='### Published - 24 Feb 2020 3:55 PM IST'
    result=source_publications([record(text)])['S1']
    assert result['text']=='24 Feb 2020 3:55 PM IST'
    assert result['matches'][0]['literal_dateline']==text
    assert result['matches'][0]['literal_quote']==text
    assert not result['authenticated_publication_time']


def test_distinct_explicit_datelines_remain_ambiguous_with_all_evidence_retained():
    text='Published March 2, 2020\nPublished March 3, 2020'
    result=source_publications([record(text)])['S1']
    assert result['text'] is None and result['status']=='ambiguous_datelines'
    assert len(result['matches'])==2


def test_date_candidates_preserve_literal_context_without_inferred_roles():
    from kaji_langgraph.publication_dates import source_date_mentions
    text='Press release, 2024-06-01. Survey covers 2023.'
    mentions=source_date_mentions([record(text)])['S1']
    assert [m['text'] for m in mentions]==['2024-06-01','2023']
    for item in mentions:
        assert item['role']=='unassigned' and item['literal_context']==text
        a,b=item['paragraph_character_span']
        assert text[a:b]==item['text']
