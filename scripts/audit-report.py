"""Validate discovery evidence before accepting a recurring audit."""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

CHANNELS = {'domestic_media', 'international_media', 'official', 'social_leads', 'historical'}
DECISIONS = {'published', 'updated', 'duplicate', 'pending', 'out_of_scope', 'deferred'}


def validate_report(report, started_at, incident_ids, mode='fresh', *,
                    incidents=None, sources=None, changed_ids=None, carryover=()):
    if report.get('schema_version') != 2:
        raise ValueError('Audit report requires schema_version 2')
    completed = datetime.fromisoformat(report['completed_at'].replace('Z', '+00:00'))
    if completed.tzinfo is None or not started_at <= completed <= datetime.now(timezone.utc):
        raise ValueError('Audit report timestamp is stale or invalid')
    for key in ('searches', 'changed_ids', 'pending_ids', 'candidates'):
        if not isinstance(report.get(key), list):
            raise ValueError('Missing report list: ' + key)
    if not report['searches'] or not report.get('summary'):
        raise ValueError('Missing search evidence or summary')
    for key in ('changed_ids', 'pending_ids'):
        if any(value not in incident_ids for value in report[key]):
            raise ValueError('Unknown incident in ' + key)
    coverage = report.get('coverage', {})
    required = CHANNELS - {'historical'} if mode == 'fresh' else CHANNELS - {'social_leads'}
    if report.get('mode') != mode:
        raise ValueError('Audit mode mismatch')
    for channel in required:
        evidence = coverage.get(channel, {})
        for field in ('searches', 'checked_urls'):
            values = evidence.get(field)
            if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
                raise ValueError('Missing discovery evidence: ' + channel + '.' + field)
        if not all(v.startswith(('https://', 'http://')) for v in evidence['checked_urls']):
            raise ValueError('Invalid checked URL: ' + channel)
        if not isinstance(evidence.get('limitations'), list):
            raise ValueError('Missing limitations: ' + channel)
    for candidate in report['candidates']:
        if not all(candidate.get(key) for key in ('title', 'url', 'reason')):
            raise ValueError('Incomplete candidate')
        candidate_url = urlparse(candidate['url'])
        if candidate_url.scheme not in {'https', 'http'} or not candidate_url.hostname:
            raise ValueError('Invalid candidate URL')
        if candidate.get('priority') not in {'high', 'normal'} or candidate.get('decision') not in DECISIONS:
            raise ValueError('Invalid candidate decision or priority')
        incident_id = candidate.get('incident_id')
        if incident_id is not None and incident_id not in incident_ids:
            raise ValueError('Unknown candidate incident')
        if candidate['decision'] in {'published', 'updated', 'duplicate', 'pending'} and incident_id is None:
            raise ValueError('Candidate requires a matching incident')

    validate_quality(report, incidents, sources, changed_ids, carryover)


def candidate_key(candidate):
    return candidate.get('incident_id') or candidate['url']


def collect_carryover(reports, incidents, mode, started_at):
    """Fold reports chronologically; absence from a newer report never resolves a lead."""
    latest = {}
    for report in sorted(reports, key=lambda item: datetime.fromisoformat(item['completed_at'].replace('Z', '+00:00'))):
        for candidate in report.get('candidates', []):
            for key, previous in list(latest.items()):
                if candidate.get('url') and previous['url'] == candidate['url']:
                    del latest[key]
            latest[candidate_key(candidate)] = candidate
    records = {record['id']: record for record in incidents}
    result = {}
    for key, candidate in latest.items():
        record = records.get(candidate.get('incident_id'))
        if record and record['publication_status'] == 'published':
            continue
        if candidate['decision'] == 'deferred' and (mode == 'historical' or candidate['priority'] == 'high'):
            result[key] = candidate
    cutoff = (started_at - timedelta(hours=72)).date().isoformat()
    for record in incidents:
        if record['publication_status'] != 'pending':
            continue
        if mode == 'fresh' and record['published_at'] < cutoff:
            continue
        result[record['id']] = {
            'title': record['title'], 'incident_id': record['id'],
            'url': None, 'priority': 'high', 'decision': 'pending',
            'reason': 'Existing pending record requires another verification attempt.',
        }
    return list(result.values())


