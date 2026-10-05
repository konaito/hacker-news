"""Track public editorial changes and render a reproducible update history."""
import json
import re
from datetime import datetime, timedelta, timezone
from html import escape

JST = timezone(timedelta(hours=9))
LABELS = {'added': '記事追加', 'updated': '内容更新', 'withdrawn': '掲載取り下げ'}
PRIVATE_FIELDS = {'first_seen_at', 'last_verified_at', 'verification_note'}


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
    entries = json.loads((root / 'data/updates.json').read_text())
    seen = set()
    for entry in entries:
        assert entry['id'] not in seen, 'Duplicate update ID'
        seen.add(entry['id'])
        assert datetime.fromisoformat(entry['timestamp']).tzinfo is not None
        assert isinstance(entry['summary'], str) and entry['summary']
        for change in entry['changes']:
            assert re.fullmatch(r'[a-z0-9-]+', change['id'])
            assert change['action'] in LABELS
            assert isinstance(change['title'], str) and isinstance(change['company'], str)
    return sorted(entries, key=lambda entry: datetime.fromisoformat(entry['timestamp']), reverse=True)


def timestamp_html(value):
    label = datetime.fromisoformat(value).astimezone(JST).strftime('%Y年%m月%d日 %H:%M')
    return f'<time datetime="{escape(value, quote=True)}">{label}（日本時間）</time>'


def render_entry(entry, published_ids, details=True):
    body = timestamp_html(entry['timestamp']) + f'<p>{escape(entry["summary"])}</p>'
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
