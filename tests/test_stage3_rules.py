"""Authored unit cases, NOT actual human-labelled reviews or model evaluation."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from topic_methods import rule_predict,clauses

def label(text,topic):return next(l for l in rule_predict(text) if l['topic']==topic)
class RulesBehaviour(unittest.TestCase):
    def test_negated_cleanliness(self):
        self.assertEqual(label('El piso no estaba limpio.','cleanliness')['sentiment'],'negative')
    def test_negated_noise(self):
        self.assertEqual(label('No había ruido.','noise')['sentiment'],'positive')
    def test_adversative_mixed(self):
        self.assertEqual(label('La habitación estaba limpia pero el baño estaba sucio.','cleanliness')['sentiment'],'mixed')
    def test_no_solo_is_not_negation(self):
        self.assertEqual(label('No solo estaba limpio, era impecable.','cleanliness')['sentiment'],'positive')
    def test_uncertainty(self):
        self.assertEqual(label('Quizás había ruido.','noise')['sentiment'],'uncertain')
    def test_descriptive_neutral(self):
        self.assertEqual(label('Hay cocina y wifi.','facilities')['sentiment'],'neutral')
    def test_mention_not_equal_negative(self):
        l=label('La ubicación.','location')
        self.assertEqual((l['mention_status'],l['sentiment']),('present','uncertain'))
    def test_multilabel_and_exact_offsets(self):
        text='Muy limpio. Buena ubicación, cerca del metro. No había ruido.'
        labels=rule_predict(text)
        self.assertEqual(len(labels),6)
        for l in labels:
            for span in l['spans']:self.assertEqual(text[span['start']:span['end']],span['text'])
        self.assertEqual(sum(l['mention_status']=='present' for l in labels),3)
    def test_absence_is_explicit(self):
        l=label('Gracias por todo.','noise')
        self.assertEqual((l['mention_status'],l['sentiment'],l['evidence_text']),('absent','not_applicable',''))
    def test_chunking_does_not_change_text_evidence(self):
        text=('El apartamento estaba limpio y cómodo. '*30)
        parts=clauses(text,50)
        self.assertTrue(all(text[p['start']:p['end']]==p['text'] and len(p['text'])<=50 for p in parts))
if __name__=='__main__':unittest.main(verbosity=2)
