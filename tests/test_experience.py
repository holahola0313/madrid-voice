"""Evidence provenance, SQL distinct counts, filters and export roundtrip."""
import csv
import io
import unittest
from dashboard import data as d, experience as x

class EvidenceWorkflow(unittest.TestCase):
    def test_case_quotes_labels_and_export(self):
        for aid in x.CASES:
            c=x.case_data(aid)  # validates source substrings and fixed model versions
            for t in c['topics']:
                self.assertEqual(set(c['labels'][t]),{'人工参考','关键词规则','本地AI'})
            self.assertIn('<mark>',x.highlighted(c))
        c=x.case_data('TS008')
        self.assertEqual(c['labels']['facilities']['人工参考']['sentiment'],'negative')
        self.assertEqual(c['labels']['facilities']['本地AI']['sentiment'],'positive')
        items=[x.checklist_item(a) for a in ['TS008','TS021']]
        rows=list(csv.DictReader(io.StringIO(x.checklist_csv(items).decode('utf-8-sig'))))
        self.assertEqual(rows,items)
        self.assertTrue(all(r['状态']=='待核查' for r in rows))
        self.assertNotIn('review_id',rows[0]);self.assertNotIn('listing_id',rows[0])
        self.assertIn('尚未经作者复核',rows[0]['翻译状态'])
        malicious=[dict(items[0],问题='=1+1')]
        self.assertIn("'=1+1",x.checklist_csv(malicious).decode('utf-8-sig'))
    def test_counts_against_independent_row_dedup(self):
        for method in d.METHODS:
            for p in [d.parameters(method=method),d.parameters(district='Centro',method=method),d.parameters(room_type='Hotel room',method=method),d.parameters(start='2026-05-01',end='2026-05-31',method=method)]:
                counts=x.topic_counts(p).set_index('topic')
                allmeta=d.filtered_metadata(p)
                labels=d.query('SELECT review_id,topic,mention_status,sentiment FROM review_labels WHERE method_id=:method_id AND version=:version',p)
                joined=allmeta.merge(labels,on='review_id',validate='one_to_many')
                self.assertEqual(len(joined),6*len(allmeta))
                old=d.topics(p).set_index('topic')
                for t in d.TOPICS:
                    mention=joined[(joined.topic==t)&(joined.mention_status=='present')]
                    lead=mention[mention.sentiment.isin(['negative','mixed'])]
                    self.assertEqual(int(counts.loc[t,'lead_reviews']),lead.review_id.nunique())
                    self.assertEqual(int(counts.loc[t,'lead_listings']),lead.listing_id.nunique())
                    self.assertEqual(int(counts.loc[t,'lead_reviews']),old.loc[t,'negative_n']+old.loc[t,'mixed_n'])
    def test_prediction_examples_respect_all_filters(self):
        for method in d.METHODS:
            for topic in d.TOPICS:
                examples=x.prediction_examples(d.parameters(method=method),topic)
                self.assertGreater(len(examples),0)
                for e in examples:
                    self.assertFalse(any(s in e['quote'] for s in ['@','http','Carmen','Maria']))
                    self.assertIn(e['sentiment'],['negative','mixed'])
                p=d.parameters(district='Centro',room_type='Entire home/apt',start='2026-05-01',end='2026-05-31',method=method)
                for e in x.prediction_examples(p,topic):
                    self.assertEqual(e['district'],'Centro');self.assertEqual(e['room_type'],'Entire home/apt')
                    self.assertTrue(e['date'].startswith('2026-05'))
        p=d.parameters(district='not-a-district')
        self.assertTrue(x.topic_counts(p).empty)
        self.assertEqual(x.prediction_examples(p,'facilities'),[])
        self.assertEqual(x.matching_cases(p,'facilities'),[])
    def test_gold_cases_do_not_escape_filters(self):
        self.assertEqual(x.matching_cases(d.parameters(district='Chamberí'),'facilities'),['TS021'])
        self.assertEqual(x.matching_cases(d.parameters(room_type='Hotel room'),'facilities'),[])
        self.assertEqual(x.matching_cases(d.parameters(),'cleanliness'),[])

if __name__=='__main__':unittest.main()
