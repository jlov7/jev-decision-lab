import copy
import unittest
from jev_lab import engine, metrics, provider

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.case = engine.cases()[0]
        self.request = engine.request_for(self.case)
        self.response = provider.replay(self.case['id'])
    def test_valid_contract(self):
        self.assertEqual(engine.validate(self.request, self.response), self.response)
    def test_labels_never_in_prompt(self):
        import json
        text = json.dumps(self.request)
        self.assertNotIn('expected_owner', text)
        self.assertNotIn('teaching_note', text)
        self.assertNotIn('fixture', text)
    def test_bad_probability_sum_rejected(self):
        self.response['answers']['owner']['probabilities']['operations'] = 3
        with self.assertRaises(ValueError): engine.validate(self.request, self.response)
    def test_unknown_answer_rejected(self):
        self.response['answers']['invented'] = {'type':'noul','noul':.5}
        with self.assertRaises(ValueError): engine.validate(self.request, self.response)
    def test_nan_rejected(self):
        self.response['answers']['sufficient']['noul'] = float('nan')
        with self.assertRaises(ValueError): engine.validate(self.request, self.response)
    def test_wrong_score_mean_rejected(self):
        self.response['answers']['severity']['score'] = 0
        with self.assertRaises(ValueError): engine.validate(self.request, self.response)
    def test_negative_usage_rejected(self):
        self.response['usage']['input_tokens'] = -1
        with self.assertRaises(ValueError): engine.validate(self.request, self.response)
    def test_selected_option_must_be_argmax(self):
        a = self.response['answers']['owner']
        a['choice'] = min(a['probabilities'], key=a['probabilities'].get)
        with self.assertRaises(ValueError): engine.validate(self.request, self.response)
    def test_noul_has_no_confidence(self):
        self.assertNotIn('confidence', self.response['answers']['sufficient'])

class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.case = engine.cases()[1]
        self.response = provider.replay(self.case['id'])
    def test_unverified_source_overrides_confidence(self):
        r = engine.decide(self.case, self.response, .5, 'unverified')
        self.assertEqual(r['route'], 'VERIFY_SOURCE')
    def test_stale_source_overrides_confidence(self):
        self.assertEqual(engine.decide(self.case,self.response,.5,'stale')['route'], 'REFRESH_EVIDENCE')
    def test_threshold_is_not_correctness(self):
        self.assertEqual(engine.decide(self.case,self.response,.99)['route'], 'HUMAN_REVIEW')
    def test_invalid_threshold_rejected(self):
        for t in [-1, 2, float('nan'), True]:
            with self.assertRaises(ValueError): engine.decide(self.case,self.response,t)
    def test_fixture_is_explicit(self):
        r = engine.run(self.case['id'])
        self.assertEqual(r['provenance']['kind'],'synthetic_replay')
        self.assertIsNone(r['provenance']['latency_ms'])
        self.assertIsNone(r['provenance']['usage'])
    def test_replay_same_receipt_without_new_call(self):
        r = engine.run(self.case['id'])
        updated = engine.reconsider(r,.99,'original')
        self.assertEqual(r['response'],updated['response'])
        self.assertEqual(r['provenance'],updated['provenance'])
        self.assertEqual(updated['additional_model_calls'],0)
    def test_all_cases_valid(self):
        self.assertEqual(len(engine.cases()),12)
        for c in engine.cases():
            r=engine.run(c['id'])
            self.assertTrue(r['receipt_hash'])
    def test_unknown_variant_rejected(self):
        with self.assertRaises(ValueError): engine.decide(self.case,self.response,.8,'secret')

class MetricTests(unittest.TestCase):
    def test_perfect_predictions(self):
        m=metrics.classification([({'a':1.,'b':0.},'a'),({'a':0.,'b':1.},'b')])
        self.assertEqual(m['accuracy'],1)
        self.assertEqual(m['brier'],0)
        self.assertEqual(m['ece_10'],0)
    def test_brier_definition(self):
        m=metrics.classification([({'a':.75,'b':.25},'a')])
        self.assertAlmostEqual(m['brier'],.125)
    def test_empty_is_not_zero_error(self):
        m=metrics.classification([])
        self.assertIsNone(m['accuracy'])
    def test_zero_coverage_risk_is_null(self):
        m=metrics.classification([({'a':.6,'b':.4},'a')])
        self.assertIsNone(m['risk_coverage'][-1]['error_rate'])
    def test_unknown_gold_rejected(self):
        with self.assertRaises(ValueError): metrics.classification([({'a':1},'b')])

class NetworkTests(unittest.TestCase):
    def test_live_disabled_by_default(self):
        from unittest.mock import patch
        with patch.dict('os.environ',{},clear=True):
            with self.assertRaises(PermissionError): provider.live({'state':'test','questions':{},'model':'jev-1.13.0'})
    def test_budget_attempts_reserved_atomically(self):
        b=provider.CallBudget(2)
        b.reserve(); b.reserve()
        with self.assertRaises(RuntimeError): b.reserve()
        self.assertEqual(b.used,2)

if __name__ == '__main__': unittest.main()
