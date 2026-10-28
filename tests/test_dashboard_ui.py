"""Exercise navigation, real checklist state and filter-empty behavior."""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest
ROOT=Path(__file__).resolve().parents[1]

class DashboardFlows(unittest.TestCase):
    def app(self): return AppTest.from_file(str(ROOT/'app.py'),default_timeout=30).run()
    def clean(self,a): self.assertEqual([e.message for e in a.exception],[])
    def button(self,a,label): return next(b for b in a.button if b.label==label)
    def select(self,a,label): return next(b for b in a.selectbox if b.label==label)
    def test_demo_checklist_and_case_switch(self):
        a=self.app(); self.clean(a)
        self.assertEqual(len(a.selectbox),0)  # no filters before starting
        self.button(a,'查看案例').click().run(); self.clean(a)
        self.assertEqual(a.session_state['case'],'TS008')
        self.assertIn('判断依据',[e.label for e in a.expander])
        self.button(a,'加入清单').click().run(); self.clean(a)
        self.assertEqual(list(a.session_state['checklist']),['TS008'])
        self.assertTrue(self.button(a,'已加入清单').disabled)
        self.button(a,'查看清单').click().run(); self.clean(a)
        self.assertEqual(len(a.get('download_button')),1)
        self.button(a,'返回评论').click().run()
        for aid in ['TS004','TS021','TS029','TS006']:
            self.select(a,'选择案例').set_value(aid).run(); self.clean(a)
        a.radio(key='page').set_value('核查清单').run()
        self.button(a,'移除').click().run(); self.clean(a)
        self.assertEqual(a.session_state['checklist'],{})
    def test_topics_filters_and_empty(self):
        a=self.app(); self.button(a,'主题分析').click().run(); self.clean(a)
        for topic in ['cleanliness','noise','checkin','facilities','communication','location']:
            a.button(key='topic_'+topic).click().run(); self.clean(a)
        self.select(a,'预测方法').set_value('本地AI').run(); self.clean(a)
        self.select(a,'月份').set_value('2026-05').run(); self.clean(a)
        self.assertTrue(any('429 条候选评论' in c.value for c in a.caption))
        self.select(a,'月份').set_value('全部').run()
        self.select(a,'房型').set_value('Hotel room').run(); self.clean(a)
        self.assertTrue(any('4 条候选评论' in c.value for c in a.caption))
        self.assertTrue(any('没有可展示的人工复核案例' in i.value for i in a.info))
        self.select(a,'区域').set_value('Vicálvaro').run(); self.clean(a)
        self.assertTrue(any('当前筛选没有评论' in i.value for i in a.info))
    def test_research_metrics_and_case_entry(self):
        a=self.app(); self.button(a,'方法说明').click().run(); self.clean(a)
        self.select(a,'评估任务').set_value('mention').run(); self.clean(a)
        self.assertEqual(len(a.get('download_button')),5)
        self.button(a,'查看原文 · 房间采光').click().run(); self.clean(a)
        self.assertEqual(a.session_state['case'],'TS004')
if __name__=='__main__':unittest.main()
