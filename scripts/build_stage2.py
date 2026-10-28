"""Offline, stdlib-only stage 2 build. Never sample or classify new texts.

Run from any working directory. The raw files and stage 1 artifacts are immutable
inputs. A temporary SQLite file is checked before replacing the prior build.
"""
import csv
import gzip
import hashlib
import hmac
import json
import secrets
import sqlite3
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / 'sql'
OUT = ROOT / 'outputs/stage2'
DB = ROOT / 'data/processed/madrid_voice.sqlite'
SAMPLE = ROOT / 'data/interim/sample_with_join_status.csv'

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def query_export(conn, filename, parameters=None):
    cursor = conn.execute((SQL / filename).read_text(encoding='utf-8'), parameters or {})
    fields = [c[0] for c in cursor.description]
    rows = [dict(zip(fields, row)) for row in cursor.fetchall()]
    with (OUT / filename.replace('.sql','.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    return rows

def main():
    config=json.loads((ROOT/'config/stage2.json').read_text(encoding='utf-8'))
    OUT.mkdir(parents=True,exist_ok=True)
    DB.parent.mkdir(parents=True,exist_ok=True)
    if DB.exists():
        with sqlite3.connect(DB) as previous:
            for table in ['review_labels','methods','language_human_checks']:
                if previous.execute(f'SELECT count(*) FROM {table}').fetchone()[0]:
                    raise RuntimeError('Existing DB contains labels/methods/human checks. Preserve it; use a migration instead of rebuilding.')
    # Verify both original files by bytes, without processing additional texts.
    manifest=json.loads((ROOT/'outputs/download_manifest.json').read_text(encoding='utf-8'))
    for entry in manifest:
        path=ROOT/'data/raw'/config['snapshot']/entry['file']
        if sha256(path)!=entry['sha256']:
            raise ValueError(f"Source checksum changed: {entry['file']}")
    sample=read_csv(SAMPLE)
    if len(sample)>config['text_limit']:
        raise ValueError('Text processing cap exceeded')
    if len(sample)!=len({r['review_id'] for r in sample}):
        raise ValueError('Sample review IDs must be unique')
    key_path=ROOT/'data/private/public_id_key.bin'
    key_path.parent.mkdir(parents=True,exist_ok=True)
    if not key_path.exists():
        key_path.write_bytes(secrets.token_bytes(32))
    key=key_path.read_bytes()
    def alias(kind, original):
        return kind+'_'+hmac.new(key,(kind+':'+original).encode(),hashlib.sha256).hexdigest()[:24]

    temp=DB.with_suffix('.building.sqlite')
    if temp.exists():
        raise RuntimeError('An unfinished build exists; inspect it before retrying.')
    conn=sqlite3.connect(temp)
    conn.executescript((SQL/'00_schema.sql').read_text(encoding='utf-8'))
    conn.execute('INSERT INTO settings VALUES (1,?,?,?,?,?,?,?)',
                 tuple(config[k] for k in ['snapshot','start_date','end_date','min_reviews','min_listings','min_topic_mentions','pipeline_version']))
    with gzip.open(ROOT/'data/raw'/config['snapshot']/'listings.csv.gz','rt',encoding='utf-8',newline='') as f:
        listings=list(csv.DictReader(f))
    lookup={r['id']:r for r in listings}
    if len(lookup)!=len(listings):
        raise ValueError('Nonunique listing IDs')
    conn.executemany('INSERT INTO listings VALUES (?,?,?,?,?,?,?,?)',
        [(r['id'],alias('L',r['id']),r['scrape_id'],r['last_scraped'],
          r['neighbourhood_group_cleansed'],r['neighbourhood_cleansed'],r['room_type'],
          int(r['number_of_reviews'])) for r in listings])
    ambiguous=set(json.loads((ROOT/'data/interim/ambiguous_review_ids.json').read_text()))
    insert=[]
    for i,r in enumerate(sample,1):
        listing=lookup[r['listing_id']]
        # Fail fast if sample metadata was edited or isolation flags were lost.
        if (r['district'],r['neighbourhood'],r['room_type']) != (
            listing['neighbourhood_group_cleansed'],listing['neighbourhood_cleansed'],listing['room_type']):
            raise ValueError('Sample listing metadata disagrees with snapshot')
        if (r['review_id'] in ambiguous)!=(r['join_status']=='quarantine_cross_listing_id'):
            raise ValueError('Isolation flag mismatch')
        date.fromisoformat(r['date'])
        if hashlib.sha256(r['text_clean'].casefold().encode()).hexdigest()!=r['text_hash']:
            raise ValueError('Stage 1 text hash mismatch')
        # Ordered, exclusive reasons make the sample flow sum exactly to 10,000.
        if r['join_status']!='unambiguous':
            reason='cross_listing_review_id'
        elif not config['start_date']<=r['date']<=config['end_date']:
            reason='outside_window'
        elif not any(c.isalpha() for c in r['text_clean']):
            reason='no_alphabetic_text'
        elif r['language_status']=='needs_review':
            reason='language_needs_review'
        elif r['language_status']=='other_language':
            reason='language_other_prediction'
        else:
            reason=''
        insert.append((r['review_id'],alias('R',r['review_id']),r['listing_id'],r['date'],
                       r['comments'],r['text_clean'],r['text_hash'],r['language_top'],
                       float(r['language_score']),r['language_status'],r['language_method'],r['join_status'],
                       'excluded' if reason else 'included',reason,'stage1-html-nfkc-space-v1',i))
    conn.executemany('INSERT INTO reviews VALUES ('+','.join(['?']*16)+')',insert)
    # Preserve user input separately; never silently turn it into training truth.
    check_file=ROOT/'data/interim/language_spotcheck_30.csv'
    for r in read_csv(check_file):
        if r['user_language_label'].strip():
            conn.execute('INSERT INTO language_human_checks VALUES (?,?,?)',
                         (r['review_id'],r['user_language_label'].strip(),r['user_notes']))
    manifest2={
        'pipeline_version':config['pipeline_version'],
        'built_at_utc':datetime.now(timezone.utc).isoformat(),
        'python':sys.version.split()[0],'sqlite':sqlite3.sqlite_version,
        'sample_sha256':sha256(SAMPLE),'config_sha256':sha256(ROOT/'config/stage2.json'),
        'ambiguity_ids_sha256':sha256(ROOT/'data/interim/ambiguous_review_ids.json'),
        'human_check_template_sha256':sha256(check_file),
        'sql_sha256':{p.name:sha256(p) for p in sorted(SQL.glob('*.sql'))},
        'build_script_sha256':sha256(Path(__file__)),
        'raw_files':manifest,
        'language_status':'unvalidated_predictions',
        'text_processing':'same 10000 stage1 rows; no resampling or language rerun'
    }
    conn.execute('INSERT INTO build_metadata VALUES (?,?)',('manifest',json.dumps(manifest2,ensure_ascii=False)))
    conn.commit()
    integrity=conn.execute('PRAGMA integrity_check').fetchall()
    foreign=conn.execute('PRAGMA foreign_key_check').fetchall()
    if integrity!=[('ok',)] or foreign:
        raise RuntimeError('SQLite integrity or foreign key check failed')
    results={}
    for name in ['01_join_checks.sql','02_sample_flow.sql','03_group_summary.sql','04_coverage_ranking.sql','05_monthly_trend.sql','07_text_duplicate_groups.sql']:
        results[name]=query_export(conn,name)
    params={'district':None,'room_type':None,'start_date':config['start_date'],'end_date':config['end_date']}
    results['06_filtered_coverage.sql']=query_export(conn,'06_filtered_coverage.sql',params)
    results['08_future_topic_metrics.sql']=query_export(conn,'08_future_topic_metrics.sql',params)
    j=results['01_join_checks.sql'][0]
    if not (j['sample_rows']==j['joined_rows']==j['joined_distinct_ids']==len(sample)
            and j['orphan_rows']==0 and j['eligible_rows']==j['eligible_distinct_ids']):
        raise RuntimeError('Join inflated counts or lost identifiers')
    stage1=json.loads((ROOT/'outputs/final_scope.json').read_text(encoding='utf-8'))
    if j['eligible_rows']!=stage1['usable_language_status']['es_candidate']:
        raise RuntimeError('Unexpected ES cohort change; inspect before continuing')
    if j['label_rows']!=0 or results['08_future_topic_metrics.sql']:
        raise RuntimeError('Stage 2 must not create actual theme labels')
    conn.close()
    temp.replace(DB)
    manifest2['checks']={'sqlite_integrity':'ok','foreign_keys':'ok','join_counts':'ok',
                         'stage1_cohort_reconciled':True,'topic_labels_created':0}
    manifest2['results']=results
    (OUT/'build_manifest.json').write_text(json.dumps(manifest2,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'database':str(DB),'join_checks':j,'flow':results['02_sample_flow.sql'],
                      'duplicate_texts':results['07_text_duplicate_groups.sql']},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
