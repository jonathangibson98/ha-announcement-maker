#!/usr/bin/env python3
"""Tiny backend: serves the UI, exposes add-on options, pushes scripts to HA."""
import json, os, re, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import yaml

OPTS = json.load(open('/data/options.json')) if os.path.exists('/data/options.json') else {}
TOKEN = (OPTS.get('ha_token') or '').strip()
if TOKEN:   # user supplied a long-lived token: talk to HA directly
    BASE = (OPTS.get('ha_url') or 'http://homeassistant:8123').rstrip('/')
else:       # default: use the Supervisor proxy, no token needed
    TOKEN, BASE = os.environ.get('SUPERVISOR_TOKEN', ''), 'http://supervisor/core'
WWW = Path(__file__).parent / 'www'
INGRESS_IP = '172.30.32.2'   # only the HA ingress gateway may talk to us
ID_RE = re.compile(r'^[a-z0-9_]{1,60}$')


def ha(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 502, str(e)


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype='application/json'):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def allowed(self):
        return os.environ.get('DEV') or self.client_address[0] == INGRESS_IP

    def do_GET(self):
        if not self.allowed():
            return self.send(403, {'error': 'ingress only'})
        path = self.path.split('?')[0]
        if path in ('/', '/index.html'):
            return self.send(200, (WWW / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        if path == '/api/options':
            o = {k: v for k, v in OPTS.items() if k not in ('ha_token', 'ha_url')}
            return self.send(200, o)
        self.send(404, {'error': 'not found'})

    def do_POST(self):
        if not self.allowed():
            return self.send(403, {'error': 'ingress only'})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        except ValueError:
            return self.send(400, {'error': 'bad json'})
        sid = str(body.get('id', ''))
        if not ID_RE.match(sid):
            return self.send(400, {'error': 'script id must be lowercase letters, numbers, underscores'})
        path = self.path.split('?')[0]
        if path == '/api/push':
            try:
                cfg = yaml.safe_load(body.get('yaml', ''))
            except yaml.YAMLError as e:
                return self.send(400, {'error': 'YAML problem: %s' % e})
            code, text = ha('POST', '/api/config/script/config/' + sid, cfg)
            if code != 200:
                return self.send(200, {'ok': False, 'detail': 'HA said %s: %s' % (code, text[:300])})
            ha('POST', '/api/services/script/reload', {})
            return self.send(200, {'ok': True, 'entity': 'script.' + sid})
        if path == '/api/run':
            code, text = ha('POST', '/api/services/script/turn_on', {'entity_id': 'script.' + sid})
            return self.send(200, {'ok': code == 200, 'detail': text[:300]})
        self.send(404, {'error': 'not found'})

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    print('Listening on :8099 (base %s)' % BASE, flush=True)
    ThreadingHTTPServer(('0.0.0.0', 8099), Handler).serve_forever()
