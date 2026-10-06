"""Check public changes, candidate exclusion, withdrawals and history escaping."""
import sys
import unittest
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from updates import public_changes, render_entry, timestamp_html, parse_timestamp, load_history


class HistoryTests(unittest.TestCase):
    def test_history_tracks_real_commits_and_ignores_working_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', directory, *args], text=True).strip()
            git('init', '-b', 'main')
            git('config', 'user.name', 'Test')
            git('config', 'user.email', 'test@example.com')
            (root / 'data').mkdir()
            (root / 'data/updates.json').write_text('invalid legacy history')
            git('add', '.')
            git('commit', '-m', 'Initial site')
            first = git('rev-parse', 'HEAD')
            git('commit', '--allow-empty', '-m', 'Site maintenance <script>')
            latest = git('rev-parse', 'HEAD')
            (root / 'data/updates.json').write_text('uncommitted changes')
            entries = load_history(root)
            self.assertEqual([entry['id'] for entry in entries], [latest, first])
            self.assertEqual(entries[0]['timestamp'], git('show', '-s', '--format=%cI', 'HEAD'))
            html = render_entry(entries[0], set(), details=False)
            self.assertIn('/commit/' + latest, html)
            self.assertIn('Site maintenance &lt;script&gt;', html)
            self.assertEqual(entries, load_history(root))
            shallow = root / 'shallow'
            subprocess.run(['git', 'clone', '--depth', '1', root.as_uri(), str(shallow)], check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, 'full Git checkout'):
                load_history(shallow)
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
