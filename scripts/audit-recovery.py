"""Persist a verified audit for publication retries without adopting later edits."""
import hashlib
import json
from pathlib import Path


ALLOWED_FILES = {'public/index.html', 'public/sitemap.xml', 'public/feed.xml',
                 'public/sw.js', 'public/updates/index.html'}


def allowed_changes(paths):
    return all(path.startswith(('data/', 'public/news/', 'public/archive/'))
               or path in ALLOWED_FILES for path in paths)


def data_hashes(root):
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((root / 'data').rglob('*')) if path.is_file()}


def report_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_recovery(path, root, report_path, base_commit, started_at, carryover):
    recovery = {'base_commit': base_commit, 'started_at': started_at.isoformat(),
                'data_hashes': data_hashes(root), 'report_hash': report_hash(report_path),
                'carryover': carryover}
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(recovery, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)
    return recovery


def check_recovery(recovery, root, report_path):
    if data_hashes(root) != recovery['data_hashes']:
        raise ValueError('Audit data changed after verification; preserve edits for manual reconciliation.')
    if not report_path.exists() or report_hash(report_path) != recovery['report_hash']:
        raise ValueError('Audit report changed after verification; publication retry halted.')
