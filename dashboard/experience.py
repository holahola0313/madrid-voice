"""Curated public excerpts and simulated checks. Human labels stay in frozen inputs.

Chinese paraphrases and suggested actions are AI-assisted editorial content, not
new human annotations. Excerpts must match their source and are never used as gold.
"""
import csv
import io
from html import escape
from dashboard import data as d

TRANSLATION_STATUS = 'AI辅助翻译 · 尚未经作者复核 · 以西语原文为准'
CASES = {
    'TS008': dict(name='空调异响', kicker='整体好评里，也可能藏着具体问题',
        excerpt='lo unico el aire acondicionado que tenia un ruido extraño, de resto todo perfecto',
        translation='唯一的问题是空调有奇怪的噪声，除此之外一切都很好。',
        highlights=['aire acondicionado', 'ruido extraño'], topics=['facilities','noise'],
        context=[],
        human='“ruido extraño”明确说了异响；“de resto todo perfecto”是对其他方面的好评，不能抵消空调这项具体批评。设施和噪音均为负面。',
        rules='规则命中 aire acondicionado（空调），却没有在设施词表里匹配到负面情绪，因此设施情绪不确定；ruido（噪声）在噪音规则中触发负面。',
        ai='本地AI把设施判为正面，对噪音则不确定。保存的整句相似度中，设施正面原型最高；结果没有识别出整体赞扬中的具体批评。不能据此解释模型内部的因果机制。',
        check='核对空调异响发生的时段、运行模式与来源，确认设备是否需要维护。',
        action='若现场确认异常，安排检修并记录复测结果；若未复现，补充运行条件后再排查。'),
    'TS004': dict(name='房间采光', kicker='转折后的好话，不会让前面的不足消失',
        excerpt='Si es pequeño, no le entra mucha luz, pero las fotos y la descripción son claras y si lo dice',
        translation='房间确实小、采光不多，不过照片和描述很清楚，也确实说明了这一点。',
        highlights=['no le entra mucha luz', 'pero'], topics=['facilities'],
        context=[('bonito adentro, tampoco pasas frío','内部好看，也不会觉得冷。')],
        human='“no le entra mucha luz”是采光不足；同条评论还有“bonito adentro, tampoco pasas frío”的正面设施反馈，所以整条评论的设施参考标签为混合。',
        rules='规则未识别设施主题：保存结果为 no_topic_cue。采光的间接表达没有被当前关键词覆盖。',
        ai='本地AI也判为未提及设施：保存结果为相似度低于主题不确定阈值。语义模型同样会漏掉间接表达。',
        check='核对房间朝向、自然采光与页面照片、描述是否一致。',
        action='若描述不充分，补充白天实拍与采光说明；若实际照明不足，再评估补充灯具。'),
    'TS021': dict(name='没有电梯', kicker='一句话里，可以同时有肯定和遗憾',
        excerpt='El espacio es pequeño pero cómodo para 2 personas, lamentablemente no tiene elevador',
        translation='空间虽小，但两个人住还算舒适；遗憾的是没有电梯。',
        highlights=['cómodo para 2 personas','no tiene elevador'], topics=['facilities'], context=[],
        human='“cómodo”肯定舒适度，“lamentablemente no tiene elevador”表达缺少电梯的遗憾。同一设施主题既有正面也有负面，因此是混合。',
        rules='规则将设施判为中性。保存的证据命中的是同条评论中厨房的 cocinar / cocina，没有捕捉这句无电梯的批评。',
        ai='本地AI检索到了“no tiene elevador”，但主题和情绪都不确定。检索到一句话，并不等于正确理解了它。',
        check='核对楼层、电梯配置，以及预订前是否明确告知搬运行李的条件。',
        action='若确实无电梯且说明不足，补充醒目的楼层与无电梯提示，并说明可提供的搬运协助。'),
    'TS029': dict(name='电视功能不符预期', kicker='“总体很棒”不代表每一项设施都满意',
        excerpt='la única pega que la tele no era SmartTV',
        translation='唯一的不足是电视不是智能电视。',
        highlights=['la única pega','no era SmartTV'], topics=['facilities'], context=[],
        human='“la única pega”引出具体缺点。整体好评不是电视功能的正面依据，设施参考标签为负面。',
        rules='规则判为未提及设施，保存结果为 no_topic_cue；当前词表没有覆盖这段 tele / SmartTV 的表达。',
        ai='本地AI也判为未提及设施，相似度低于主题不确定阈值。短而具体的设备表达仍然会漏判。',
        check='核对实际电视功能、页面设施说明与住客预期。',
        action='若描述造成误解，明确电视是否支持联网和投屏；是否升级设备需另行评估成本与需求。'),
    'TS006': dict(name='“安静”还是氛围舒适？', kicker='含糊的表达，值得保留不确定性',
        excerpt='en un sector tranquilo', translation='位于一个安静／平和的区域。',
        highlights=['tranquilo'], topics=['noise'], context=[],
        human='tranquilo 可能指声环境，也可能指氛围。原文没有明确声音或睡眠背景，人工参考保留“不确定”，不把它当作噪音好评。',
        rules='规则命中 tranquilo，直接判为噪音正面；这比原文可以支持的判断更强。',
        ai='本地AI判为未提及噪音。它与人工参考的不确定也不相同；当前证据不足以认定声环境好或差。',
        check='如运营确需了解声环境，进一步核实是否涉及声音、时段或睡眠体验。',
        action='仅在获得明确声环境证据后考虑措施；不能凭这句模糊表达安排维修。'),
}

