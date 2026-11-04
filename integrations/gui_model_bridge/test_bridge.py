"""Real isolated files/state/locks; SYNTHETIC UI, owner, N1 and clipboard ports."""
from dataclasses import replace
from pathlib import Path
import hashlib,json,tempfile,unittest,uuid,threading,subprocess,sys,sqlite3
from contextlib import contextmanager
from bridge import *

PIN=AppPin('fixture.package','1.0','fixture.publisher','a'*64,'fixture.exe','b'*64,123,'fixture-start',1,9,(0,0,1000,700),96,'c'*64)
class FixtureAuthority:
 def __init__(self):self.stop=False;self.revoked=False;self.terms=True;self.checks=[];self.fence=threading.Lock()
 @contextmanager
 def protect(self,r,phase):
  with self.fence:self.check(r,phase);yield
 def check(self,r,phase):
  self.checks.append(phase);need(not self.stop,'OWNER_STOP');need(not self.revoked,'OWNER_REVOKED')
  need(r.person=='fixture-owner' and r.thread=='fixture-private','N1_PERSON_SCOPE_DENIED')
 def provider_terms_allowed(self):return self.terms
class FixtureClip:
 def __init__(self):self.text='SYNTHETIC_USER_CLIPBOARD_724';self.seq=10;self.restore_calls=0;self.snapshot_calls=0;self.busy=0;self.restore_busy=0;self.race=False;self.unsupported=False
 def snapshot_private(self):
  self.snapshot_calls+=1
  if self.busy:self.busy-=1;raise ClipboardBusy()
  need(not self.unsupported,'CLIPBOARD_FORMATS_UNSUPPORTED');return self.text
 def read(self):return Capture(self.text,self.seq)
 def preflight(self):retry_clipboard(self.snapshot_private)
 def copy_verified(self,copy_ui,visible_sha256,max_bytes):
  # SYNTHETIC custodian: a real implementation needs native write ownership,
  # all-format preservation and crash-surviving custody. Not provided here.
  try:before=retry_clipboard(self.snapshot_private)
  except Blocked as e:raise ClipboardSafeFailure(e.code,'NO_WRITE') from None
  try:copy_ui()
  except InputNotAdmitted as e:raise ClipboardSafeFailure(e.code,'NO_WRITE') from None
  capture=self.read()
  need(digest(capture.text.encode())==visible_sha256,'CLIPBOARD_VISIBLE_MISMATCH')
  try:restored=retry_clipboard(lambda:self.restore_verified(before,capture.sequence))
  except Blocked:restored=False
  need(restored,'CLIPBOARD_RESTORE_UNVERIFIED');return capture
 def restore_verified(self,snapshot,expected_sequence):
  self.restore_calls+=1
  if self.restore_busy:self.restore_busy-=1;raise ClipboardBusy()
  if self.race:self.text='SYNTHETIC_NEW_USER_COPY';self.seq+=1
  if expected_sequence!=self.seq:return False
  self.text=snapshot;self.seq+=1;return self.text==snapshot
