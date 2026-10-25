"""Source-informed development tests. No clinical validation or blind-test claim."""
import asyncio,json
from pathlib import Path
import pytest,httpx
from backend.app.core import assess
from backend.app.schemas import Request,Extraction,FlagEvidence,ClinicalFinding
from backend.app.providers import GroqAccounts,ProviderError,strict_schema

def req(text,history=(),lang='en'):return Request(user_input=text,conversation_history=list(history),language=lang,location={'lat':28.54,'lng':77.27})
def run(text,history=(),lang='en',provider=None,mode='rules'):return asyncio.run(assess(req(text,history,lang),provider,mode=mode))

@pytest.mark.parametrize('text',[
 'Drain cleaner splashed into my left eye.', 'An acid spray got into his eye.',
 'मेरी आंख में तेजाब पड़ गया है।', 'ankh me chemical gir gaya',
 'Glass has pierced my eye.', 'A sharp fragment punctured her eyeball.',
 'My right eye is bleeding.', 'आँख से खून बह रहा है।',
 'After a racket hit my eye, my vision got blurry.',
 'I suddenly lost feeling down the right side of my body.',
 'My left side feels numb. This started ten minutes ago.',
 'अभी शरीर का दायाँ हिस्सा सुन्न हो गया है।',
 'ek taraf achanak sunn ho gaya hai',
 'One hour ago my left side went numb but I feel normal now.',
 'I suddenly cannot speak clearly.', 'My face has dropped on one side.',
 'मेरी बोली अचानक लड़खड़ा रही है।',
 'My child drank rat poison.', 'He ingested drain cleaner.',
 'I may have swallowed some pesticide.', 'मैंने गलती से कीटनाशक पी लिया।',
 'maine galti se phenyl pi liya',
 'I have sudden unbearable scrotal pain.', 'अचानक अंडकोष में बहुत तेज दर्द है।',
 'I am gasping and cannot get my words out.',
])
def test_fresh_warning_paraphrases_interrupt_before_provider(text):
 class Broken:
  text_key='test'
  async def extract(self,req):raise AssertionError('A locally established warning must not call provider')
 r,u=run(text,provider=Broken(),mode='live')
 assert r.care_type=='emergency_112' and not r.follow_up_question and not r.matched_caregivers
 assert u['assessment_status']=='emergency'

@pytest.mark.parametrize('text',[
 'No chest pain or trouble breathing. My knee aches.',
 'I do not have chest pain or difficulty breathing. My wrist hurts.',
 'No bleach splashed into my eye.', 'My eye is not bleeding.',
 'My eye has a small red spot. No pain, injury or change in vision.',
 'I got shampoo in my eye, but it is fine now.',
 'What if someone swallowed bleach?', 'The bleach label says if swallowed seek help. Nobody swallowed it.',
 'I did not swallow pesticide.', 'Last year I swallowed rat poison and was treated.',
 'Five years ago I had sudden numbness down my left side.',
 'I have tingling in both hands for months.',
 'Hypothetical example: a sharp object pierced an eye.',
 'My eyes suddenly started itching after dust exposure.',
 'I took ten paracetamol tablets over the last month as prescribed.',
 'There is no sudden severe pain in my testicle.',
])
def test_controls_are_not_false_emergencies(text):
 r,u=run(text)
 assert r.care_type!='emergency_112'

@pytest.mark.parametrize('text,family,question',[
 ('It stings when I urinate.','urinary','urine_retention'),
 ('Burning happens when I pass urine.','urinary','urine_retention'),
 ('The back of my neck hurts.','neck_pain','joint_stiffness'),
 ('My lower back hurts.','back_pain','bladder_change'),
 ('I have an existing kidney condition.','kidney','symptom_severity'),
 ('My thyroid condition is longstanding.','thyroid','symptom_severity'),
 ('My fingers hurt when I grip something.','hand_pain','joint_swelling'),
 ('My fingers are numb.','neuro','one_sided_weakness'),
 ('I cannot sleep at night.','sleep_problem','snoring'),
 ('I keep losing weight without trying.','nutrition','symptom_severity'),
 ('My throat is sore when I swallow.','sore_throat','swallow_saliva'),
 ('My heart skips beats.','cardiac','cardiac_chest'),
])
def test_complaint_context_and_followup(text,family,question):
 r,u=run(text)
 assert u['state']['facts']['complaint']==family and u['question_id']==question
 assert not r.red_flags

