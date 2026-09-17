import copy
import io
import json
import unittest
import urllib.error
from unittest.mock import patch, MagicMock
from jev_lab import engine, provider, metrics

class AdversarialTests(unittest.TestCase):
    def test_critical_consequence_precedes_evidence_repair(self):
        c=engine.case_by_id('S01');r=provider.replay('S01')
        self.assertGreater(r['answers']['contradiction']['noul'],.5)
        self.assertGreater(r['answers']['severity']['probabilities']['3'],.3)
        self.assertEqual(engine.decide(c,r)['route'],'HUMAN_REVIEW')
    def test_inconsistent_heads_require_person(self):
        c=engine.case_by_id('T03');r=provider.replay('T03')
        a=r['answers']['next_evidence'];a['choice']='none'
        a['probabilities']={k:float(k=='none') for k in a['probabilities']}
        self.assertEqual(engine.decide(c,r)['route'],'HUMAN_REVIEW')
    def test_replay_never_opens_network(self):
        with patch('urllib.request.build_opener') as opener:
            engine.run('S01');opener.assert_not_called()
    def test_reconsider_never_opens_network(self):
        r=engine.run('S02')
        with patch('jev_lab.provider.live') as live:
            engine.reconsider(r,.98,'stale');live.assert_not_called()
    def test_missing_score_probabilities_rejected(self):
        r=provider.replay('S01');r['answers']['severity'].pop('probabilities')
        with self.assertRaises(ValueError):engine.validate(engine.request_for(engine.case_by_id('S01')),r)
    def test_gold_labels_cannot_change_inference_payload(self):
        c=engine.case_by_id('S01');before=engine.request_for(c)
        c['expected_owner']='other';c['teaching_note']='answer leakage'
        self.assertEqual(engine.request_for(c),before)
    def test_duplicate_eval_cases_rejected(self):
        r=engine.run('S01')
        with self.assertRaises(ValueError):metrics.evaluate([r,r],engine.load('labels'))
    def test_mixed_provenance_eval_rejected(self):
        a=engine.run('S01');b=engine.run('S02');b['provenance']['kind']='live_typesafe'
        with self.assertRaises(ValueError):metrics.evaluate([a,b],engine.load('labels'))
    def test_choice_option_injection_rejected(self):
        r=provider.replay('S01');r['answers']['owner']['choice']='delete-all-records'
        with self.assertRaises(ValueError):engine.validate(engine.request_for(engine.case_by_id('S01')),r)
    def test_receipt_hash_covers_policy(self):
        r=engine.run('S02');h=r.pop('receipt_hash');self.assertEqual(engine.digest(r),h)
        r['decision']['route']='HUMAN_REVIEW';self.assertNotEqual(engine.digest(r),h)
    def test_confident_wrong_fixture_is_visible(self):
        r=engine.run('S04');a=r['response']['answers']['owner']
        self.assertGreater(a['probabilities'][a['choice']],.95)
        self.assertNotEqual(a['choice'],engine.load('labels')['S04']['expected_owner'])

class TransportContractTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict('os.environ',{'JEV_ALLOW_LIVE':'1','TYPESAFE_API_KEY':'unit-test-only-not-a-real-key'})
        self.env.start();self.addCleanup(self.env.stop)
        self.b=patch.object(provider,'BUDGET',provider.CallBudget(20));self.b.start();self.addCleanup(self.b.stop)
        self.payload=engine.request_for(engine.case_by_id('S01'))
    def test_native_transport_headers_endpoint_and_usage(self):
        reply=provider.replay('S01');reply['model']='jev-1.13.0';reply['usage']={'input_tokens':2000,'output_tokens':100}
        connection=MagicMock();connection.__enter__.return_value.read.return_value=json.dumps(reply).encode()
        opener=MagicMock();opener.open.return_value=connection
        with patch('urllib.request.build_opener',return_value=opener):
            result,provenance=provider.live(self.payload)
        request=opener.open.call_args.args[0]
        self.assertEqual(request.full_url,provider.ENDPOINT)
        self.assertEqual(json.loads(request.data),self.payload)
        self.assertEqual(request.get_header('Authorization'),'Bearer unit-test-only-not-a-real-key')
        self.assertEqual(provenance['kind'],'live_typesafe')
        self.assertAlmostEqual(provenance['estimated_cost_usd'],.000084)
        self.assertEqual(provider.BUDGET.used,1)
    def test_401_redacted_and_not_retried(self):
        opener=MagicMock();opener.open.side_effect=urllib.error.HTTPError(provider.ENDPOINT,401,'unauthorized',{},io.BytesIO(b'unit-test-only-not-a-real-key'))
        with patch('urllib.request.build_opener',return_value=opener):
            with self.assertRaises(RuntimeError) as e:provider.live(self.payload)
        self.assertIn('401',str(e.exception));self.assertNotIn('unit-test-only',str(e.exception));self.assertEqual(opener.open.call_count,1)
    def test_timeout_never_replayed(self):
        opener=MagicMock();opener.open.side_effect=TimeoutError()
        with patch('urllib.request.build_opener',return_value=opener),patch.object(provider,'replay') as fallback:
            with self.assertRaises(RuntimeError):provider.live(self.payload)
            fallback.assert_not_called()
    def test_oversize_not_sent_or_counted(self):
        self.payload['state']='x'*provider.MAX_INPUT_BYTES
        with patch('urllib.request.build_opener') as opener:
            with self.assertRaises(ValueError):provider.live(self.payload)
            opener.assert_not_called()
        self.assertEqual(provider.BUDGET.used,0)
    def test_redirects_not_followed(self):
        self.assertIsNone(provider.NoRedirect().redirect_request(None,None,302,'',{},'https://example.com'))

if __name__=='__main__':unittest.main()
