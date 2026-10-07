"""Exercise publication retries with real local Git repositories and simulated research."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HARNESS = '''
import json
import runpy
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

root = Path.cwd()
real_run = subprocess.run
def run(command, **kwargs):
    if command[0] == 'codex':
        count = root / '.audit/research-calls'
        count.write_text(str(int(count.read_text()) + 1) if count.exists() else '1')
        action = json.loads((root / '.audit/action.json').read_text())
        if action['change']:
            path = root / 'data/incidents.json'
            records = json.loads(path.read_text())
            records[0]['summary'] = 'Verified follow-up'
            path.write_text(json.dumps(records))
        if action['unrelated']:
            (root / 'public/style.css').write_text('User interface edit')
            if action.get('staged'):
                real_run(['git', 'add', 'public/style.css'], check=True)
        report = action['report']
        report['completed_at'] = datetime.now(timezone.utc).isoformat()
        (root / '.audit/fresh/current-report.json').write_text(json.dumps(report))
        return subprocess.CompletedProcess(command, 0)
    if command[0] in {'python3', 'node'}:
        return subprocess.CompletedProcess(command, 0)
    if command[:2] == ['git', 'push'] and (root / '.audit/fail-push').exists():
        (root / '.audit/fail-push').unlink()
        raise subprocess.CalledProcessError(1, command)
    return real_run(command, **kwargs)

with patch('subprocess.run', side_effect=run):
    runpy.run_path(str(root / 'scripts/hourly-audit.py'), run_name='__main__')
'''


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'checkout'
        self.root.mkdir()
        self.origin = Path(self.temporary.name) / 'origin.git'
        self.git('init', '-b', 'main')
        self.git('config', 'user.email', 'test@example.com')
        self.git('config', 'user.name', 'Audit test')
        for name in ('hourly-audit.py', 'audit-report.py', 'audit-recovery.py'):
            target = self.root / 'scripts' / name
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(ROOT / 'scripts' / name, target)
        shutil.copyfile(ROOT / 'updates.py', self.root / 'updates.py')
        self.write('.gitignore', '.audit/\n__pycache__/\n')
        self.record = {'id': 'incident', 'company': 'Company', 'title': 'Incident',
                       'summary': 'Original', 'sources': ['official'],
                       'published_at': '2026-10-07', 'publication_status': 'published'}
        self.write('data/incidents.json', json.dumps([self.record]))
        self.write('data/sources.json', json.dumps([{'id': 'official'}]))
        for name in ('index.html', 'sitemap.xml', 'feed.xml', 'sw.js', 'updates/index.html',
                     'news/incident/index.html', 'archive/2026-10/index.html', 'style.css'):
            self.write('public/' + name, 'Original')
        self.write('.codex/news-audit.md', 'Simulated research')
        self.write('.codex/news-audit-fresh.md', 'Simulated fresh audit')
        self.git('add', '.')
        self.git('commit', '-m', 'Initial')
        self.base = self.git('rev-parse', 'HEAD')
        subprocess.run(['git', 'init', '--bare', str(self.origin)], check=True, capture_output=True)
        self.git('remote', 'add', 'origin', str(self.origin))
        self.git('push', '-u', 'origin', 'main')
        self.write('.audit/harness.py', HARNESS)
        self.state = self.root / '.audit/fresh'
        self.state.mkdir()

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args],
                                       text=True, stderr=subprocess.DEVNULL).strip()

    def prepare(self, *, change=True, unrelated=True, staged=False):
        candidate = {'title': 'Incident', 'url': 'https://primary.example/incident',
                     'reason': 'Simulated primary source verified', 'priority': 'high',
                     'decision': 'updated', 'incident_id': 'incident'}
        report = {'schema_version': 2, 'quality_version': 1, 'mode': 'fresh',
                  'searches': ['incident'], 'summary': 'Simulated audit',
                  'changed_ids': ['incident'] if change else [], 'pending_ids': [],
                  'candidates': [candidate] if change else [], 'source_checks': {},
                  'coverage': {}}
        if change:
            report['source_checks']['official'] = {'result': 'body_checked', 'method': 'simulation',
                                                   'supported_claims': ['Verified follow-up']}
        for channel in ('domestic_media', 'international_media', 'official', 'social_leads'):
            urls = ['https://first.example/news', 'https://second.example/news']
            report['coverage'][channel] = {'searches': ['incident'], 'checked_urls': urls,
                                           'limitations': []}
            if channel.endswith('media'):
                report['coverage'][channel]['listing_checks'] = [
                    {'url': url, 'result': 'reviewed', 'reason': 'Simulated listing review',
                     'candidate_urls': [candidate['url']] if change else []} for url in urls]
        action = {'change': change, 'unrelated': unrelated, 'staged': staged, 'report': report}
        self.write('.audit/action.json', json.dumps(action))
        return action

    def audit(self, *args):
        return subprocess.run([sys.executable, str(self.root / '.audit/harness.py'), *args],
                              cwd=self.root, capture_output=True, text=True)

    def assert_saved(self):
        self.assertTrue((self.state / 'publication-retry.json').exists())
        self.assertFalse((self.state / 'last-success.json').exists())

    def test_concurrent_ui_edit_is_saved_then_retried_after_ui_commit(self):
        self.prepare()
        self.assertNotEqual(self.audit().returncode, 0)
        self.assert_saved()
        self.assertIn('unrelated edits remain', self.audit().stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)
        self.git('add', 'public/style.css')
        self.git('commit', '-m', 'Finish user interface edit')
        result = self.audit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / '.audit/research-calls').read_text(), '1')
        self.assertEqual(self.git('status', '--porcelain'), '')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'origin/main'))
        self.assertTrue((self.state / 'last-success.json').exists())
        self.assertFalse((self.state / 'publication-retry.json').exists())
        self.assertEqual((self.root / 'public/style.css').read_text(), 'User interface edit')

    def test_staged_unrelated_edit_is_not_committed(self):
        self.prepare(staged=True)
        self.assertNotEqual(self.audit().returncode, 0)
        self.assert_saved()
        self.assertEqual(self.git('diff', '--cached', '--name-only'), 'public/style.css')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)

    def test_later_data_edit_is_preserved_and_rejected(self):
        self.prepare()
        self.audit()
        self.write('data/incidents.json', json.dumps([dict(self.record, summary='Later user edit')]))
        result = self.audit()
        self.assertIn('data changed after verification', result.stderr)
        self.assert_saved()
        self.assertIn('Later user edit', (self.root / 'data/incidents.json').read_text())

    def test_report_change_is_rejected(self):
        self.prepare()
        self.audit()
        report = self.state / 'current-report.json'
        report.write_text(report.read_text() + '\n')
        self.assertIn('report changed after verification', self.audit().stderr)
        self.assert_saved()

    def test_invalid_report_is_never_saved_for_retry(self):
        action = self.prepare()
        action['report']['source_checks'] = {}
        self.write('.audit/action.json', json.dumps(action))
        self.assertNotEqual(self.audit().returncode, 0)
        self.assertFalse((self.state / 'publication-retry.json').exists())
        self.assertFalse((self.state / 'last-success.json').exists())

    def test_failed_push_is_retried_without_new_research_or_duplicate_commit(self):
        self.prepare(unrelated=False)
        self.write('.audit/fail-push', 'Fail once')
        self.assertNotEqual(self.audit().returncode, 0)
        self.assert_saved()
        committed = self.git('rev-parse', 'HEAD')
        self.assertNotEqual(committed, self.base)
        result = self.audit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD'), committed)
        self.assertEqual(self.git('rev-parse', 'origin/main'), committed)
        self.assertEqual((self.root / '.audit/research-calls').read_text(), '1')

    def test_newer_remote_commit_is_not_overwritten(self):
        self.prepare()
        self.audit()
        self.git('restore', 'public/style.css')
        other = Path(self.temporary.name) / 'other'
        subprocess.run(['git', 'clone', '-b', 'main', str(self.origin), str(other)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(other), 'config', 'user.email', 'other@example.com'], check=True)
        subprocess.run(['git', '-C', str(other), 'config', 'user.name', 'Other'], check=True)
        (other / 'public/style.css').write_text('Remote edit')
        subprocess.run(['git', '-C', str(other), 'commit', '-am', 'Remote change'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(other), 'push'], check=True, capture_output=True)
        self.assertNotEqual(self.audit().returncode, 0)
        self.assert_saved()
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)

    def test_no_change_audit_does_not_create_a_commit(self):
        self.prepare(change=False, unrelated=False)
        result = self.audit()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)
        self.assertTrue((self.state / 'last-success.json').exists())

    def test_legacy_audit_can_resume_from_explicit_baseline(self):
        self.prepare()
        self.audit()
        (self.state / 'publication-retry.json').unlink()
        self.git('restore', 'public/style.css')
        result = self.audit('--resume-from', self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / '.audit/research-calls').read_text(), '1')

    def test_dirty_checkout_without_saved_audit_is_preserved(self):
        self.prepare(unrelated=False)
        self.write('public/style.css', 'Uncommitted user edit')
        self.assertIn('uncommitted edits', self.audit().stderr)
        self.assertFalse((self.root / '.audit/research-calls').exists())
        self.assertEqual((self.root / 'public/style.css').read_text(), 'Uncommitted user edit')


if __name__ == '__main__':
    unittest.main()
