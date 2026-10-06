"""Regression cases for missed leads, weak research reports and incorrect decisions."""
import copy
import unittest
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

spec = spec_from_file_location('audit_quality', Path(__file__).with_name('audit-report.py'))
module = module_from_spec(spec)
spec.loader.exec_module(module)


class QualityTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.candidate = {'title': 'Incident', 'url': 'https://news.example/incident',
                          'priority': 'high', 'decision': 'published', 'incident_id': 'incident',
                          'reason': 'Primary announcement checked'}
        self.records = [{'id': 'incident', 'title': 'Incident', 'publication_status': 'published',
                         'published_at': self.now.date().isoformat(), 'sources': ['official']}]
        self.sources = [{'id': 'official', 'type': 'primary', 'publisher': 'Company'}]
        self.report = {'quality_version': 1, 'candidates': [self.candidate],
                       'changed_ids': ['incident'], 'pending_ids': [],
                       'source_checks': {'official': {'result': 'body_checked', 'method': 'web',
                                          'supported_claims': ['Unauthorized access confirmed; extent unknown']}},
                       'coverage': {}}
        for channel in ('domestic_media', 'international_media'):
            urls = ['https://first.example/news', 'https://second.example/news']
            self.report['coverage'][channel] = {'checked_urls': urls, 'listing_checks': [
                {'url': url, 'result': 'reviewed', 'reason': 'Latest incident articles reconciled',
                 'candidate_urls': [self.candidate['url']]} for url in urls]}

    def validate(self, carryover=()):
        module.validate_quality(self.report, self.records, self.sources, {'incident'}, carryover)

    def test_verified_changed_record_passes(self):
        self.validate()

    def test_generic_urls_without_listing_review_fail(self):
        del self.report['coverage']['domestic_media']['listing_checks']
        with self.assertRaisesRegex(ValueError, 'listing review'):
            self.validate()

    def test_unavailable_listings_do_not_establish_coverage(self):
        self.report['coverage']['domestic_media']['listing_checks'][1]['result'] = 'unavailable'
        with self.assertRaisesRegex(ValueError, 'two available'):
            self.validate()

    def test_alternative_listing_can_restore_coverage(self):
        coverage = self.report['coverage']['domestic_media']
        coverage['listing_checks'][1]['result'] = 'unavailable'
        coverage['checked_urls'].append('https://alternative.example/news')
        coverage['listing_checks'].append({'url': 'https://alternative.example/news',
            'result': 'reviewed', 'reason': 'Alternative index read', 'candidate_urls': []})
        self.validate()

    def test_media_candidate_without_decision_fails(self):
        self.report['coverage']['domestic_media']['listing_checks'][0]['candidate_urls'].append('https://missing.example/')
        with self.assertRaisesRegex(ValueError, 'no decision'):
            self.validate()

    def test_http_success_without_body_claims_fails(self):
        self.report['source_checks']['official']['supported_claims'] = []
        with self.assertRaisesRegex(ValueError, 'supported claims'):
            self.validate()

    def test_inaccessible_source_cannot_verify_changed_publication(self):
        self.report['source_checks']['official'] = {'result': 'unavailable', 'method': 'web', 'reason': '403'}
        with self.assertRaisesRegex(ValueError, 'body verification'):
            self.validate()

    def test_unreported_changes_fail(self):
        self.report['changed_ids'] = []
        with self.assertRaisesRegex(ValueError, 'actual record'):
            self.validate()

    def test_source_only_change_requires_reverification(self):
        before_sources = copy.deepcopy(self.sources)
        self.sources[0]['url'] = 'https://changed.example/announcement'
        self.assertEqual({'incident'}, module.changed_incident_ids(self.records, self.records, before_sources, self.sources))

    def test_pending_decision_cannot_point_to_published_record(self):
        self.candidate['decision'] = 'pending'
        with self.assertRaisesRegex(ValueError, 'Pending decision'):
            self.validate()

    def test_omitted_unresolved_lead_fails(self):
        lead = dict(self.candidate, incident_id=None, url='https://unresolved.example/')
        with self.assertRaisesRegex(ValueError, 'Unresolved candidate omitted'):
            self.validate([lead])

    def test_new_incident_id_can_resolve_previous_discovery_url(self):
        self.validate([dict(self.candidate, incident_id=None, decision='deferred')])

    def test_changed_record_needs_matching_decision(self):
        self.candidate['decision'] = 'duplicate'
        with self.assertRaisesRegex(ValueError, 'no matching candidate'):
            self.validate()

    def test_no_change_audit_can_pass_with_real_listing_reviews(self):
        self.report['changed_ids'] = []
        self.report['candidates'] = []
        self.report['source_checks'] = {}
        for coverage in self.report['coverage'].values():
            for listing in coverage['listing_checks']:
                listing['candidate_urls'] = []
        module.validate_quality(self.report, self.records, self.sources, set())

    def test_deferred_survives_intervening_no_change_report(self):
        lead = dict(self.candidate, incident_id=None, decision='deferred')
        reports = [{'completed_at': '2026-10-01T00:00:00Z', 'candidates': [lead]},
                   {'completed_at': '2026-10-02T00:00:00Z', 'candidates': []}]
        self.assertEqual([lead], module.collect_carryover(reports, [], 'fresh', self.now))

    def test_later_decision_resolves_unlinked_lead(self):
        lead = dict(self.candidate, incident_id=None, decision='deferred')
        reports = [{'completed_at': '2026-10-01T00:00:00Z', 'candidates': [lead]},
                   {'completed_at': '2026-10-02T00:00:00Z', 'candidates': [self.candidate]}]
        self.assertEqual([], module.collect_carryover(reports, self.records, 'historical', self.now))

    def test_historical_keeps_normal_deferred_and_all_pending(self):
        lead = dict(self.candidate, incident_id=None, decision='deferred', priority='normal')
        pending = dict(self.records[0], publication_status='pending', published_at='2026-09-01')
        reports = [{'completed_at': '2026-10-01T00:00:00Z', 'candidates': [lead]}]
        self.assertEqual([], module.collect_carryover(reports, [pending], 'fresh', self.now))
        self.assertEqual(2, len(module.collect_carryover(reports, [pending], 'historical', self.now)))

    def test_input_snapshot_keeps_multiple_pending_ids(self):
        candidates = [dict(self.candidate, incident_id=incident_id, url=None, decision='pending')
                      for incident_id in ('first', 'second')]
        pending = [dict(self.records[0], id=incident_id, publication_status='pending')
                   for incident_id in ('first', 'second')]
        reports = [{'completed_at': '2026-10-01T00:00:00Z', 'candidates': candidates}]
        carried = module.collect_carryover(reports, pending, 'historical', self.now)
        self.assertEqual({'first', 'second'}, {item['incident_id'] for item in carried})

    def test_incident_deletion_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'preserve existing'):
            module.changed_incident_ids(self.records, [], self.sources, self.sources)


if __name__ == '__main__':
    unittest.main()
