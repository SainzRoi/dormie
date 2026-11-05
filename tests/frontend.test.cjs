const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const tick=()=>new Promise(resolve=>setTimeout(resolve,30));
const resident={resident_id:1,name:'Alex <script>',username:'alex'};
const chore={chore_id:1,name:'Bathroom <img src=x>',description:'Shared bathroom',frequency:'weekly',due_weekday:4,is_active:true,mean:4.5,count:4,my_rating:5};
const assignment={assignment_id:1,chore_id:1,chore:chore.name,resident_id:1,original:resident.name,responsible_id:1,responsible:resident.name,due_date:'2026-11-12',workload_points:4.5,status:'pending',rationale:'Score 4.50; available Thursday',eligible_substitutes:[{resident_id:2,name:'Bea'}]};
const stats={resident_id:1,name:resident.name,original:4.5,actual:4.5,completed:0,cumulative:{original:4.5,actual:4.5,completed:0},average:4.5,eligible_weeks:1,four_week_sum:0};
function boot(loggedIn=true){
 const dom=new JSDOM(fs.readFileSync('app/templates/index.html','utf8'),{url:'http://localhost/',runScripts:'outside-only'});
 const calls=[];
 dom.window.fetch=async(path,options={})=>{
  calls.push({path,options});let result;
  if(options.method&&options.method!=='GET') result={message:'Saved',assignments:[assignment],warnings:[]};
  else if(path==='/api/session')result={csrf:'token',resident:loggedIn?resident:null};
  else if(path.startsWith('/api/assignments'))result={assignments:[assignment],warnings:[]};
  else if(path.startsWith('/api/statistics'))result={residents:[stats],average_through:'2026-11-09',chart:[{week:'2026-11-09',residents:[stats]}]};
  else if(path==='/api/chores')result=[chore];
  else if(path==='/api/availability')result={days:[true,false,false,true,false,false,false],configured_days:7};
  else if(path==='/api/delegations')result=[{delegation_id:1,chore:chore.name,original:'Bea',original_id:2,substitute:resident.name,substitute_id:1,due_date:'2026-11-12',reason:'Study group',status:'pending',delegated_at:'2026-11-09T10:00:00'}];
  else throw Error('Unexpected request '+path);
  return {ok:true,json:async()=>result};
 };
 dom.window.eval(fs.readFileSync('app/static/app.js','utf8'));
 return {dom,calls};
}
test('all six authenticated views render and escape resident/chore text',async()=>{
 const {dom}=boot();await tick();
 for(const [page,label] of Object.entries({dashboard:'My chores this week',assignments:'Why this assignment?',chores:'Add a shared chore',availability:'Your recurring week',delegations:'Your requests & history',statistics:'Everyone’s share'})){
  dom.window.location.hash=page;await tick();
  assert.ok(dom.window.document.querySelector('#content').textContent.includes(label),page);
  assert.equal(dom.window.document.querySelectorAll('#content script,#content img').length,0);
 }
 dom.window.close();
});
test('rating submit remains enabled on click and sends own integer rating with CSRF',async()=>{
 const {dom,calls}=boot();await tick();dom.window.location.hash='chores';await tick();
 const form=dom.window.document.querySelector('[data-rate]');
 form.querySelector('select').value='4';
 form.querySelector('button').click();await tick();
 const call=calls.find(c=>c.path==='/api/chores/1/rating');
 assert.ok(call);assert.equal(call.options.method,'PUT');
 assert.deepEqual(JSON.parse(call.options.body),{intensity_rating:4});
 assert.equal(call.options.headers['X-CSRF-Token'],'token');
 dom.window.close();
});
test('availability saves seven recurring days',async()=>{
 const {dom,calls}=boot();await tick();dom.window.location.hash='availability';await tick();
 dom.window.document.querySelector('#availability-form button').click();await tick();
 const call=calls.find(c=>c.path==='/api/availability'&&c.options.method==='PUT');
 assert.deepEqual(JSON.parse(call.options.body),{days:[true,false,false,true,false,false,false]});
 dom.window.close();
});
test('login and registration switch are accessible without authentication',async()=>{
 const {dom}=boot(false);await tick();
 assert.equal(dom.window.document.querySelector('#auth').hidden,false);
 assert.equal(dom.window.document.querySelector('#shell').hidden,true);
 dom.window.document.querySelector('#auth-switch').click();
 assert.equal(dom.window.document.querySelector('#name-label').hidden,false);
 assert.equal(dom.window.document.querySelector('[name=name]').required,true);
 dom.window.close();
});
