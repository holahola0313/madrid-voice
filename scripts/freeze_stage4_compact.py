"""Diagnose accepted development labels, then freeze cached methods before test release.

No training, external calls, or human-label synthesis. Private evidence stays in data/.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / 'data/stage4/compact'
PUBLIC = ROOT / 'outputs/stage4'
TOPICS = ('cleanliness', 'noise', 'checkin', 'facilities', 'communication', 'location')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save_new(path, data):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def inputs():
    manifest = read(PUBLIC / 'compact_scope_manifest.json')
    for path, key in [
        ('data/stage4/compact/scope.json', 'compact_scope_sha256'),
        ('data/stage4/compact/development_accepted_v1.json', 'accepted_development_sha256'),
        ('docs/ANNOTATION_GUIDE_ES_v1.0.md', 'guideline_sha256'),
        ('docs/EVALUATION_PROTOCOL_v1.1_COMPACT.md', 'protocol_sha256'),
        ('data/stage4/formal_split.json', 'original_formal_split_sha256'),
        ('config/stage4_compact.json', 'config_sha256'),
    ]:
        if sha(ROOT / path) != manifest[key]:
            raise ValueError(f'Frozen input changed: {path}')
    scope = read(PRIVATE / 'scope.json')['active_assignments']
    development = [r for r in scope if r['stage'] == 'development']
    test = [r for r in scope if r['stage'] == 'test']
    if [r['annotation_id'] for r in development] != [f'DV{i:03}' for i in range(1, 21)]:
        raise ValueError('Unexpected development selection')
    if [r['annotation_id'] for r in test] != [f'TS{i:03}' for i in range(1, 31)]:
        raise ValueError('Unexpected test selection')
    for key in ('review_id', 'listing_id', 'component_id', 'text_cluster'):
        if len({r[key] for r in scope}) != 80:
            raise ValueError(f'Overlap in {key}')
    return manifest, development, test


def predictions(assignments):
    run = read(ROOT / 'outputs/stage3/run_manifest.json')
    for path, expected in run['source_hashes'].items():
        if sha(ROOT / path) != expected:
            raise ValueError(f'Method source changed: {path}')
    # Verify exact local model/tokenizer artifacts, not merely the repository name.
    for item in run['model']['files']:
        if sha(ROOT / 'data/models/multilingual-minilm' / item['name']) != item['sha256']:
            raise ValueError(f'Model artifact changed: {item["name"]}')
    con = sqlite3.connect((ROOT / 'data/processed/madrid_voice.sqlite').as_uri() + '?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    result = []
    try:
        for assignment in assignments:
            for method, version, _ in run['methods']:
                rows = con.execute('''SELECT l.*, d.spans_json, d.decision_reason,
                    d.source_text_hash FROM review_labels l JOIN label_details d
                    USING(review_id, topic, method_id, version)
                    WHERE l.review_id=? AND l.method_id=? AND l.version=? ORDER BY l.topic''',
                    (assignment['review_id'], method, version)).fetchall()
                if len(rows) != 6 or {r['topic'] for r in rows} != set(TOPICS):
                    raise ValueError('Missing or duplicate prediction keys')
                for row in rows:
                    item = dict(row)
                    if item['source_text_hash'] != assignment['text_sha256']:
                        raise ValueError('Prediction source text mismatch')
                    item['annotation_id'] = assignment['annotation_id']
                    result.append(item)
    finally:
        con.close()
    return run, result


def diagnose():
    _, development, _ = inputs()
    run, pred = predictions(development)
    human = read(PRIVATE / 'development_accepted_v1.json')['answers']
    if {r['annotation_id'] for r in human} != {r['annotation_id'] for r in development}:
        raise ValueError('Human development sample mismatch')
    gold = {(r['annotation_id'], t['topic']): t for r in human for t in r['labels']}
    if len(gold) != 120:
        raise ValueError('Development labels incomplete or duplicated')
    differences = []
    table = []
    for method, version, _ in run['methods']:
        for topic in TOPICS:
            rows = [p for p in pred if p['method_id'] == method and p['topic'] == topic]
            mention_diff = pair_diff = 0
            for p in rows:
                g = gold[(p['annotation_id'], topic)]
                mention_diff += g['mention_status'] != p['mention_status']
                unequal = (g['mention_status'], g['sentiment']) != (p['mention_status'], p['sentiment'])
                pair_diff += unequal
                if unequal:
                    differences.append({'annotation_id': p['annotation_id'], 'topic': topic,
                        'method_id': method, 'version': version, 'human': g, 'prediction': p})
            table.append({'method_id': method, 'version': version, 'topic': topic,
                'development_topic_rows': len(rows), 'mention_disagreements': mention_diff,
                'mention_sentiment_pair_disagreements': pair_diff})
    summary = {'scope': 'development_only_not_independent_test', 'review_n': len(human),
        'human_topic_rows': len(gold),
        'human_label_counts': dict(Counter(f"{r['mention_status']}/{r['sentiment']}" for r in gold.values())),
        'comparisons': table, 'test_metrics_generated': False,
        'accepted_development_sha256': sha(PRIVATE / 'development_accepted_v1.json')}
    save_new(PRIVATE / 'development_disagreements.json', differences)
    save_new(PUBLIC / 'development_diagnostics.json', summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def freeze():
    manifest, _, test = inputs()
    diagnostic = read(PUBLIC / 'development_diagnostics.json')
    if diagnostic['accepted_development_sha256'] != manifest['accepted_development_sha256']:
        raise ValueError('Development diagnostics stale')
    run, pred = predictions(test)
    # Freeze inference outputs before constructing or rendering the human test workbook.
    save_new(PRIVATE / 'test_predictions_frozen_v1.json', pred)
    frozen_paths = [
        'data/stage4/compact/scope.json', 'data/stage4/compact/development_accepted_v1.json',
        'data/stage4/compact/test_predictions_frozen_v1.json',
        'outputs/stage4/development_diagnostics.json', 'outputs/stage3/run_manifest.json',
        'docs/ANNOTATION_GUIDE_ES_v1.0.md', 'docs/EVALUATION_PROTOCOL_v1.0.md',
        'docs/EVALUATION_PROTOCOL_v1.1_COMPACT.md', 'config/stage4_compact.json',
        'requirements.txt', 'requirements-stage3.txt', 'scripts/freeze_stage4_compact.py',
    ] + list(run['source_hashes'])
    record = {'version': 'compact-method-freeze-v1.0', 'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'methods': run['methods'], 'model': run['model'], 'config': run['config'],
        'decision': 'Retain both original stage-3 baselines unchanged; no training or threshold calibration on these 20 development reviews.',
        'reason': 'Only 3 purely negative and 4 mixed human topic labels; report observed limitations without claiming tuning gains.',
        'test_n': 30, 'prediction_rows': len(pred), 'test_human_labels': 0,
        'test_metrics_generated': False, 'source_prediction_run_utc': run['run_utc'],
        'hashes': {p: sha(ROOT / p) for p in frozen_paths}}
    save_new(PUBLIC / 'compact_method_freeze.json', record)
    # The historical plan contains texts; select mechanically, without examining test semantics.
    plan_path = ROOT / 'data/stage4/annotation_plan.json'
    prep = read(PUBLIC / 'preparation_summary.json')
    if sha(plan_path) != prep['plan_sha256']:
        raise ValueError('Original plan changed')
    plan = {r['annotation_id']: r for r in read(plan_path)}
    blind = []
    for item in test:
        source = plan[item['source_annotation_id']]
        if source['text_sha256'] != item['text_sha256'] or hashlib.sha256(source['text'].encode()).hexdigest() != item['text_sha256']:
            raise ValueError('Test text changed')
        blind.append({'annotation_id': item['annotation_id'], 'text': source['text'],
            'language': '', 'notes': '', 'labels': [{'topic': t, 'mention': '',
                'sentiment': '', 'evidence': '', 'notes': ''} for t in TOPICS]})
    save_new(PRIVATE / 'test_blind.json', blind)
    release = {'version': 'compact-test-release-v1.0', 'review_n': 30, 'topic_rows': 180,
        'test_id_range': 'TS001-TS030', 'human_inputs_filled': 0,
        'method_freeze_sha256': sha(PUBLIC / 'compact_method_freeze.json'),
        'scope_sha256': sha(PRIVATE / 'scope.json'), 'blind_sha256': sha(PRIVATE / 'test_blind.json'),
        'test_metrics_generated': False}
    save_new(PUBLIC / 'compact_test_release.json', release)
    print(json.dumps(release, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['diagnose', 'freeze'])
    args = parser.parse_args()
    (diagnose if args.action == 'diagnose' else freeze)()


if __name__ == '__main__':
    main()