def changed_incident_ids(before, after, before_sources, after_sources):
    old = {record['id']: record for record in before}
    if set(old) - {record['id'] for record in after}:
        raise ValueError('Audit must preserve existing stable incident IDs')
    old_sources = {source['id']: source for source in before_sources}
    changed_sources = {source['id'] for source in after_sources if source != old_sources.get(source['id'])}
    return {record['id'] for record in after
            if record != old.get(record['id']) or changed_sources.intersection(record['sources'])}


def validate_quality(report, incidents=None, sources=None, changed_ids=None, carryover=()):
    if report.get('quality_version') != 1:
        raise ValueError('Audit requires quality_version 1')
    candidates = report['candidates']
    by_url = {candidate['url']: candidate for candidate in candidates}
    for channel in ('domestic_media', 'international_media'):
        evidence = report['coverage'][channel]
        listings = evidence.get('listing_checks')
        if not isinstance(listings, list) or not listings:
            raise ValueError('Missing media listing review: ' + channel)
        reviewed_hosts = set()
        for listing in listings:
            if listing.get('url') not in evidence['checked_urls'] or not listing.get('reason'):
                raise ValueError('Listing requires checked URL and review reason')
            if listing.get('result') not in {'reviewed', 'unavailable'}:
                raise ValueError('Invalid listing result')
            urls = listing.get('candidate_urls')
            if not isinstance(urls, list) or any(url not in by_url for url in urls):
                raise ValueError('Media listing candidate has no decision')
            if listing['result'] == 'reviewed':
                hostname = urlparse(listing['url']).hostname
                if not hostname:
                    raise ValueError('Invalid media listing URL')
                reviewed_hosts.add(hostname.removeprefix('www.'))
        if len(reviewed_hosts) < 2:
            raise ValueError('Review two available media listings: ' + channel)
    keys = {key for candidate in candidates for key in (candidate.get('incident_id'), candidate['url']) if key}
    for previous in carryover:
        if candidate_key(previous) not in keys:
            raise ValueError('Unresolved candidate omitted: ' + str(candidate_key(previous)))
    if changed_ids is not None and set(report['changed_ids']) != set(changed_ids):
        raise ValueError('Reported changed_ids do not match actual record/source changes')
    checks = report.get('source_checks')
    if not isinstance(checks, dict):
        raise ValueError('Missing source body checks')
    if incidents is None or sources is None:
        return
    records = {record['id']: record for record in incidents}
    source_map = {source['id']: source for source in sources}
    for source_id, check in checks.items():
        if source_id not in source_map:
            raise ValueError('Unknown checked source: ' + source_id)
        if check.get('result') not in {'body_checked', 'unavailable'} or not check.get('method'):
            raise ValueError('Invalid source body check: ' + source_id)
        if check['result'] == 'body_checked':
            claims = check.get('supported_claims')
            if not isinstance(claims, list) or not claims or not all(isinstance(c, str) and c.strip() for c in claims):
                raise ValueError('Missing supported claims: ' + source_id)
        elif not check.get('reason'):
            raise ValueError('Missing source access limitation: ' + source_id)
    decisions = {}
    for candidate in candidates:
        incident_id = candidate.get('incident_id')
        if incident_id is None:
            continue
        decisions.setdefault(incident_id, set()).add(candidate['decision'])
        status = records[incident_id]['publication_status']
        if candidate['decision'] in {'published', 'updated'} and status != 'published':
            raise ValueError('Publication decision points to pending record')
        if candidate['decision'] == 'pending' and status != 'pending':
            raise ValueError('Pending decision points to published record')
    for incident_id in report['changed_ids']:
        record = records[incident_id]
        allowed = {'published', 'updated'} if record['publication_status'] == 'published' else {'pending'}
        if not allowed.intersection(decisions.get(incident_id, set())):
            raise ValueError('Changed record has no matching candidate decision: ' + incident_id)
        if record['publication_status'] != 'published':
            continue
        for source_id in record['sources']:
            if checks.get(source_id, {}).get('result') != 'body_checked':
                raise ValueError('Changed published record lacks source body verification: ' + source_id)
    if any(records[incident_id]['publication_status'] != 'pending' for incident_id in report['pending_ids']):
        raise ValueError('pending_ids includes a published record')
