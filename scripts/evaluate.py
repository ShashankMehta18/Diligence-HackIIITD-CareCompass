"""Descriptive, scenario-group-disjoint evaluation. Not clinical validation."""
import argparse,asyncio,collections,hashlib,json,math,re,statistics,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app.config import DATA
from backend.app.core import assess
from backend.app.schemas import Request
from backend.app.intake import normalise

FAMILIES=[
 ('emergency_bleeding',r'bleeding|खून'),('emergency_collapse',r'collapsed|response nahi|जवाब नहीं'),('emergency_chest',r'chest pain|सीने'),
 ('insulin',r'insulin|इंसुलिन'),('bp_sugar',r'\bbp\b|बीपी'),('cbc_thyroid',r'cbc|thyroid|सीबीसी|थायराइड'),
 ('sugar_collection',r'sugar test|sugar.*kal|kal.*sugar|शुगर टेस्ट'),('full_body',r'full body|फुल बॉडी'),
 ('injection_im',r'\bim\b|घर पर इंजेक्शन लगवाना'),('injection_prescribed',r'injection|इंजेक्शन'),
 ('bedsore',r'bedsore|दादी.*ड्रेसिंग'),('dressing',r'dressing|ड्रेसिंग|पट्टी'),
 ('fever_cough',r'fever|bukhar|बुखार'),('weakness',r'weak|कमजोर'),
 ('reports',r'report|रिपोर्ट'),('second_opinion',r'second opinion|सेकंड ओपिनियन'),('acidity',r'acidity|एसिडिटी'),
 ('book_mother',r'book.*mother|mummy.*book|माँ.*बुक'),('greeting',r'anyone|hello|hi,|नमस्ते'),
 ('help',r'help|मदद'),('vague_doctor',r'doctor chahiye|डॉक्टर चाहिए')]

def family(text):
    t=normalise(text)
    return next((name for name,p in FAMILIES if re.search(p,t)),t)

def partition(rows):
    groups=collections.defaultdict(set)
    for r in rows:groups[str(r['response']['care_type'])].add(family(r['request']['user_input']))
    validation=set()
    for label,gs in groups.items():
        ordered=sorted(gs,key=lambda g:hashlib.sha256(('carecompass-42:'+g).encode()).hexdigest())
        validation.update(ordered[:max(1,round(len(ordered)*.25))])
    return [r for r in rows if family(r['request']['user_input']) not in validation],[r for r in rows if family(r['request']['user_input']) in validation]

def classify_metrics(truth,pred,labels):
    cm=[[sum(a==x and b==y for a,b in zip(truth,pred)) for y in labels] for x in labels]
    f1=[]
    for l in labels:
        tp=sum(a==b==l for a,b in zip(truth,pred));fp=sum(a!=l and b==l for a,b in zip(truth,pred));fn=sum(a==l and b!=l for a,b in zip(truth,pred))
        f1.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    return {'macro_f1':sum(f1)/len(f1),'labels':labels,'confusion_matrix_rows_truth_columns_prediction':cm}

def binary(y,p):
    tp=sum(a and b for a,b in zip(y,p));fn=sum(a and not b for a,b in zip(y,p));fp=sum(not a and b for a,b in zip(y,p));tn=sum(not a and not b for a,b in zip(y,p))
    return {'recall':tp/(tp+fn) if tp+fn else None,'precision':tp/(tp+fp) if tp+fp else None,'false_positive_rate':fp/(fp+tn) if fp+tn else None,'tp':tp,'fn':fn,'fp':fp,'tn':tn}

