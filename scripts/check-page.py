"""Check generated interactive table and detail-template integrity."""
import json
from pathlib import Path
from html.parser import HTMLParser
root=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self): super().__init__(); self.ids=set(); self.rows=set(); self.details=set(); self.sources=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:
            assert a['id'] not in self.ids, f'Duplicate DOM ID {a["id"]}'
            self.ids.add(a['id'])
        if tag=='tr' and 'data-id' in a: self.rows.add(a['data-id'])
        if 'data-detail' in a: self.details.add(a['data-detail'])
        if tag=='a' and a.get('class')=='source-button': self.sources.append(a['href'])
p=Page(); p.feed((root/'public/index.html').read_text())
for record in p.details: assert 'detail-'+record in p.ids, f'Missing detail: {record}'
data=json.loads((root/'data/incidents.json').read_text())
assert {r['id'] for r in data if r['publication_status']=='published'} <= p.rows
assert not {r['id'] for r in data if r['publication_status']=='pending'} & p.rows
assert len(p.rows)==len(p.sources)
for key in ('search','month-filter','category-filter','region-filter','sort','detail-dialog','load-more'): assert key in p.ids
print('Page integrity passed: records, pending exclusion, dialogs, filters, source links')
