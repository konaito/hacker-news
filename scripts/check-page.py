"""Check generated interactive table and detail-template integrity."""
import json
from pathlib import Path
from html.parser import HTMLParser
root=Path(__file__).resolve().parents[1]
class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=set(); self.rows=set(); self.details=set(); self.sources=[]
        self.dates={}; self.current_row=None; self.in_date=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:
            assert a['id'] not in self.ids, f'Duplicate DOM ID {a["id"]}'
            self.ids.add(a['id'])
        if tag=='tr' and 'data-id' in a:
            self.rows.add(a['data-id'])
            self.current_row=a['data-id']
            self.dates[self.current_row]={'sort':a['data-date'], 'display':''}
        if tag=='time' and self.current_row:
            self.dates[self.current_row]['datetime']=a.get('datetime')
            self.in_date=True
        if 'data-detail' in a: self.details.add(a['data-detail'])
        if tag=='a' and a.get('class')=='source-button': self.sources.append(a['href'])
    def handle_data(self,text):
        if self.in_date: self.dates[self.current_row]['display']+=text
    def handle_endtag(self,tag):
        if tag=='time': self.in_date=False
        if tag=='tr': self.current_row=None
p=Page(); p.feed((root/'public/index.html').read_text())
for record in p.details: assert 'detail-'+record in p.ids, f'Missing detail: {record}'
data=json.loads((root/'data/incidents.json').read_text())
assert {r['id'] for r in data if r['publication_status']=='published'} <= p.rows
assert not {r['id'] for r in data if r['publication_status']=='pending'} & p.rows
assert len(p.rows)==len(p.sources)
for record in data:
    if record['publication_status']=='published':
        assert p.dates[record['id']]['sort']==record['published_at'], f'Wrong publication date: {record["id"]}'
for record_id,dates in p.dates.items():
    assert dates['datetime']==dates['sort'], f'Wrong time attribute: {record_id}'
    assert dates['display']==dates['sort'][5:].replace('-','.'), f'Display/sort date mismatch: {record_id}'
ordered_dates=[dates['sort'] for dates in p.dates.values()]
assert ordered_dates==sorted(ordered_dates,reverse=True), 'Initial table must be newest first'
for key in ('search','month-filter','category-filter','region-filter','sort','detail-dialog','load-more'): assert key in p.ids
print('Page integrity passed: records, publication dates/order, pending exclusion, dialogs, filters, source links')
