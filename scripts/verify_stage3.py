"""Validate stored predictions and evidence; does not evaluate label correctness."""
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    run=json.loads((ROOT/'outputs/stage3/run_manifest.json').read_text(encoding='utf-8'))
    db=sqlite3.connect(ROOT/'data/processed/madrid_voice.sqlite')
    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    n=db.execute('SELECT count(*) FROM analysis_reviews').fetchone()[0]
    checked=0
    for method,version,_ in run['methods']:
        count,distinct=db.execute('SELECT count(*),count(DISTINCT review_id) FROM review_labels WHERE method_id=? AND version=?',(method,version)).fetchone()
        assert (count,distinct)==(6*n,n)
        assert db.execute('SELECT validation_status FROM methods WHERE method_id=? AND version=?',(method,version)).fetchone()[0]=='unvalidated'
        assert not db.execute('''SELECT l.review_id FROM review_labels l LEFT JOIN analysis_reviews r ON r.review_id=l.review_id
          WHERE l.method_id=? AND l.version=? AND r.review_id IS NULL''',(method,version)).fetchall()
    for text,evidence,spans,sha in db.execute('''SELECT r.clean_text,l.evidence_text,d.spans_json,d.source_text_hash
      FROM review_labels l JOIN reviews r ON r.review_id=l.review_id
      JOIN label_details d USING(review_id,topic,method_id,version)'''):
        assert hashlib.sha256(text.encode()).hexdigest()==sha
        assert not evidence or evidence in text
        for span in json.loads(spans):
            assert text[span['start']:span['end']]==span['text'];checked+=1
    assert checked==run['evidence_spans_checked']
    assert db.execute('SELECT count(*) FROM analysis_reviews').fetchone()[0]==n
    for path,sha in run['source_hashes'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha
    result={'integrity':'ok','foreign_keys':'ok','candidate_n':n,'evidence_spans_checked':checked,
            'complete_six_topics_per_method':True,'source_hashes_verified':True,
            'label_accuracy_checked':False,'human_metrics_generated':False}
    (ROOT/'outputs/stage3/verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
