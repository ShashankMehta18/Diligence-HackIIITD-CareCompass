"""Offline, reproducible replay of the frozen deployed-app audit (no API calls).

Run each checkout in a separate process using --project-root to avoid import
contamination. The original challenge labels remain unchanged, even where a
clinical-source distinction is explicitly recorded as pending review.
"""
import argparse,asyncio,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def answer(case,q):
 if case['profile']=='unknown':return 'पता नहीं' if case['language']=='hi' else 'not sure'
 values={'symptom_age':'32 years old','age':'32 years old','symptom_severity':'mild','abdominal_severity':'mild','symptom_duration':'two days','duration':'two days','temperature':'37 degrees C','abdominal_location':'around the navel','symptom_change':'staying the same','keep_fluids':'yes','swallow_saliva':'yes','bear_weight':'yes','fluids_normal':'yes','nebulizer_home':'yes','symptom_detail':case['initial_message'],'complaint_clarify':case['initial_message'],'injection':'IM'}
 if q in values:return values[q]
 # These booleans are declared synthetic profile facts, never actual patient assumptions.
 boolean={'breathing','headache_sudden','one_sided_weakness','blood_vomit','blood_stool','airway_swelling','vision_loss','bladder_change','saddle_numbness','urine_retention','flank_pain','associated_fever','sudden_pain','joint_swelling','joint_moving','joint_injury','lifting_arm','joint_stiffness','arm_pain','leg_pain','grip_difficulty','bend_difficulty','fever_high','wound_leaking','wound_redness','sugar_check','foot_sore','foot_wound','catheter_block','catheter_pain','vitals_bp','vitals_sugar','postop_redness','postop_stitches','bedsores','daily_care','elderly_meds','heavy_bleeding','sleep_with','snoring','blood_cough','hearing_sudden','cardiac_chest','stroke_speech','immediate_harm'}
 return 'no' if q in boolean else 'not sure'

async def main(args):
 sys.path.insert(0,str(args.project_root.resolve()))
 from backend.app.core import assess
 from backend.app.schemas import Request
 cases=[json.loads(l) for l in args.cases.read_text().splitlines() if l]
 rows=[]
 for c in cases:
  history=[];questions=[];turns=[]
  async def turn(text):
   r,u=await assess(Request(user_input=text,language=c['language'],location={'lat':28.54,'lng':77.27},conversation_history=history),mode='rules')
   history.append({'role':'user','text':text})
   turns.append({'message':text,'response':r.model_dump(),'ui':u})
   if r.follow_up_question:
    questions.append(u['question_id']);history.append({'role':'assistant','text':r.follow_up_question,'question_id':u['question_id']})
   return r,u
  r,u=await turn(c['initial_message']);initial=u['state']['facts'].get('complaint')
  if c['late_message']:r,u=await turn(c['late_message'])
  elif c['complete_conversation']:
   for n in range(4):
    if not r.follow_up_question:break
    r,u=await turn(answer(c,u['question_id']))
  target=turns[-1] if c['late_message'] else turns[0]
  emergency_required=c['reference']['immediate_emergency'] is True
  rows.append(dict(case_id=c['case_id'],family=c['family'],initial_complaint=initial,intended_named_family=c['scenario_group'].startswith('presenting-') and c['family']!='other',complaint_aligned=initial==c['family'],full_conversation=c['complete_conversation'] and not c['late_message'],unknown=c['profile']=='unknown',late=bool(c['late_message']),expected_emergency=emergency_required,immediate_emergency=target['response']['care_type']=='emergency_112',question_ids=questions,final_care=r.care_type,final_status=u.get('assessment_status'),final_conclusion=not r.follow_up_question,caregiver_count=len(r.matched_caregivers),schema_ok=all(set(t['response'])=={'follow_up_question','care_type','urgency','red_flags','reasoning','matched_caregivers'} for t in turns),turns=turns))
 required=[r for r in rows if r['expected_emergency']];full=[r for r in rows if r['full_conversation']];unknown=[r for r in rows if r['unknown']];named=[r for r in rows if r['intended_named_family']]
 out=dict(case_sha256=hashlib.sha256(args.cases.read_bytes()).hexdigest(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),mode='rules_offline_no_provider',clinical_validation=False,clinical_accuracy=None,cases=len(rows),warning_checks=len(required),immediate_emergency=sum(r['immediate_emergency'] for r in required),not_immediate_emergency_ids=[r['case_id'] for r in required if not r['immediate_emergency']],full_conversations=len(full),final_conclusions=sum(r['final_conclusion'] for r in full),unknown_cases=len(unknown),unknown_no_matches=sum(not r['caregiver_count'] for r in unknown),named_complaints=len(named),named_complaints_aligned=sum(r['complaint_aligned'] for r in named),schema_cases=sum(r['schema_ok'] for r in rows),max_questions=max(len(r['question_ids']) for r in rows),repeated_question_cases=sum(len(r['question_ids'])!=len(set(r['question_ids'])) for r in rows),rows=rows)
 args.out.parent.mkdir(exist_ok=True,parents=True);args.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--project-root',type=Path,default=ROOT);p.add_argument('--cases',type=Path,default=ROOT/'evaluation_0_5/deployment_cases.jsonl');p.add_argument('--out',type=Path,default=ROOT/'evaluation_0_5/current.json');asyncio.run(main(p.parse_args()))
