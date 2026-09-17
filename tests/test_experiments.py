import unittest
from jev_lab import experiments, engine, provider

class ExperimentTests(unittest.TestCase):
    def test_three_call_shapes_without_network(self):
        request=engine.request_for(engine.case_by_id('S02'))
        def fake(payload):
            response=provider.replay('S02')
            response['answers']={k:response['answers'][k] for k in payload['questions']}
            response['usage']={'input_tokens':100,'output_tokens':5}
            return response,{'latency_ms':1.,'usage':response['usage'],'estimated_cost_usd':.0000042,'model_calls':1}
        r=experiments.compare_shapes(request,fake)
        self.assertEqual({x['shape']:x['requests'] for x in r},{'one_batch':1,'serial_questions':6,'parallel_requests':6})
        self.assertTrue(all(x['succeeded']==x['requests'] for x in r))
    def test_failures_are_counted(self):
        request=engine.request_for(engine.case_by_id('S02'))
        def failed(payload):raise RuntimeError('controlled failure')
        r=experiments.compare_shapes(request,failed)
        self.assertTrue(all(x['failed']==x['requests'] for x in r))
        self.assertTrue(all(x['all_successful'] is False for x in r))
    def test_input_payload_not_mutated(self):
        request=engine.request_for(engine.case_by_id('S02'));before=engine.digest(request)
        def failed(payload):raise RuntimeError('controlled failure')
        experiments.compare_shapes(request,failed)
        self.assertEqual(engine.digest(request),before)
