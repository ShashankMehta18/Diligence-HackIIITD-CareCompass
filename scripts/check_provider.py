"""Opt-in, synthetic provider diagnostic. Never prints credentials or raw errors.

Default is offline. With --allow-live, uses the locally configured TEXT account
only and at most two requests. It stops on a rate limit. No clinical validation.
"""
import argparse,asyncio,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
async def main(args):
 if not args.allow_live:
  print(json.dumps({'live':'not_run','reason':'Pass --allow-live to use your configured text account for at most two synthetic requests.'},indent=2));return
 from backend.app.providers import GroqAccounts,ProviderError
 from backend.app.schemas import Request
 p=GroqAccounts();rows=[]
 try:
  for n,text in enumerate(['It burns when I pass urine.','I have an existing thyroid condition.']):
   start=time.perf_counter()
   try:
    x=await p.extract(Request(user_input=text,language='en',location={'lat':28.54,'lng':77.27}))
    rows.append({'case':n+1,'status':'schema_valid','complaint':x.complaint,'elapsed_ms':round((time.perf_counter()-start)*1000,2)})
   except ProviderError as error:
    rows.append({'case':n+1,'status':'failed',**error.public()})
    if error.kind in ('rate_limit','credentials','text_not_configured'):break
   if n==0:await asyncio.sleep(3)
  report={'model':p.text_model,'clinical_validation':False,'results':rows,'provider_status':p.diagnostics()}
  args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps(report,indent=2))
 finally:await p.close()
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--allow-live',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'evaluation_0_5/provider_live_check.json');asyncio.run(main(p.parse_args()))
