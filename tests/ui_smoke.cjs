// Optional DOM integration QA, not a screenshot/real-microphone browser test.
// Start the server in rules mode, then: npm install && npm run test:ui
const {JSDOM,VirtualConsole}=require('jsdom');
const assert=require('node:assert/strict');
const base=process.argv[2]||'http://127.0.0.1:8000';
const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let n=0;n<150;n++){if(fn())return;await pause(25);}throw Error('Timed out waiting for UI state');}
(async()=>{
 const dom=await JSDOM.fromURL(base,{resources:'usable',runScripts:'dangerously',virtualConsole:vc,beforeParse(w){w.AbortController=global.AbortController;w.fetch=(url,opts)=>fetch(new URL(url,base),opts);w.HTMLElement.prototype.scrollIntoView=function(){};}});
 const w=dom.window,d=w.document,$=id=>d.getElementById(id);
 await until(()=>$('mode').textContent.includes('baseline'));
 async function submit(text){$('message').value=text;$('intake').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await until(()=>$('submit').disabled===false||$('result').classList.contains('emergency'));}
 function answer(text){const b=[...$('answers').querySelectorAll('button')].find(b=>b.textContent===text);assert.ok(b,'Answer button '+text+' exists');b.click();}
 await submit('I have stomach ache');assert.match($('chat').textContent,/How severe is the stomach pain/);
 answer('Mild');await until(()=>$('chat').textContent.includes('Does touching your abdomen'));
 answer('No');await until(()=>$('chat').textContent.includes('How long have you'));
 await submit('two days');assert.match($('chat').textContent,/Where in your abdomen/);
 await submit('lower left');assert.match($('result').textContent,/stomach pain/);
 const book=[...d.querySelectorAll('button')].find(b=>b.textContent==='Simulate booking');assert.ok(book);book.click();assert.match($('booking').textContent,/SIMULATED BOOKING/);
 $('reset').click();await submit('I have severe stomach pain');assert.match($('concern').textContent,/prompt in-person/);
 answer('Yes');await until(()=>$('result').classList.contains('emergency'));
 assert.equal($('result').querySelector('a').getAttribute('href'),'tel:112');assert.equal($('result').querySelectorAll('button').length,0);assert.equal($('submit').disabled,true);
 $('reset').click();
 for(const text of ['कान में दर्द है','mild','loss nhi hai sirf dard hai','No','5 days'])await submit(text);
 assert.match($('result').textContent,/clinician needs to assess/);
 assert.doesNotMatch($('result').textContent,/One useful question/);
 assert.equal($('result').querySelectorAll('button').length,0);
 assert.equal($('chat').querySelectorAll('.assistant').length,4);
 $('reset').click();await submit('I am dizzy');
 for(let n=0;n<4;n++)await submit('not sure');
 assert.match($('result').textContent,/Human assessment needed/);
 assert.equal($('result').querySelectorAll('button').length,0);
 $('reset').click();const normalFetch=w.fetch;
 w.fetch=(url,opts)=>url==='/ui/triage'?Promise.reject(Error('Synthetic network outage')):normalFetch(url,opts);
 await submit('My ear hurts');
 assert.match($('result').textContent,/Assessment not completed/);
 assert.doesNotMatch($('result').textContent,/One useful question/);
 assert.equal($('message').value,'My ear hurts');
 assert.equal($('result').querySelectorAll('button').length,0);
 w.fetch=normalFetch;await submit('My ear hurts');
 assert.match($('result').textContent,/One useful question/);
 $('reset').click();const normalTimer=w.setTimeout;
 w.setTimeout=(fn,ms,...args)=>normalTimer.call(w,fn,ms===45000?5:ms,...args);
 w.fetch=(url,opts)=>url==='/ui/triage'?new Promise((resolve,reject)=>opts.signal.addEventListener('abort',()=>{const e=Error('deadline');e.name='AbortError';reject(e);})):normalFetch(url,opts);
 await submit('My ear hurts');
 assert.match($('status').textContent,/too long/);
 assert.match($('result').textContent,/Assessment not completed/);
 assert.equal($('message').value,'My ear hurts');
 w.fetch=normalFetch;w.setTimeout=normalTimer;
 $('reset').click();await submit('Toilet cleaner splashed into my eye.');
 assert.match($('result').textContent,/Emergency help now/);
 assert.equal($('result').querySelector('a').getAttribute('href'),'tel:112');
 $('reset').click();await submit('It burns when I pass urine.');
 assert.match($('chat').textContent,/completely unable to pass urine/);
 assert.doesNotMatch($('chat').textContent,/wound open or leaking/);
 $('reset').click();$('language').value='hi';$('language').dispatchEvent(new w.Event('change'));
 await submit('मुझे पेट में दर्द है');assert.ok([...$('answers').querySelectorAll('button')].some(b=>b.textContent==='हल्का'));
 $('reset').click();$('transcriptTools').classList.remove('hidden');$('message').value='I am vomiting blood';$('message').dispatchEvent(new w.Event('input'));
 await until(()=>!$('immediate').classList.contains('hidden'));
 $('message').value='No vomiting blood; mild stomach ache';$('message').dispatchEvent(new w.Event('input'));
 await until(()=>$('immediate').classList.contains('hidden'));
 assert.deepEqual(errors,[]);dom.window.close();console.log('PASS: stomach intake, choices, matching, simulated booking, emergency bypass, Hindi, corrected-transcript safety, four-question ear/dizziness conclusions, network outage and retry; no DOM runtime errors');
})().catch(e=>{console.error(e);process.exit(1);});
