"""Engineering tests on authored text; these are NOT human model evaluations."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from prepare_stage4 import find_text_groups, normalize, UnionFind
from validate_annotations import validate_label
from advance_stage4 import group_split


class AnnotationSafety(unittest.TestCase):
    def test_blank_is_not_absent(self):
        self.assertTrue(validate_label('', '', '', '', 'Hay cocina.'))
        self.assertEqual(validate_label('ausente', 'no_aplica', '', '', 'Hay cocina.'), [])

    def test_evidence_must_be_verbatim_and_nonempty(self):
        text = 'La cama era cómoda, pero el wifi no funcionaba.'
        self.assertEqual(validate_label('presente', 'mixto',
            'La cama era cómoda || el wifi no funcionaba.', '', text), [])
        self.assertTrue(validate_label('presente', 'negativo', 'La ducha fallaba', '', text))
        self.assertTrue(validate_label('presente', 'mixto', 'La cama era cómoda ||', '', text))

    def test_uncertainty_cannot_be_silently_completed(self):
        self.assertTrue(validate_label('incierto', 'positivo', 'tranquilo', 'ambiguo', 'tranquilo'))
        self.assertTrue(validate_label('presente', 'incierto', 'tranquilo', '', 'tranquilo'))
        self.assertEqual(validate_label('incierto', 'incierto', 'tranquilo',
                                        'No hay contexto acústico.', 'tranquilo'), [])

    def test_absence_cannot_have_sentiment_or_evidence(self):
        self.assertTrue(validate_label('ausente', 'positivo', '', '', 'Hola'))
        self.assertTrue(validate_label('ausente', 'no_aplica', 'Hola', '', 'Hola'))

    def test_grouping_prevents_template_and_listing_leakage(self):
        base = 'La casa estaba muy cerca del metro y el anfitrión respondió siempre con mucha rapidez.'
        records = [dict(review_id='a', clean_text=base),
                   dict(review_id='b', clean_text=base.upper()),
                   dict(review_id='c', clean_text=base + ' Gracias.'),
                   dict(review_id='d', clean_text='Una experiencia totalmente distinta y sin más detalles.')]
        groups, edges, _ = find_text_groups(records)
        self.assertEqual(groups.find('a'), groups.find('b'))
        self.assertEqual(groups.find('a'), groups.find('c'))
        self.assertNotEqual(groups.find('a'), groups.find('d'))
        self.assertTrue(any(edge[2] == 'near' for edge in edges))
        components = UnionFind(['a', 'b', 'c', 'd'])
        for rid in components.parent:
            components.union(rid, groups.find(rid))
        components.union('c', 'd')  # Same listing links two otherwise distinct texts.
        self.assertEqual(components.find('a'), components.find('d'))

    def test_short_text_and_negation_are_preserved(self):
        self.assertNotEqual(normalize('Estaba limpio'), normalize('No estaba limpio'))
        self.assertNotEqual(normalize('Sí'), normalize('Si'))
        records = [dict(review_id='a', clean_text='Bien!'), dict(review_id='b', clean_text='BIEN'),
                   dict(review_id='c', clean_text='No bien')]
        groups, _, _ = find_text_groups(records)
        self.assertEqual(groups.find('a'), groups.find('b'))
        self.assertNotEqual(groups.find('a'), groups.find('c'))

    def test_formal_split_rejects_shared_listing_and_explored_group(self):
        rows=[dict(annotation_id=f'x{i}',review_id=f'r{i}',listing_id=f'l{i}',
                   component_id=f'g{i}',text_cluster=f't{i}',stage='reserve_unsplit') for i in range(6)]
        a,b=group_split(rows,set(),17,4)
        self.assertEqual((len(a),len(b)),(4,2))
        self.assertEqual(group_split(list(reversed(rows)),set(),17,4),(a,b))
        with self.assertRaises(ValueError):group_split(rows,{'g2'},17,4)
        rows[-1]['listing_id']=rows[0]['listing_id']
        with self.assertRaises(ValueError):group_split(rows,set(),17,4)


if __name__ == '__main__':
    unittest.main()
