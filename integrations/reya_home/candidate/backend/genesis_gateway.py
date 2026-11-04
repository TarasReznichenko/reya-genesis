"""Feature-gated HOME routes; uses existing authenticated session and Core."""
from .durable_goal import DurableGoals,fail
from .telegram_channel import Channels
from . import home_computer_service as H
import json,re
from pathlib import Path

def load_runtime_config(backend):
    """Trusted host configuration, pinned to this release; never HTTP/model input.

    The standard launcher deliberately clears inherited REYA_* variables.
    Activation therefore uses an explicit local configuration, just as the
    existing computer adapter does. It creates no Person, rule or grant.
    """
    path=backend.home_data/'genesis-config.json'
    if not path.exists():return None
    if path.is_symlink() or not path.is_file():fail('GENESIS_CONFIG_PATH_INVALID')
    raw=path.read_bytes()
    if len(raw)>16384:fail('GENESIS_CONFIG_LIMIT')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:fail('GENESIS_CONFIG_DUPLICATE_KEY')
            result[key]=value
        return result
    config=json.loads(raw.decode('utf-8-sig'),object_pairs_hook=pairs)
    if type(config)is not dict or set(config)!={'schema','enabled','release_record_sha256','bot_id','bot_username','receiver_enabled','telegram_rule_id'}:fail('GENESIS_CONFIG_FIELDS')
    if config['schema']!='reya.genesis-runtime/1' or type(config['enabled'])is not bool or type(config['receiver_enabled'])is not bool:fail('GENESIS_CONFIG_SCHEMA')
    if not config['enabled']:return None
    if not backend.n1_enabled or not backend._n1_required:fail('GENESIS_N1_REQUIRED')
    from .home_working_profile import CORE
    expected='ISOLATED_ONLY'
    if backend.path.resolve()==CORE.resolve():
        selector=json.loads(H.SELECTOR.read_text('utf-8-sig'))
        if (Path(selector['release_root'])/'stage/wt').resolve()!=Path(__file__).resolve().parents[1]:fail('GENESIS_RUNTIME_SOURCE_CHANGED')
        expected=selector['record_sha256']
    if config['release_record_sha256']!=expected:fail('GENESIS_CONFIG_RELEASE_CHANGED')
    if type(config['bot_id'])is not int or config['bot_id']<=0 or type(config['bot_username'])is not str or not re.fullmatch('[A-Za-z0-9_]{5,32}',config['bot_username']):fail('GENESIS_CONFIG_BOT_INVALID')
    if type(config['telegram_rule_id'])is not str or not config['telegram_rule_id'] or len(config['telegram_rule_id'])>160:fail('GENESIS_CONFIG_RULE_INVALID')
    return {k:config[k] for k in ('bot_id','bot_username','receiver_enabled','telegram_rule_id')}

class LocalPoolOnly:
    """No external CLI/API. Reuses WorkRouter's one pool when none is attached."""
    def run(self,*args,**kwargs):fail('EXTERNAL_WORK_NOT_ADMITTED')

class Genesis:
    def __init__(self,backend,orchestration,work,config):
        if set(config)!={'bot_id','bot_username','receiver_enabled','telegram_rule_id'}:fail('GENESIS_CONFIG_INVALID')
        self.goals=DurableGoals(backend,orchestration,work)
        self.channels=Channels(self.goals,config['bot_id'],config['bot_username'])
        self.receiver=None
        if config['receiver_enabled']:
            from .telegram_transport import Receiver,BotAPI,credential
            c,_,_=H.configuration(backend)
            self.receiver=Receiver(self.channels,BotAPI(lambda:credential(c['device_id'])),config['telegram_rule_id'])
            self.receiver.start()
        self.goals.start()
    def dispatch(self,token,method,path,body):
        b=self.goals.b;p=H.owner(b,token)
        if method=='GET' and path=='/status':
            with b.db() as db:
                ids=[r[0] for r in db.execute('SELECT task_id FROM home_durable_goals WHERE person=?',(p['person'],))]
                tasks=[self.goals.public(self.goals.row(db,tid)) for tid in ids]
                delivery=[dict(key=k,task_id=t,state=s) for k,t,s in db.execute('SELECT delivery_key,task_id,state FROM home_channel_outbox WHERE person=?',(p['person'],))]
            return {'tasks':tasks,'delivery':delivery,'pump_error':self.goals.last_error,
                    'receiver':self.receiver.status() if self.receiver else {'state':'DISABLED','thread_alive':False}}
        if path=='/agents' and method=='GET':
            from .system_agent_identity import cards
            return cards(b,token)
        if path=='/agents/name' and method=='POST':
            from .system_agent_identity import rename
            return rename(b,token,body)
        if method!='POST':fail('GENESIS_ROUTE_NOT_FOUND')
        if path=='/challenge' and set(body)=={'expected_actor'}:return self.channels.challenge(token,body['expected_actor'])
        if path=='/rule' and set(body)=={'rule_id','source','root','inputs','mode'}:return self.channels.install_rule(token,**body)
        if path=='/rule/revoke' and set(body)=={'rule_id'}:return self.channels.revoke_rule(token,body['rule_id']) or {'state':'REVOKED'}
        if path=='/task' and set(body)=={'task_id','goal','root','input_paths'}:return self.goals.admit(token,**body)
        if path=='/engineering-task' and set(body)=={'task_id','goal','root','input_paths','task_type'}:return self.goals.admit(token,**body)
        if path=='/engineering/revise':
            from .engineering_task import revise
            return revise(self.goals,token,body)
        if path=='/stop' and set(body)=={'task_id'}:return self.goals.stop(token,body['task_id'])
        fail('GENESIS_ROUTE_OR_FIELDS_DENIED')
    def close(self):
        if self.receiver:self.receiver.close()
        self.goals.close()
