/* SOURCE_ONLY in-process CUA port, not a daemon or executable UI fallback.
 * observer is trusted reviewed host code; never model-produced coordinates.
 * CUA has no native clipboard custody API: Python clipboard port is separate
 * and MUST NOT be run from this session to bypass a tool permission boundary.
 */
const stable=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.entries(x).sort(([a],[b])=>a.localeCompare(b))):x);
const freeze=v=>{if(v&&typeof v==='object'){Object.values(v).forEach(freeze);Object.freeze(v);}return v;};
export class CuaGuiFactory {
  constructor(app,observer,fence) { this.app=app;this.observer=observer;this.fence=fence; }
  bind_request(r) { return new CuaGuiPort(this.app,this.observer,this.fence,r); }
}
export class CuaGuiPort {
  constructor(app, observer, fence, request) {
    if(!request?.request_id||!request?.pin||!['GPT-6 Astra','GPT-6.1 Terra','GPT-6.1 Sol'].includes(request.model))throw new Error('REQUEST_BINDING_REQUIRED');
    this.app=app;this.observer=observer;this.fence=fence;this.sendUsed=false;this.chat=null;this.attached=false;
    this.binding=freeze(JSON.parse(JSON.stringify(request)));
    this.pinEncoding=stable(this.binding.pin);
  }
  async observe() {
    const ax=await this.app.getAXState({emit:false});
    if (!ax || /Accessibility state unavailable/i.test(ax))
      throw new Error('FLUTTER_AX_UNAVAILABLE_REQUIRES_TRUSTED_GUI_OBSERVER');
    if (!this.observer) throw new Error('GUI_OBSERVER_NOT_ATTESTED');
    // Host observer supplies current package/signer/exe/session/window/layout,
    // foreground/lock/model/chat/entitlement evidence, not a cached screenshot.
    const o=await this.observer.attest(this.app, ax);
    if(!o.logged_in)throw new Error('REQUIRES_OWNER_LOGIN');
    if(!o.entitled)throw new Error('ENTITLEMENT_NOT_VERIFIED');
    if(stable(o.pin)!==this.pinEncoding||o.model!==this.binding.model||!o.foreground||!o.unlocked)
      throw new Error('GUI_REQUEST_PIN_OR_ACCESS_DRIFT');
    if(this.chat!==null&&o.chat_id!==this.chat)throw new Error('GUI_CHAT_CHANGED');
    return o;
  }
  async step(name, value) {
    if(!this.fence?.run)throw new Error('HOST_CP_FENCE_NOT_BOUND');
    // Sole fence for this ONE input; caller never holds an outer fence.
    // run MUST revalidate original host operation/Person/N1/STOP/revoke/cancel.
    return await this.fence.run(this.binding,name,async()=>{
    const before=await this.observe();
    if(name==='copy_reply')await this.observer.verifyReply(before,value);
    const command=await this.observer.control(before,name); // fresh AX index only
    if (command.window_id!==before.pin.window_id || command.observation!==before.observation)
      throw new Error('GUI_OBSERVATION_STALE');
    if (command.kind==='click') await this.app.click(command.element);
    else if (command.kind==='file_path' && name==='file_path' && typeof value==='string')
      await this.app.setValue(command.element,value);
    else throw new Error('GUI_ACTION_UNSUPPORTED');
    return await this.observe(); // one action, then fresh state; no automatic retry
    });
  }
  async new_chat() {
    const o=await this.step('new_chat');
    if(!o.empty_chat||!o.chat_id)throw new Error('NEW_EMPTY_CHAT_NOT_VERIFIED');
    this.chat=o.chat_id;this.attached=false;return o;
  }
  async attach(path,sha256) {
    await this.step('plus');await this.step('add_file');await this.step('file_path',path);
    if(await this.observer.verifyDialogPath(await this.observe(),path)!==true)throw new Error('FILE_DIALOG_PATH_NOT_VERIFIED');
    await this.step('open_file');const a=await this.observer.attachment(await this.observe(),path,sha256);
    if(a.chat_id!==this.chat||a.file_sha256!==sha256||a.filename!==path.split(/[\\/]/).at(-1)||!a.path_readback||!a.single_file||!a.composer_empty)throw new Error('ATTACHMENT_NOT_VERIFIED');
    this.attached=true;return a;
  }
  async send_once(effect_id) {
    if(this.sendUsed) throw new Error('SEND_ALREADY_ATTEMPTED');
    if(this.chat===null||!this.attached)throw new Error('SEND_WITHOUT_VERIFIED_ATTACHMENT');
    this.sendUsed=true; // must be set BEFORE the CUA call, including timeout
    const after=await this.step('send');return await this.observer.sendReceipt(after,effect_id);
  }
  async wait_answer(timeout) { return await this.observer.answer(this.app,timeout); }
  async copy_answer(message_id) {
    return await this.step('copy_reply',message_id);
  }
  async alert(code) { if(!this.observer) throw new Error(code);return await this.observer.alert(code); }
}
