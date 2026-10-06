"""Reject incomplete or stale audits without advancing the success checkpoint."""
import copy
import unittest
from datetime import datetime, timedelta, timezone
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

spec = spec_from_file_location('audit_report', Path(__file__).with_name('audit-report.py'))
module = module_from_spec(spec)
spec.loader.exec_module(module)


class AuditReportTests(unittest.TestCase):
    def setUp(self):
        self.started = datetime.now(timezone.utc) - timedelta(seconds=2)
        self.report = {
            'schema_version': 2, 'quality_version': 1, 'source_checks': {}, 'mode': 'fresh', 'completed_at': datetime.now(timezone.utc).isoformat(),
            'searches': ['breach'], 'changed_ids': [], 'pending_ids': [],
            'summary': 'No verified new incidents', 'candidates': [],
            'coverage': {key: {'searches': ['breach'], 'checked_urls': ['https://example.com/news'],
                               'limitations': []} for key in module.CHANNELS},
        }

        for channel in ('domestic_media', 'international_media'):
            coverage = self.report['coverage'][channel]
            coverage['checked_urls'] = ['https://first.example/news', 'https://second.example/news']
            coverage['listing_checks'] = [
                {'url': url, 'result': 'reviewed', 'candidate_urls': [],
                 'reason': 'Latest articles reconciled; no incident leads'}
                for url in coverage['checked_urls']]

    def test_complete_no_change_audit_is_valid(self):
        module.validate_report(self.report, self.started, {'existing'})

    def test_missing_discovery_route_is_rejected(self):
        for key in module.CHANNELS - {'historical'}:
            report = copy.deepcopy(self.report)
            del report['coverage'][key]
            with self.assertRaises(ValueError):
                module.validate_report(report, self.started, set())

    def test_historical_requires_backfill_and_accepts_no_social(self):
        self.report['mode'] = 'historical'
        del self.report['coverage']['social_leads']
        module.validate_report(self.report, self.started, set(), 'historical')
        del self.report['coverage']['historical']
        with self.assertRaises(ValueError):
            module.validate_report(self.report, self.started, set(), 'historical')

    def test_wrong_loop_report_is_rejected(self):
        with self.assertRaises(ValueError):
            module.validate_report(self.report, self.started, set(), 'historical')

    def test_stale_report_is_rejected(self):
        self.report['completed_at'] = (self.started - timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError):
            module.validate_report(self.report, self.started, set())

    def test_unmatched_publication_is_rejected(self):
        self.report['candidates'] = [{'title': 'Breaking', 'url': 'https://example.com',
            'priority': 'high', 'decision': 'published', 'incident_id': None, 'reason': 'Confirmed'}]
        with self.assertRaises(ValueError):
            module.validate_report(self.report, self.started, set())


def load_tests(loader, tests, pattern):
    quality_spec = spec_from_file_location('audit_quality_tests', Path(__file__).with_name('test-audit-quality.py'))
    quality_tests = module_from_spec(quality_spec)
    quality_spec.loader.exec_module(quality_tests)
    tests.addTests(loader.loadTestsFromModule(quality_tests))
    return tests


if __name__ == '__main__':
    unittest.main()
