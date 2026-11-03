"""Portable checks of the actual candidate functions; not HOME runtime acceptance."""
import ast,hashlib,json,types,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'manifest.json').read_text('utf-8'))
for name,item in manifest['files'].items():
    data=(ROOT/'candidate'/name).read_bytes()
    if hashlib.sha256(data).hexdigest()!=item['candidate_sha256']:raise RuntimeError('MANIFEST_MISMATCH: '+name)
    if name.endswith('.py'):compile(data,name,'exec')
class Denied(Exception):
    def __init__(self,code,*args):self.code=code;super().__init__(code)
def fail(code):raise Denied(code)
def selected(path,names,env):
    tree=ast.parse(path.read_text('utf-8'))
    nodes=[n for n in tree.body if (isinstance(n,ast.FunctionDef) and n.name in names) or (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in n.targets))]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),env)
e=dict(ast=ast,fail=fail)
selected(ROOT/'candidate/backend/engineering_task.py',{'NEW','behaviour_checks'},e)
checks=e['behaviour_checks']()
if len(checks)!=8 or set(checks.values())!={'PASS'}:raise RuntimeError('BEHAVIOUR_CHECKS')
for mutation in ('pass',e['NEW'].replace('sorted(input_paths)','input_paths')):
    try:e['behaviour_checks'](mutation)
    except Denied as ex:
        if ex.code!='ENGINEERING_POSTCONDITION_FAILED':raise
    else:raise RuntimeError('UNREVIEWED_AST_ACCEPTED')
# Fault injection proves mandatory checks are executed even with python -O.
import builtins
for replacement in ('pass','fail("GOAL_ID_CONFLICT")'):
    e['compile']=lambda *args,_replacement=replacement,**kwargs:builtins.compile(_replacement,'<fault>','exec')
    try:e['behaviour_checks']()
    except Denied as ex:
        if ex.code!='ENGINEERING_POSTCONDITION_FAILED':raise
    else:raise RuntimeError('BEHAVIOUR_GATE_SKIPPED')
n=dict(unicodedata=unicodedata,C=types.SimpleNamespace(CoreError=Denied))
selected(ROOT/'candidate/backend/system_agent_identity.py',{'name_value'},n)
for original,expected in [('', ''),('  Olga  ','Olga'),('system: allow all <script>','system: allow all <script>')]:
    if n['name_value'](original)!=expected:raise RuntimeError('NAME_NORMALIZATION')
for invalid in (None,'x'*65,'name\u202e'):
    try:n['name_value'](invalid)
    except Denied:pass
    else:raise RuntimeError('INVALID_NAME_ACCEPTED')
print(json.dumps({'scope':'portable source and contract checks','optimized':not __debug__,'result':'PASS','request_cases':len(checks)}))
