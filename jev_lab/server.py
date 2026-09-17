"""Local teaching server, not an internet-facing production service."""
from __future__ import annotations
import json
import secrets
import threading
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from . import engine, metrics, provider

TOKEN=secrets.token_urlsafe(32)
RECEIPTS: OrderedDict[str,dict] = OrderedDict()
LOCK=threading.Lock()
STATIC={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}

def store(receipt: dict) -> dict:
    key=secrets.token_urlsafe(16)
    with LOCK:
        RECEIPTS[key]=receipt
        while len(RECEIPTS)>200: RECEIPTS.popitem(last=False)
    return dict(receipt,receipt_id=key)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Do not persist request content or credentials.
    def origin_allowed(self) -> bool:
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        if self.headers.get('Host') not in allowed: return False
        origin=self.headers.get('Origin')
        return origin is None or origin in {'http://'+h for h in allowed}
    def send(self,status: int,value,kind='application/json; charset=utf-8'):
        body=json.dumps(value,allow_nan=False).encode() if kind.startswith('application/json') else value
        self.send_response(status)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if not self.origin_allowed(): return self.send(403,{'error':'Local same-origin access only'})
        path=urlparse(self.path).path
        if path=='/api/config':
            return self.send(200,{'session_token':TOKEN,'live_enabled':provider.live_enabled(),'live_attempts':provider.BUDGET.used,
                                  'live_attempt_limit':provider.BUDGET.limit,'model':engine.request_for(engine.cases()[0])['model'],
                                  'price_per_million_input':provider.PRICE_PER_MILLION_INPUT,'price_as_of':'2026-09-17'})
        if path=='/api/cases': return self.send(200,{'cases':engine.cases(),'packs':engine.load('packs')})
        if path in STATIC:
            filename,kind=STATIC[path]
            return self.send(200,(engine.ROOT/'web'/filename).read_bytes(),kind)
        self.send(404,{'error':'Not found'})
    def do_POST(self):
        if not self.origin_allowed() or not secrets.compare_digest(self.headers.get('X-Lab-Token',''),TOKEN):
            return self.send(403,{'error':'A same-origin lab session token is required'})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            return self.send(415,{'error':'Use application/json'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=16384: return self.send(413,{'error':'Invalid or oversized request body'})
            self.connection.settimeout(10)
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict): raise ValueError('Expected a JSON object')
            path=urlparse(self.path).path
            if path=='/api/run':
                result=engine.run(body.get('case_id'),body.get('mode','replay'),body.get('threshold',.85),body.get('consent',False))
                return self.send(200,store(result))
            if path=='/api/reconsider':
                key=body.get('receipt_id')
                if not isinstance(key,str): raise ValueError('Missing receipt ID')
                with LOCK: original=RECEIPTS.get(key)
                if original is None: raise ValueError('Receipt expired or unknown. Run the case again.')
                result=engine.reconsider(original,body.get('threshold',.85),body.get('variant','original'))
                return self.send(200,store(result))
            if path=='/api/evaluate':
                # UI batch is always offline. Live evaluation is an explicit CLI action.
                return self.send(200,metrics.evaluate([engine.run(c['id']) for c in engine.cases()],engine.load('labels')))
            return self.send(404,{'error':'Not found'})
        except PermissionError as exc: self.send(403,{'error':str(exc)})
        except (ValueError,TypeError,KeyError) as exc: self.send(400,{'error':str(exc) if isinstance(exc,ValueError) else 'Invalid request or provider contract'})
        except RuntimeError as exc: self.send(502,{'error':str(exc)})
        except Exception: self.send(500,{'error':'Unexpected local error. Inspect the terminal or run the test suite; no fallback was used.'})

def make_server(port: int=8765) -> ThreadingHTTPServer:
    return ThreadingHTTPServer(('127.0.0.1',port),Handler)

def serve(port: int=8765) -> None:
    http=make_server(port)
    print(f'Jev Decision Lab: http://127.0.0.1:{http.server_port}',flush=True)
    print('Synthetic replay is the default. No live API call occurs until explicitly requested.',flush=True)
    try: http.serve_forever()
    except KeyboardInterrupt: pass
    finally: http.server_close()