# Privacy-reviewed substrings of model evidence, NOT user-reviewed gold labels.
# These selected examples are not a representative sample and do not add metrics.
MODEL_EXCERPTS = [
 ('PX01','R_04745476bbf04a082a0c2e2d','cleanliness','los baños estaban sucios','浴室很脏。'),
 ('PX02','R_83edddb2eb9bf96a9c8d0ede','noise','mucho ruido en el edificio','楼里噪声很多。'),
 ('PX03','R_8f3a8dcd0a3f11bf18bfa582','checkin','nos dejaron 15-20 minutos bajo la lluvia después de la hora del check in esperando afuera sin darnos los códigos de acceso','到了入住时间以后，仍在雨中等了15至20分钟，没有拿到门禁码。'),
 ('PX04','R_0b059db1adf1018dfbd5299d','facilities','La cocina muy pequeña, no la hemos utilizado por ese motivo','厨房太小，因此没有使用。'),
 ('PX05','R_cbb83959129634f6ad652435','communication','mala comunicación con los administradores','与管理人员沟通不畅。'),
 ('PX06','R_a634597083ab6906afea28ce','location','La zona parece un poco insegura','这个区域让评论者感觉有些不安全。'),
 ('PX07','R_1bbfc3793d7aa9c2d94ec38a','checkin','Check-in rápido y sin problemas, instrucciones claras','入住迅速、没有问题，指引清晰。'),
 ('PX08','R_49cb27d28f5694949de74a56','checkin','No podía abrir la puerta principal con el código que me enviaron','用发给我的密码打不开大门。'),
 ('PX09','R_92b1a046ad03aa46a111b98e','communication','aunque no consiguió resolver los problemas siempre ha sido muy comunicativa y con respuesta rápida','虽然没能解决问题，但一直积极沟通、回复迅速。'),
]
TOPIC_CHECKS = {
 'cleanliness':'先核对具体空间、清扫记录与住客描述；确认问题后，再调整检查点或安排补清。',
 'noise':'先确认声音来源、时段与影响；确认设备、建筑或邻里因素后，再选择维护或沟通措施。',
 'checkin':'核对到达时间、门禁码发送记录和操作指引；确认阻碍后，再调整通知或备用进入方式。',
 'facilities':'核对设备运行、功能与页面承诺；确认故障或预期差异后，再安排维护或更新描述。',
 'communication':'核对消息时间线、未解决的诉求与回复记录；确认沟通中断后，再补充答复或完善交接。',
 'location':'先区分交通不便、主观安全感和位置描述差异；核实后完善信息，不据评论给区域贴标签。',
}

def label_text(label):
    if label['mention_status']=='absent': return '未提及'
    if label['mention_status']=='uncertain': return '主题不确定 · 情绪不确定'
    return '已提及 · '+d.SENTIMENTS[label['sentiment']]

