"""Source-informed synthetic regressions; no claim of clinical validation."""
import asyncio
from typing import get_args
import pytest
from backend.app.schemas import Request,Extraction,FlagEvidence,ClinicalFinding,Complaint
from backend.app.core import assess
from backend.app.intake import detect_flags,extract_local
from backend.app.safety_policy import REQUIRED_QUESTIONS
from backend.app.complaints import BROAD_QUESTIONS,QUESTION_PLANS
from backend.app.providers import ProviderError

def request(text,history=(),language='en'):
    return Request(user_input=text,language=language,location={'lat':28.54,'lng':77.27},conversation_history=list(history))

def run(text,history=(),language='en',provider=None,mode='rules'):
    return asyncio.run(assess(request(text,history,language),provider,mode=mode))

def turn(history,text,language='en'):
    r,u=run(text,history,language)
    history.append({'role':'user','text':text})
    if r.follow_up_question:history.append({'role':'assistant','text':r.follow_up_question,'question_id':u['question_id']})
    return r,u

@pytest.mark.parametrize('text,flag',[
 ('papa behosh ho gaye','unconsciousness'),
 ('mummy ko hosh nahi aa raha','unconsciousness'),
 ('He has passed out and cannot wake up','unconsciousness'),
 ('She is not responding to her name','unconsciousness'),
 ('dam ghut raha hai','breathlessness'),
 ('saas nahi aa rahi hai','breathlessness'),
 ('साँस लेने में बहुत दिक्कत है','breathlessness'),
 ('I am gasping for air','breathlessness'),
 ('I cannot get enough air','breathlessness'),
 ('Deep cut and blood is gushing out','severe_bleeding'),
 ('Blood is spurting from the wound','severe_bleeding'),
 ('zakhm se bohot khun nikal raha hai','severe_bleeding'),
 ('घाव से बहुत खून बह रहा है','severe_bleeding'),
 ('ek taraf ka haath kaam nahi kar raha','stroke_symptoms'),
 ('अचानक शरीर के एक तरफ का हाथ काम नहीं कर रहा','stroke_symptoms'),
 ('My speech suddenly became slurred','stroke_symptoms'),
 ('There is pressure in my chest','chest_pain'),
 ('मेरी छाती में दर्द है','chest_pain'),
 ('He is convulsing','seizure'),
])
def test_emergency_paraphrases_stop_full_pipeline(text,flag):
    r,u=run(text)
    assert r.care_type=='emergency_112' and flag in r.red_flags
    assert r.follow_up_question is None and not r.matched_caregivers
    assert u['assessment_status']=='emergency' and not u['routine_booking_allowed']

@pytest.mark.parametrize('text',[
 'papa behosh nahi hain',
 'पापा बेहोश नहीं हैं',
 'I am not gasping for air',
 'No chest pressure or chest pain',
 'I do not have slurred speech or sudden arm weakness',
 'What if someone is gasping for air?',
 'Last year, my father passed out and could not wake up; now resolved',
 'Hypothetical example: blood is gushing out',
 'No blood is gushing out',
 'dam nahi ghut raha hai',
])
def test_negation_history_and_hypothetical_are_not_affirmed(text):
    r,_=run(text)
    assert r.care_type!='emergency_112'

@pytest.mark.parametrize('text,flag',[
 ('No chest pain but I am gasping for air','breathlessness'),
 ('Last year I had chest pain. Now I am gasping for air','breathlessness'),
 ('No severe bleeding and now blood is gushing out','severe_bleeding'),
 ('My father is not unconscious but my speech suddenly became slurred','stroke_symptoms'),
])
def test_denial_or_history_does_not_mask_new_warning(text,flag):
    r,_=run(text)
    assert r.care_type=='emergency_112' and flag in r.red_flags

def test_original_user_evidence_is_preserved():
    text='Papa BEHOSH ho gaye'
    flags=detect_flags(text)
    assert flags and all(v.quote in text for v in flags)

def test_all_complaints_have_explicit_minimum_information_policies():
    assert set(REQUIRED_QUESTIONS)==set(get_args(Complaint))
    for c,questions in REQUIRED_QUESTIONS.items():
        for q in questions:assert q in BROAD_QUESTIONS or q in ('age','breathing')
        if c not in ('fever','other'):
            assert set(questions)<=set(QUESTION_PLANS[c]),c

