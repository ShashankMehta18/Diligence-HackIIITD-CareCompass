'use strict';
// Presentation only. No API calls or changes to the CareCompass workflow.
(() => {
 const get = id => document.getElementById(id), theme = get('theme');
 let dark = false;
 try { dark = localStorage.getItem('carecompass-theme') === 'dark'; } catch {}
 function paintTheme() {
  document.body.classList.toggle('dark', dark);
  theme.setAttribute('aria-pressed', String(dark));
  theme.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
  document.querySelector('meta[name="theme-color"]').content = dark ? '#101d19' : '#f7f8f4';
 }
 paintTheme();
 theme.addEventListener('click', () => {dark = !dark; paintTheme(); try {localStorage.setItem('carecompass-theme', dark ? 'dark' : 'light');} catch {}});
 get('howBtn').addEventListener('click', () => get('how').showModal());
 get('closeHow').addEventListener('click', () => get('how').close());
 function paintJourney() {
  const stage = !get('chat').children.length ? 1 : !get('progress').classList.contains('hidden') ? 2 : 3;
  for (let i=1;i<=3;i++) {
   const step=get('step'+i); step.classList.toggle('active',i===stage); step.classList.toggle('complete',i<stage);
   if(i===stage)step.setAttribute('aria-current','step');else step.removeAttribute('aria-current');
  }
  get('stageLabel').textContent=['LET’S START WITH YOU','A FEW USEFUL QUESTIONS','YOUR CARE PATHWAY'][stage-1];
 }
 const observer = new MutationObserver(paintJourney);
 observer.observe(get('result'),{childList:true,subtree:true});
 observer.observe(get('chat'),{childList:true});
 observer.observe(get('progress'),{attributes:true,attributeFilter:['class']});
 paintJourney();
})();