def case_data(aid):
    case=dict(CASES[aid])
    h=next(x for x in d.read('data/stage4/compact/test_accepted_v1.json')['answers'] if x['annotation_id']==aid)
    source=next(x['text'] for x in d.read('data/stage4/compact/test_blind.json') if x['annotation_id']==aid)
    for s in [case['excerpt']]+[x[0] for x in case['context']]:
        if s not in source: raise ValueError('案例原文不匹配：'+aid)
    for s in case['highlights']:
        if s not in case['excerpt']: raise ValueError('高亮不匹配：'+aid)
    predictions=d.read('data/stage4/compact/test_predictions_frozen_v1.json')
    case['labels']={t:{'人工参考':next(x for x in h['labels'] if x['topic']==t),
        **{name:next(x for x in predictions if x['annotation_id']==aid and x['topic']==t and x['method_id']==mid and x['version']==version)
        for name,(mid,version) in d.METHODS.items()}} for t in case['topics']}
    meta=d.filtered_metadata(d.parameters()).set_index('review_id').loc[h['review_id']]
    case.update(aid=aid,district=meta.district,room_type=meta.room_type,review_date=meta.review_date)
    return case

def highlighted(case):
    text=escape(case['excerpt'])
    for span in sorted(case['highlights'],key=len,reverse=True):
        text=text.replace(escape(span),'<mark>'+escape(span)+'</mark>')
    return text

def matching_cases(p,topic):
    ids={x['annotation_id'] for x in d.human_rows(p)}
    return [aid for aid,c in CASES.items() if aid in ids and topic in c['topics']]

def prediction_examples(p,topic):
    rows=d.query('''SELECT a.public_review_id,a.district,a.room_type,a.review_date,a.clean_text,
       l.mention_status,l.sentiment,l.evidence_text FROM analysis_reviews a
       JOIN review_labels l ON a.review_id=l.review_id
       WHERE (:district IS NULL OR a.district=:district)
       AND (:room_type IS NULL OR a.room_type=:room_type)
       AND a.review_date BETWEEN :start_date AND :end_date
       AND l.method_id=:method_id AND l.version=:version AND l.topic=:topic
       AND l.mention_status='present' AND l.sentiment IN ('negative','mixed')''',dict(p,topic=topic))
    rows={r['public_review_id']:r for r in rows.to_dict('records')}
    result=[]
    for code,pid,t,quote,translation in MODEL_EXCERPTS:
        if t!=topic or pid not in rows: continue
        r=rows[pid]
        if quote not in r['evidence_text'] or quote not in r['clean_text']:
            raise ValueError('预测片段未包含在保存的证据与原文中：'+code)
        result.append(dict(code=code,quote=quote,translation=translation,
            district=r['district'],room_type=r['room_type'],date=r['review_date'],sentiment=r['sentiment']))
    return result

def topic_counts(p):
    return d.query((d.ROOT/'sql/11_problem_leads.sql').read_text(encoding='utf-8'),p)

def checklist_item(aid):
    c=case_data(aid)
    return {'案例':aid,'问题':c['name'],'主题':'、'.join(d.TOPICS[t] for t in c['topics']),
        '西语证据':c['excerpt'],'中文释义':c['translation'],'翻译状态':TRANSLATION_STATUS,
        '人工参考':'；'.join(d.TOPICS[t]+'：'+label_text(c['labels'][t]['人工参考']) for t in c['topics']),
        '建议核查':c['check'],'核实后可能采取的措施':c['action'],
        '状态':'待核查','场景':'个人项目 · 模拟核查清单 · 未派单、未验证处理结果',
        '评论日期':c['review_date'],'来源':'Inside Airbnb / Madrid / 2026-09-17 / CC BY 4.0',
        '参考标签版本':'test_accepted_v1','规则版本':d.METHODS['关键词规则'][1],
        'AI版本':d.METHODS['本地AI'][1]}

def checklist_csv(items):
    if not items: return b''
    output=io.StringIO(newline='')
    writer=csv.DictWriter(output,fieldnames=list(items[0]))
    writer.writeheader()
    # Protect spreadsheet users if future editorial values start with a formula.
    for row in items:
        writer.writerow({k:("'"+str(v) if str(v).lstrip().startswith(('=','+','-','@')) else v) for k,v in row.items()})
    return output.getvalue().encode('utf-8-sig')
