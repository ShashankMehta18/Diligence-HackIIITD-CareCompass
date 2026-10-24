"""Run on synthetic audio only. Manifest CSV: path,language,reference.
Models share the audio account; neither uses the text account.
"""
import argparse,asyncio,csv,json,mimetypes,statistics,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.providers import GroqAccounts
from backend.app.intake import extract_local,normalise

def edit_distance(a,b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        current=[i]
        for j,y in enumerate(b,1):current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=current
    return previous[-1]

async def main(args):
    rows=list(csv.DictReader(args.manifest.open()));p=GroqAccounts();out=[]
    try:
        for model in ['whisper-large-v3','whisper-large-v3-turbo']:
            p.audio_model=model
            for row in rows:
                path=args.manifest.parent/row['path'];start=time.perf_counter()
                transcript=await p.transcribe(path.read_bytes(),path.name,mimetypes.guess_type(path)[0] or 'audio/wav',row['language'])
                truth=normalise(row['reference']);pred=normalise(transcript)
                a=extract_local(row['reference']);b=extract_local(transcript)
                fields=['age_months','duration_days','temperature','temperature_unit']
                fact_errors={k:{'expected':getattr(a,k),'predicted':getattr(b,k)} for k in fields if getattr(a,k)!=getattr(b,k)}
                flag_error=[(f.flag,f.status) for f in a.flags]!=[(f.flag,f.status) for f in b.flags]
                out.append({'model':model,'path':row['path'],'language':row['language'],'transcript':transcript,'wer':edit_distance(truth.split(),pred.split())/max(1,len(truth.split())),'cer':edit_distance(truth,pred)/max(1,len(truth)),'critical_fact_errors':fact_errors,'flag_or_negation_error':flag_error,'latency_ms':(time.perf_counter()-start)*1000})
    finally:await p.close()
    args.out.write_text(json.dumps({'scope':'Local synthetic recordings, WER tokenisation is whitespace; fact checking uses finite local extractor. Not clinical validation.','results':out},ensure_ascii=False,indent=2));print(f'Saved {len(out)} measured transcriptions')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);p.add_argument('--out',type=Path,default=Path('stt_benchmark.json'));asyncio.run(main(p.parse_args()))
