"""Hash-bound isolated checks. No provider/UI/clipboard/network invocation."""
from pathlib import Path
import hashlib,json,subprocess,sys,datetime
R=Path(__file__).resolve().parent;O=R/'receipts';O.mkdir(exist_ok=True)
files=('bridge.py','cua_port.mjs','test_bridge.py','test_cua_port.mjs','run_checks.py')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();before={n:sha(R/n) for n in files}
flags=0x08000000 if sys.platform=='win32' else 0
r=subprocess.run([sys.executable,'-X','utf8','-B','-m','unittest','-v','test_bridge'],cwd=R,capture_output=True,text=True,encoding='utf-8',timeout=30,creationflags=flags)
j=subprocess.run(['node','--test','test_cua_port.mjs'],cwd=R,capture_output=True,text=True,encoding='utf-8',timeout=15,creationflags=flags)
if before!={n:sha(R/n) for n in files}:raise SystemExit('SOURCE_BYTES_CHANGED_DURING_TEST')
name='TEST-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S')
out=dict(schema='reya.gui-source-slice-tests/1',status='PASS_SYNTHETIC_PORTS' if r.returncode==j.returncode==0 else 'FAILED',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source=before,exit_code=r.returncode or j.returncode,stdout=r.stdout,stderr=r.stderr,JS=dict(exit_code=j.returncode,stdout=j.stdout,stderr=j.stderr),real_local_files_and_lock=True,GUI='SYNTHETIC',clipboard='SYNTHETIC',Person_N1_STOP='SYNTHETIC_AUTHORITY',real_model_send='NOT_RUN',A1_replayed=False,HOME_Core='NOT_OPENED_OR_WRITTEN')
with (O/(name+'.json')).open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
print(json.dumps(dict(receipt=str(O/(name+'.json')),status=out['status'],source=before,exit_code=out['exit_code'])));raise SystemExit(out['exit_code'])
