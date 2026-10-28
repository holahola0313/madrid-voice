"""Additional structural checks. Does not analyse additional review texts."""
import csv
import gzip
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
raw = ROOT / 'data/raw/2026-09-17'
with gzip.open(raw / 'listings.csv.gz','rt',encoding='utf-8',newline='') as f:
    listings = {r['id']:r for r in csv.DictReader(f)}
seen = {}
stats = Counter()
duplicate_ids = set()
with gzip.open(raw / 'reviews.csv.gz','rt',encoding='utf-8',newline='') as f:
    for r in csv.DictReader(f):
        key = r['id']
        meta = (r['listing_id'],r['date'],r['reviewer_id'])
        stats['after_listing_last_scraped'] += r['date'] > listings[r['listing_id']]['last_scraped']
        if key in seen:
            duplicate_ids.add(key)
            stats['duplicate_extra_rows'] += 1
            stats['duplicate_same_metadata'] += meta == seen[key]
            stats['duplicate_different_listing'] += meta[0] != seen[key][0]
            stats['duplicate_different_date'] += meta[1] != seen[key][1]
            stats['duplicate_different_reviewer'] += meta[2] != seen[key][2]
        else:
            seen[key] = meta
stats['unique_review_ids'] = len(seen)
stats['repeated_review_ids'] = len(duplicate_ids)
stats['text_equality_checked_on_full_file'] = False
stats['unambiguous_unique_ids'] = len(seen) - len(duplicate_ids)
stats['unambiguous_window_ids'] = sum('2025-09-01' <= meta[1] <= '2026-08-31' for key,meta in seen.items() if key not in duplicate_ids)
(ROOT / 'data/interim/ambiguous_review_ids.json').write_text(json.dumps(sorted(duplicate_ids)),encoding='utf-8')
output = ROOT / 'outputs/duplicate_checks.json'
output.write_text(json.dumps(stats,indent=2),encoding='utf-8')
print(json.dumps(stats,indent=2))
