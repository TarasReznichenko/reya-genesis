'use strict';
const labels={READY:'Ожидает запуска',RUNNING:'Выполняется',COMPLETE:'Результат проверен',BLOCKED:'Нужна проверка',STOPPED:'Остановлена',REVOKED:'Разрешение отозвано',PENDING:'Ожидает отправки',SENT:'Доставлено',DELIVERY_UNKNOWN:'Отправка не подтверждена. Автоповтор отключён.',HELD:'Доставка приостановлена',FAILED:'Ошибка доставки'};
async function api(path,body){const r=await fetch('/api/genesis'+path,{method:body?'POST':'GET',credentials:'same-origin',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});const j=await r.json();if(!r.ok)throw new Error(j.error||'Запрос не выполнен');return j;}
const node=(tag,text)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
let viewRevision=0;
function renderAgents(value){
 const area=document.querySelector('#agents');area.replaceChildren();
 for(const agent of value.agents){
  const a=node('article'),heading=node('h3',agent.label),label=node('label','Личное имя (видно в вашем профиле)'),input=node('input');
  input.maxLength=64;input.value=agent.display_name;input.placeholder=agent.technical_name;input.setAttribute('aria-label','Личное имя системного агента');label.append(node('br'),input);
  const save=node('button','Сохранить имя'),reset=node('button','Сбросить имя'),message=node('p');message.setAttribute('role','status');
  const mutate=async name=>{save.disabled=reset.disabled=true;try{const v=await api('/agents/name',{agent_id:agent.agent_id,display_name:name,expected_name:agent.display_name});renderAgents(v);}catch(e){message.textContent=e.message;save.disabled=reset.disabled=false;}};
  save.onclick=()=>mutate(input.value);reset.onclick=()=>mutate('');
  a.append(heading,node('p',agent.profile),label,node('br'),save,reset,message);
  a.append(node('p',agent.readiness==='PROTOTYPE'?'Прототип: подтверждённой проверки этой версии пока нет.':'Есть проверенный результат в указанной ниже области.'));
  for(const cap of agent.capabilities){
   a.append(node('p','Навык: проверка исправления повторного запроса задачи'));
   for(const ev of cap.evidence){
    a.append(node('small',(ev.environment==='isolated'?'Изолированная проверка':'Проверка в HOME')+' · '+new Date(ev.verified_ms).toLocaleString()+' · задача '+ev.task_id));
    a.append(node('p','Исполнитель принятого предложения: '+(ev.assignment?.executor||'не указан')+'. Модельные циклы: '+(ev.model_route?.route_id||'не указаны')));
   }
  }
  a.append(node('p',agent.authority.state==='ACTIVE'?'Текущий допуск действует для: '+agent.authority.roots.join(', '):'Сейчас нет действующего допуска к выполнению. Имя можно изменить независимо.'));
  const details=node('details');details.append(node('summary','Версия, ресурс и происхождение'),node('pre',JSON.stringify({agent_id:agent.agent_id,profile_version:agent.profile_version,implementation:agent.implementation_pin,current_default_route:agent.current_default_route,legacy_mapping:agent.legacy_mapping},null,2)));a.append(details);area.append(a);
 }
}
async function show(){
 const revision=++viewRevision;
 try{
  const [v,agents]=await Promise.all([api('/status'),api('/agents')]);if(revision!==viewRevision)return;
  document.querySelector('#notice').textContent='';renderAgents(agents);
  const area=document.querySelector('#tasks');area.replaceChildren();
  for(const t of v.tasks){
   const a=node('article');a.append(node('h2',t.goal),node('p',(labels[t.state]||t.state)+' · циклов: '+t.cycles+' · действий: '+t.actions),node('small',t.task_id));
   if(t.result){
    if(t.result.schema==='reya.engineering-result/1'){
     a.append(node('p','Исправление проверено в области: '+t.result.profile+'. Артефакты: '+Object.keys(t.result.artifacts).join(', ')+'. Выпуск отдельно.'));
     const d=node('details');d.append(node('summary','Проверенный diff'),node('pre',t.result.patch));a.append(d);
    }else if(Array.isArray(t.result.input_facts))a.append(node('p','Проверено файлов: '+t.result.input_facts.length+'. Сумма: '+t.result.total+'. Артефакты: report.md, manifest.json.'));
   }
   if(t.reason)a.append(node('pre',t.reason));
   if(['READY','RUNNING'].includes(t.state)){const b=node('button','Остановить');b.onclick=async()=>{try{await api('/stop',{task_id:t.task_id});await show();}catch(e){document.querySelector('#notice').textContent=e.message;}};a.append(node('br'),b);}
   area.append(a);
  }
  const delivery=document.querySelector('#delivery');delivery.replaceChildren();for(const x of v.delivery)delivery.append(node('p',x.task_id+': '+(labels[x.state]||x.state)));
 }catch(e){if(revision===viewRevision)document.querySelector('#notice').textContent=e.message;}
}
document.querySelector('#refresh').onclick=show;show();
