// Optional DOM integration QA, not a screenshot/real-microphone browser test.
// Start the server in rules mode, then: npm install && npm run test:ui
const {JSDOM,VirtualConsole}=require('jsdom');
const assert=require('node:assert/strict');
const base=process.argv[2]||'http://127.0.0.1:8000';
const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
const pause=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let n=0;n<150;n++){if(fn())return;await pause(25);}throw Error('Timed out waiting for UI state');}
(async()=>{
 const dom=await JSDOM.fromURL(base,{resources:'usable',runScripts:'dangerously',virtualConsole:vc,beforeParse(w){w.fetch=(url,opts)=>fetch(new URL(url,base),opts);w.HTMLElement.prototype.scrollIntoView=function(){};}});
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
 $('reset').click();await submit('I have pain in my knee');assert.match($('chat').textContent,/pain in your knee/);
 answer('Moderate');await until(()=>$('chat').textContent.includes('injury, fall or twist'));
 answer('No');await until(()=>$('chat').textContent.includes('swelling around your knee'));
 answer('No');await until(()=>$('chat').textContent.includes('stand and put weight'));
 answer('Yes');await until(()=>$('chat').textContent.includes('bend, straighten or move your knee'));
 answer('Yes');await until(()=>$('chat').textContent.includes('How long have you'));
 await submit('two days');assert.match($('result').textContent,/joint pain/);assert.doesNotMatch($('chat').textContent,/difficulty breathing/);
 $('reset').click();await submit('My wrist hurts');answer('Mild');await until(()=>$('chat').textContent.includes('injury, fall or twist'));
 await submit('Now I cannot breathe');await until(()=>$('result').classList.contains('emergency'));
 assert.equal($('result').querySelector('a').getAttribute('href'),'tel:112');
 $('reset').click();await submit('I have severe stomach pain');assert.match($('concern').textContent,/prompt in-person/);
 answer('Yes');await until(()=>$('result').classList.contains('emergency'));
 assert.equal($('result').querySelector('a').getAttribute('href'),'tel:112');assert.equal($('result').querySelectorAll('button').length,0);assert.equal($('submit').disabled,true);
 $('reset').click();$('language').value='hi';$('language').dispatchEvent(new w.Event('change'));
 await submit('मुझे पेट में दर्द है');assert.ok([...$('answers').querySelectorAll('button')].some(b=>b.textContent==='हल्का'));
 $('reset').click();$('transcriptTools').classList.remove('hidden');$('message').value='I am vomiting blood';$('message').dispatchEvent(new w.Event('input'));
 await until(()=>!$('immediate').classList.contains('hidden'));
 $('message').value='No vomiting blood; mild stomach ache';$('message').dispatchEvent(new w.Event('input'));
 await until(()=>$('immediate').classList.contains('hidden'));
 assert.deepEqual(errors,[]);dom.window.close();console.log('PASS: stomach and knee intake, contextual choices, matching, simulated booking, late breathing emergency during wrist intake, emergency bypass, Hindi, corrected-transcript safety; no DOM runtime errors');
})().catch(e=>{console.error(e);process.exit(1);});