class FixtureGUI:
 def __init__(self,r,a,c):
  self.r=r;self.a=a;self.c=c;self.sends=0;self.copies=0;self.alerts=[];self.chat='fixture-new-chat'
  self.o=Observation(PIN,True,True,True,True,r.model,self.chat,False)
  self.closed=False;self.file_accepted=True;self.tamper=False;self.unknown_send=False;self.timeout=False
  self.stop_after=False;self.revoke_after=False;self.bad_clip=False;self.bad_answer=False;self.changed_chat=False;self.revoke_before_commit=False
 def bind_request(self,r):self.r=r;return self
 def observe(self):
  need(not self.closed,'APP_CLOSED')
  if self.revoke_before_commit and self.copies:self.a.revoked=True
  return self.o
 @contextmanager
 def input(self,phase):
  with self.a.protect(self.r,phase):
   need(not self.cancelled(self.r.request_id,self.r.operation_id),'REQUEST_CANCELLED');yield
 def new_chat(self):
  with self.input('NEW_CHAT_INPUT'):self.o=replace(self.o,empty_chat=True)
 def attach(self,p,h):
  with self.input('ATTACH_INPUT'):
   if self.tamper:p.write_bytes(b'SYNTHETIC_TAMPER')
  return Attachment(self.chat,p.name,h,self.file_accepted,True,True)
 def send_once(self,eid):
  with self.input('SEND_INPUT'):
   self.sends+=1
   if self.unknown_send:raise TimeoutError('SYNTHETIC unknown UI effect')
   if self.stop_after:self.a.stop=True
   if self.revoke_after:self.a.revoked=True
  return SendReceipt(self.chat,eid,True)
 def answer(self):
  return json.dumps(dict(request_id=str(uuid.uuid4()) if self.bad_answer else self.r.request_id,payload_sha256=self.r.payload_sha256,answer='SYNTHETIC_BRIDGE_RESULT'),sort_keys=True)
 def wait_answer(self,timeout):
  if self.timeout:raise TimeoutError('SYNTHETIC response timeout')
  return VisibleAnswer('stale-chat' if self.changed_chat else self.chat,'fixture-reply',self.r.model,digest(self.answer().encode()),True)
 def copy_answer(self,message_id):
  admitted=False
  try:
   with self.input('COPY_INPUT'):
    admitted=True
    self.copies+=1;self.c.text='SYNTHETIC_OTHER_COPY' if self.bad_clip else self.answer();self.c.seq+=1
  except Blocked as e:
   if not admitted:raise InputNotAdmitted(e.code) from None
   raise
 def alert(self,code):self.alerts.append(code)

