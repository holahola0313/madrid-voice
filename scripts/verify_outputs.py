"""Consistency checks for the audit artifacts, not a model evaluation."""
import csv
import json
from collections import Counter
from pathlib import Path

root=Path(__file__).resolve().parents[1]
load=lambda name: json.loads((root/'outputs'/name).read_text(encoding='utf-8'))
a,d,s=load('audit_results.json'),load('duplicate_checks.json'),load('final_scope.json')
assert a['reviews']['rows']-a['reviews']['duplicate_id_excess']==d['unique_review_ids']
assert d['duplicate_extra_rows']==d['duplicate_different_listing']
assert s['usable_sample_rows']+s['quarantined_sample_rows']==10000
with (root/'data/interim/sample_with_join_status.csv').open(encoding='utf-8-sig') as f:
    rows=list(csv.DictReader(f))
assert len(rows)==len({r['review_id'] for r in rows})==10000
safe=[r for r in rows if r['join_status']=='unambiguous']
assert len(safe)==s['usable_sample_rows']
assert dict(Counter(r['language_status'] for r in safe))==s['usable_language_status']
assert all('2025-09-01' <= r['date'] <= '2026-08-31' for r in rows)
with (root/'data/interim/language_spotcheck_30.csv').open(encoding='utf-8-sig') as f:
    checks=list(csv.DictReader(f))
assert len(checks)==30
assert {r['review_id'] for r in checks} <= {r['review_id'] for r in rows}
print('PASS: row/ID reconciliation, sample cap, isolation totals, language totals, dates, spotcheck membership.')
print('Human-filled language rows:',sum(bool(r['user_language_label']) for r in checks))
