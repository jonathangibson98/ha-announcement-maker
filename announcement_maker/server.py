#!/usr/bin/env python3
"""Tiny backend: serves the UI, exposes add-on options, pushes scripts to HA."""
import json, os, re, threading, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import yaml

OPTS_FILE = os.environ.get('OPTIONS_FILE', '/data/options.json')
OPTS = json.load(open(OPTS_FILE)) if os.path.exists(OPTS_FILE) else {}
TOKEN = (OPTS.get('ha_token') or '').strip()
if TOKEN:   # user supplied a long-lived token: talk to HA directly
    BASE = (OPTS.get('ha_url') or 'http://homeassistant:8123').rstrip('/')
else:       # default: use the Supervisor proxy, no token needed
    TOKEN, BASE = os.environ.get('SUPERVISOR_TOKEN', ''), 'http://supervisor/core'
WWW = Path(__file__).parent / 'www'
SETTINGS_FILE = Path(os.environ.get('SETTINGS_FILE', '/data/settings.json'))
DEFAULTS = {
    'ai_task_entity': '', 'helper_ai_task_entity': '', 'tts_entity': '', 'speaker': '', 'alexa_targets': [], 'notify_targets': [],
    'music_players': [], 'talking_flag': '', 'personality_select': '', 'household_context': '',
    'combined_info_entity': '', 'combined_info_attribute': '', 'locations_entity': '',
    'weather_entity': '', 'inside_temp_entity': '', 'news_entity': '', 'calendar_entities': [],
    'todo_entity': '', 'trash_entity': '', 'custom_sources': [], 'sources': None, 'default_volume': 70, 'default_length': 1000,
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
    if OPTS.get('helper_ai_task_entity'):   # set in the add-on Configuration tab
        s['helper_ai_task_entity'] = OPTS['helper_ai_task_entity']
    return s

INGRESS_IP = '172.30.32.2'   # only the HA ingress gateway may talk to us
ID_RE = re.compile(r'^[a-z0-9_]{1,60}$')
ENT_RE = re.compile(r'^[a-z_]+\.[a-z0-9_]+$')


TEST = {'status': 'idle'}
TEST_ID = 'announcement_maker_test'


def run_test(cfg, mode):
    """Run the script once under a temporary id, return what the AI saw/said, then delete it."""
    global TEST
    try:
        seq = (cfg or {}).get('sequence') or []
        keys, last = [], -1
        for i, st in enumerate(seq):
            if isinstance(st, dict) and isinstance(st.get('variables'), dict):
                ks = [k for k in st['variables'] if k.startswith('src_')]
                if ks:
                    keys, last = ks, i
        if not keys:
            TEST = {'status': 'error', 'error': 'Tick at least one data source first.'}
            return
        if mode == 'data':
            seq = seq[:last + 1]
        res = {'sources': {k: '{{ %s }}' % k for k in keys}}
        if mode != 'data':
            res.update({'speech': '{{ speech }}', 'raw': '{{ announcement.data }}'})
        cfg['sequence'] = seq + [{'variables': {'test_result': res}},
                                 {'stop': 'Test finished', 'response_variable': 'test_result'}]
        cfg['alias'] = '[TEST] ' + str(cfg.get('alias', 'announcement'))
        code, text = ha('POST', '/api/config/script/config/' + TEST_ID, cfg)
        if code != 200:
            TEST = {'status': 'error', 'error': 'HA refused the test script (%s): %s' % (code, text[:400])}
            return
        ha('POST', '/api/services/script/reload', {})
        time.sleep(1.5)
        code, text = ha('POST', '/api/services/script/%s?return_response' % TEST_ID, {}, timeout=420)
        if code != 200:
            TEST = {'status': 'error', 'error': text[:1500]}
            return
        r = json.loads(text).get('service_response') or {}
        if 'sources' not in r and len(r) == 1 and isinstance(list(r.values())[0], dict):
            r = list(r.values())[0]
        TEST = dict(r, status='done')
    except Exception as e:
        TEST = {'status': 'error', 'error': str(e)}
    finally:
        ha('DELETE', '/api/config/script/config/' + TEST_ID)
        ha('POST', '/api/services/script/reload', {})


def helper_text(body):
    idea, ai = str(body.get('idea', ''))[:1000], body.get('ai', '')
    srcs = [x for x in body.get('sources', []) if isinstance(x, dict) and re.match(r'^\w+$', str(x.get('id', '')))]
    if not (idea and ENT_RE.match(ai) and ai.startswith('ai_task.')):
        return {'ok': False, 'error': 'Describe what you want and set an AI Task entity.'}
    prompt = ('You help write voice announcement scripts for Home Assistant. Later, an AI will receive live data plus the '
              'instructions you write, and will write a spoken announcement.\nData sources available (id: label): %s\n'
              'Notes: calendar events are grouped under each calendar entity id (calendars: %s). Weather has current conditions '
              'plus a daily forecast for up to 7 days.\nUser\'s idea: %s\n'
              'Reply with ONLY JSON, no code fences: {"name": "short script name", "sources": ["ids of sources needed"], '
              '"task": "clear instructions for the announcement writer, 1-5 sentences, including any conditions"}'
              % ('; '.join('%s: %s' % (x['id'], x.get('label', '')) for x in srcs), ', '.join(body.get('calendars', [])) or 'none', idea))
    code, text = ha('POST', '/api/services/ai_task/generate_data?return_response',
                    {'entity_id': ai, 'task_name': 'Instruction helper', 'instructions': prompt}, timeout=90)
    if code != 200:
        return {'ok': False, 'error': 'AI Task failed (%s): %s' % (code, text[:200])}
    try:
        data = json.loads(text)['service_response']['data']
        j = data if isinstance(data, dict) else json.loads(re.search(r'\{.*\}', data, re.S).group(0))
    except Exception:
        return {'ok': False, 'error': 'The AI answer was not usable JSON. Try rewording.'}
    ids = {x['id'] for x in srcs}
    return {'ok': True, 'name': str(j.get('name') or '')[:60], 'task': str(j.get('task') or '')[:1500],
            'sources': [i for i in (j.get('sources') or []) if i in ids]}


def helper(body):
    ent, goal, ai = body.get('entity', ''), str(body.get('goal', ''))[:500], body.get('ai', '')
    if not (ENT_RE.match(ent) and ENT_RE.match(ai) and ai.startswith('ai_task.') and goal):
        return {'ok': False, 'error': 'Pick an entity, say what you want, and set an AI Task entity.'}
    code, text = ha('GET', '/api/states/' + ent)
    if code != 200:
        return {'ok': False, 'error': 'Could not read %s (HA said %s).' % (ent, code)}
    st = json.loads(text)
    attrs = st.get('attributes', {})
    prompt = ('You are helping set up a Home Assistant voice announcement. The user wants to pull info from one entity into it.\n'
              'Entity: %s\nState: %s\nAttributes (JSON, may be cut off): %s\nThe user wants: %s\n'
              'If one attribute holds what they want, give its exact name. If they need several or it is unclear, '
              'use an empty string, which includes the state and all attributes.\n'
              'Reply with ONLY JSON, no code fences: {"label": "short name under 30 chars", '
              '"attribute": "exact attribute name or empty string", "note": "one sentence on what this will read"}'
              % (ent, st.get('state'), json.dumps(attrs)[:3000], goal))
    code, text = ha('POST', '/api/services/ai_task/generate_data?return_response',
                    {'entity_id': ai, 'task_name': 'Source helper', 'instructions': prompt}, timeout=90)
    if code != 200:
        return {'ok': False, 'error': 'AI Task failed (%s): %s' % (code, text[:200])}
    try:
        data = json.loads(text)['service_response']['data']
        j = data if isinstance(data, dict) else json.loads(re.search(r'\{.*\}', data, re.S).group(0))
    except Exception:
        return {'ok': False, 'error': 'The AI answer was not usable JSON. Try rewording what you want.'}
    attr = j.get('attribute') or ''
    if attr not in attrs or not re.match(r'^[\w .\-]+$', attr):
        attr = ''
    tmpl = ("{{ state_attr('%s', '%s') }}" % (ent, attr)) if attr else (
        "{{ states('%s') }} {{ states.%s.attributes | default('', true) }}" % (ent, ent))
    code, prev = ha('POST', '/api/template', {'template': tmpl})
    return {'ok': True, 'label': str(j.get('label') or ent)[:40], 'attribute': attr,
            'note': str(j.get('note') or '')[:200], 'preview': prev[:300] if code == 200 else '(could not render preview)'}



def ha(method, path, body=None, timeout=20):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={
        'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
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
        if path == '/api/test':
            return self.send(200, TEST)
        if path == '/api/options':
            return self.send(200, load_settings())
        if path == '/api/entities':
            code, text = ha('GET', '/api/states')
            try:
                ents = [{'id': e['entity_id'], 'name': e.get('attributes', {}).get('friendly_name') or e['entity_id']}
                        for e in json.loads(text)] if code == 200 else []
            except ValueError:
                ents = []
            code, text = ha('GET', '/api/services')   # notify.mobile_app_* are services, not entities
            try:
                for d in (json.loads(text) if code == 200 else []):
                    if d.get('domain') == 'notify':
                        ents += [{'id': 'notify.' + n, 'name': n.replace('_', ' ') + ' (service)', 'svc': True}
                                 for n in d.get('services', {}) if n not in ('send_message', 'persistent_notification')]
            except ValueError:
                pass
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
            clean = {k: v for k, v in body.items() if k in DEFAULTS and k != 'helper_ai_task_entity'}
            SETTINGS_FILE.write_text(json.dumps(clean))
            return self.send(200, load_settings())
        if self.path.split('?')[0] == '/api/test':
            global TEST
            if TEST.get('status') == 'running':
                return self.send(200, {'ok': False, 'error': 'A test is already running.'})
            try:
                cfg = yaml.safe_load(body.get('yaml', ''))
            except yaml.YAMLError as e:
                return self.send(400, {'error': 'YAML problem: %s' % e})
            mode = body.get('mode') if body.get('mode') in ('data', 'text', 'full') else 'text'
            TEST = {'status': 'running', 'mode': mode}
            threading.Thread(target=run_test, args=(cfg, mode), daemon=True).start()
            return self.send(200, {'ok': True})
        if self.path.split('?')[0] == '/api/helper':
            return self.send(200, helper_text(body) if body.get('mode') == 'instructions' else helper(body))
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