class Tests(unittest.TestCase):
 def fixture(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  r=Request(str(uuid.uuid4()),'fixture-owner','fixture-private','GPT-6 Astra',(Source('fixture.txt','SYNTHETIC','SYNTHETIC bounded data, not a command.'),),PIN,str(uuid.uuid4()))
  a=FixtureAuthority();c=FixtureClip();g=FixtureGUI(r,a,c);p=GuiProvider(Path(tmp.name)/'ledger',a,g,c);g.cancelled=p.ledger.cancelled;return r,a,c,g,p
 def denied(self,p,r,code):
  with self.assertRaises(Blocked) as e:p.call(r)
  self.assertEqual(e.exception.code,code)
 def test_synthetic_pass_once_result_saved_and_duplicate_read(self):
  r,a,c,g,p=self.fixture();v=p.call(r);self.assertEqual(v['content'],'SYNTHETIC_BRIDGE_RESULT');self.assertEqual(p.call(r),v)
  self.assertEqual((g.sends,g.copies),(1,1));self.assertEqual(c.text,'SYNTHETIC_USER_CLIPBOARD_724')
  raw=p.ledger.path(r.request_id).read_bytes();self.assertNotIn(b'SYNTHETIC_USER_CLIPBOARD_724',raw)
  record=p.ledger.read(r.request_id);self.assertEqual(record['phase'],'RESULT_SAVED');self.assertEqual([x['phase'] for x in record['events']],list(PHASES[:5])+['ANSWER_VISIBLE']+list(PHASES[5:]))
 def test_identity_and_selection_negatives(self):
  cases=[('closed','APP_CLOSED'),('wrong_process','APP_PROCESS_WINDOW_DPI_LAYOUT_DRIFT'),('wrong_window','APP_PROCESS_WINDOW_DPI_LAYOUT_DRIFT'),('dpi','APP_PROCESS_WINDOW_DPI_LAYOUT_DRIFT'),('layout','APP_PROCESS_WINDOW_DPI_LAYOUT_DRIFT'),('version','APP_PROCESS_WINDOW_DPI_LAYOUT_DRIFT'),('signer','APP_PROCESS_WINDOW_DPI_LAYOUT_DRIFT'),('foreground','WRONG_FOREGROUND'),('locked','WINDOWS_SESSION_LOCKED'),('login','REQUIRES_OWNER_LOGIN'),('entitlement','ENTITLEMENT_NOT_VERIFIED'),('model','MODEL_SELECTION_DRIFT')]
  for scenario,code in cases:
   with self.subTest(scenario=scenario):
    r,a,c,g,p=self.fixture()
    if scenario=='closed':g.closed=True
    elif scenario in ('wrong_process','wrong_window','dpi','layout','version','signer'):
     fields={'wrong_process':{'pid':999},'wrong_window':{'window_id':8},'dpi':{'dpi':144},'layout':{'layout_sha256':'d'*64},'version':{'version':'2'},'signer':{'signature_sha256':'0'*64}}[scenario];g.o=replace(g.o,pin=replace(PIN,**fields))
    else:g.o=replace(g.o,**{'foreground':{'foreground':False},'locked':{'unlocked':False},'login':{'logged_in':False},'entitlement':{'entitled':False},'model':{'model':'GPT-6.1 Sol'}}[scenario])
    self.denied(p,r,code);self.assertEqual(g.sends,0)
 def test_attachment_not_accepted(self):
  r,a,c,g,p=self.fixture();g.file_accepted=False;self.denied(p,r,'ATTACHMENT_NOT_VERIFIED');self.assertEqual(g.sends,0)
 def test_file_hash_mismatch(self):
  r,a,c,g,p=self.fixture();g.tamper=True;self.denied(p,r,'FILE_SHA_MISMATCH');self.assertEqual(g.sends,0)
 def test_stop_before_send(self):
  r,a,c,g,p=self.fixture();a.stop=True;self.denied(p,r,'OWNER_STOP');self.assertEqual(g.sends,0)
 def test_stop_and_revoke_after_send_have_no_further_gui_actions(self):
  for flag,code in [('stop_after','OWNER_STOP'),('revoke_after','OWNER_REVOKED')]:
   with self.subTest(flag=flag):
    r,a,c,g,p=self.fixture();setattr(g,flag,True);self.denied(p,r,code);self.assertEqual((g.sends,g.copies),(1,0));self.assertEqual(p.ledger.read(r.request_id)['phase'],'UNKNOWN')
 def test_owner_permission_revoked_before_dispatch(self):
  r,a,c,g,p=self.fixture();a.revoked=True;self.denied(p,r,'OWNER_REVOKED');self.assertEqual(g.sends,0)
 def test_response_timeout_and_unknown_send_never_retry_even_new_id(self):
  for flag in ('timeout','unknown_send'):
   with self.subTest(flag=flag):
    r,a,c,g,p=self.fixture();setattr(g,flag,True)
    with self.assertRaises(TimeoutError):p.call(r)
    self.denied(p,r,'PRIOR_EFFECT_RECONCILIATION_REQUIRED');self.denied(p,replace(r,request_id=str(uuid.uuid4())),'PRIOR_OPERATION_RECONCILIATION_REQUIRED');self.assertEqual(g.sends,1)
 def test_clipboard_busy_blocks_before_send_and_retry_is_bounded(self):
  r,a,c,g,p=self.fixture();c.busy=20;self.denied(p,r,'CLIPBOARD_BUSY_LIMIT');self.assertEqual((c.snapshot_calls,g.sends),(3,0))
 def test_clipboard_contention_then_recovery(self):
  r,a,c,g,p=self.fixture();c.busy=2;c.restore_busy=2;self.assertEqual(p.call(r)['content'],'SYNTHETIC_BRIDGE_RESULT');self.assertEqual((c.snapshot_calls,c.restore_calls),(4,3))
 def test_clipboard_unsupported_formats_block_before_send(self):
  r,a,c,g,p=self.fixture();c.unsupported=True;self.denied(p,r,'CLIPBOARD_FORMATS_UNSUPPORTED');self.assertEqual(g.sends,0)
 def test_clipboard_restore_busy_alerts_and_result_not_valid(self):
  r,a,c,g,p=self.fixture();c.restore_busy=20;self.denied(p,r,'CLIPBOARD_RESTORE_UNVERIFIED');self.assertEqual(c.restore_calls,3);self.assertEqual(g.alerts,['CLIPBOARD_RESTORE_UNVERIFIED']);self.assertNotIn('result',p.ledger.read(r.request_id))
 def test_clipboard_concurrent_change_not_overwritten(self):
  r,a,c,g,p=self.fixture();c.race=True;self.denied(p,r,'CLIPBOARD_RESTORE_UNVERIFIED');self.assertEqual(c.text,'SYNTHETIC_NEW_USER_COPY');self.assertTrue(g.alerts)
 def test_clipboard_mismatch_not_success(self):
  r,a,c,g,p=self.fixture();g.bad_clip=True;self.denied(p,r,'CLIPBOARD_VISIBLE_MISMATCH');self.assertTrue(g.alerts);self.assertNotIn('result',p.ledger.read(r.request_id))
 def test_stale_chat_reply_denied_before_copy(self):
  r,a,c,g,p=self.fixture();g.changed_chat=True;self.denied(p,r,'ANSWER_STALE_OR_INCOMPLETE');self.assertEqual(g.copies,0)
 def test_concurrent_writer(self):
  r,a,c,g,p=self.fixture()
  with p.ledger.lock():self.denied(p,r,'CONCURRENT_OR_STALE_WRITER_RECONCILE')
  self.assertEqual(g.sends,0)
 def test_request_id_payload_immutable(self):
  r,a,c,g,p=self.fixture();p.call(r);self.denied(p,replace(r,sources=(Source('fixture.txt','SYNTHETIC','SYNTHETIC new payload'),)),'REQUEST_ID_PAYLOAD_CONFLICT');self.assertEqual(g.sends,1)
 def test_private_context_never_staged(self):
  r,a,c,g,p=self.fixture();self.denied(p,replace(r,sources=(Source('private.txt','PRIVATE','SYNTHETIC_PRIVATE_CANARY'),)),'PRIVATE_CONTEXT_EXPORT_DENIED');self.assertEqual(list(p.ledger.root.glob('*.txt')),[])
 def test_unknown_terms_deny_before_model_effect(self):
  r,a,c,g,p=self.fixture();a.terms=False;self.denied(p,r,'PROVIDER_AUTOMATION_TERMS_NOT_VERIFIED');self.assertEqual(g.sends,0)
 def test_missing_real_host_authority_denies(self):
  r,a,c,g,p=self.fixture();p.authority=DenyUnboundAuthority();self.denied(p,r,'HOST_N1_CP_AUTHORITY_NOT_BOUND');self.assertEqual(g.sends,0)
 def test_cancel_before_send(self):
  r,a,c,g,p=self.fixture();attach=g.attach
  def cancelled(path,sha):
   result=attach(path,sha);p.request_cancel(r);return result
  g.attach=cancelled;self.denied(p,r,'REQUEST_CANCELLED');self.assertEqual(g.sends,0)
 def test_stop_at_last_dispatch_boundary(self):
  r,a,c,g,p=self.fixture();check=a.check
  def stop(req,phase):
   if phase=='DISPATCH_BOUNDARY':a.stop=True
   return check(req,phase)
  a.check=stop;self.denied(p,r,'OWNER_STOP');self.assertEqual(g.sends,0);self.assertEqual(p.ledger.read(r.request_id)['phase'],'UNKNOWN')
 def test_file_changed_at_last_readback(self):
  r,a,c,g,p=self.fixture();check=a.check
  def tamper(req,phase):
   if phase=='BEFORE_SEND':next(p.ledger.root.glob('*.txt')).write_text('SYNTHETIC_TAMPER')
   return check(req,phase)
  a.check=tamper;self.denied(p,r,'FILE_SHA_MISMATCH');self.assertEqual(g.sends,0)
 def test_latest_clipboard_during_model_wait_is_preserved(self):
  r,a,c,g,p=self.fixture();wait=g.wait_answer
  def user_copy(t):c.text='SYNTHETIC_LATEST_USER_CLIPBOARD';c.seq+=1;return wait(t)
  g.wait_answer=user_copy;p.call(r);self.assertEqual(c.text,'SYNTHETIC_LATEST_USER_CLIPBOARD')
 def test_unknown_commit_failure_prevents_send(self):
  r,a,c,g,p=self.fixture();save=p.ledger.save
  def fail(rec):
   if rec['phase']=='UNKNOWN':raise sqlite3.OperationalError('SYNTHETIC_DISK_FAULT')
   return save(rec)
  p.ledger.save=fail
  with self.assertRaises(sqlite3.OperationalError):p.call(r)
  self.assertEqual(g.sends,0)
 def test_sqlite_unknown_survives_process_exit_and_never_replays(self):
  r,a,c,g,p=self.fixture()
  record=dict(request_id=r.request_id,fingerprint=r.fingerprint,operation_id=r.operation_id,operation_fingerprint=r.operation_fingerprint,phase='UNKNOWN',events=[],effect_id=str(uuid.uuid4()))
  code='from bridge import Ledger;import json,sys,os;l=Ledger(sys.argv[1]);l.save(json.loads(sys.argv[2]));os._exit(17)'
  child=subprocess.run([sys.executable,'-B','-c',code,str(p.ledger.root),json.dumps(record)],cwd=Path(__file__).parent,timeout=5,capture_output=True)
  self.assertEqual(child.returncode,17);self.assertEqual(p.ledger.read(r.request_id)['phase'],'UNKNOWN');self.denied(p,r,'PRIOR_EFFECT_RECONCILIATION_REQUIRED');self.assertEqual(g.sends,0)
 def test_second_distinct_request_uses_new_lifecycle(self):
  r,a,c,g,p=self.fixture();p.call(r);second=replace(r,request_id=str(uuid.uuid4()),operation_id=str(uuid.uuid4()));self.assertEqual(p.call(second)['request_id'],second.request_id);self.assertEqual(g.sends,2)
 def test_final_commit_readback_failure_new_request_recovers_without_send(self):
  r,a,c,g,p=self.fixture();read=p.ledger.read;failed=False
  def transient(rid):
   nonlocal failed
   rec=read(rid)
   if rec and rec['phase']=='RESULT_SAVED' and not failed:
    failed=True;raise sqlite3.OperationalError('SYNTHETIC_READBACK_FAULT')
   return rec
  p.ledger.read=transient
  with self.assertRaises(sqlite3.OperationalError):p.call(r)
  second=replace(r,request_id=str(uuid.uuid4()));result=p.call(second)
  self.assertEqual((g.sends,g.copies),(1,1));self.assertEqual(result['request_id'],r.request_id)
  self.assertEqual(result['recovered_for_request_id'],second.request_id)
 def test_same_operation_changed_payload_rejected(self):
  r,a,c,g,p=self.fixture();p.call(r)
  second=replace(r,request_id=str(uuid.uuid4()),sources=(Source('new.txt','SYNTHETIC','SYNTHETIC new data'),))
  self.denied(p,second,'OPERATION_PAYLOAD_CONFLICT');self.assertEqual(g.sends,1)
 def test_compound_attach_stop_between_inputs_with_nonreentrant_fence(self):
  r,a,c,g,p=self.fixture();inputs=[]
  def compound(path,sha):
   with g.input('PLUS'):inputs.append('PLUS')
   a.stop=True
   with g.input('OPEN_FILE'):inputs.append('OPEN_FILE')
  g.attach=compound;self.denied(p,r,'OWNER_STOP');self.assertEqual(inputs,['PLUS']);self.assertEqual(g.sends,0)
 def test_no_gui_observation_while_python_holds_host_fence(self):
  r,a,c,g,p=self.fixture();observe=g.observe
  def no_nested_observation():
   acquired=a.fence.acquire(blocking=False)
   self.assertTrue(acquired,'GUI observation must be outside Python host fence')
   if acquired:a.fence.release()
   return observe()
  g.observe=no_nested_observation;p.call(r);self.assertEqual(g.sends,1)
 def test_ledger_identity_mutation_denied_by_api_and_sql(self):
  r,a,c,g,p=self.fixture();p.call(r);record=p.ledger.read(r.request_id);record['operation_id']=str(uuid.uuid4())
  with self.assertRaises(Blocked) as e:p.ledger.save(record)
  self.assertEqual(e.exception.code,'LEDGER_IDENTITY_IMMUTABLE')
  with p.ledger.connection() as d:
   with self.assertRaises(sqlite3.IntegrityError):d.execute('UPDATE effects SET operation_id=? WHERE request_id=?',(str(uuid.uuid4()),r.request_id))
  self.assertEqual(p.ledger.read(r.request_id)['operation_id'],r.operation_id)
 def test_each_supported_model_label_in_synthetic_contract_only(self):
  for model in MODELS:
   with self.subTest(model=model):
    r,a,c,g,p=self.fixture();r=replace(r,model=model);g.o=replace(g.o,model=model)
    self.assertEqual(p.call(r)['model'],model);self.assertEqual(g.sends,1)
 def test_failed_final_save_does_not_retry_result_after_revoke_or_cancel(self):
  for control in ('revoke','cancel'):
   with self.subTest(control=control):
    r,a,c,g,p=self.fixture();save=p.ledger.save;annotate=p.ledger.annotate_error;failed=False;intervened=False
    def fail_before_commit(rec):
     nonlocal failed
     if rec['phase']=='RESULT_SAVED' and not failed:
      failed=True;raise sqlite3.OperationalError('SYNTHETIC_PRE_COMMIT_FAILURE')
     return save(rec)
    def control_between_fence_and_annotation(rid,code,clipboard_alert=None):
     nonlocal intervened
     if not intervened:
      intervened=True
      if control=='revoke':a.revoked=True
      else:p.request_cancel(r)
     return annotate(rid,code,clipboard_alert)
    p.ledger.save=fail_before_commit;p.ledger.annotate_error=control_between_fence_and_annotation
    with self.assertRaises(sqlite3.OperationalError):p.call(r)
    persisted=p.ledger.read(r.request_id)
    self.assertTrue(intervened);self.assertEqual(persisted['phase'],'ANSWER_COPIED_VERIFIED')
    self.assertNotIn('result',persisted);self.assertEqual(g.sends,1)
 def test_cancelled_saved_operation_blocks_original_and_retry_alias(self):
  for cancel_alias in (False,True):
   with self.subTest(cancel_alias=cancel_alias):
    r,a,c,g,p=self.fixture();p.call(r);alias=replace(r,request_id=str(uuid.uuid4()))
    p.request_cancel(alias if cancel_alias else r)
    self.denied(p,r,'REQUEST_CANCELLED');self.denied(p,alias,'REQUEST_CANCELLED')
    self.assertEqual((g.sends,g.copies),(1,1))
 def test_copy_guard_control_failure_never_emits_clipboard_restore_warning(self):
  for control in ('stop','revoke','cancel'):
   with self.subTest(control=control):
    r,a,c,g,p=self.fixture();check=a.check
    def intervene(req,phase):
     if phase=='COPY':
      if control=='stop':a.stop=True
      elif control=='revoke':a.revoked=True
      else:p.ledger.cancel(r)
     return check(req,phase)
    a.check=intervene
    self.denied(p,r,dict(stop='OWNER_STOP',revoke='OWNER_REVOKED',cancel='REQUEST_CANCELLED')[control])
    self.assertEqual(g.copies,0);self.assertEqual(g.alerts,[])
    rec=p.ledger.read(r.request_id);self.assertIsNone(rec['clipboard_alert']);self.assertNotIn('clipboard_dirty_possible',rec)
 def test_unbound_authority_denies_saved_result_read(self):
  r,a,c,g,p=self.fixture();p.call(r);p.authority=DenyUnboundAuthority()
  self.denied(p,r,'HOST_N1_CP_AUTHORITY_NOT_BOUND');self.assertEqual(g.sends,1)
 def test_mutable_request_containers_rejected_before_staging(self):
  r,a,c,g,p=self.fixture();self.denied(p,replace(r,sources=list(r.sources)),'REQUEST_CONTAINER_INVALID')
  self.denied(p,replace(r,pin=replace(PIN,bounds=list(PIN.bounds))),'APP_PIN_INVALID')
  self.assertEqual(g.sends,0);self.assertEqual(list(p.ledger.root.glob('*.txt')),[])
 def test_pre_call_cancel_survives_retry_uuid_and_changed_limits_or_payload(self):
  r,a,c,g,p=self.fixture();p.request_cancel(r)
  for changes in ({'max_output_bytes':1024},{'sources':(Source('other.txt','SYNTHETIC','SYNTHETIC changed'),)}):
   self.denied(p,replace(r,request_id=str(uuid.uuid4()),**changes),'REQUEST_CANCELLED')
  self.assertEqual(g.sends,0);self.assertEqual(list(p.ledger.root.glob('*.txt')),[])
 def test_cancel_request_id_cannot_be_rebound_before_first_call(self):
  r,a,c,g,p=self.fixture();p.request_cancel(r)
  with self.assertRaises(Blocked) as e:p.request_cancel(replace(r,operation_id=str(uuid.uuid4())))
  self.assertEqual(e.exception.code,'REQUEST_ID_OPERATION_CONFLICT')
  self.assertTrue(p.ledger.cancelled(str(uuid.uuid4()),r.operation_id))
 def test_legacy_ledger_requires_explicit_reconciliation_without_mutation(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'GUI_EFFECTS.sqlite3'
   with closing(sqlite3.connect(path)) as d:
    with d:
     d.execute('CREATE TABLE cancellations(request_id TEXT PRIMARY KEY,operation_fingerprint TEXT)')
     d.execute('CREATE TABLE effects(phase TEXT)');d.execute("INSERT INTO effects VALUES('UNKNOWN')")
   before=path.read_bytes()
   with self.assertRaises(Blocked) as e:Ledger(folder)
   self.assertEqual(e.exception.code,'LEDGER_SCHEMA_UPGRADE_REQUIRED');self.assertEqual(path.read_bytes(),before)
 def test_copy_input_control_rejection_proves_no_clipboard_write(self):
  for control in ('stop','revoke','cancel'):
   with self.subTest(control=control):
    r,a,c,g,p=self.fixture();check=a.check
    def intervene(req,phase):
     if phase=='COPY_INPUT':
      if control=='stop':a.stop=True
      elif control=='revoke':a.revoked=True
      else:p.ledger.cancel(r)
     return check(req,phase)
    a.check=intervene
    self.denied(p,r,dict(stop='OWNER_STOP',revoke='OWNER_REVOKED',cancel='REQUEST_CANCELLED')[control])
    self.assertEqual(g.copies,0);self.assertEqual(g.alerts,[]);self.assertEqual(c.text,'SYNTHETIC_USER_CLIPBOARD_724')
    rec=p.ledger.read(r.request_id);self.assertFalse(rec['clipboard_dirty_possible']);self.assertEqual(rec['clipboard_disposition'],'NO_WRITE')
    self.assertNotIn('result',rec)
 def test_verified_restored_custodian_failure_has_no_false_dirty_warning(self):
  r,a,c,g,p=self.fixture();copy=c.copy_verified
  def restored_failure(*args):
   copy(*args);raise ClipboardSafeFailure('SYNTHETIC_CAPTURE_REJECTED','RESTORED')
  c.copy_verified=restored_failure;self.denied(p,r,'SYNTHETIC_CAPTURE_REJECTED')
  rec=p.ledger.read(r.request_id);self.assertFalse(rec['clipboard_dirty_possible']);self.assertEqual(rec['clipboard_disposition'],'RESTORED')
  self.assertEqual(g.alerts,[]);self.assertEqual(c.text,'SYNTHETIC_USER_CLIPBOARD_724');self.assertNotIn('result',rec)

if __name__=='__main__':unittest.main(verbosity=2)
