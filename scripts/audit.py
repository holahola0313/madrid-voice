"""Stage 1 only. Full structural scan; at most 10,000 texts for NLP.

No data are sent to a service. csv preserves large identifiers as strings.
Reservoir sampling gives every eligible review the same inclusion probability.
"""
import csv
import gzip
import hashlib
import html
import json
import random
import re
import sys
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.packages'))
from langdetect import DetectorFactory, detect_langs, LangDetectException

RAW = ROOT / 'data/raw/2026-09-17'
OUT = ROOT / 'outputs'
PRIVATE = ROOT / 'data/interim'
START, END = '2025-09-01', '2026-08-31'
SEED, LIMIT = 20261013, 10000

def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')

def write_csv(path, rows, fields=None):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def main():
    OUT.mkdir(exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    with gzip.open(RAW / 'listings.csv.gz', 'rt', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        listing_fields = reader.fieldnames
        listings = list(reader)
    ids = Counter(r['id'] for r in listings)
    lookup = {r['id']: r for r in listings}
    missing_l = {c: sum(not r[c].strip() for r in listings) for c in listing_fields}
    result = {'scope': {'snapshot': '2026-09-17', 'start': START, 'end': END,
                         'text_limit': LIMIT, 'seed': SEED, 'method': 'uniform reservoir over eligible CSV rows'},
              'listings': {'rows': len(listings), 'columns': len(listing_fields),
                           'duplicate_id_excess': sum(v-1 for v in ids.values()),
                           'missing': missing_l,
                           'last_scraped': dict(Counter(r['last_scraped'] for r in listings)),
                           'scrape_ids': dict(Counter(r['scrape_id'] for r in listings)),
                           'room_types': dict(Counter(r['room_type'] for r in listings)),
                           'district_count': len(set(r['neighbourhood_group_cleansed'] for r in listings)),
                           'neighbourhood_count': len(set(r['neighbourhood_cleansed'] for r in listings))}}
    rng = random.Random(SEED)
    sample, seen = [], set()
    missing_r, years, months, eligible_groups = Counter(), Counter(), Counter(), Counter()
    n = duplicate = orphan = invalid_date = future_date = eligible = missing_body = 0
    min_date, max_date = '9999-12-31', '0000-01-01'
    reviewed_listings = set()
    review_counts = Counter()
    with gzip.open(RAW / 'reviews.csv.gz', 'rt', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        review_fields = reader.fieldnames
        for row in reader:
            n += 1
            for c in review_fields:
                missing_r[c] += not row[c].strip()
            is_dup = row['id'] in seen
            duplicate += is_dup
            seen.add(row['id'])
            listing = lookup.get(row['listing_id'])
            orphan += listing is None
            reviewed_listings.add(row['listing_id'])
            review_counts[row['listing_id']] += 1
            valid = True
            try:
                date.fromisoformat(row['date'])
            except ValueError:
                invalid_date += 1
                valid = False
            if valid:
                d = row['date']
                min_date, max_date = min(min_date, d), max(max_date, d)
                future_date += d > '2026-09-17'
                years[d[:4]] += 1
                months[d[:7]] += 1
            blank = not row['comments'].strip()
            missing_body += blank
            if valid and START <= row['date'] <= END and listing and row['id'] and not is_dup and not blank:
                eligible += 1
                group = (listing['neighbourhood_group_cleansed'], listing['room_type'])
                eligible_groups[group] += 1
                item = {'review_id': row['id'], 'listing_id': row['listing_id'], 'date': row['date'],
                        'district': group[0], 'neighbourhood': listing['neighbourhood_cleansed'],
                        'room_type': group[1], 'comments': row['comments']}
                if len(sample) < LIMIT:
                    sample.append(item)
                else:
                    j = rng.randrange(eligible)
                    if j < LIMIT:
                        sample[j] = item
            if n % 500000 == 0:
                print('Scanned rows:', n, flush=True)
    result['reviews'] = {'rows': n, 'columns': len(review_fields), 'missing': dict(missing_r),
                         'duplicate_id_excess': duplicate, 'orphan_rows': orphan,
                         'invalid_dates': invalid_date, 'after_snapshot_dates': future_date,
                         'date_min': min_date, 'date_max': max_date,
                         'by_year': dict(sorted(years.items())), 'by_month': dict(sorted(months.items())),
                         'listings_with_reviews': len(reviewed_listings & set(lookup)),
                         'listings_without_reviews': len(set(lookup) - reviewed_listings),
                         'eligible_rows': eligible,
                         'listing_review_count_mismatches': sum(int(r['number_of_reviews'] or 0) != review_counts[r['id']] for r in listings)}
    write_json(OUT / 'audit_structural.json', result)
    print(json.dumps(result['reviews'], ensure_ascii=False), flush=True)
    if result['listings']['duplicate_id_excess']:
        raise ValueError('Listing IDs not unique: stop before join-dependent NLP.')
    DetectorFactory.seed = SEED
    hashes = Counter()
    for i, r in enumerate(sample):
        text = re.sub(r'<[^>]*>', ' ', html.unescape(r['comments']))
        text = re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text)).strip()
        r['text_clean'] = text
        r['text_hash'] = hashlib.sha256(text.casefold().encode('utf-8')).hexdigest()
        hashes[r['text_hash']] += 1
        try:
            predictions = detect_langs(text)
            top = predictions[0]
            r['language_top'], r['language_score'] = top.lang, round(top.prob, 6)
            r['language_alternatives'] = str(predictions)
        except LangDetectException:
            r['language_top'], r['language_score'], r['language_alternatives'] = 'und', 0, ''
        r['language_method'] = 'langdetect-1.0.9-seed20261013'
        r['language_status'] = ('es_candidate' if r['language_top'] == 'es' and r['language_score'] >= .9 and len(text) >= 20
                                else 'needs_review' if len(text) < 20 or r['language_score'] < .9 or r['language_top'] == 'und'
                                else 'other_language')
        if (i+1) % 2000 == 0:
            print('Language checked:', i+1, flush=True)
    write_csv(PRIVATE / 'audit_sample_10000.csv', sample)
    result['sample'] = {'n': len(sample), 'unique_listings': len(set(r['listing_id'] for r in sample)),
                        'by_language_top': dict(Counter(r['language_top'] for r in sample)),
                        'by_language_status': dict(Counter(r['language_status'] for r in sample)),
                        'normalized_exact_duplicate_excess': sum(v-1 for v in hashes.values()),
                        'duplicate_text_groups': sum(v > 1 for v in hashes.values()),
                        'short_text_lt20': sum(len(r['text_clean']) < 20 for r in sample),
                        'html_rows': sum(bool(re.search(r'<[^>]*>',r['comments'])) for r in sample)}
    write_json(OUT / 'audit_results.json', result)
    inventory = []
    for table, fields, missing, count in [('listings', listing_fields, missing_l, len(listings)), ('reviews', review_fields, missing_r, n)]:
        inventory += [dict(table=table, field=c, missing_count=missing[c], total_rows=count,
                           missing_pct=round(100*missing[c]/count,4)) for c in fields]
    write_csv(OUT / 'field_inventory.csv', inventory)
    sample_groups = Counter((r['district'], r['room_type']) for r in sample)
    es_groups = Counter((r['district'], r['room_type']) for r in sample if r['language_status']=='es_candidate')
    es_listings = {}
    for r in sample:
        if r['language_status']=='es_candidate':
            es_listings.setdefault((r['district'], r['room_type']), set()).add(r['listing_id'])
    write_csv(OUT / 'coverage.csv', [dict(district=g[0],room_type=g[1],eligible_rows=c,
              sample_rows=sample_groups[g],es_candidate_rows=es_groups[g],es_candidate_listings=len(es_listings.get(g,set())))
              for g,c in sorted(eligible_groups.items())])
    checks = []
    check_rng = random.Random(SEED)
    for status in ['es_candidate','needs_review','other_language']:
        pool = [r for r in sample if r['language_status'] == status]
        for r in check_rng.sample(pool, min(10,len(pool))):
            checks.append({**r, 'user_language_label':'', 'user_notes':''})
    write_csv(PRIVATE / 'language_spotcheck_30.csv', checks)
    print(json.dumps(result['sample'], ensure_ascii=False), flush=True)

if __name__ == '__main__':
    main()
