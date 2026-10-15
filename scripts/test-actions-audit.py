"""Exercise cloud publication with real Git remotes and simulated research evidence."""
import importlib.util
import json
import shutil
import subprocess
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cloud = load('cloud_audit', 'actions-audit.py')
fixtures = load('recovery_fixture', 'test-audit-recovery.py')


class CloudAuditTests(unittest.TestCase):
    write = fixtures.RecoveryTests.write
    git = fixtures.RecoveryTests.git
    prepare_report = fixtures.RecoveryTests.prepare

    def setUp(self):
        fixtures.RecoveryTests.setUp(self)
        self.write('data/sources.json', json.dumps([{'id': 'official', 'url': 'https://primary.example/incident'}]))
        self.write('data/monthly-digests.json', '[]')
        self.write('data/featured-reading.json', '[]')
        for path in (self.root / 'data').glob('*.json'):
            cloud.write_json(path, json.loads(path.read_text()))
        self.git('add', 'data')
        self.git('commit', '-m', 'Complete data fixture')
        self.git('push', 'origin', 'main')
        self.base = self.git('rev-parse', 'HEAD')
        self.audit = cloud.ActionsAudit(self.root)
        self.artifact = self.root / '.audit/result'
        self.build = patch.object(self.audit, 'validate_build')
        self.build.start()
        self.addCleanup(self.build.stop)

    def research(self, *, change=True):
        self.audit.prepare('fresh')
        self.context = cloud.read_json(self.root / '.audit/cloud/context.json')
        for path in (self.root / 'data').glob('*.json'):
            target = self.artifact / 'data' / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        action = self.prepare_report(change=change, unrelated=False)
        self.report = action['report']
        self.report['completed_at'] = datetime.now(timezone.utc).isoformat()
        if change:
            cloud.write_json(self.artifact / 'data/incidents.json', [dict(self.record, summary='Verified follow-up')])
        self.save_report()

    def save_report(self):
        cloud.write_json(self.artifact / '.audit/fresh/current-report.json', self.report)

    def finalize(self, run_id='123'):
        return self.audit.finalize(self.artifact, 'fresh', self.base,
                                   self.context['started_at'], self.context['state_base'], run_id)

    def remote_main(self):
        return subprocess.check_output(['git', '--git-dir', str(self.origin), 'rev-parse', 'main'], text=True).strip()

    def test_valid_report_publishes_data_and_checkpoint_atomically(self):
        self.research()
        self.assertTrue(self.finalize())
        head = self.git('rev-parse', 'HEAD')
        self.assertNotEqual(head, self.base)
        self.assertEqual(head, self.remote_main())
        _, state = self.audit.read_state()
        self.assertEqual(state['last_success']['fresh']['main_sha'], head)
        self.assertEqual(state['last_attempt']['result'], 'success')

    def test_no_change_updates_state_without_news_commit(self):
        self.research(change=False)
        self.assertTrue(self.finalize())
        self.assertEqual(self.remote_main(), self.base)
        _, state = self.audit.read_state()
        self.assertIn('fresh', state['last_success'])

    def test_missing_report_preserves_leads_without_publishing(self):
        self.research()
        (self.artifact / '.audit/fresh/current-report.json').unlink()
        self.assertFalse(self.finalize())
        self.assertEqual(self.remote_main(), self.base)
        _, state = self.audit.read_state()
        self.assertEqual(state['last_success'], {})
        self.assertTrue(state['candidates'][0]['requires_recheck'])
        self.assertEqual(state['candidates'][0]['incident_id'], 'incident')

    def test_single_unverified_source_report_is_rejected(self):
        self.research()
        self.report['source_checks'] = {}
        self.save_report()
        self.assertFalse(self.finalize())
        self.assertEqual(self.remote_main(), self.base)
        _, state = self.audit.read_state()
        self.assertEqual(state['last_success'], {})

    def test_stale_report_is_not_published(self):
        self.research()
        self.report['completed_at'] = '2026-10-01T00:00:00Z'
        self.save_report()
        self.assertFalse(self.finalize())
        self.assertEqual(self.remote_main(), self.base)

    def test_changed_ids_must_match_actual_changes(self):
        self.research()
        self.report['changed_ids'] = []
        self.save_report()
        self.assertFalse(self.finalize())
        self.assertEqual(self.remote_main(), self.base)

    def test_main_advance_preserves_remote_edit_and_research_leads(self):
        self.research()
        other = Path(self.temporary.name) / 'other'
        subprocess.run(['git', 'clone', '-b', 'main', str(self.origin), str(other)], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(other), 'config', 'user.name', 'Other'], check=True)
        subprocess.run(['git', '-C', str(other), 'config', 'user.email', 'other@example.com'], check=True)
        (other / 'public/style.css').write_text('Concurrent remote change')
        subprocess.run(['git', '-C', str(other), 'commit', '-am', 'Remote change'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(other), 'push'], check=True, capture_output=True)
        advanced = self.remote_main()
        self.assertFalse(self.finalize())
        self.assertEqual(self.remote_main(), advanced)
        _, state = self.audit.read_state()
        self.assertEqual(state['last_success'], {})
        self.assertTrue(state['candidates'])

    def test_main_push_rejection_cannot_advance_success_checkpoint(self):
        self.research()
        hook = self.origin / 'hooks/pre-receive'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        with self.assertRaises(subprocess.CalledProcessError):
            self.finalize()
        self.assertEqual(self.remote_main(), self.base)
        state_base, state = self.audit.read_state()
        self.assertEqual(state_base, '')
        self.assertEqual(state['last_success'], {})
        hook.unlink()
        # A new Actions checkout retries the preserved artifact at the same baseline.
        self.git('reset', '--hard', self.base)
        self.assertTrue(self.finalize())

    def test_replayed_success_does_not_create_duplicate_news_commit(self):
        self.research()
        self.assertTrue(self.finalize())
        published = self.remote_main()
        self.git('reset', '--hard', self.base)
        self.assertTrue(self.finalize())
        self.assertEqual(self.remote_main(), published)

    def test_unresolved_candidates_cannot_disappear_on_invalid_report(self):
        state = cloud.empty_state()
        lead = {'title': 'Older lead', 'url': 'https://other.example/lead', 'incident_id': None,
                'priority': 'high', 'decision': 'deferred', 'reason': 'Needs verification'}
        state['candidates'] = [lead]
        self.audit.push(state, '')
        self.research()
        self.assertFalse(self.finalize())
        _, saved = self.audit.read_state()
        self.assertIn(lead['url'], [candidate['url'] for candidate in saved['candidates']])

    def test_rechecks_rotate_without_dropping_the_rest(self):
        state = cloud.empty_state()
        state['candidates'] = [
            {'title': str(i), 'url': 'https://example.com/' + str(i), 'incident_id': None,
             'priority': 'high', 'decision': 'deferred', 'reason': 'Needs verification'} for i in range(30)]
        self.audit.push(state, '')
        self.research(change=False)
        selected = self.context['required_candidates']
        self.assertEqual(len(selected), 8)
        self.report['candidates'] = selected
        self.save_report()
        self.assertTrue(self.finalize())
        _, saved = self.audit.read_state()
        self.assertEqual(len(saved['candidates']), 30)
        following = cloud.select_candidates(saved, [self.record], 'fresh', datetime.now(timezone.utc))
        self.assertFalse({candidate['url'] for candidate in selected} & {candidate['url'] for candidate in following})
        self.assertEqual(len(cloud.select_candidates(saved, [self.record], 'historical', datetime.now(timezone.utc))), 20)

    def test_build_failure_preserves_old_checkpoint_and_does_not_publish(self):
        self.research()
        self.audit.validate_build.side_effect = subprocess.CalledProcessError(1, ['validation'])
        self.assertFalse(self.finalize())
        self.assertEqual(self.remote_main(), self.base)
        _, state = self.audit.read_state()
        self.assertEqual(state['last_success'], {})

    def test_symlink_artifact_is_never_used_as_data(self):
        self.research()
        path = self.artifact / 'data/incidents.json'
        path.unlink()
        path.symlink_to(self.root / 'data/incidents.json')
        self.assertFalse(self.finalize())
        self.assertEqual(self.remote_main(), self.base)

    def test_claude_artifact_cannot_replace_build_scripts(self):
        self.research()
        malicious = self.artifact / 'scripts/build.py'
        malicious.parent.mkdir()
        malicious.write_text('raise RuntimeError("Untrusted artifact must not run")')
        original = (self.root / 'scripts/hourly-audit.py').read_bytes()
        self.assertTrue(self.finalize())
        self.assertEqual((self.root / 'scripts/hourly-audit.py').read_bytes(), original)

    def test_wrong_report_shape_is_rejected_without_losing_state(self):
        self.research()
        cloud.write_json(self.artifact / '.audit/fresh/current-report.json', [])
        self.assertFalse(self.finalize())
        self.assertEqual(self.remote_main(), self.base)
        _, state = self.audit.read_state()
        self.assertEqual(state['last_success'], {})

    def test_research_cannot_change_user_selected_article_urls(self):
        self.research()
        cloud.write_json(self.artifact / 'data/featured-reading.json', [{'url': 'https://unrequested.example/'}])
        self.assertFalse(self.finalize())
        self.assertEqual(self.remote_main(), self.base)

    def test_claude_can_check_report_before_publication(self):
        self.research()
        shutil.copy2(self.artifact / 'data/incidents.json', self.root / 'data/incidents.json')
        target = self.root / '.audit/fresh/current-report.json'
        cloud.write_json(target, self.report)
        self.audit.check('fresh')
        self.report['candidates'].append({'title': 'Unknown duplicate', 'url': 'https://other.example/',
                                          'priority': 'normal', 'decision': 'duplicate',
                                          'incident_id': None, 'reason': 'Existing record not identified'})
        cloud.write_json(target, self.report)
        with self.assertRaisesRegex(ValueError, 'matching incident: https://other.example/'):
            self.audit.check('fresh')


if __name__ == '__main__':
    unittest.main()
