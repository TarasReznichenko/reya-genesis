"""Presentation of existing host components. Never an identity/permission issuer."""
import hashlib
import json
import unicodedata
from pathlib import Path
from . import continuity as C, home_computer_service as H
from reya_goal.contracts import digest

# An implementation locator, not a new Person or a claim about the legacy PDF.
HOST_ID = 'backend.durable_goal.DurableGoals'
CATALOG = {HOST_ID: {'technical_name': 'Системный агент REYA',
    'profile': 'Системная инженерия', 'profile_version': '1',
    'legacy_mapping': 'UNRESOLVED', 'aliases': []}}
KEY = 'system_agent_display_names_v1'

def name_value(value):
    if type(value) is not str:
        raise C.CoreError('AGENT_NAME_INVALID', 400)
    value = unicodedata.normalize('NFC', value).strip()
    if len(value) > 64 or any(unicodedata.category(c).startswith('C') for c in value):
        raise C.CoreError('AGENT_NAME_INVALID', 400)
    return value

def _source_pin():
    root = Path(__file__).parent
    names = ('durable_goal.py', 'engineering_task.py', 'system_agent_identity.py')
    return hashlib.sha256(json.dumps({n: hashlib.sha256((root/n).read_bytes()).hexdigest()
        for n in names}, sort_keys=True).encode()).hexdigest()

_LOADED_PIN = _source_pin()

def implementation_pin():
    if _source_pin()!=_LOADED_PIN:
        raise C.CoreError('AGENT_IMPLEMENTATION_CHANGED_RESTART_REQUIRED',409)
    return _LOADED_PIN

def cards(backend, token):
    principal = H.owner(backend, token)
    profile = backend.profile(principal['person'])
    names = profile['prefs'].get(KEY, {})
    pin = implementation_pin()
    with backend.db() as db:
        evidence = []
        for tid, raw in db.execute("SELECT task_id,record FROM home_durable_goals WHERE person=? AND state='COMPLETE'", (principal['person'],)):
            result = json.loads(raw).get('result', {})
            receipt=result.get('receipt_sha256')
            if (result.get('component_id') == HOST_ID and result.get('implementation_pin') == pin
                    and receipt==digest({k:v for k,v in result.items() if k!='receipt_sha256'})):
                evidence.append({'task_id': tid, 'receipt_sha256': result['receipt_sha256'],
                    'environment': result['environment'], 'verified_ms': result['verified_ms'],
                    'model_route':result.get('model_route'), 'assignment':result.get('assignment'),
                    'assignment_history':result.get('assignment_history',[])})
    authority={'state':'UNAVAILABLE','source':'existing HOME grant; name grants nothing'}
    try:
        _,consent,config,_=H.require(backend,token)
        authority.update(state='ACTIVE',roots=sorted(config['roots']),programs=sorted(config['programs']),evidence_id=consent['evidence_id'])
    except C.CoreError as error: authority['reason']=error.code
    return {'scope': 'personal', 'owner': principal['person'], 'agents': [dict(
        agent_id=aid, **meta, display_name=names.get(aid, ''),
        label=(names[aid]+' — ' if names.get(aid) else '')+meta['technical_name'],
        implementation_pin=pin, readiness='VERIFIED_IN_RECORDED_SCOPE' if evidence else 'PROTOTYPE',
        capabilities=[{'id':'python.admission-replay-repair', 'evidence': evidence}],
        authority=authority,
        current_default_route={'route_id': backend.router.default_route, 'provider': backend.router.routes[backend.router.default_route].get('provider')},
    ) for aid, meta in CATALOG.items()]}

def rename(backend, token, body):
    if set(body) != {'agent_id', 'display_name', 'expected_name'} or body['agent_id'] not in CATALOG:
        raise C.CoreError('AGENT_NAME_FIELDS', 400)
    name = name_value(body['display_name'])
    backend.profile(H.owner(backend, token)['person'])  # existing lazy profile creation
    with backend.db() as db:
        db.execute('BEGIN IMMEDIATE')
        principal = H.owner(backend, token, db=db)
        row = db.execute('SELECT prefs_json FROM home_profiles WHERE person_id=?', (principal['person'],)).fetchone()
        prefs = json.loads(row[0]); names = dict(prefs.get(KEY, {}))
        old = names.get(body['agent_id'], '')
        if old != body['expected_name']:
            raise C.CoreError('AGENT_NAME_CHANGED', 409)
        if name: names[body['agent_id']] = name
        else: names.pop(body['agent_id'], None)
        prefs[KEY] = names
        db.execute('UPDATE home_profiles SET prefs_json=?,updated_ms=? WHERE person_id=?',
            (json.dumps(prefs, ensure_ascii=False), C.now_ms(), principal['person']))
        # Do not put personal aliases in the global audit payload.
        db.execute('INSERT INTO home_audit(person_id,action,target,detail_json,created_ms) VALUES(?,?,?,?,?)',
            (principal['person'], 'AGENT_DISPLAY_UPDATED', body['agent_id'], '{"scope":"personal","authority_changed":false}', C.now_ms()))
    return cards(backend, token)
