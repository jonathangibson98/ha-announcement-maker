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
SETTINGS_FILE = Path(os.environ.get('SETTINGS_FILE', '/data/settings.json'))
DEFAULTS = {
    'ai_task_entity': '', 'tts_entity': '', 'speaker': '', 'alexa_targets': [], 'notify_targets': [],
    'music_players': [], 'talking_flag': '', 'personality_select': '', 'household_context': '',
    'combined_info_entity': '', 'combined_info_attribute': '', 'locations_entity': '',
    'weather_entity': '', 'inside_temp_entity': '', 'news_entity': '', 'calendar_entities': [],
    'todo_entity': '', 'trash_entity': '', 'custom_sources': [], 'default_volume': 70, 'default_length': 1000,
    'hype_style': 'Be funny and hype us up. Boost our confidence. PG-13 language, no insults.',
    'roast_style': 'Roast us super aggressively. Rated-R, heavy profanity, funny not hurtful.',
    'sweet_style': 'Be super sweet and warm to everyone. Playful teasing only, never mean.'}


def load_settings():
    s = dict(DEFAULTS)
    s.update({k: v for k, v in OPTS.items() if k in DEFAULTS})   # settings from older versions
    try:
        s.update({k: v for k, v in json.load(open(SETTINGS_FILE)).items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return s

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
            return self.send(200, load_settings())
        if path == '/api/entities':
            code, text = ha('GET', '/api/states')
            try:
                ents = [{'id': e['entity_id'], 'name': e.get('attributes', {}).get('friendly_name') or e['entity_id']}
                        for e in json.loads(text)] if code == 200 else []
            except ValueError:
                ents = []
            return self.send(200, sorted(ents, key=lambda e: e['id']))
        self.send(404, {'error': 'not found'})

    def do_POST(self):
        if not self.allowed():
            return self.send(403, {'error': 'ingress only'})
        try:
            body = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or '{}')
        except ValueError:
            return self.send(400, {'error': 'bad json'})
        if self.path.split('?')[0] == '/api/settings':
            clean = {k: v for k, v in body.items() if k in DEFAULTS}
            SETTINGS_FILE.write_text(json.dumps(clean))
            return self.send(200, load_settings())
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
