"""Local, evidence-first Madrid Voice. Run with streamlit run app.py."""
from html import escape
import pandas as pd
import plotly.express as px
import streamlit as st
from dashboard import data as d
from dashboard import experience as x

st.set_page_config(page_title='Madrid Voice | 西语评论分析',page_icon='◉',layout='wide')
st.markdown('<style>'+(d.ROOT/'dashboard/style.css').read_text(encoding='utf-8')+'</style>',unsafe_allow_html=True)
try:
    d.verify_frozen()
except (ValueError,FileNotFoundError) as e:
    st.error('固定输入校验失败，请按复现说明恢复文件。'+str(e)); st.stop()
PAGES=['首页','体验一条评论','探索评论中的问题','核查清单','研究发现与方法']
# Keep existing session routes; display short, consistent names in navigation.
PAGE_LABELS=dict(zip(PAGES,['首页','评论分析','主题分析','核查清单','方法说明']))
for key,value in [('page','首页'),('case','TS008'),('topic','facilities'),('checklist',{})]:
    st.session_state.setdefault(key,value)

def go(page,aid=None):
    st.session_state.page=page
    if aid: st.session_state.case=aid
def choose_topic(topic): st.session_state.topic=topic
def add_check(aid): st.session_state.checklist[aid]=x.checklist_item(aid)
def remove_check(aid): st.session_state.checklist.pop(aid,None)

with st.sidebar:
    st.markdown('<div class="brand"><span>MV</span><b>Madrid Voice</b></div>',unsafe_allow_html=True)
    st.caption('住宿体验分析')
    st.radio('工作区',PAGES,key='page',format_func=PAGE_LABELS.get,label_visibility='collapsed')
    st.divider()
    st.markdown('**个人项目 · 模拟运营场景**')
    st.caption('面向住宿运营人员的评论分析原型。\n\n本地运行，不上传评论。')
    if st.session_state.checklist:
        st.caption(f'本次会话已记录 {len(st.session_state.checklist)} 项待核查事项')
    st.markdown('[数据来源：Inside Airbnb](https://insideairbnb.com/get-the-data/)')
    st.caption('Madrid · 2026-09-17快照目录\n\n[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)')

def eyebrow(text): st.markdown(f'<div class="eyebrow">{escape(text)}</div>',unsafe_allow_html=True)
def title(text,description):
    st.title(text); st.markdown(f'<div class="intro">{escape(description)}</div>',unsafe_allow_html=True)
def plot(fig):
    fig.update_layout(font=dict(family='Arial, Microsoft YaHei',color='#10294A',size=14),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)',margin=dict(l=8,r=8,t=45,b=8),legend_title_text='')
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor='#E5EBF3',zeroline=False)
    st.plotly_chart(fig,width='stretch')
def quote(c,hero=False):
    tags=''.join('<span class="tag tag-'+c['labels'][t]['人工参考']['sentiment']+'">'+d.TOPICS[t]+' · '+d.SENTIMENTS[c['labels'][t]['人工参考']['sentiment']]+'</span>' for t in c['topics'])
    st.markdown(f'''<div class="quote-card {'hero-quote' if hero else ''}"><div class="original-pane">
      <div class="quote-label">真实评论 · {escape(c['aid'])} / {escape(c['name'])}</div>
      <div class="spanish" lang="es">“{x.highlighted(c)}”</div>
      </div><div class="reference-pane"><div class="translation">{escape(c['translation'])}</div>
      <div class="translation-note">{x.TRANSLATION_STATUS}</div>
      <div class="tags">{tags}</div>
      <div class="quote-foot">人工参考：作者单人标注 · 高亮：本次演示选取的原文证据</div>
    </div></div>''',unsafe_allow_html=True)
def comparison(c):
    with st.expander('判断依据'):
        st.caption('比较的是同一条评论的固定结果。人工参考来自作者的单人标注；下方解释为本次整理，没有据此修改模型。')
        for col,(name,key) in zip(st.columns(3),[('关键词规则','rules'),('本地AI','ai'),('人工参考','human')]):
            with col:
                st.markdown('#### '+name)
                for t in c['topics']:
                    st.markdown('**'+d.TOPICS[t]+'** · '+x.label_text(c['labels'][t][name]))
                st.write(c[key])
        st.caption('规则：rules-v1.0.0 · 本地AI：minilm-prototypes-v1.0.0 · 人工参考：test_accepted_v1。AI为本地句向量与原型匹配；没有调用付费API。')
