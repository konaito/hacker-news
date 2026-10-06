"""Render the site's update history directly from committed Git history."""
import re
import subprocess
from datetime import datetime, timedelta, timezone
from html import escape

JST = timezone(timedelta(hours=9))
REPOSITORY_URL = 'https://github.com/konaito/hacker-news'
LABELS = {'added': '記事追加', 'updated': '内容更新', 'withdrawn': '掲載取り下げ'}
PRIVATE_FIELDS = {'first_seen_at', 'last_verified_at', 'verification_note'}


def parse_timestamp(value):
    # Python 3.9 is used by the macOS LaunchAgent and does not accept UTC Z.
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def public_changes(before, after, old_sources, new_sources):
    old = {r['id']: r for r in before if r['publication_status'] == 'published'}
    new = {r['id']: r for r in after if r['publication_status'] == 'published'}
    old_refs = {s['id']: s for s in old_sources}
    new_refs = {s['id']: s for s in new_sources}
    changes = []
    for rid in sorted(old.keys() | new.keys()):
        previous, current = old.get(rid), new.get(rid)
        if previous is None:
            action = 'added'
        elif current is None:
            action = 'withdrawn'
        else:
            content = lambda r: {k: v for k, v in r.items() if k not in PRIVATE_FIELDS}
            refs_changed = any(old_refs.get(sid) != new_refs.get(sid) for sid in current['sources'])
            if content(previous) == content(current) and not refs_changed:
                continue
            action = 'updated'
        record = current or previous
        changes.append({'id': rid, 'company': record['company'], 'title': record['title'], 'action': action})
    return changes


def change_summary(changes):
    return '、'.join(f'{label} {sum(c["action"] == action for c in changes)}件'
                     for action, label in LABELS.items() if any(c['action'] == action for c in changes))


def load_history(root):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()

    if git('rev-parse', '--is-shallow-repository') == 'true':
        raise ValueError('Update history requires a full Git checkout (fetch-depth: 0).')
    fields = git('log', '--first-parent', '-z', '--format=%H%x00%cI%x00%s', 'HEAD').rstrip('\0').split('\0')
    entries = []
    for offset in range(0, len(fields), 3):
        sha, timestamp, subject = fields[offset:offset + 3]
        assert re.fullmatch(r'[0-9a-f]{40}', sha)
        assert parse_timestamp(timestamp).tzinfo is not None
        entries.append({'id': sha, 'timestamp': timestamp, 'summary': subject, 'changes': []})
    # Git's order follows main's ancestry, including commits with unusual clocks.
    return entries


def timestamp_html(value):
    label = parse_timestamp(value).astimezone(JST).strftime('%Y年%m月%d日 %H:%M')
    return f'<time datetime="{escape(value, quote=True)}">{label}（日本時間）</time>'


def render_entry(entry, published_ids, details=True):
    body = timestamp_html(entry['timestamp']) + f'<p>{escape(entry["summary"])}</p>'
    if re.fullmatch(r'[0-9a-f]{40}', entry.get('id', '')):
        sha = entry['id']
        body += f'<a class="history-label" href="{REPOSITORY_URL}/commit/{sha}">コミット {sha[:7]} を見る</a>'
    if details and entry['changes']:
        items = []
        for change in entry['changes']:
            title = escape(change['company'] + '：' + change['title'])
            if change['id'] in published_ids and change['action'] != 'withdrawn':
                title = f'<a href="/news/{change["id"]}/">{title}</a>'
            else:
                title = '現在は掲載していない記事'
            items.append(f'<li><span class="history-label">{LABELS[change["action"]]}</span> {title}</li>')
        body += '<ul>' + ''.join(items) + '</ul>'
    return '<li class="history-entry">' + body + '</li>'
