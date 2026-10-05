import json
from pathlib import Path
from datetime import date
from urllib.parse import urlparse
import argparse,urllib.request
ROOT=Path(__file__).resolve().parents[1]
def validate():
    incidents=json.loads((ROOT/'data/incidents.json').read_text())
    sources=json.loads((ROOT/'data/sources.json').read_text())
    ids=[s['id'] for s in sources]; assert len(ids)==len(set(ids)), 'Duplicate source IDs'
    source_map={s['id']:s for s in sources}
    seen=set(); fingerprints=set()
    for s in sources:
        assert urlparse(s['url']).scheme=='https' and urlparse(s['url']).hostname
        assert s['type'] in ('primary','reporting')
    for r in incidents:
        assert r['id'] not in seen; seen.add(r['id'])
        fingerprint=(r['company'],r['published_at'],r['title']); assert fingerprint not in fingerprints; fingerprints.add(fingerprint)
        for key in ('published_at','first_seen_at','last_verified_at'): date.fromisoformat(r[key])
        assert r['published_at']>='2026-09-01'
        if r['occurred_at']: date.fromisoformat(r['occurred_at'])
        assert r['status'] in ('confirmed_leak','confirmed_access','possible_leak','disruption')
        assert r['publication_status'] in ('pending','published')
        assert r['sources'] and all(s in source_map for s in r['sources'])
        evidence=[source_map[s] for s in r['sources']]
        if r['publication_status']=='published':
            assert any(s['type']=='primary' for s in evidence) or len({s['publisher'] for s in evidence if s['type']=='reporting'})>=2, f'Insufficient evidence: {r["id"]}'
        for a in r['affected']:
            assert a['unit'] in ('people','accounts','records','documents')
            assert isinstance(a['count'],int) and a['count']>=0
            assert a['source_id'] in r['sources']
    json.loads((ROOT/'data/monthly-digests.json').read_text())
    print(f'Validated {len(incidents)} incidents and {len(sources)} sources')
    return sources
if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--links',action='store_true'); args=parser.parse_args()
    sources=validate()
    if args.links:
        failed=[]
        for s in sources:
            try:
                req=urllib.request.Request(s['url'],headers={'User-Agent':'Mozilla/5.0 ALLALARM source verification'})
                with urllib.request.urlopen(req,timeout=20) as response: assert response.status==200
            except Exception as exc: failed.append((s['id'],str(exc)))
        for sid,error in failed: print(f'REVIEW {sid}: {error}')
        if failed: raise SystemExit('Link checks need browser verification; never treat HTTP blocking as proof of source validity.')
