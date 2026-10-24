"""Full-pipeline offline development evaluation; live calls require explicit opt-in.

Use --project-root to run the SAME suite in a separate baseline checkout. Invoke
as a separate process per checkout so Python imports cannot contaminate results.
No patient logs, credentials, prompts or raw provider responses are written.
"""
import argparse
import asyncio
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import sys
import time

async def evaluate(args):
    exported_key=bool(os.environ.get('GROQ_TEXT_API_KEY'))
    # Import only after the selected project's root has been prepended.
    sys.path.insert(0,str(args.project_root.resolve()))
    from backend.app.core import assess
    from backend.app.schemas import Request
    from backend.app.providers import GroqAccounts,ProviderError
    cases=[json.loads(l) for l in args.cases.read_text().splitlines() if l.strip()]
    modes=['rules','live'] if args.mode=='both' else [args.mode]
    runs={}
    for mode in modes:
        if mode=='live' and (not args.allow_live or not exported_key):
            runs[mode]={'status':'not_run','reason':'Requires --allow-live and an explicitly exported GROQ_TEXT_API_KEY; never reads private ZIP settings.'}
            continue
        provider=GroqAccounts() if mode=='live' else None
        outputs=[]
        try:
            for c in cases:
                history=[];questions=[];r=None;ui={};error=None;t0=time.perf_counter()
                try:
                    for message in [c['user_input']]+c.get('answers',[]):
                        # Cases stop at final recommendation, except an explicit
                        # late-warning case: new information must still be assessed.
                        if r is not None and not r.follow_up_question and c['kind']!='late_warning':break
                        req=Request(user_input=message,language=c['language'],location={'lat':28.54,'lng':77.27},conversation_history=history)
                        r,ui=await assess(req,provider,mode=mode)
                        history.append({'role':'user','text':message})
                        if r.follow_up_question:
                            questions.append(ui.get('question_id'))
                            history.append({'role':'assistant','text':r.follow_up_question,'question_id':ui.get('question_id')})
                except ProviderError as exc:error=exc.kind
                expected=c['expected'];checks={}
                if error is None:
                    emergency=r.care_type=='emergency_112'
                    checks['emergency']=emergency==expected['emergency']
                    if expected.get('flag'):checks['flag']=expected['flag'] in r.red_flags
                    if 'care_type' in expected:checks['care_type']=r.care_type==expected['care_type']
                    if 'routine_matching_allowed' in expected:
                        if expected['routine_matching_allowed']:
                            # Permission to match is distinct from actual roster
                            # availability; an empty eligible roster is valid.
                            checks['routine_matching']=not r.follow_up_question and ui.get('assessment_status') not in ('needs_human_assessment','emergency') and 'unknown' not in r.reasoning.lower()
                        else:checks['routine_matching']=not r.matched_caregivers
                    if expected.get('human_review_required'):
                        checks['human_review']=not r.follow_up_question and not r.matched_caregivers and ('unknown' in r.reasoning.lower() or ui.get('assessment_status')=='needs_human_assessment')
                    checks['question_budget']=len(questions)<=4
                    checks['no_repeated_question']=len(questions)==len(set(questions))
                    if emergency:checks['emergency_invariant']=r.follow_up_question is None and not r.matched_caregivers
                outputs.append(dict(id=c['id'],scenario_id=c['scenario_id'],language=c['language'],kind=c['kind'],
                    expected_emergency=expected['emergency'],predicted_emergency=None if error else r.care_type=='emergency_112',
                    checks=checks,passed=error is None and all(checks.values()),error=error,
                    question_ids=questions,care_type=None if error else r.care_type,
                    caregiver_count=0 if error else len(r.matched_caregivers),
                    assessment_status=ui.get('assessment_status'),elapsed_ms=round((time.perf_counter()-t0)*1000,3)))
        finally:
            if provider:await provider.close()
        positives=[x for x in outputs if x['expected_emergency']]
        negatives=[x for x in outputs if not x['expected_emergency']]
        runs[mode]=dict(status='completed',cases=len(outputs),passed=sum(x['passed'] for x in outputs),
            emergency_cases=len(positives),emergency_detected=sum(x['predicted_emergency'] is True for x in positives),
            nonemergency_cases=len(negatives),false_emergencies=sum(x['predicted_emergency'] is True for x in negatives),
            provider_errors=sum(x['error'] is not None for x in outputs),
            missed_emergency_ids=[x['id'] for x in positives if x['predicted_emergency'] is False],
            failed_ids=[x['id'] for x in outputs if not x['passed']],
            by_language={l:{'n':sum(x['language']==l for x in outputs),'passed':sum(x['passed'] for x in outputs if x['language']==l)} for l in sorted({x['language'] for x in outputs})},
            rows=outputs)
    report=dict(suite_sha256=hashlib.sha256(args.cases.read_bytes()).hexdigest(),
        evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        provenance='Developer-authored regression suite; not blind held-out or clinically validated. Translation/control variants share scenario groups.',
        clinical_accuracy=None,runs=runs)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:{a:b for a,b in v.items() if a!='rows'} for k,v in runs.items()},indent=2))

if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root',type=Path,default=root)
    p.add_argument('--cases',type=Path,default=root/'evaluation_safety/cases.jsonl')
    p.add_argument('--out',type=Path,default=root/'evaluation_safety/results.json')
    p.add_argument('--mode',choices=['rules','live','both'],default='both')
    p.add_argument('--allow-live',action='store_true',help='Explicitly authorise live API calls using an EXPORTED key; consumes provider quota.')
    asyncio.run(evaluate(p.parse_args()))
