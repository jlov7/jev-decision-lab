import json
import threading
import unittest
import urllib.request
import urllib.error
try:
    from jev_lab import server
except ImportError:
    server=None

class ServerExists(unittest.TestCase):
    def test_server_implemented(self):self.assertIsNotNone(server)

@unittest.skipIf(server is None,'server pending')
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
    def token(self):return self.get('/api/config')['session_token']
    def test_token_required(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.post('/api/run',{'case_id':'S01'})
        self.assertEqual(e.exception.code,403)
    def test_cross_origin_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.post('/api/run',{'case_id':'S01'},self.token(),'https://evil.example')
        self.assertEqual(e.exception.code,403)
    def test_replay_reconsider(self):
        t=self.token();r=self.post('/api/run',{'case_id':'S02'},t)
        s=self.post('/api/reconsider',{'receipt_id':r['receipt_id'],'threshold':.99,'variant':'stale'},t)
        self.assertEqual(s['decision']['route'],'REFRESH_EVIDENCE');self.assertEqual(s['additional_model_calls'],0)
    def test_fabricated_receipt_not_accepted(self):
        with self.assertRaises(urllib.error.HTTPError):self.post('/api/reconsider',{'receipt_id':'fake','threshold':.8},self.token())
    def test_config_no_key(self):self.assertNotIn('TYPESAFE_API_KEY',json.dumps(self.get('/api/config')))
    def test_no_path_traversal(self):
        with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(self.base+'/../data/labels.json')
    def test_synthetic_eval(self):
        r=self.post('/api/evaluate',{},self.token())
        self.assertEqual(r['overall']['n'],12);self.assertEqual(r['provenance'],'synthetic_replay')
    def test_action_preview_hold(self):
        t=self.token();r=self.post('/api/run',{'case_id':'S02'},t)
        p=self.post('/api/action-preview',{'receipt_id':r['receipt_id'],'current':{}},t)
        self.assertEqual(p['result'],'HOLD');self.assertEqual(p['external_actions'],0)
    def test_garden(self):
        r=self.post('/api/garden',{'task':'calculate','allow_cloud':False,'consequence_high':True},self.token())
        self.assertEqual(r['lane'],'deterministic')
    def test_arbitrary_state_cannot_be_sent(self):
        with self.assertRaises(urllib.error.HTTPError):self.post('/api/run',{'case_id':'S02','state':'client confidential'},self.token())
