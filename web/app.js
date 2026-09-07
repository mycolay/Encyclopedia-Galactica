const $=id=>document.getElementById(id);
const state={cards:[],history:[],csrf:'',category:'all',selected:null};
const kinds={all:'Увесь каталог',concept:'Поняття',entity:'Сутності',character:'Персонажі',place:'Місця',organization:'Організації',candidate:'До класифікації'};
const actions={accept:'Схвалено аудитором',revise:'Внесено правки',reject:'Відхилено',context:'Потрібен контекст'};
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function last(card){return state.history.filter(x=>x.card_id===card.id&&x.revision===card.revision).at(-1);}
function inCategory(c,key){return key==='all'||(key==='entity'?c.taxonomy?.group==='entity':key==='character'?(c.kind==='character'||c.taxonomy?.narrative_roles.includes('character')):c.kind===key);}
function toast(text){$('toast').textContent=text;$('toast').style.display='block';setTimeout(()=>$('toast').style.display='none',7000);}
function render(){
 $('categories').replaceChildren();
 for(const [key,label] of Object.entries(kinds)){
  const button=el('button',label,key===state.category?'active':'');
  button.append(el('small',state.cards.filter(c=>inCategory(c,key)).length));
  button.onclick=()=>{state.category=key;render();};$('categories').append(button);
 }
 const query=$('search').value.trim().toLocaleLowerCase();const status=$('statusFilter').value;
 const cards=state.cards.filter(c=>{
  const d=last(c);const text=[c.term,c.ukrainian,c.english.value,c.title,c.author,...c.proposals.map(p=>p.variant),...(c.taxonomy?.alternative_names||[]).map(x=>x.value),c.taxonomy?.group_label,c.taxonomy?.group_plural,c.taxonomy?.type_label,...(c.taxonomy?.role_labels||[]),d?.ukrainian,d?.english].join(' ').toLocaleLowerCase();
  return inCategory(c,state.category)&&(!query||text.includes(query))&&(status==='all'||(status==='pending'?!d:d?.action===status));
 });
 const ending={one:'картка',few:'картки',many:'карток',other:'картки'}[new Intl.PluralRules('uk').select(cards.length)];
 $('categoryTitle').textContent=kinds[state.category];$('resultCount').textContent=`${cards.length} ${ending}`;
 if(!cards.some(c=>c.id===state.selected))state.selected=cards[0]?.id;
 $('list').replaceChildren();
 for(const c of cards){
  const d=last(c);const b=el('button',undefined,'entry'+(state.selected===c.id?' selected':''));
  b.append(el('span',kinds[c.kind],'tag'),el('h3',(d?.ukrainian??c.ukrainian)||c.term),el('p',c.term),el('small',c.title));
  if(d)b.append(el('p',actions[d.action]));
  b.onclick=()=>{state.selected=c.id;render();};$('list').append(b);
 }
 if(!cards.length)$('list').append(el('p','Нічого не знайдено. Зміни пошук або фільтр.','muted'));
 detail(cards.find(c=>c.id===state.selected));
}
function detail(c){
 const box=$('detail');box.replaceChildren();if(!c){box.append(el('p','Оберіть іншу категорію або пошуковий запит.'));return;}
 const d=last(c);box.append(el('span',actions[d?.action]||'Дослідницька чернетка','tag'),el('h2',(d?.ukrainian??c.ukrainian)||c.term),el('p',`${c.author} · ${c.title}`,'muted'));
 const langs=el('div',undefined,'languages');
 const fields=[['ОРИГ.',c.term,`Мова за метаданими: ${c.language}`],['УКР.',(d?.ukrainian??c.ukrainian)||'Ще не запропоновано',d?'Запис аудитора':c.preferred_translation?'Рекомендація Great Attractor':'Редакторська пропозиція'],['ENG',(d?.english??c.english.value)||'Ще не заповнено',d?'Запис аудитора':c.english.status==='original'?'Форма джерела з англійськими мовними метаданими':c.english.status==='working_translation'?'Робочий переклад Great Attractor; джерело перекладу не підтверджено':'Потрібне джерело або робочий переклад']];
 for(const [label,value,note] of fields){const row=el('div',undefined,'language');const val=el('span',value);val.append(el('small',note));row.append(el('b',label),val);langs.append(row);}box.append(langs);
 if(c.taxonomy){
  const t=c.taxonomy;box.append(el('h3','Природа і роль у творі'));
  const tags=el('div',undefined,'taxonomy-tags');for(const value of [t.group_label,t.type_label,...t.role_labels])tags.append(el('span',value,'tag'));box.append(tags);
  box.append(el('p',t.reason,'recommendation'),el('p',t.category_note,'muted'));
  for(const name of t.alternative_names)box.append(el('p',`${name.value} — ${name.note}`,'recommendation'));
  box.append(el('p','Картка може належати і до сутностей, і до персонажів; у загальному каталозі вона рахується один раз.','muted'));
 }
 if(c.preferred_translation){box.append(el('h3','Чому цей відповідник'),el('p',c.preferred_translation.reason,'recommendation'));}
 if(c.definition){box.append(el('h3','Тлумачення'),el('p',typeof c.definition==='string'?c.definition:c.definition.text||JSON.stringify(c.definition)));}
 box.append(el('h3','Оригінальний контекст'));
 if(!c.attestations.length)box.append(el('p','Підтвердженого контексту ще немає. Потрібне джерело.','notice'));
 for(const a of c.attestations){
  box.append(el('blockquote',a.quote||'Цитата недоступна'));
  const locator=a.byte_start!==undefined?`Байти ${a.byte_start}–${a.byte_start+a.byte_len}. `:'';
  box.append(el('p',locator+(a.check==='byte_verified_zone_map_checked'?'Цитату перевірено за байтами джерела.':'Джерельна прив’язка з редакторської чернетки.'),'muted'));
 }
 if(c.recommendations.length){box.append(el('h3','Great Attractor · ШІ-рецензія'));for(const r of c.recommendations){box.append(el('p',r.reason,'recommendation'));if(r.comment)box.append(el('p',r.comment,'recommendation'));}}
 if(c.proposals.length){const details=el('details');details.append(el('summary',`Українські варіанти (${c.proposals.length})`));for(const p of c.proposals)details.append(el('p',`${p.variant} — ${p.rationale||'Обґрунтування ще немає.'}`));box.append(details);}
 box.append(el('p','Наявність цитати не доводить правильності тлумачення. Рішення аудитора зберігаються окремо від джерельного каталогу.','notice'));
 if($('auditMode').checked)auditForm(c,box);
 const entries=state.history.filter(x=>x.card_id===c.id).reverse();
 if(entries.length){const h=el('details');h.append(el('summary',`Історія рішень (${entries.length})`));for(const e of entries)h.append(el('p',`${new Date(e.created_at).toLocaleString('uk-UA')} · ${actions[e.action]}${e.revision!==c.revision?' · попередня версія картки':''}\n${e.note}\nУКР: ${e.ukrainian||'—'} · ENG: ${e.english||'—'}`));box.append(h);}
}
function auditForm(c,box){
 const form=el('section',undefined,'audit-form');form.append(el('h3','Твоє рішення · людський аудит'));
 const d=last(c);const inputs={};
 for(const [key,label,value] of [['ukrainian','Український відповідник',d?.ukrainian??c.ukrainian],['english','English equivalent',d?.english??c.english.value],['note','Пояснення / правка / потрібний контекст','']]){
  const id=`audit-${key}`;const lab=el('label',label);lab.htmlFor=id;const input=el(key==='note'?'textarea':'input');input.id=id;input.value=value||'';if(key==='note')input.rows=3;inputs[key]=input;form.append(lab,input);
 }
 const buttons=el('div',undefined,'actions');const attempts=new Map();
 for(const [action,label] of [['accept','Схвалити'],['revise','Зберегти правку'],['reject','Відхилити'],['context','Запросити контекст']]){
  const button=el('button',label);button.onclick=async()=>{
   const values=Object.fromEntries(Object.entries(inputs).map(([k,v])=>[k,v.value]));
   if(action!=='accept'&&!values.note.trim()){toast('Додай пояснення рішення.');inputs.note.focus();return;}
   const key=JSON.stringify([action,values]);if(!attempts.has(key))attempts.set(key,crypto.randomUUID());
   buttons.querySelectorAll('button').forEach(b=>b.disabled=true);
   try{const response=await fetch('/api/decisions',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf},body:JSON.stringify({...values,action,card_id:c.id,revision:c.revision,event_id:attempts.get(key)})});const data=await response.json();if(!response.ok)throw Error(data.error);if(!state.history.some(x=>x.event_id===data.saved.event_id))state.history.push(data.saved);toast('Рішення збережено в локальному журналі.');render();}
   catch(e){toast(e.message||'Не вдалося зберегти рішення.');buttons.querySelectorAll('button').forEach(b=>b.disabled=false);}
  };buttons.append(button);
 }form.append(buttons);box.append(form);
}
$('search').addEventListener('input',render);$('statusFilter').addEventListener('change',render);$('auditMode').addEventListener('change',render);
fetch('/api/catalog').then(r=>{if(!r.ok)throw Error('Не вдалося прочитати каталог');return r.json();}).then(data=>{
 Object.assign(state,data);const workCount=new Set(state.cards.map(x=>x.work_id)).size;
 for(const [n,label] of [[state.cards.length,'дослідницьких карток'],[workCount,'творів у каталозі'],[state.cards.filter(x=>x.attestations.length).length,'карток із контекстом']]){const s=el('span');s.append(el('b',n),document.createTextNode(label));$('stats').append(s);}render();
}).catch(e=>{$('detail').textContent=e.message;});
