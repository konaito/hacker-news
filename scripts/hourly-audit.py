"""Local hourly audit. LaunchAgent invokes this on startup and every hour."""
import fcntl,json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'.audit'; STATE.mkdir(exist_ok=True)
lock=(STATE/'run.lock').open('w')
try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError: sys.exit(0)
os.chdir(ROOT)
env=os.environ.copy()
env['PATH']='/Users/konaito/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin'
def run(args,**kwargs): return subprocess.run(args,check=True,env=env,**kwargs)
if subprocess.check_output(['git','status','--porcelain'],text=True).strip():
    raise SystemExit('Checkout has uncommitted edits; audit deferred to preserve user work.')
checkpoint=STATE/'last-success.json'; previous=checkpoint.read_bytes() if checkpoint.exists() else None
with (ROOT/'.codex/news-audit.md').open() as prompt:
    run(['codex','exec','-C',str(ROOT),'-s','danger-full-access','-c','approval_policy="never"','-c','web_search="live"','-o',str(STATE/'last-response.txt'),'-'],stdin=prompt,timeout=3300)
if not checkpoint.exists() or checkpoint.read_bytes()==previous: raise SystemExit('Audit did not produce a new completion checkpoint.')
json.loads(checkpoint.read_text())
changed=subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()
if any(not p.startswith('data/') and p not in ('public/index.html','public/sitemap.xml') for p in changed): raise SystemExit('Unexpected changes; publication halted.')
if changed:
    run(['python3','scripts/validate.py']); run(['python3','build.py']); run(['node','--check','public/app.js'])
    run(['git','add','data','public/index.html','public/sitemap.xml'])
    run(['git','commit','-m','Update verified cybersecurity news'])
# Resume deployment after previous publish failure, including runs with no new content.
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
published=STATE/'published-commit'
if not published.exists() or published.read_text().strip()!=head:
    remote=subprocess.check_output(['git','remote'],text=True).splitlines()
    if 'origin' in remote: run(['git','push','origin','main'])
    credentials=Path.home()/'.config/allalarm/cloudflare.json'
    secret=json.loads(credentials.read_text())
    env['CLOUDFLARE_API_TOKEN']=secret['token']; env['CLOUDFLARE_ACCOUNT_ID']=secret['account_id']
    run(['npm','exec','--yes','--package=wrangler','--','wrangler','pages','deploy','public','--project-name','allalarm-hackernews','--branch','main'],timeout=600)
    published.write_text(head+'\n')
