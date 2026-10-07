"""Audit locally and push verified updates; GitHub Actions deploys main."""
import fcntl
import json
import os
import subprocess
import sys
import argparse
import time
from pathlib import Path
from datetime import datetime, timezone
from importlib.util import spec_from_file_location, module_from_spec

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from updates import change_summary, public_changes
spec = spec_from_file_location('audit_report', ROOT / 'scripts/audit-report.py')
audit_report = module_from_spec(spec)
spec.loader.exec_module(audit_report)
spec = spec_from_file_location('audit_recovery', ROOT / 'scripts/audit-recovery.py')
audit_recovery = module_from_spec(spec)
spec.loader.exec_module(audit_recovery)
STATE = ROOT / '.audit'
STATE.mkdir(exist_ok=True)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mode', choices=('fresh', 'historical'), default='fresh')
parser.add_argument('--resume-from', help='Recover a completed legacy audit using its original Git baseline')
args = parser.parse_args()
MODE_STATE = STATE / args.mode
MODE_STATE.mkdir(exist_ok=True)
lock = (STATE / 'run.lock').open('w')
deadline = time.monotonic() + (1800 if args.mode == 'historical' else 0)
while True:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        break
    except BlockingIOError:
        if time.monotonic() >= deadline:
            print('Audit deferred: another loop is running.', flush=True)
            sys.exit(0)
        time.sleep(10)
os.chdir(ROOT)
env = os.environ.copy()
env['PATH'] = '/Users/konaito/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'

def run(args, **kwargs):
    return subprocess.run(args, check=True, env=env, **kwargs)

def git(*args):
    return subprocess.check_output(['git', *args], text=True, env=env).strip()

def changed_paths():
    paths = subprocess.check_output(['git', 'diff', 'HEAD', '--name-only', '-z'], env=env).decode().split('\0')
    paths += subprocess.check_output(['git', 'ls-files', '--others', '--exclude-standard', '-z'], env=env).decode().split('\0')
    return {path for path in paths if path}


if git('branch', '--show-current') != 'main':
    raise SystemExit('Audit requires the main branch.')
if 'origin' not in git('remote').splitlines():
    raise SystemExit('Configure the GitHub origin with scripts/setup-github.py first.')
checkpoint = MODE_STATE / 'last-success.json'
report_path = MODE_STATE / 'current-report.json'
carryover_path = MODE_STATE / 'carryover-input.json'
recovery_path = MODE_STATE / 'publication-retry.json'
recovery = json.loads(recovery_path.read_text()) if recovery_path.exists() else None
if args.resume_from:
    if recovery:
        raise SystemExit('A publication retry already exists; run without --resume-from.')
    base_commit = git('rev-parse', '--verify', args.resume_from + '^{commit}')
    run(['git', 'merge-base', '--is-ancestor', base_commit, 'HEAD'])
    if git('diff', base_commit, 'HEAD', '--', 'data/'):
        raise SystemExit('Committed audit data changed since the supplied baseline; manual reconciliation required.')
    original_input = json.loads(carryover_path.read_text())
    started_at = datetime.fromisoformat(original_input['completed_at'].replace('Z', '+00:00'))
    carryover = original_input['candidates']
elif recovery:
    audit_recovery.check_recovery(recovery, ROOT, report_path)
    base_commit = recovery['base_commit']
    run(['git', 'merge-base', '--is-ancestor', base_commit, 'HEAD'])
    started_at = datetime.fromisoformat(recovery['started_at'])
    carryover = recovery['carryover']
    if not audit_recovery.allowed_changes(changed_paths()):
        raise SystemExit('Publication retry deferred: unrelated edits remain; verified audit is saved.')
    print('Resuming saved audit publication without repeating research.', flush=True)
else:
    if git('status', '--porcelain'):
        raise SystemExit('Checkout has uncommitted edits; audit deferred to preserve user work.')

# A saved audit must not overwrite newer remote data. Keep it for reconciliation.
run(['git', 'fetch', 'origin', 'main'])
if recovery or args.resume_from:
    run(['git', 'merge-base', '--is-ancestor', 'origin/main', 'HEAD'])
else:
    run(['git', 'merge', '--ff-only', 'origin/main'])
    base_commit = git('rev-parse', 'HEAD')
    started_at = datetime.now(timezone.utc)