def checklist_preview():
    items=list(st.session_state.checklist.values())
    if items:
        st.download_button('导出 CSV',x.checklist_csv(items),'Madrid_Voice_核查清单.csv','text/csv',key='download_checks')
        st.caption('含西语证据、翻译状态、参考版本和条件性建议；无姓名、精确地址或原始ID。')
def human_case_card(aid,topic,method):
    c=x.case_data(aid)
    with st.container(border=True):
        st.markdown('**'+c['name']+'** · '+x.label_text(c['labels'][topic]['人工参考']))
        st.write('“'+next(z[2] for z in d.EXCERPTS if z[0]==aid and z[1]==topic)+'”')
        st.caption('当前方法：'+x.label_text(c['labels'][topic][method])+'。人工案例可能包含模型漏判。')
        st.button('查看案例 · '+c['name'],key='explore_'+aid,on_click=go,args=('体验一条评论',aid))
def filters():
    with st.expander('筛选条件'):
        meta=d.filtered_metadata(d.parameters())
        a,b,c=st.columns(3)
        district=a.selectbox('区域',['全部']+sorted(meta.district.unique()),key='district')
        room=b.selectbox('房型',['全部']+sorted(meta.room_type.unique()),key='room')
        months=pd.period_range(d.START,d.END,freq='M').astype(str).tolist()
        month=c.selectbox('月份',['全部']+months,key='month')
        method=st.selectbox('预测方法',list(d.METHODS),key='prediction_method')
        st.caption('房型与区域是快照时属性，未必等同评论发生时。切换主题或方法会保留筛选。')
    start,end=d.START,d.END
    if month!='全部':
        period=pd.Period(month,freq='M'); start=str(period.start_time.date());end=str(period.end_time.date())
    return d.parameters(None if district=='全部' else district,None if room=='全部' else room,start,end,method=method)

page=st.session_state.page
if page=='首页':
    eyebrow('MADRID VOICE')
    st.markdown('<h1 class="home-title">西语评论分析</h1>',unsafe_allow_html=True)
    st.markdown('<p class="hero-sub">面向住宿运营人员，整理体验问题、原文证据与核查事项。</p>',unsafe_allow_html=True)
    a,b,_=st.columns([1,1.15,2.1])
    a.button('查看案例',type='primary',width='stretch',on_click=go,args=('体验一条评论','TS008'))
    b.button('主题分析',width='stretch',on_click=go,args=('探索评论中的问题',))
    st.markdown('<div class="workbench-heading"><span>案例预览</span><small>原文 · 判断 · 核查</small></div>',unsafe_allow_html=True)
    left,right=st.columns([1.65,1],gap='medium')
    with left: quote(x.case_data('TS008'),True)
    with right:
        st.markdown('''<div class="home-action"><div class="eyebrow">模拟运营</div><h2>核查建议</h2><div class="action-step"><b>01</b><div><strong>核查事项</strong><p>核对出现异响的时段、运行模式与来源。</p></div></div><div class="action-step"><b>02</b><div><strong>确认后处理</strong><p>若确认设备异常，安排检修并复测；若未复现，补充运行条件后排查。</p></div></div><p class="action-note">模拟建议 · 尚未确认故障或派单</p></div>''',unsafe_allow_html=True)
    meta=d.filtered_metadata(d.parameters())
    st.markdown(f'<div class="scope-line"><span><b>{len(meta):,}</b> 条西语候选评论</span><span><b>{meta.listing_id.nunique():,}</b> 套房源</span><span>{d.START} 至 {d.END}</span></div>',unsafe_allow_html=True)
    a,b=st.columns([4,1])
    a.caption('个人项目 · 模拟业务场景。模型仅在30条单人标注测试上有限评估，漏判明显；预测线索不等于已核实投诉。')
    b.button('方法说明',on_click=go,args=('研究发现与方法',),width='stretch')
elif page=='体验一条评论':
    title('评论分析','查看真实案例的原文、判断依据与核查建议。')
    st.selectbox('选择案例',list(x.CASES),format_func=lambda k:x.CASES[k]['name'],key='case')
    c=x.case_data(st.session_state.case)
    st.caption(f'{c["district"]} · {c["review_date"]}')
    left,right=st.columns([1.65,1],gap='medium')
    with left:
        quote(c)
        for original,meaning in c['context']:
            st.markdown('**补充证据**');st.write('“'+original+'”');st.caption(meaning+'（AI辅助翻译，待作者复核）')
        st.caption('展示经过隐私检查的短片段；标签基于整条评论，补充上下文已在需要时列出。')
    with right:
        with st.container(border=True,key='case_actions'):
            eyebrow('模拟运营')
            st.markdown('### 核查建议');st.write(c['check'])
            st.markdown('**确认后处理**');st.write(c['action'])
            added=c['aid'] in st.session_state.checklist
            st.button('已加入清单' if added else '加入清单',type='primary',disabled=added,width='stretch',on_click=add_check,args=(c['aid'],),key='add_case')
            if added:st.button('查看清单',on_click=go,args=('核查清单',),width='stretch')
            st.caption('仅记录待核查事项，不表示已派单、已确认故障或已完成处理。')
    comparison(c)
    st.button('主题分析',on_click=go,args=('探索评论中的问题',))
