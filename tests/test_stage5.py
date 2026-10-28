"""SQL denominators, evidence privacy and holdout metrics; not model-accuracy claims."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard import data as d

class PresentationIntegrity(unittest.TestCase):
    def test_grouping_does_not_multiply_counts(self):
        for dim in ('overall','district','room_type','month'):
            p=d.parameters(dimension=dim);v=d.topics(p)
            self.assertEqual(v.denominator_n.sum(),6*3763)
            self.assertTrue((v.labelled_n==v.denominator_n).all())
    def test_sparse_room_suppresses_rates(self):
        p=d.parameters(room_type='Hotel room');v=d.topics(p)
        self.assertTrue(v.negative_content_pct.isna().all())
        self.assertEqual(len(d.filtered_metadata(p)),4)
    def test_empty_filter_returns_no_invented_zero_rates(self):
        p=d.parameters(district='not-a-district')
        self.assertTrue(d.topics(p).empty)
        e=d.evaluation(p);self.assertTrue((e.n==0).all());self.assertTrue(e.f1.isna().all())
    def test_metrics_denominators_and_abstentions(self):
        c=d.binary_counts([(True,True),(True,False),(False,True)])
        self.assertEqual(c['f1'],.5)
        self.assertIsNone(d.binary_counts([])['f1'])
        e=d.evaluation(d.parameters());r=e[(e.method=='local_minilm_prototypes')&(e.topic=='facilities')&(e.task=='negative_content')].iloc[0]
        self.assertEqual((r.support,r.tp,r.fn),(5,1,4))
    def test_filtered_test_cannot_add_records(self):
        p=d.parameters(district='Centro');ids={r['review_id'] for r in d.human_rows(p)}
        self.assertTrue(ids.issubset(set(d.filtered_metadata(p).review_id)))
        self.assertLessEqual(len(ids),30)
    def test_curated_evidence_privacy_and_filtering(self):
        e=d.evidence(d.parameters());self.assertEqual(len(e),6)
        self.assertNotIn('review_id',e.columns);self.assertNotIn('listing_id',e.columns)
        self.assertTrue(all(len(x)<120 for x in e['匿名原文片段']))
        for s in e['匿名原文片段']:self.assertFalse(any(x in s for x in ('http','@','Carmen','John')))
        f=d.evidence(d.parameters(district='Chamberí'));self.assertTrue((f['区域']=='Chamberí').all())
    def test_current_metrics_equal_frozen_evaluation(self):
        v=d.evaluation(d.parameters()).set_index(['method','topic','task'])
        for r in d.read('outputs/stage4/evaluation/metrics.json'):
            hit=v.loc[(r['method'],r['topic'],r['task'])]
            for k in ('n','support','tp','fp','fn'):self.assertEqual(hit[k],r[k])
    def test_frozen_inputs(self):d.verify_frozen()

if __name__=='__main__':unittest.main()