@pytest.mark.parametrize('text',[
 'I am dizzy','I have palpitations','I have tingling',
 'I feel unusually tired','My knee hurts','I have an injury',
 'I have menstrual problems','I feel anxious','I have a fever',
 'I have a wound','I need nebulization','I have thyroid problems',
])
def test_unclear_answers_withhold_routine_booking(text):
    h=[]
    for message in [text]+['not sure']*4:
        r,u=turn(h,message)
        if not r.follow_up_question:break
    assert r.follow_up_question is None
    assert not r.matched_caregivers and not u['caregivers']
    assert u['assessment_status']=='needs_human_assessment'
    assert u['unresolved_information'] and not u['routine_booking_allowed']
    assert 'unknown' in r.reasoning
    assert 'No eligible caregiver is available' not in r.reasoning

@pytest.mark.parametrize('text',[
 'Need prescribed wound dressing at home',
 'Need BP and sugar checked at home',
 'Need an IM injection at home',
 'Need a CBC home sample collection',
])
def test_simple_explicit_procedures_preserve_original_flow(text):
    r,u=run(text)
    assert r.follow_up_question is None and u['assessment_status']=='care_pathway'

def test_service_request_does_not_bypass_co_reported_dizziness():
    h=[]
    for t in ['Need wound dressing and I am dizzy']+['not sure']*4:
        r,u=turn(h,t)
        if not r.follow_up_question:break
    assert not r.matched_caregivers and u['assessment_status']=='needs_human_assessment'

def test_dizziness_yes_and_no_have_different_outcomes():
    h=[];r,u=turn(h,'I am dizzy');assert u['question_id']=='one_sided_weakness'
    yes,_=run('yes',h)
    assert yes.care_type=='emergency_112'
    no,u=turn(h,'no');assert u['question_id']=='stroke_speech'
    yes,_=run('yes',h);assert yes.care_type=='emergency_112'
    for t in ['no','mild','two days']:r,u=turn(h,t)
    assert r.care_type=='teleconsultation' and u['assessment_status']=='care_pathway'

def test_cardiac_chest_answer_has_flag_and_no_question_delay():
    h=[];r,u=turn(h,'I have palpitations')
    assert u['question_id']=='cardiac_chest'
    r,u=run('हाँ',h,'hi')
    assert r.care_type=='emergency_112' and 'chest_pain' in r.red_flags

def test_knee_never_gets_respiratory_question_but_late_warning_interrupts():
    h=[]
    for t in ['My knee hurts','no','no']:
        r,u=turn(h,t)
        assert u['question_id']!='breathing'
    r,u=run('abhi dam ghut raha hai',h)
    assert r.care_type=='emergency_112' and not r.matched_caregivers

def test_hindi_unclear_answers_remain_unknown():
    h=[]
    for t in ['मुझे चक्कर आ रहे हैं']+['पता नहीं']*4:
        r,u=turn(h,t,'hi')
        if not r.follow_up_question:break
    assert u['assessment_status']=='needs_human_assessment' and not r.matched_caregivers
    assert all(v['status']!='denied' for v in u['state']['warning_signs'].values())

class Broken:
    text_key='stub'
    async def extract(self,req):raise ProviderError('unavailable')

def test_new_emergency_phrasing_bypasses_provider_outage():
    r,_=run('papa behosh ho gaye',provider=Broken(),mode='live')
    assert r.care_type=='emergency_112'

def test_quoted_model_evidence_cannot_reintroduce_previous_patient_warning():
    class Stub:
        text_key='stub'
        async def extract(self,req):return Extraction(flags=[FlagEvidence(flag='unconsciousness',status='affirmed',quote='My father is unconscious')],evidence=['My father is unconscious'])
    r,u=run('For my mother, mild ear pain',[{'role':'user','text':'My father is unconscious'}],provider=Stub(),mode='live')
    assert r.care_type!='emergency_112' and not u['state']['warning_signs']

