"""Validate discovery evidence before accepting a recurring audit."""
from datetime import datetime, timezone

CHANNELS = {'domestic_media', 'international_media', 'official', 'social_leads', 'historical'}
DECISIONS = {'published', 'updated', 'duplicate', 'pending', 'out_of_scope', 'deferred'}


def validate_report(report, started_at, incident_ids, mode='fresh'):
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
        if candidate.get('priority') not in {'high', 'normal'} or candidate.get('decision') not in DECISIONS:
            raise ValueError('Invalid candidate decision or priority')
        incident_id = candidate.get('incident_id')
        if incident_id is not None and incident_id not in incident_ids:
            raise ValueError('Unknown candidate incident')
        if candidate['decision'] in {'published', 'updated', 'duplicate', 'pending'} and incident_id is None:
            raise ValueError('Candidate requires a matching incident')