before_incidents = json.loads(git('show', base_commit + ':data/incidents.json'))
before_sources = json.loads(git('show', base_commit + ':data/sources.json'))
if not recovery and not args.resume_from:
    prior_reports = []
    for mode in ('fresh', 'historical'):
        directory = STATE / mode
        paths = list((directory / 'reports').glob('*.json'))
        paths.extend(directory / name for name in ('last-success.json', 'carryover-input.json'))
        if not (directory / 'last-success.json').exists():
            paths.append(directory / 'current-report.json')
        for path in paths:
            if path.exists():
                prior_reports.append(json.loads(path.read_text()))
    carryover = audit_report.collect_carryover(prior_reports, before_incidents, args.mode, started_at)
    carryover_path.write_text(json.dumps({
        'completed_at': started_at.isoformat(), 'candidates': carryover,
    }, ensure_ascii=False, indent=2) + '\n')
    report_path.unlink(missing_ok=True)
    prompt = (ROOT / '.codex/news-audit.md').read_text()
    prompt += '\n' + (ROOT / ('.codex/news-audit-' + args.mode + '.md')).read_text()
    prompt += '\n今回の必須再調査候補（runnerが過去報告とpendingから抽出）:\n'
    prompt += json.dumps(carryover, ensure_ascii=False, indent=2)
    prompt += '\n各候補を実際に再調査し、元urlまたはincident_idを維持してcandidatesへ判断を記録する。未検証の情報を事実として掲載しない。\n'
    run(['codex', 'exec', '-C', str(ROOT), '-s', 'danger-full-access',
         '-c', 'approval_policy="never"', '-c', 'web_search="live"',
         '-o', str(MODE_STATE / 'last-response.txt'), '-'], input=prompt, text=True,
        timeout=1500 if args.mode == 'fresh' else 3000)
if not report_path.exists():
    raise SystemExit('Audit did not produce a discovery report.')
completion = json.loads(report_path.read_text())
after_incidents = json.loads((ROOT / 'data/incidents.json').read_text())
after_sources = json.loads((ROOT / 'data/sources.json').read_text())
incident_ids = {record['id'] for record in after_incidents}
changed_ids = audit_report.changed_incident_ids(before_incidents, after_incidents, before_sources, after_sources)
audit_report.validate_report(completion, started_at, incident_ids, args.mode,
                             incidents=after_incidents, sources=after_sources,
                             changed_ids=changed_ids, carryover=carryover)
if not recovery:
    recovery = audit_recovery.save_recovery(recovery_path, ROOT, report_path, base_commit, started_at, carryover)
audit_recovery.check_recovery(recovery, ROOT, report_path)
changed = changed_paths()
allowed_files = audit_recovery.ALLOWED_FILES
if not audit_recovery.allowed_changes(changed):
    raise SystemExit('Unexpected changes; publication deferred. Verified audit saved for retry after edits finish.')
if changed:
    changes = public_changes(before_incidents, json.loads((ROOT / 'data/incidents.json').read_text()), before_sources, json.loads((ROOT / 'data/sources.json').read_text()))
    if changes:
        subject = 'Update verified cybersecurity news: ' + change_summary(changes)
    else:
        subject = 'Update cybersecurity research data'
    for script in ('scripts/validate.py', 'build.py', 'scripts/check-page.py', 'scripts/check-seo-pwa.py'):
        run(['python3', script])
    for script in ('public/app.js', 'public/pwa.js', 'public/sw.js'):
        run(['node', '--check', script])
    run(['node', 'scripts/test-service-worker.cjs'])
    audit_recovery.check_recovery(recovery, ROOT, report_path)
    if not audit_recovery.allowed_changes(changed_paths()):
        raise SystemExit('Unexpected changes during validation; verified audit saved for retry.')
    run(['git', 'add', 'data', *sorted(allowed_files), 'public/news', 'public/archive'])
    run(['git', 'commit', '-m', subject])
# Retry a previously failed push even when the latest audit has no content changes.
head = git('rev-parse', 'HEAD')
if head != git('rev-parse', 'origin/main'):
    run(['git', 'push', 'origin', 'main'])
(STATE / 'pushed-commit').write_text(head + '\n')
history = MODE_STATE / 'reports'
history.mkdir(exist_ok=True)
report_name = started_at.strftime('%Y%m%dT%H%M%S%fZ') + '.json'
(history / report_name).write_bytes(report_path.read_bytes())
temporary = MODE_STATE / 'last-success.tmp'
temporary.write_bytes(report_path.read_bytes())
temporary.replace(checkpoint)
recovery_path.unlink()
print('Audit complete; main synchronized with GitHub. Deployment is handled by GitHub Actions.')
