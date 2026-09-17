import json
import threading
import unittest
import urllib.request
import urllib.error
from jev_lab import server

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.http=server.make_server(0)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.http.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join(timeout=2)
    def get(self,path):
        with urllib.request.urlopen(self.base+path) as r:return json.load(r)
    def post(self,path,body,token=None,origin=None):
        headers={'Content-Type':'application/json'}
        if token:headers['X-Lab-Token']=token
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode(),headers=headers)
        with urllib.request.urlopen(req) as r:return json.load(r)
    def test_token_required(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.post('/api/run',{'case_id':'S01'})
        self.assertEqual(e.exception.code,403)
    def test_cross_origin_blocked(self):
        token=self.get('/api/config')['session_token']
        with self.assertRaises(urllib.error.HTTPError) as e:self.post('/api/run',{'case_id':'S01'},token,'https://evil.example')
        self.assertEqual(e.exception.code,403)
    def test_replay_flow_and_receipt_reconsideration(self):
        token=self.get('/api/config')['session_token']
        r=self.post('/api/run',{'case_id':'S02','mode':'replay'},token)
        self.assertEqual(r['provenance']['kind'],'synthetic_replay')
        s=self.post('/api/reconsider',{'receipt_id':r['receipt_id'],'threshold':.99,'variant':'stale'},token)
        self.assertEqual(s['decision']['route'],'REFRESH_EVIDENCE')
        self.assertEqual(s['additional_model_calls'],0)
    def test_arbitrary_receipt_not_accepted(self):
        token=self.get('/api/config')['session_token']
        with self.assertRaises(urllib.error.HTTPError):
            self.post('/api/reconsider',{'receipt_id':'fake','threshold':.8},token)
    def test_no_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(self.base+'/../data/labels.json')
    def test_config_contains_no_key(self):
        self.assertNotIn('TYPESAFE_API_KEY',json.dumps(self.get('/api/config')))
    def test_eval_is_explicitly_synthetic(self):
        token=self.get('/api/config')['session_token']
        report=self.post('/api/evaluate',{},token)
        self.assertEqual(report['provenance'],'synthetic_replay')
        self.assertEqual(report['overall']['n'],12)

if __name__=='__main__':unittest.main()