def test_structured_urinary_understanding():
 r,u=run('It burns when I pass urine.')
 assert u['state']['understanding']['body_site']=='urinary tract'
 assert u['state']['understanding']['trigger']=='passing urine'
 assert all(s['name']!='wound' for s in u['state']['facts']['associated_symptoms'])

def test_medication_excess_gets_immediate_urgent_review_not_dose_clearance():
 r,u=run('I accidentally took ten paracetamol tablets in the last hour.')
 assert r.follow_up_question is None and not r.matched_caregivers
 assert u['assessment_status']=='needs_human_assessment' and 'urgent' in r.reasoning.lower()
 assert 'dose is safe' not in r.reasoning.lower()

def test_clarification_conflict_never_silently_books():
 class Confused:
  text_key='fake'
  async def extract(self,req):return Extraction(complaint='thyroid',complaint_text=req.user_input,evidence=[req.user_input])
 r,u=run('My knee hurts',provider=Confused(),mode='live')
 assert u['question_id']=='complaint_clarify' and not r.matched_caregivers
 assert u['state']['extraction_conflicts']

def test_clear_short_answers_do_not_spend_provider_quota():
 class Unused:
  text_key='fake'
  async def extract(self,req):raise AssertionError('Do not call for deterministic follow-up answer')
 r,u=run('My knee hurts');h=[{'role':'user','text':'My knee hurts'},{'role':'assistant','text':r.follow_up_question,'question_id':u['question_id']}]
 r,u=run('no',h,provider=Unused(),mode='live')
 assert u['engine']=='rules_contextual_answer' and u['question_id']=='joint_moving'

def test_grounded_complex_model_denial_cannot_undo_safety():
 class Unused:
  text_key='fake'
  async def extract(self,req):raise AssertionError('Bypass provider for new hazard')
 r,u=run('My knee hurts');h=[{'role':'user','text':'My knee hurts'},{'role':'assistant','text':r.follow_up_question,'question_id':u['question_id']}]
 r,u=run('No swelling, but bleach splashed into my eye.',h,provider=Unused(),mode='live')
 assert r.care_type=='emergency_112'

def test_provider_schema_is_portable_but_local_validation_stays_strict():
 schema=strict_schema(Extraction.model_json_schema())
 raw=json.dumps(schema)
 assert 'maxLength' not in raw and 'minimum' not in raw
 from pydantic import ValidationError
 with pytest.raises(ValidationError):Extraction(age_months=-1)

def test_retry_after_cooldown_does_not_retry_or_affect_audio(monkeypatch):
 async def scenario():
  p=GroqAccounts();p.text_key='fake';calls=[]
  async def handler(request):calls.append(1);return httpx.Response(429,headers={'Retry-After':'90'},json={'error':{'message':'PRIVATE PATIENT SECRET'}})
  await p.text_client.aclose();p.text_client=httpx.AsyncClient(transport=httpx.MockTransport(handler),base_url='https://synthetic.test/')
  try:
   for n in range(2):
    with pytest.raises(ProviderError) as error:await p.extract(req('My wrist hurts'))
    assert error.value.kind=='rate_limit'
   assert len(calls)==1
   d=p.diagnostics();assert d['text']['cooldown_seconds']>=89 and d['audio']['cooldown_seconds']==0
   assert 'PRIVATE' not in json.dumps(d)
  finally:await p.close()
 asyncio.run(scenario())

