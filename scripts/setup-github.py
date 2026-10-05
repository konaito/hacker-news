"""One-time setup from a normal terminal: private repo, Secrets, commit, push."""
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'konaito/hacker-news'
os.chdir(ROOT)
env = os.environ.copy()
env['PYTHONPYCACHEPREFIX'] = '/tmp/allalarm-pycache'

def run(args, **kwargs):
    return subprocess.run(args, check=True, env=env, **kwargs)

def output(args):
    return subprocess.check_output(args, text=True, env=env).strip()

login = output(['gh', 'api', 'user', '--jq', '.login'])
if login != 'konaito':
    raise SystemExit('Expected the konaito GitHub account; no changes made.')
if output(['git', 'branch', '--show-current']) != 'main':
    raise SystemExit('Checkout must be on main.')
origin = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True)
expected = ('git@github.com:' + REPO + '.git', 'https://github.com/' + REPO + '.git', 'https://github.com/' + REPO)
if origin.returncode == 0 and origin.stdout.strip() not in expected:
    raise SystemExit('Origin points to a different repository; refusing to replace it.')
for script in ('scripts/validate.py', 'build.py', 'scripts/check-page.py', 'scripts/check-seo-pwa.py'):
    run(['python3', script])
for script in ('public/app.js', 'public/pwa.js', 'public/sw.js', 'scripts/verify-live.cjs'):
    run(['node', '--check', script])
run(['node', 'scripts/test-service-worker.cjs'])
secret_path = Path.home() / '.config/allalarm/cloudflare.json'
secret = json.loads(secret_path.read_text())
if not secret.get('token') or not secret.get('account_id'):
    raise SystemExit('Missing Cloudflare credentials.')
# Reject accidental secret copies before any repository upload, without printing secret values.
tracked = output(['git', 'ls-files', '--cached', '--others', '--exclude-standard']).splitlines()
for name in tracked:
    p = ROOT / name
    if p.is_file() and secret['token'].encode() in p.read_bytes():
        raise SystemExit('Cloudflare credential found in repository file; upload aborted.')
# Listing distinguishes an absent repo from authentication/network errors.
repos = json.loads(output(['gh', 'api', '--paginate', '--slurp', 'user/repos?per_page=100']))
existing = next((r for page in repos for r in page if r['full_name'] == REPO), None)
if existing is None:
    run(['gh', 'repo', 'create', REPO, '--private', '--description', 'ALLALARM Cyber Journal: source-grounded cybersecurity news'])
else:
    if not existing['private']:
        raise SystemExit('Existing repository is public; refusing to change its visibility.')
    if origin.returncode != 0:
        # Refuse attaching this history to a previously populated repository.
        info = json.loads(output(['gh', 'api', 'repos/' + REPO]))
        if info['size'] > 0:
            raise SystemExit('Existing repository has content; inspect it before attaching this checkout.')
for name, value in [('CLOUDFLARE_API_TOKEN', secret['token']), ('CLOUDFLARE_ACCOUNT_ID', secret['account_id'])]:
    run(['gh', 'secret', 'set', name, '--repo', REPO], input=value, text=True)
if origin.returncode != 0:
    run(['git', 'remote', 'add', 'origin', expected[0]])
# All existing changes have been reviewed for this migration; ignored credentials stay excluded.
run(['git', 'add', '-A'])
if output(['git', 'diff', '--cached', '--name-only']):
    run(['git', 'commit', '-m', 'Add SEO and PWA with GitHub Actions deployment'])
run(['git', 'push', '--set-upstream', 'origin', 'main'])
info = json.loads(output(['gh', 'repo', 'view', REPO, '--json', 'visibility,url']))
if info['visibility'] != 'PRIVATE':
    raise SystemExit('Repository privacy verification failed.')
if output(['git', 'status', '--porcelain']):
    raise SystemExit('Setup finished with unexpected uncommitted changes; inspect checkout.')
print('Private repository: ' + info['url'])
print('Actions deployment: ' + info['url'] + '/actions')
print('Hourly audits now push to GitHub; Cloudflare deployment runs in Actions.')