elif page=='探索评论中的问题':
    title('主题分析','按主题查看模型预测与评论证据。预测数量不等于已确认的投诉数量。')
    p=filters()
    method=st.session_state.prediction_method
    meta=d.filtered_metadata(p)
    st.caption(f'{method}预测 · 当前范围：{p["district"] or "全部区域"} / {p["room_type"] or "全部房型"} / {p["start_date"]} 至 {p["end_date"]} · {len(meta):,} 条候选评论 / {meta.listing_id.nunique():,} 套房源')
    if meta.empty:
        st.info('当前筛选没有评论。请扩大区域、房型或月份范围。')
        st.button('查看其他案例',on_click=go,args=('体验一条评论','TS008'))
        st.caption('将离开当前筛选，打开独立案例。')
    else:
        counts=x.topic_counts(p).set_index('topic')
        rail,detail=st.columns([.78,2.35],gap='medium')
        with rail,st.container(key='topic_rail'):
            eyebrow('体验主题')
            for t in d.TOPICS:
                r=counts.loc[t]
                st.button(f'{d.TOPICS[t]} · {int(r.lead_reviews)} 条线索',type='primary' if t==st.session_state.topic else 'secondary',width='stretch',on_click=choose_topic,args=(t,),key='topic_'+t)
                st.caption(f'主题提及 {int(r.mention_reviews):,} 条 / {int(r.mention_listings):,} 套')
            st.caption('线索＝负面＋混合预测。主题可重叠，数量不能相加。')
        with detail,st.container(key='topic_detail'):
            t=st.session_state.topic;r=counts.loc[t]
            st.markdown(f'<div class="lead-heading"><h2>{d.TOPICS[t]}</h2><p><strong>{int(r.lead_reviews):,}</strong> 条评论 · <strong>{int(r.lead_listings):,}</strong> 套房源含预测负面内容</p></div>',unsafe_allow_html=True)
            st.caption('这里的房源数只统计涉及负面内容的不同房源，不是当前范围全部房源。')
            a,b=st.columns([1.2,1],gap='large')
            with a:
                st.markdown('#### 预测证据')
                examples=x.prediction_examples(p,t)
                if not examples:
                    st.info('当前筛选下，该方法未识别出此主题的负面内容线索；这不等于已证实没有问题。' if int(r.lead_reviews)==0 else '当前筛选和方法下，没有可公开展示的精选预测片段。上方数量仍按全部匹配记录计算；不代表没有预测线索。')
                for e in examples:
                    with st.container(border=True):
                        st.caption(f'{e["code"]} · {e["district"]} · {e["date"]} · 模型预测：{d.SENTIMENTS[e["sentiment"]]}')
                        st.markdown('<div class="evidence-quote" lang="es">“'+escape(e['quote'])+'”</div>',unsafe_allow_html=True)
                        st.write(e['translation'])
                        st.caption('AI辅助翻译，待作者复核。未纳入作者人工参考标注；证据片段并不保证模型判断正确。')
                st.caption('仅展示本项目选取并检查隐私的短片段，非随机样本。未用其他区域、房型或月份的案例填补空缺。')
            with b:
                st.markdown('#### 人工参考')
                aids=x.matching_cases(p,t)
                for aid in aids[:1]:human_case_card(aid,t,method)
                if len(aids)>1:
                    with st.expander(f'更多案例（{len(aids)-1}）'):
                        for aid in aids[1:]:human_case_card(aid,t,method)
                if not aids:
                    st.info('当前筛选内没有可展示的人工复核案例。不能把模型片段补成人工证据。')
                    st.button('查看其他案例',on_click=go,args=('体验一条评论','TS008'))
                    st.caption('将离开当前筛选，打开独立案例。')
                st.markdown('#### 核查建议');st.write(x.TOPIC_CHECKS[t]);st.caption('仅为模拟核查方向。先核实具体事实，再决定措施。')
        with st.expander('分组对比'):
            dim=st.radio('比较维度',['区域','房型','月份'],horizontal=True)
            v=d.topics(dict(p,dimension={'区域':'district','房型':'room_type','月份':'month'}[dim]))
            v=v[v.topic==t].copy();v['负面内容线索']=v.negative_n+v.mixed_n
            plot(px.bar(v,x='group_name',y='负面内容线索',color_discrete_sequence=['#1556DB'],labels={'group_name':dim},title=d.TOPICS[t]+' · 预测线索'))
            st.caption('数量受样本覆盖影响。各组≥100评论、≥20房源且标签完整时才显示比例。低于门槛仍展示数量；门槛不保证统计显著。')
            st.dataframe(v[['group_name','denominator_n','mention_n','negative_n','mixed_n','negative_content_pct']].rename(columns={'group_name':dim,'denominator_n':'评论分母','mention_n':'提及数','negative_n':'负面','mixed_n':'混合','negative_content_pct':'负面内容预测比例%'}),hide_index=True,width='stretch')
        with st.expander('指标定义'):
            st.write('分子：所选方法和版本标为“已提及”，且情绪为负面或混合的不同评论ID数。房源数另按不同房源ID去重。分母：当前区域、房型和月份内全部西语候选评论。月份为评论日期，不是入住日期。标签缺失不视作未提及。')
            st.caption(f'版本：{p["version"]}。数据窗口 {d.START} 至 {d.END}。主题概览中的数量无最低样本限制，不用于质量排名。')