def test_model_yes_to_joint_question_is_not_breathlessness():
    class Stub:
        text_key='stub'
        async def extract(self,req):return Extraction(flags=[FlagEvidence(flag='breathlessness',status='affirmed',quote='yes')],evidence=['yes'])
    h=[];turn(h,'My knee hurts')
    r,u=run('yes',h,provider=Stub(),mode='live')
    assert r.care_type!='emergency_112' and 'breathlessness' not in u['state']['warning_signs']

def test_model_unknown_reply_is_not_a_negative_safety_answer():
    class Stub:
        text_key='stub'
        async def extract(self,req):return Extraction(clinical_features=[ClinicalFinding(name='new_one_sided_weakness',status='denied',quote='not sure')],evidence=['not sure'])
    h=[];turn(h,'I am dizzy')
    r,u=run('not sure',h,provider=Stub(),mode='live')
    assert 'new_one_sided_weakness' not in {v['name'] for v in u['state']['facts']['clinical_features']}

def test_review_status_is_ui_only_and_safety_preview_uses_same_lexicon():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as c:
        h=[]
        for t in ['I am dizzy']+['not sure']*4:
            body=c.post('/ui/triage',json=request(t,h).model_dump()).json()
            r=body['response'];u=body['ui'];h.append({'role':'user','text':t})
            if r['follow_up_question']:h.append({'role':'assistant','text':r['follow_up_question'],'question_id':u['question_id']})
        assert u['assessment_status']=='needs_human_assessment'
        assert set(r)=={'follow_up_question','care_type','urgency','red_flags','reasoning','matched_caregivers'}
        assert c.post('/ui/safety',json=request('dam ghut raha hai').model_dump()).json()['emergency_warning']
        assert not c.post('/ui/safety',json=request('dam nahi ghut raha hai').model_dump()).json()['emergency_warning']

def test_explicit_fever_facts_skip_supplied_safety_questions():
    h=[];r,u=turn(h,'I have fever, age 25 years old, no difficulty breathing')
    assert u['question_id']=='fever_high'

@pytest.mark.parametrize('failure',[ProviderError('rate_limit'),ProviderError('ungrounded_text_output'),asyncio.TimeoutError()])
def test_ui_provider_failure_completes_ear_interview(failure,monkeypatch):
    from fastapi.testclient import TestClient
    from backend.app import main
    original=main.assess
    async def broken(req,providers=None,mode=None):
        if mode!='rules':raise failure
        return await original(req,mode='rules')
    monkeypatch.setattr(main,'assess',broken)
    with TestClient(main.app) as c:
        h=[];questions=[]
        for t in ['कान में दर्द है','mild','loss nhi hai sirf dard hai','No','5 days']:
            response=c.post('/ui/triage',json=request(t,h,'hi').model_dump())
            assert response.status_code==200
            body=response.json();r=body['response'];u=body['ui']
            h.append({'role':'user','text':t})
            if r['follow_up_question']:
                questions.append(u['question_id'])
                h.append({'role':'assistant','text':r['follow_up_question'],'question_id':u['question_id']})
            else:break
        assert len(questions)<=4 and not r['follow_up_question']
        assert r['care_type']=='teleconsultation' and not r['matched_caregivers']
        assert u['assessment_status']=='needs_human_assessment'
        assert u['provider_status']=='unavailable' and u['engine']=='rules_fallback'

def test_successful_ear_interview_always_reaches_a_conclusion():
    h=[]
    for t in ['कान में दर्द है','mild','No','No','5 days']:r,u=turn(h,t)
    assert r.follow_up_question is None and r.care_type=='teleconsultation'
    assert u['assessment_status']=='care_pathway'
    assert u['state']['facts']['duration_days']==5

@pytest.mark.parametrize('reply',['yeah','ji','जी','nope','नही'])
def test_model_short_answers_cannot_invent_unrelated_flags(reply):
    class Stub:
        text_key='stub'
        async def extract(self,req):return Extraction(flags=[FlagEvidence(flag='breathlessness',status='affirmed',quote=reply)],evidence=[reply])
    h=[];turn(h,'My knee hurts')
    r,u=run(reply,h,provider=Stub(),mode='live')
    assert 'breathlessness' not in r.red_flags
