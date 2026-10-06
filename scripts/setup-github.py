"""Configure the public GitHub repository and Actions-based Pages publishing."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = 'konaito/hacker-news'
DOMAIN = 'cyber.allalarm.app'


def output(args):
    return subprocess.check_output(args, text=True, cwd=ROOT).strip()


def run(args):
    subprocess.run(args, cwd=ROOT, check=True)


if output(['gh', 'api', 'user', '--jq', '.login']) != 'konaito':
    raise SystemExit('Expected the konaito GitHub account; no changes made.')
if output(['git', 'branch', '--show-current']) != 'main':
    raise SystemExit('Checkout must be on main.')
origin = subprocess.run(['git', 'remote', 'get-url', 'origin'], capture_output=True, text=True, cwd=ROOT)
expected = ('git@github.com:' + REPO + '.git', 'https://github.com/' + REPO + '.git', 'https://github.com/' + REPO)
if origin.returncode == 0 and origin.stdout.strip() not in expected:
    raise SystemExit('Origin points to a different repository; refusing to replace it.')
repos = json.loads(output(['gh', 'api', '--paginate', '--slurp', 'user/repos?per_page=100']))
existing = next((repo for page in repos for repo in page if repo['full_name'] == REPO), None)
if existing is None:
    run(['gh', 'repo', 'create', REPO, '--public', '--description', 'ALLALARM Cyber Journal: source-grounded cybersecurity news'])
else:
    if existing['private']:
        raise SystemExit('Repository is private. Review its content and explicitly make it public before enabling Pages.')
    if origin.returncode != 0 and existing['size'] > 0:
        raise SystemExit('Existing repository has content; inspect it before attaching this checkout.')
if origin.returncode != 0:
    run(['git', 'remote', 'add', 'origin', expected[0]])
site = subprocess.run(['gh', 'api', 'repos/' + REPO + '/pages'], capture_output=True, text=True)
if site.returncode:
    if 'HTTP 404' not in site.stderr:
        raise SystemExit('Unable to inspect Pages settings; no settings changed.')
    run(['gh', 'api', '--method', 'POST', 'repos/' + REPO + '/pages', '-f', 'build_type=workflow'])
run(['gh', 'api', '--method', 'PUT', 'repos/' + REPO + '/pages', '-f', 'build_type=workflow', '-f', 'cname=' + DOMAIN])
print('Public repository: https://github.com/' + REPO)
print('Pages configured for https://' + DOMAIN + '/. Push main to deploy.')
print('DNS must point ' + DOMAIN + ' to konaito.github.io (CNAME, proxy disabled).')