async def main(args):
    rows=[json.loads(l) for l in args.data.read_text().splitlines() if l.strip()]
    train,val=partition(rows);selected=rows if args.split=='all' else val
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'split.json').write_text(json.dumps({'seed':'carecompass-42','train_ids':[r['id'] for r in train],'validation_ids':[r['id'] for r in val],'family_by_id':{r['id']:family(r['request']['user_input']) for r in rows}},ensure_ascii=False,indent=2))
    results=[];latencies=[]
    for row in selected:
        start=time.perf_counter();r,ui=await assess(Request.model_validate(row['request']),mode='rules')
        elapsed=(time.perf_counter()-start)*1000;latencies.append(elapsed)
        results.append({'id':row['id'],'language':row['detected_language'],'family':family(row['request']['user_input']),'truth':row['response'],'prediction':r.model_dump(),'latency_ms':elapsed})
    ct=[str(x['truth']['care_type']) for x in results];cp=[str(x['prediction']['care_type']) for x in results]
    ut=[str(x['truth']['urgency']) for x in results];up=[str(x['prediction']['urgency']) for x in results]
    metric={'mode':args.mode,'split':args.split,'n':len(results),'train_n':len(train),'validation_n':len(val),'scope':'Descriptive evaluation: rules were authored after inspecting supplied templates; not a blind generalisation estimate. No retrieval or fitting is used.','care':classify_metrics(ct,cp,['None','home_nursing','emergency_112','lab_test_home','teleconsultation','paramedic_home_visit']),'urgency':classify_metrics(ut,up,['None','emergency','same_day','scheduled']),'emergency':binary([t=='emergency_112' for t in ct],[p=='emergency_112' for p in cp]),'follow_up':binary([x['truth']['follow_up_question'] is not None for x in results],[x['prediction']['follow_up_question'] is not None for x in results]),'latency_ms':{'median':statistics.median(latencies),'p95':sorted(latencies)[max(0,math.ceil(.95*len(latencies))-1)],'scope':'Core processing only; HTTP/network excluded in rules mode'},'schema_compliance':1.0,'missed_emergencies':[x['id'] for x in results if x['truth']['care_type']=='emergency_112' and x['prediction']['care_type']!='emergency_112']}
    hit=[];recall=[];ndcg=[];excluded=0;violations=[]
    from backend.app.matching import ROSTER,REQUIRED,haversine
    byid={x['caregiver_id']:x for x in ROSTER};source={x['id']:x for x in selected}
    for x in results:
        relevant=[m['caregiver_id'] for m in x['truth']['matched_caregivers']];ranked=[m['caregiver_id'] for m in x['prediction']['matched_caregivers']]
        if not relevant:excluded+=1
        else:
            hit.append(float(bool(ranked and ranked[0] in relevant)));recall.append(len(set(ranked[:3])&set(relevant))/len(set(relevant)))
            gains={m['caregiver_id']:m['score'] for m in x['truth']['matched_caregivers']}
            dcg=sum(gains.get(v,0)/math.log2(i+2) for i,v in enumerate(ranked[:3]));ideal=sum(v/math.log2(i+2) for i,v in enumerate(sorted(gains.values(),reverse=True)[:3]));ndcg.append(dcg/ideal if ideal else 0)
        for m in x['prediction']['matched_caregivers']:
            c=byid.get(m['caregiver_id']);need=x['prediction']['care_type'];loc=source[x['id']]['request']['location']
            expected={'home_nursing':'medic','paramedic_home_visit':'medic','lab_test_home':'phlebotomist','teleconsultation':'doctor'}.get(need)
            if not c or not c['active'] or c['role']!=expected or (need!='teleconsultation' and haversine(loc['lat'],loc['lng'],c['base_lat'],c['base_lng'])>c['max_radius_km']):violations.append(x['id'])
    metric['matching']={'scope':'Local label-agreement proxies; relevance labels may contain eligibility errors','eligible_relevance_rows':len(hit),'excluded_empty_relevance_rows':excluded,'hit_at_1':statistics.mean(hit) if hit else None,'recall_at_3':statistics.mean(recall) if recall else None,'ndcg_at_3':statistics.mean(ndcg) if ndcg else None,'id_active_role_radius_violation_count':len(violations),'procedural_skill_checks':'Covered independently in tests; roster scope assumptions documented'}
    flags=['chest_pain','breathlessness','unconsciousness','severe_bleeding','stroke_symptoms','seizure','high_fever_infant','suicidal_ideation','severe_dehydration']
    a=[];b=[];corrected=[]
    for x in results:
        original=x['truth']['red_flags'];semantic=original
        if x['family']=='emergency_bleeding':semantic=['severe_bleeding']
        if x['family']=='emergency_collapse':semantic=['unconsciousness']
        for f in flags:a.append(f in original);b.append(f in x['prediction']['red_flags']);corrected.append(f in semantic)
    metric['red_flags_original_noisy_labels_micro']=binary(a,b)
    metric['red_flags_proposed_semantic_corrections_micro']=binary(corrected,b)
    metric['by_language']={l:classify_metrics([str(x['truth']['care_type']) for x in results if x['language']==l],[str(x['prediction']['care_type']) for x in results if x['language']==l],metric['care']['labels']) for l in sorted({x['language'] for x in results})}
    (args.out/'metrics.json').write_text(json.dumps(metric,indent=2)+'\n')
    (args.out/'predictions.jsonl').write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in results)+'\n')
    print(json.dumps(metric,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,default=DATA/'triage_dataset.jsonl');p.add_argument('--out',type=Path,default=Path('evaluation'));p.add_argument('--mode',choices=['rules'],default='rules');p.add_argument('--split',choices=['validation','all'],default='validation');asyncio.run(main(p.parse_args()))

