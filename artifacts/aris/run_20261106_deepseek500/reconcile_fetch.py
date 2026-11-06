"""Read-only TinyFetch usage lookup for the stopped DeepSeek reservation."""

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request


def provider_timestamp(value):
    timestamp = datetime.fromisoformat(value)
    return timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--attempt', default='dev-001-deepseek-baseline')
    parser.add_argument('--number', type=int, default=4)
    args = parser.parse_args()
    run = Path('artifacts/aris/run_20261106_deepseek500')
    schedule = json.loads((run / 'protocol.json').read_bytes())['schedule']
    assert args.attempt in {f"{task['case']}-{task['model']}-{task['arm']}" for task in schedule}
    attempt = run / 'attempts' / args.attempt
    request_path = attempt / f'request-{args.number:03}.json'
    request = json.loads(request_path.read_bytes())
    assert request['service'] == 'tinyfish_fetch'
    key = next(line.split('=', 1)[1].strip().strip('"').strip("'")
               for line in Path('.env').read_text(encoding='utf-8').splitlines()
               if line.split('=', 1)[0].strip() == 'TINYFISH_API_KEY')
    sent = datetime.fromisoformat(request['timestamp'])
    end = sent + timedelta(minutes=5)
    start = sent - timedelta(minutes=2)
    query = urllib.parse.urlencode({'start_after': start.isoformat(), 'end_before': end.isoformat(), 'limit': 100})

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    endpoint = 'https://api.fetch.tinyfish.ai/usage'
    lookup = urllib.request.Request(f'{endpoint}?{query}', headers={'X-API-Key': key, 'Accept': 'application/json'})
    with urllib.request.build_opener(NoRedirect()).open(lookup, timeout=20) as response:
        result = json.load(response)
        status = response.status
    body = request['request']['body']
    response_path = request_path.with_name(request_path.name.replace('request-', 'response-'))
    terminal_end = None
    if response_path.is_file():
        metadata = json.loads(response_path.read_bytes())
        if metadata.get('finished_at'):
            terminal_end = datetime.fromisoformat(metadata['finished_at'])
    if terminal_end is None:
        terminal_end = datetime.fromisoformat(json.loads((attempt / 'job.json').read_bytes())['finished_at']) + timedelta(seconds=120)
    matches = [item for item in result['items']
               if item.get('url') in body['urls'] and item.get('format') == body['format']
               and item.get('status') in {'completed', 'failed'} and item.get('request_origin') == 'api'
               and (terminal_end is None or sent - timedelta(seconds=2) <= provider_timestamp(item['created_at'])
                    <= terminal_end + timedelta(seconds=5))]
    controls = []
    for path in sorted(attempt.glob('request-*.json')):
        known = json.loads(path.read_bytes())
        if path == request_path or known['service'] != 'tinyfish_fetch' or not path.with_name(path.name.replace('request-', 'response-')).is_file():
            continue
        controls.append({'reservation': path.name, 'provider_terminal_matches': sum(
            item.get('url') in known['request']['body']['urls'] and item.get('status') in {'completed', 'failed'}
            for item in result['items'])})
    receipt = {'lookup_at': datetime.now(timezone.utc).isoformat(), 'http_status': status, 'endpoint': endpoint,
               'request_sha256': hashlib.sha256(request_path.read_bytes()).hexdigest(),
               'start_after': start.isoformat(), 'end_before': end.isoformat(), 'local_terminal_controls': controls,
               'provider_items': len(result['items']), 'has_more': result.get('has_more'), 'matching_rows': matches,
               'attempt': args.attempt, 'request_number': args.number, 'original_response_saved': response_path.exists(),
               'provider_created_at_assumption': 'Timestamp without an offset is interpreted as UTC and matched against the local request interval.',
               'inference_calls': 0, 'fetch_dispatches': 0}
    receipt_path = run / (f'fetch-reconciliation-{args.attempt}-{args.number:03}.json')
    if receipt_path.exists():
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
        receipt_path = receipt_path.with_name(f'{receipt_path.stem}-{stamp}.json')
    with receipt_path.open('x', encoding='utf-8') as file:
        json.dump(receipt, file, ensure_ascii=False, indent=2)
    print(json.dumps({'http_status': status, 'matches': len(matches), 'has_more': result.get('has_more'),
                      'provider_items': len(result['items']), 'controls': controls,
                      'matching_status': [item['status'] for item in matches]}))


if __name__ == '__main__':
    main()
