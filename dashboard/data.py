"""SQLite supplies counts; explicit human labels supply evaluation, never predictions as gold."""
from pathlib import Path
import hashlib
import json
import sqlite3
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
TOPICS={'cleanliness':'清洁','noise':'噪音','checkin':'入住流程','facilities':'设施','communication':'沟通','location':'位置'}
METHODS={'关键词规则':('spanish_rules','rules-v1.0.0'),'本地AI':('local_minilm_prototypes','minilm-prototypes-v1.0.0')}
SENTIMENTS={'positive':'正面','negative':'负面','neutral':'中性','mixed':'混合','uncertain':'不确定','not_applicable':'不适用'}
START='2025-09-01';END='2026-08-31'

def read(relative):return json.loads((ROOT/relative).read_text(encoding='utf-8'))
def connection():return sqlite3.connect((ROOT/'data/processed/madrid_voice.sqlite').as_uri()+'?mode=ro',uri=True)
def query(sql,params=None):
    with connection() as c:return pd.read_sql_query(sql,c,params=params)
def parameters(district=None,room_type=None,start=START,end=END,dimension='overall',method='关键词规则'):
    if dimension not in ('overall','district','room_type','month'):raise ValueError('Invalid dimension')
    mid,version=METHODS[method]
    return dict(district=district,room_type=room_type,start_date=str(start),end_date=str(end),dimension=dimension,method_id=mid,version=version)
def filtered_metadata(p):
    return query('''SELECT review_id,listing_id,district,room_type,review_date FROM analysis_reviews
    WHERE (:district IS NULL OR district=:district) AND (:room_type IS NULL OR room_type=:room_type)
    AND review_date BETWEEN :start_date AND :end_date''',p)
def coverage(p):return query((ROOT/'sql/09_dashboard_coverage.sql').read_text(encoding='utf-8'),p)
def topics(p):return query((ROOT/'sql/10_dashboard_topics.sql').read_text(encoding='utf-8'),p)
def monthly(p):
    rows=coverage(dict(p,dimension='month')).set_index('group_name')
    index=pd.period_range(p['start_date'],p['end_date'],freq='M').astype(str)
    return rows.reindex(index).fillna({'reviews':0,'listings':0,'sample_status':'样本不足，仅展示数量'}).rename_axis('月份').reset_index()

def verify_frozen():
    freeze=read('outputs/stage4/compact_method_freeze.json')
    for name,digest in freeze['hashes'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('固定输入被修改：'+name)
    # Stage 5 also pins the accepted test answers and evaluated files.
    pin=ROOT/'outputs/stage5/input_manifest.json'
    if pin.exists():
        for name,digest in read('outputs/stage5/input_manifest.json')['hashes'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('展示输入被修改：'+name)

def human_rows(p):
    ids=set(filtered_metadata(p).review_id)
    return [r for r in read('data/stage4/compact/test_accepted_v1.json')['answers'] if r['review_id'] in ids]

def binary_counts(pairs):
    tp=sum(g and p for g,p in pairs);fp=sum(not g and p for g,p in pairs);fn=sum(g and not p for g,p in pairs)
    div=lambda a,b:a/b if b else None
    return dict(n=len(pairs),support=tp+fn,predicted=tp+fp,tp=tp,fp=fp,fn=fn,
                precision=div(tp,tp+fp),recall=div(tp,tp+fn),f1=div(2*tp,2*tp+fp+fn))

def evaluation(p):
    answers=human_rows(p)
    predictions=read('data/stage4/compact/test_predictions_frozen_v1.json')
    pred={(r['annotation_id'],r['topic'],r['method_id']):r for r in predictions}
    if len(pred)!=360:raise ValueError('测试预测键不唯一或缺失')
    result=[]
    for method,version in METHODS.values():
      for topic in TOPICS:
       rows=[(r['annotation_id'],next(t for t in r['labels'] if t['topic']==topic)) for r in answers]
       for task in ['mention','negative_content','positive','negative','neutral','mixed']:
        pairs=[];excluded=abstain=0
        for aid,g in rows:
            x=pred[aid,topic,method]
            definite=g['mention_status']=='present' and g['sentiment'] in ('positive','negative','neutral','mixed')
            eligible=(g['mention_status']!='uncertain') if task=='mention' else (g['mention_status']=='absent' or definite) if task=='negative_content' else definite
            if not eligible:excluded+=1;continue
            abstain+=x['mention_status']=='uncertain' or (task!='mention' and x['sentiment']=='uncertain')
            def positive(t):
                if task=='mention':return t['mention_status']=='present'
                return t['mention_status']=='present' and (t['sentiment'] in ('negative','mixed') if task=='negative_content' else t['sentiment']==task)
            pairs.append((positive(g),positive(x)))
        c=binary_counts(pairs)
        result.append(dict(method=method,version=version,topic=topic,task=task,**c,excluded=excluded,
            model_abstentions=abstain,abstention_rate=abstain/len(pairs) if pairs else None,rare=c['support']<10))
    return pd.DataFrame(result)

# Manually reviewed excerpts only: no names, contact details, exact addresses or entire comments.
# The full original evidence remains private. These substrings never replace human labels.
EXCERPTS=[
 ('TS004','facilities','no le entra mucha luz','检查采光说明与房间照片是否准确。'),
 ('TS008','facilities','el aire acondicionado que tenia un ruido extraño','安排空调异响排查；核对维修前后反馈。'),
 ('TS008','noise','el aire acondicionado que tenia un ruido extraño','识别设备噪音来源，与设施问题合并处理。'),
 ('TS021','facilities','lamentablemente no tiene elevador','预订前明确无电梯、楼层与行李搬运条件。'),
 ('TS029','facilities','la única pega que la tele no era SmartTV','明确电视功能，减少预期与配置不符。'),
 ('TS006','noise','en un sector tranquilo','语义不确定，不能据此断言声环境好。'),
]
def evidence(p,topic=None):
    human={r['annotation_id']:r for r in human_rows(p)}
    texts={r['annotation_id']:r['text'] for r in read('data/stage4/compact/test_blind.json')}
    metadata=filtered_metadata(p).set_index('review_id')
    predicted={(r['annotation_id'],r['topic'],r['method_id']):r for r in read('data/stage4/compact/test_predictions_frozen_v1.json')}
    result=[]
    for aid,t,span,action in EXCERPTS:
        if aid not in human or (topic and topic!=t):continue
        if span not in texts[aid]:raise ValueError('公开引文不匹配')
        h=human[aid];gold=next(x for x in h['labels'] if x['topic']==t)
        m=metadata.loc[h['review_id']]
        row={'案例':aid,'主题':TOPICS[t],'区域':m.district,'房型':m.room_type,'人工情绪':SENTIMENTS[gold['sentiment']],'匿名原文片段':span,'模拟行动':action}
        for name,(mid,_) in METHODS.items():
            x=predicted[aid,t,mid];row[name+'预测']=('未提及' if x['mention_status']=='absent' else SENTIMENTS[x['sentiment']])
        result.append(row)
    return pd.DataFrame(result)
