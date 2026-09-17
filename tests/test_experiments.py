import unittest
try:
    from jev_lab import experiments, engine, provider
except ImportError:
    experiments=None
class ExperimentsExist(unittest.TestCase):
    def test_experiment_implemented(self):self.assertIsNotNone(experiments)
@unittest.skipIf(experiments is None,'experiment pending')
class ExperimentTests(unittest.TestCase):
    def test_request_shapes(self):
        request=engine.request_for(engine.case_by_id('S02'))
        def fake(payload):
            r=provider.replay('S02');r['answers']={k:r['answers'][k] for k in payload['questions']}
            r['usage']={'input_tokens':100,'output_tokens':5}
            return r,{'usage':r['usage'],'estimated_cost_usd':.0000042}
        result=experiments.compare_shapes(request,fake)
        self.assertEqual({r['shape']:r['requests'] for r in result},{'one_batch':1,'serial_questions':6,'parallel_requests':6})
        self.assertTrue(all(r['all_successful'] for r in result))
    def test_failed_calls_counted(self):
        def fail(payload):raise RuntimeError('controlled failure')
        result=experiments.compare_shapes(engine.request_for(engine.case_by_id('S02')),fail)
        self.assertTrue(all(r['failed']==r['requests'] for r in result))
