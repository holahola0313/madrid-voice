"""Rebuild aggregate presentation artifacts, without changing source data or labels."""
import sys,json,hashlib,importlib.metadata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard import data as d

def main():
    d.verify_frozen();out=ROOT/'outputs/stage5';out.mkdir(exist_ok=True)
    base=d.filtered_metadata(d.parameters())
    assert len(base)==base.review_id.nunique()==3763
    assert base.listing_id.nunique()==2770
    actual=d.evaluation(d.parameters());original=d.read('outputs/stage4/evaluation/metrics.json')
    for row in original:
        hit=actual[(actual.method==row['method'])&(actual.topic==row['topic'])&(actual.task==row['task'])].iloc[0]
        for k in ['n','support','predicted','tp','fp','fn','excluded','model_abstentions']:
            assert hit[k]==row[k],(row,k)
        for k in ['precision','recall','f1']:
            assert (d.pd.isna(hit[k]) and row[k] is None) or hit[k]==row[k]
    for dim in ['district','room_type','month']:
        d.coverage(d.parameters(dimension=dim)).to_csv(out/f'coverage_{dim}.csv',index=False,encoding='utf-8-sig')
    for name,(method,version) in d.METHODS.items():
        for dim in ['overall','district','room_type','month']:
            table=d.topics(d.parameters(method=name,dimension=dim))
            assert (table.labelled_n==table.denominator_n).all()
            assert table.denominator_n.sum()==3763*6
            table.to_csv(out/f'{method}_{dim}.csv',index=False,encoding='utf-8-sig')
    paths=['data/processed/madrid_voice.sqlite','data/stage4/compact/test_accepted_v1.json',
           'outputs/stage4/evaluation/metrics.json','data/stage4/compact/test_blind.json',
           'data/stage4/compact/test_predictions_frozen_v1.json']
    manifest={'built_on':'2026-10-23','candidate_reviews':3763,'listings':2770,'test_reviews':30,
        'join_check':'one label per review/topic/method/version; 6 x 3763 denominators for every grouping',
        'historical_evaluation_reproduced':True,
        'versions':{p:importlib.metadata.version(p) for p in ['streamlit','plotly','pandas','reportlab','pypdf']},
        'hashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
    (out/'input_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(d.topics(d.parameters(dimension='room_type')).query("topic == 'noise'").to_string(index=False))
if __name__=='__main__':main()