elif page=='核查清单':
    title('核查清单','保存评论证据和待核查事项，支持导出。仅用于模拟运营，未向企业派单。')
    items=list(st.session_state.checklist.values())
    st.caption('清单仅保存在本次浏览器会话中，刷新或断开可能丢失，请及时导出。切换页面会保留；同一案例不会重复加入。')
    if not items:
        st.info('暂无核查事项。可在评论分析中选择案例并加入清单。')
        st.button('查看案例',type='primary',on_click=go,args=('体验一条评论','TS008'))
    else:
        st.markdown(f'**{len(items)} 项待核查** · 尚未确认现场情况');checklist_preview()
        for item in items:
            with st.container(border=True):
                a,b=st.columns([5,1]);a.markdown('### '+item['问题']);b.button('移除',key='remove_'+item['案例'],on_click=remove_check,args=(item['案例'],))
                st.caption(item['案例']+' · '+item['主题']+' · 待核查');st.write('“'+item['西语证据']+'”')
                st.markdown('**核查：** '+item['建议核查']);st.markdown('**核实后：** '+item['核实后可能采取的措施'])
        st.button('返回评论',on_click=go,args=('体验一条评论',))
else:
    title('方法说明','查看错误案例、模型评估与数据处理过程。')
    st.subheader('错误分析')
    findings=[('TS008','情绪混淆','空调有异响，但AI把设施判成正面。原文中的具体问题，需要按主题单独判断。'),('TS004','间接表达','“no le entra mucha luz”说采光不足，规则与AI都漏掉了设施主题。'),('TS006','语义歧义','tranquilo 未必描述声音。规则判为噪音正面，人工参考保留不确定。')]
    for col,(aid,heading,body) in zip(st.columns(3),findings):
        with col:
            with st.container(border=True):
                st.markdown('### '+heading);st.write(body)
                st.button('查看原文 · '+x.CASES[aid]['name'],key='research_'+aid,on_click=go,args=('体验一条评论',aid))
    with st.expander('否定与混合情绪'):
        st.markdown('**否定范围**：“Check-in rápido y sin problemas, instrucciones claras”是“入住迅速、没有问题、指引清晰”，却被规则标为入住负面。此片段为本次展示检查发现，未纳入30条人工测试标签，不计入任何评估分数。')
        st.markdown('**混合评价**：“cómodo para 2 personas, lamentablemente no tiene elevador”同时肯定舒适度、遗憾没有电梯。人工设施标签为混合，规则中性、AI不确定。')
        st.button('查看原文 · 没有电梯',on_click=go,args=('体验一条评论','TS021'))
    st.subheader('测试结果')
    e=d.evaluation(d.parameters());neg=e[e.task=='negative_content'];facility=neg[neg.topic=='facilities'].set_index('method')
    rule=facility.loc['spanish_rules'];ai=facility.loc['local_minilm_prototypes']
    st.markdown(f'在 **{len(d.human_rows(d.parameters()))} 条**独立测试评论中，人工标注了 **{int(rule.support)} 条设施负面内容**（含混合）。关键词规则检出 **{int(rule.tp)} 条**，本地AI检出 **{int(ai.tp)} 条**。两者都有明显漏判。')
    st.caption('噪音负面只有1条；清洁、入住、沟通、位置没有负面正例，不能评价其检出能力。少量样本中的高分不说明模型可靠，也不能据此校准全量投诉率。')
    with st.expander('评估指标'):
        task=st.selectbox('评估任务',['negative_content','mention','positive','negative','neutral','mixed'],format_func=lambda k:{'mention':'主题提及','negative_content':'负面内容（含混合）',**d.SENTIMENTS}[k])
        v=e[e.task==task].copy();v['主题']=v.topic.map(d.TOPICS);v['方法']=v.method.map({a[0]:k for k,a in d.METHODS.items()})
        plot(px.bar(v,x='主题',y='f1',color='方法',barmode='group',range_y=[0,1],title='各主题 F1',hover_data=['n','support'],color_discrete_sequence=['#1556DB','#D2763B']))
        st.dataframe(v[['方法','主题','n','support','tp','fp','fn','precision','recall','f1','excluded','model_abstentions']].rename(columns={'n':'有效行','support':'人工正例','excluded':'人工排除','model_abstentions':'模型弃答'}),hide_index=True,width='stretch')
        st.caption('P=TP/(TP+FP)，R=TP/(TP+FN)，F1=2TP/(2TP+FP+FN)。零分母为NA；模型漏提及或弃答仍计入FN。逐类情绪只纳入人工明确提及且情绪明确的行；负面内容任务纳入人工未提及或明确提及且情绪明确的行。正例不足10仅作描述。')
        st.download_button('下载评估 CSV',e.to_csv(index=False).encode('utf-8-sig'),'Madrid_Voice_评估.csv','text/csv')
    with st.expander('人工标注'):
        st.write('作者完成30条试标、20条开发、30条测试标注，按房源和近重复文本隔离。先固定方法及测试预测，再用实际人工标注评估。16项测试标签经作者按原指南确认修订；有AI辅助指南复核，是单人参考标注，不是双人金标准。')
        st.write('例如，作者确认“整体好评”不能充当某一具体设施的正面证据，并将空调异响的设施评价改为负面；对只有 tranquilo 的噪音描述保留不确定。没有据测试结果重新调参或重写测试标签。')
        st.caption('中文释义为本次AI辅助整理，尚未经作者复核；它们不用于计算评估结果。')
    with st.expander('数据与复现'):
        st.markdown('''**来源与范围**：Inside Airbnb Madrid，同一2026-09-17快照目录的详细房源与评论；实际采集2026-09-19至22。分析评论窗口2025-09-01至2026-08-31。CC BY 4.0，独立个人分析，不表示来源方背书。

**处理流程**：固定10,000条评论样本，隔离879条房源归属冲突记录，保留9,121条可用记录；保守语言识别得到3,763条西语候选，覆盖2,770套房源。语言候选未全部人工确认。原始ID仅用于内部追溯，公开界面仅展示匿名短片段。

**连接与计数**：房源表、评论表、主题标签表保留唯一键；按方法＋版本限定标签，再用不同评论ID、不同房源ID分别计数。主题多标签可以重叠，不能相加当作评论总数。

**实现**：Python清洗、SQLite查询、可解释关键词规则、本地MiniLM句向量与36个西语原型匹配；Streamlit＋Plotly展示。AI辅助实现，作者完成实际西语人工标注与确认。

**适用边界**：样本描述不能代表全部马德里住宿；评论数量不等于订单，不可预订天数不等于入住天数。不作收入提升、改进效果或因果推断。''')
        for label,path,mime in [('问题线索统计 SQL','sql/11_problem_leads.sql','text/plain'),('数据字典','docs/STAGE_2_DATA_DICTIONARY.md','text/markdown'),('清洗记录','docs/CLEANING_LOG.md','text/markdown'),('本地复现说明','RUN_LOCAL.md','text/markdown')]:
            st.download_button('下载'+label,(d.ROOT/path).read_bytes(),path.split('/')[-1],mime)
    with st.expander('样本分布'):
        p=d.parameters();v=d.coverage(dict(p,dimension='district')).sort_values('reviews')
        plot(px.bar(v,x='reviews',y='group_name',orientation='h',height=560,labels={'reviews':'评论数','group_name':'区域'},color_discrete_sequence=['#1556DB']))
        plot(px.line(d.monthly(p),x='月份',y='reviews',markers=True,labels={'reviews':'评论样本数'},title='月度样本量',color_discrete_sequence=['#1556DB']))
        st.caption('评论数量不等于订单数量；时间变化仅描述当前样本。')
    st.button('返回评论',type='primary',on_click=go,args=('体验一条评论',))
