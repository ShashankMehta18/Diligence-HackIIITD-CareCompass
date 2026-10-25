"""Provisional CSV schema; adapt --columns once organisers publish the final spec."""
import argparse,asyncio,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.schemas import Request
from backend.app.core import assess

async def main(args):
    if args.input.suffix.lower()=='.csv':
        rows=list(csv.DictReader(args.input.open()))
    else:
        text=args.input.read_text();rows=json.loads(text) if text.lstrip().startswith('[') else [json.loads(l) for l in text.splitlines() if l.strip()]
    columns=args.columns.split(',');output=[]
    for index,row in enumerate(rows):
        raw=row.get('request',row)
        if isinstance(raw,str):raw=json.loads(raw)
        location=raw.get('location',{'lat':raw.get('lat'),'lng':raw.get('lng')})
        if isinstance(location,str):location=json.loads(location)
        hist=raw.get('conversation_history',[])
        if isinstance(hist,str):hist=json.loads(hist or '[]')
        request=Request(user_input=raw['user_input'],language=raw.get('language','auto'),location=location,conversation_history=hist)
        result,_=await assess(request,mode='rules');body=result.model_dump()
        out={'id':row.get('id',row.get('example_id',str(index))),'response_json':json.dumps(body,ensure_ascii=False),**body}
        for key in ['matched_caregivers','red_flags']:out[key]=json.dumps(out[key],ensure_ascii=False)
        out={k:('' if v is None else v) for k,v in out.items()}
        unknown=set(columns)-set(out)
        if unknown:raise ValueError(f'Unsupported output columns: {unknown}')
        output.append(out)
    # Atomic final output; failures never produce a misleading partial submission.
    args.output.parent.mkdir(parents=True,exist_ok=True);temp=args.output.with_suffix(args.output.suffix+'.tmp')
    with temp.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(output)
    temp.replace(args.output);print(f'Exported {len(output)} rows. Columns are provisional: {columns}')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);p.add_argument('--mode',choices=['rules'],default='rules');p.add_argument('--columns',default='id,care_type,urgency,red_flags,follow_up_question,reasoning,matched_caregivers');asyncio.run(main(p.parse_args()))