def test_rejected_provider_request_retains_only_allowlisted_diagnostic():
 async def scenario():
  p=GroqAccounts();p.text_key='fake'
  async def handler(request):return httpx.Response(400,json={'error':{'code':'json_validate_failed','message':'PRIVATE PATIENT SECRET'}})
  await p.text_client.aclose();p.text_client=httpx.AsyncClient(transport=httpx.MockTransport(handler),base_url='https://synthetic.test/')
  try:
   with pytest.raises(ProviderError) as error:await p.extract(req('My wrist hurts'))
   assert error.value.public()=={'code':'request_rejected','http_status':400,'provider_code':'json_validate_failed'}
   assert 'PRIVATE' not in json.dumps(p.diagnostics())
  finally:await p.close()
 asyncio.run(scenario())

@pytest.mark.parametrize('text',[
 'I am not sure if I have a fever.',
 'pata nahi bukhar hai ya nahi',
 'मुझे पता नहीं बुखार है या नहीं।',
])
def test_uncertain_fever_is_not_an_asserted_positive_or_negative(text):
 from backend.app.intake import extract_local
 assert extract_local(text).fever is None

def test_uncertain_service_does_not_enable_a_procedure_booking():
 r,u=run('I am not sure whether I need a CBC test.')
 assert not r.matched_caregivers and u['assessment_status']=='needs_human_assessment'

def test_complex_model_uncertainty_cannot_resolve_safety_negatively():
 class Stub:
  text_key='fake'
  async def extract(self,req):return Extraction(clinical_features=[ClinicalFinding(name='new_one_sided_weakness',status='denied',quote=req.user_input)],evidence=[req.user_input])
 r,u=run('I am dizzy');h=[{'role':'user','text':'I am dizzy'},{'role':'assistant','text':r.follow_up_question,'question_id':u['question_id']}]
 r,u=run('I do not know whether there is weakness.',h,provider=Stub(),mode='live')
 assert not any(f['name']=='new_one_sided_weakness' and f['status']=='denied' for f in u['state']['facts']['clinical_features'])

def test_safety_finding_correction_and_patient_change():
 from backend.app.intake import replay
 h=[{'role':'user','text':'Bleach splashed into my eye.'}]
 r,u=run('Transcription correction: no bleach splashed into my eye. I only have mild eye itching.',h)
 assert r.care_type!='emergency_112'
 h=[{'role':'user','text':'My father swallowed rat poison.'}]
 r,u=run('For my mother, mild knee pain.',h)
 assert r.care_type!='emergency_112' and not u['state']['safety_findings']

def test_api_safety_preview_and_hindi_emergency():
 from fastapi.testclient import TestClient
 from backend.app.main import app
 with TestClient(app) as c:
  r=c.post('/ui/safety',json=req('मेरी आंख में तेजाब पड़ गया है।',lang='hi').model_dump())
  assert r.json()['emergency_warning']
  b=c.post('/ui/triage',json=req('मेरी आंख में तेजाब पड़ गया है।',lang='hi').model_dump()).json()
  assert b['response']['care_type']=='emergency_112' and 'अभी 112' in b['response']['reasoning']
  assert c.get('/health').json()['version']=='0.5.0'
  assert 'provider_status' in c.get('/health').json()

@pytest.mark.parametrize('text',[
 'My face is not drooping.', 'My face was not drooping.',
 'Nothing has pierced my eye.', 'No sharp object pierced my eye.',
 'My eye was not injured and my vision is unchanged.',
 'My eye was injured last year. My vision is normal.',
 'My left side went numb 48 hours ago and it resolved.',
])
def test_compositional_negation_and_remote_controls(text):
 r,u=run(text)
 assert r.care_type!='emergency_112'

def test_uncertain_warning_gets_human_assessment_without_waiting_for_provider():
 class Broken:
  text_key='fake'
  async def extract(self,req):raise AssertionError('Do not wait for provider to review an uncertain warning')
 r,u=run('I am not sure if blood is coming out of my eye.',provider=Broken(),mode='live')
 assert r.follow_up_question is None and not r.matched_caregivers
 assert u['assessment_status']=='needs_human_assessment'

def test_typical_prescribed_dose_is_not_invented_as_an_overdose():
 r,u=run('I took my prescribed two tablets today.')
 assert not any(v['rule_id']=='medication_excess' for v in u['state']['safety_findings'])
