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
STATE = ROOT / '.audit'
STATE.mkdir(exist_ok=True)
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mode', choices=('fresh', 'historical'), default='fresh')
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

if git('status', '--porcelain'):
    raise SystemExit('Checkout has uncommitted edits; audit deferred to preserve user work.')
if git('branch', '--show-current') != 'main':
    raise SystemExit('Audit requires the main branch.')
if 'origin' not in git('remote').splitlines():
    raise SystemExit('Configure the private GitHub origin with scripts/setup-github.py first.')
# Incorporate merges made on GitHub without overwriting local work or creating merge commits.
run(['git', 'fetch', 'origin', 'main'])
run(['git', 'merge', '--ff-only', 'origin/main'])
before_incidents = json.loads((ROOT / 'data/incidents.json').read_text())
before_sources = json.loads((ROOT / 'data/sources.json').read_text())
checkpoint = MODE_STATE / 'last-success.json'
report_path = MODE_STATE / 'current-report.json'
report_path.unlink(missing_ok=True)
started_at = datetime.now(timezone.utc)
prompt = (ROOT / '.codex/news-audit.md').read_text()
prompt += '\n' + (ROOT / ('.codex/news-audit-' + args.mode + '.md')).read_text()
run(['codex', 'exec', '-C', str(ROOT), '-s', 'danger-full-access',
         '-c', 'approval_policy="never"', '-c', 'web_search="live"',
         '-o', str(MODE_STATE / 'last-response.txt'), '-'], input=prompt, text=True,
    timeout=1500 if args.mode == 'fresh' else 3000)
if not report_path.exists():
    raise SystemExit('Audit did not produce a discovery report.')
completion = json.loads(report_path.read_text())
incident_ids = {record['id'] for record in json.loads((ROOT / 'data/incidents.json').read_text())}
audit_report.validate_report(completion, started_at, incident_ids, args.mode)
changed = set(git('diff', '--name-only').splitlines())
changed.update(git('ls-files', '--others', '--exclude-standard').splitlines())
allowed_files = {'public/index.html', 'public/sitemap.xml', 'public/feed.xml', 'public/sw.js', 'public/updates/index.html'}
if any(not p.startswith(('data/', 'public/news/', 'public/archive/')) and p not in allowed_files for p in changed):
    raise SystemExit('Unexpected changes; push halted.')
if changed:
    changes = public_changes(before_incidents, json.loads((ROOT / 'data/incidents.json').read_text()), before_sources, json.loads((ROOT / 'data/sources.json').read_text()))
    if changes:
        history_path = ROOT / 'data/updates.json'
        history = json.loads(history_path.read_text())
        entry_id = 'audit-' + completion['completed_at']
        if not any(entry['id'] == entry_id for entry in history):
            history.append({'id': entry_id, 'timestamp': completion['completed_at'], 'summary': change_summary(changes), 'changes': changes})
            history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + '\n')
    for script in ('scripts/validate.py', 'build.py', 'scripts/check-page.py', 'scripts/check-seo-pwa.py'):
        run(['python3', script])
    for script in ('public/app.js', 'public/pwa.js', 'public/sw.js'):
        run(['node', '--check', script])
    run(['node', 'scripts/test-service-worker.cjs'])
    run(['git', 'add', 'data', *sorted(allowed_files), 'public/news', 'public/archive'])
    run(['git', 'commit', '-m', 'Update verified cybersecurity news'])
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
print('Audit complete; main synchronized with GitHub. Deployment is handled by GitHub Actions.')
