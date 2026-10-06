"""Request a GitHub Actions production deployment; never deploy locally."""
import subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
subprocess.run(['gh', 'workflow', 'run', 'github-pages.yml', '--ref', 'main', '--repo', 'konaito/hacker-news'], cwd=ROOT, check=True)
print('Deployment requested. Check https://github.com/konaito/hacker-news/actions')
