"""Synthetic in-memory fixtures test SQL behaviour, never model quality."""
import sqlite3
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PARAMS=dict(district=None,room_type=None,start_date='2025-09-01',end_date='2026-08-31')

class SqlBehaviour(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.executescript((ROOT/'sql/00_schema.sql').read_text(encoding='utf-8'))
        self.db.execute("INSERT INTO settings VALUES (1,'2026-09-17','2025-09-01','2026-08-31',1,1,1,'test')")
        self.db.execute("INSERT INTO listings VALUES ('l1','pub1','scrape','2026-09-20','A','a','Private room',2)")
        for i in (1,2):
            self.db.execute('INSERT INTO reviews VALUES ('+','.join(['?']*16)+')',
                (str(i),'r'+str(i),'l1','2025-09-01','synthetic text','synthetic text','h'+str(i),
                 'es',.99,'es_candidate','test','unambiguous','included','','test',i))

    def tearDown(self):
        self.db.close()

    def query(self,name):
        return [dict(r) for r in self.db.execute((ROOT/'sql'/name).read_text(encoding='utf-8'),PARAMS)]

    def method(self,name='rules'):
        self.db.execute('INSERT INTO methods VALUES (?,?,?,?,?)',(name,'v1','rule','unvalidated','synthetic test'))

    def label(self,review='1',topic='noise',method='rules',mention='present',sentiment='negative'):
        self.db.execute('INSERT INTO review_labels VALUES (?,?,?,?,?,?,?,?)',
                        (review,topic,method,'v1',mention,sentiment,'synthetic text','2026-10-13'))

    def test_missing_labels_are_not_zero_negativity(self):
        self.assertEqual(self.query('08_future_topic_metrics.sql'),[])
        self.method();self.label()
        noise=next(r for r in self.query('08_future_topic_metrics.sql') if r['topic']=='noise')
        self.assertEqual((noise['denominator_n'],noise['labelled_n']),(2,1))
        self.assertIsNone(noise['negative_feedback_pct'])

    def test_multilabel_and_versions_do_not_inflate_denominator(self):
        self.method();self.method('ai')
        topics=[r[0] for r in self.db.execute('SELECT topic FROM topics')]
        for method in ('rules','ai'):
            for review in ('1','2'):
                for topic in topics:
                    self.label(review,topic,method)
        rows=self.query('08_future_topic_metrics.sql')
        self.assertEqual(len(rows),12)
        self.assertTrue(all(r['denominator_n']==2 and r['labelled_n']==2 for r in rows))
        self.assertEqual(self.query('01_join_checks.sql')[0]['joined_rows'],2)

    def test_mixed_is_separate_and_absent_is_explicit(self):
        self.method();self.label(sentiment='mixed');self.label('2',mention='absent',sentiment='not_applicable')
        noise=next(r for r in self.query('08_future_topic_metrics.sql') if r['topic']=='noise')
        self.assertEqual((noise['mention_n'],noise['negative_n'],noise['mixed_n']),(1,0,1))
        self.assertEqual(noise['mention_pct'],50.0)

    def test_key_foreign_key_and_label_constraints(self):
        self.method();self.label()
        with self.assertRaises(sqlite3.IntegrityError): self.label()
        with self.assertRaises(sqlite3.IntegrityError): self.label('missing')
        with self.assertRaises(sqlite3.IntegrityError): self.label('2',mention='absent',sentiment='negative')

    def test_ambiguous_and_outside_window_are_not_analysed(self):
        self.db.execute("UPDATE reviews SET join_status='quarantine_cross_listing_id' WHERE review_id='1'")
        self.db.execute("UPDATE reviews SET review_date='2024-01-01' WHERE review_id='2'")
        self.assertEqual(self.db.execute('SELECT count(*) FROM analysis_reviews').fetchone()[0],0)

    def test_filter_minimum_and_empty_months(self):
        self.db.execute('UPDATE settings SET min_reviews=100,min_listings=20')
        row=self.query('06_filtered_coverage.sql')[0]
        self.assertEqual((row['review_n'],row['meets_minimum']),(2,0))
        months=self.query('05_monthly_trend.sql')
        self.assertEqual(len(months),12)
        self.assertEqual(months[1]['review_n'],0)
        self.assertIsNone(months[2]['sample_count_change_pct'])

if __name__=='__main__': unittest.main(verbosity=2)
