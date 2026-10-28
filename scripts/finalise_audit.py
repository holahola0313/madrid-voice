"""Quarantine cross-listing review IDs without examining extra texts."""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
private = ROOT / 'data/interim'
ambiguous = set(json.loads((private/'ambiguous_review_ids.json').read_text()))
with (private/'audit_sample_10000.csv').open(encoding='utf-8-sig',newline='') as f:
    rows = list(csv.DictReader(f))
for r in rows:
    r['join_status'] = 'quarantine_cross_listing_id' if r['review_id'] in ambiguous else 'unambiguous'
with (private/'sample_with_join_status.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
safe=[r for r in rows if r['join_status']=='unambiguous']
es=[r for r in safe if r['language_status']=='es_candidate']
stats={'sample_original':len(rows),'quarantined_sample_rows':len(rows)-len(safe),'usable_sample_rows':len(safe),
       'usable_language_status':dict(Counter(r['language_status'] for r in safe)),
       'usable_language_top':dict(Counter(r['language_top'] for r in safe)),
       'usable_unique_listings':len({r['listing_id'] for r in safe}),
       'es_unique_listings':len({r['listing_id'] for r in es}),
       'es_normalized_duplicate_excess':len(es)-len({r['text_hash'] for r in es})}
(ROOT/'outputs/final_scope.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
coverage=[]
for dimension in ['district','room_type','month']:
    values=sorted({r['date'][:7] if dimension=='month' else r[dimension] for r in safe})
    for v in values:
        sub=[r for r in safe if (r['date'][:7] if dimension=='month' else r[dimension])==v]
        sub_es=[r for r in sub if r['language_status']=='es_candidate']
        nl=len({r['listing_id'] for r in sub_es})
        coverage.append(dict(dimension=dimension,value=v,sample_n=len(sub),es_candidate_n=len(sub_es),
                             es_listing_n=nl,meets_proposed_minimum=len(sub_es)>=100 and nl>=20))
with (ROOT/'outputs/final_coverage.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(coverage[0]));w.writeheader();w.writerows(coverage)
print(json.dumps(stats,ensure_ascii=False,indent=2))
print(json.dumps(coverage,ensure_ascii=False,indent=2))
