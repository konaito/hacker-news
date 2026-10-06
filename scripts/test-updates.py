"""Check public changes, candidate exclusion, withdrawals and history escaping."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from updates import public_changes, render_entry, timestamp_html, parse_timestamp


class HistoryTests(unittest.TestCase):
    def test_utc_z_on_launchagent_python(self):
        self.assertEqual(parse_timestamp('2026-10-05T23:41:44Z'), parse_timestamp('2026-10-05T23:41:44+00:00'))
        self.assertIn('2026年10月06日 08:41', timestamp_html('2026-10-05T23:41:44Z'))

    def setUp(self):
        self.record = {'id': 'example-2026', 'publication_status': 'published', 'company': 'Example', 'title': 'Title', 'summary': 'Summary', 'sources': ['s1'], 'last_verified_at': '2026-10-06'}
        self.sources = [{'id': 's1', 'title': 'Announcement', 'url': 'https://example.com/'}]

    def changes(self, before, after, sources=None):
        return public_changes(before, after, self.sources, sources or self.sources)

    def test_candidate_promoted_and_withdrawn(self):
        pending = dict(self.record, publication_status='pending')
        self.assertEqual(self.changes([], [pending]), [])
        self.assertEqual(self.changes([pending], [self.record])[0]['action'], 'added')
        self.assertEqual(self.changes([self.record], [pending])[0]['action'], 'withdrawn')

    def test_confirmation_dates_do_not_create_updates(self):
        later = dict(self.record, last_verified_at='2026-10-07', verification_note='Checked again')
        self.assertEqual(self.changes([self.record], [later]), [])

    def test_content_and_referenced_source_changes(self):
        revised = dict(self.record, summary='Correction')
        self.assertEqual(self.changes([self.record], [revised])[0]['action'], 'updated')
        source = [dict(self.sources[0], url='https://example.com/correction')]
        self.assertEqual(self.changes([self.record], [self.record], source)[0]['action'], 'updated')
        self.assertEqual(self.changes([self.record], [self.record], self.sources + [{'id': 'unused'}]), [])

    def test_render_hides_unpublished_titles_and_escapes_text(self):
        changes = self.changes([], [dict(self.record, title='<script>')])
        entry = {'timestamp': '2026-10-05T23:00:00+00:00', 'summary': '<summary>', 'changes': changes}
        html = render_entry(entry, {'example-2026'})
        self.assertIn('&lt;summary&gt;', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('/news/example-2026/', html)
        hidden = render_entry(entry, set())
        self.assertNotIn('/news/', hidden)
        self.assertNotIn('&lt;script&gt;', hidden)
        self.assertIn('2026年10月06日 08:00', timestamp_html(entry['timestamp']))


if __name__ == '__main__':
    unittest.main()
