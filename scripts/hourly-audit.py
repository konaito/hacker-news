"""Audit locally and push verified updates; GitHub Actions deploys main."""
import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from updates import change_summary, public_changes
STATE = ROOT / '.audit'
STATE.mkdir(exist_ok=True)
lock = (STATE / 'run.lock').open('w')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit(0)
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
checkpoint = STATE / 'last-success.json'
previous = checkpoint.read_bytes() if checkpoint.exists() else None
with (ROOT / '.codex/news-audit.md').open() as prompt:
    run(['codex', 'exec', '-C', str(ROOT), '-s', 'danger-full-access',
         '-c', 'approval_policy="never"', '-c', 'web_search="live"',
         '-o', str(STATE / 'last-response.txt'), '-'], stdin=prompt, timeout=3300)
if not checkpoint.exists() or checkpoint.read_bytes() == previous:
    raise SystemExit('Audit did not produce a new completion checkpoint.')
completion = json.loads(checkpoint.read_text())
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
print('Audit complete; main synchronized with GitHub. Deployment is handled by GitHub Actions.')
