"""Run both methods offline on the same 3,763 candidates; atomic label writes."""
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from topic_methods import rule_predict,TOPICS

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data/processed/madrid_voice.sqlite'
OUT=ROOT/'outputs/stage3'
PRIVATE=ROOT/'data/stage3'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def export(cursor,path):
    names=[c[0] for c in cursor.description];rows=[dict(zip(names,row)) for row in cursor.fetchall()]
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=names);w.writeheader();w.writerows(rows)
    return rows

def main():
    from local_ai import LocalAI,np,ort
    config=json.loads((ROOT/'config/stage3.json').read_text())
    OUT.mkdir(parents=True,exist_ok=True);PRIVATE.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(DB);conn.execute('PRAGMA foreign_keys=ON')
    rows=[dict(zip(['review_id','clean_text','public_review_id','listing_id'],r)) for r in
          conn.execute('SELECT review_id,clean_text,public_review_id,listing_id FROM analysis_reviews ORDER BY review_id')]
    if len(rows)>10000:raise ValueError('Sample cap exceeded')
    methods=[('spanish_rules',config['rules_version'],'rule'),(config['ai_method'],config['ai_version'],'ai')]
    code_paths=[ROOT/'scripts'/n for n in ['topic_methods.py','local_ai.py','run_stage3.py']]
    config_paths=[ROOT/'config'/n for n in ['stage3.json','spanish_rules.json','ai_prototypes.json']]
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in code_paths+config_paths}
    for method,version,_ in methods:
        if conn.execute('SELECT 1 FROM methods WHERE method_id=? AND version=?',(method,version)).fetchone():
            raise RuntimeError('Method/version already exists. Do not overwrite labels; bump version for changes.')
    print('Candidates:',len(rows),flush=True)
    rules=[rule_predict(r['clean_text']) for r in rows]
    ai=LocalAI(config)
    all_parts=[];ranges=[]
    for r in rows:
        parts=ai.split(r['clean_text']);ranges.append((len(all_parts),len(all_parts)+len(parts)));all_parts.extend(parts)
    cache_key=hashlib.sha256(json.dumps([[(r['review_id'],r['clean_text']) for r in rows],
                         ai.manifest['revision'],ai.manifest['files'][0]['sha256'],config['max_clause_characters'],
                         config['max_tokens'],hashes['scripts/local_ai.py']],ensure_ascii=False).encode()).hexdigest()
    cache=PRIVATE/(cache_key+'.npy')
    if cache.exists():vectors=np.load(cache,allow_pickle=False)
    else:
        vectors=ai.encode([p['text'] for p in all_parts]);np.save(cache,vectors)
    if vectors.shape!=(len(all_parts),384):raise ValueError('Embedding cache shape mismatch')
    ai_labels=[ai.classify(r['clean_text'],all_parts[a:b],vectors[a:b]) for r,(a,b) in zip(rows,ranges)]
    # Keep a real database backup before migration/insertion, never delete prior work.
    timestamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=ROOT/'data/backups'/('before_stage3_'+timestamp+'.sqlite');backup.parent.mkdir(exist_ok=True)
    with sqlite3.connect(backup) as dest:conn.backup(dest)
    now=datetime.now(timezone.utc).isoformat();evidence_rows=0
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS label_details (
          review_id TEXT NOT NULL, topic TEXT NOT NULL, method_id TEXT NOT NULL, version TEXT NOT NULL,
          spans_json TEXT NOT NULL, decision_reason TEXT NOT NULL, source_text_hash TEXT NOT NULL,
          PRIMARY KEY(review_id,topic,method_id,version),
          FOREIGN KEY(review_id,topic,method_id,version) REFERENCES review_labels(review_id,topic,method_id,version))''')
        for (method,version,origin),predictions in zip(methods,[rules,ai_labels]):
            conn.execute('INSERT INTO methods VALUES (?,?,?,?,?)',(method,version,origin,'unvalidated',
                         json.dumps({'config':config,'source_hashes':hashes,'model_revision':ai.manifest['revision'] if origin=='ai' else None},ensure_ascii=False)))
            for r,labels in zip(rows,predictions):
                if len(labels)!=6 or {l['topic'] for l in labels}!=set(TOPICS):raise ValueError('Incomplete topics')
                for label in labels:
                    for span in label['spans']:
                        if r['clean_text'][span['start']:span['end']]!=span['text']:raise ValueError('Evidence mismatch')
                        evidence_rows+=1
                    if label['evidence_text'] and label['evidence_text'] not in r['clean_text']:raise ValueError('Envelope mismatch')
                    conn.execute('INSERT INTO review_labels VALUES (?,?,?,?,?,?,?,?)',
                        (r['review_id'],label['topic'],method,version,label['mention_status'],label['sentiment'],label['evidence_text'],now))
                    conn.execute('INSERT INTO label_details VALUES (?,?,?,?,?,?,?)',
                        (r['review_id'],label['topic'],method,version,json.dumps(label['spans'],ensure_ascii=False),label['reason'],
                         hashlib.sha256(r['clean_text'].encode()).hexdigest()))
        if conn.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Foreign keys invalid')
    # Aggregate public results only. Evidence stays in the private SQLite file.
    summary=export(conn.execute('''SELECT method_id,version,topic,mention_status,sentiment,count(*) AS review_n
        FROM review_labels GROUP BY method_id,version,topic,mention_status,sentiment
        ORDER BY method_id,topic,mention_status,sentiment'''),OUT/'label_counts.csv')
    params=dict(district=None,room_type=None,start_date='2025-09-01',end_date='2026-08-31')
    metrics=export(conn.execute((ROOT/'sql/08_future_topic_metrics.sql').read_text(),params),OUT/'unvalidated_topic_metrics.csv')
    differences=export(conn.execute('''SELECT a.topic,count(*) AS paired_n,
        sum(a.mention_status<>b.mention_status) AS mention_disagreements,
        sum(a.sentiment<>b.sentiment) AS sentiment_disagreements
        FROM review_labels a JOIN review_labels b ON a.review_id=b.review_id AND a.topic=b.topic
        WHERE a.method_id=? AND a.version=? AND b.method_id=? AND b.version=? GROUP BY a.topic''',
        (methods[0][0],methods[0][1],methods[1][0],methods[1][1])),OUT/'method_disagreements.csv')
    run={'candidate_reviews':len(rows),'methods':methods,'labels_written':len(rows)*12,'clauses_encoded':len(all_parts),
         'evidence_spans_checked':evidence_rows,'model':ai.manifest,'source_hashes':hashes,
         'config':config,'run_utc':now,'embedding_cache_key':cache_key,'onnxruntime_version':ort.__version__,
         'numpy_version':np.__version__,'validation_status':'unvalidated','human_metrics':None,
         'network_during_inference':False,'summary':summary,'metrics':metrics,'disagreements':differences}
    (OUT/'run_manifest.json').write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:run[k] for k in ['candidate_reviews','labels_written','clauses_encoded','evidence_spans_checked','disagreements']},ensure_ascii=False,indent=2))
    conn.close()
if __name__=='__main__':main()
