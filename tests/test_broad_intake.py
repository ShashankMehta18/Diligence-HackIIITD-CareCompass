"""Independently phrased behavioural challenges, separate from organiser rows.
Passing these finite cases is not a claim of clinical validation.
"""
import asyncio
import pytest
from backend.app.core import assess
from backend.app.schemas import Request,Extraction,ClinicalFinding
from backend.app.intake import replay,extract_local
from backend.app.providers import ProviderError

def request(text,history=(),language='en'):
    return Request(user_input=text,language=language,location={'lat':28.54,'lng':77.27},conversation_history=list(history))

def run(text,history=(),language='en'):
    return asyncio.run(assess(request(text,history,language),mode='rules'))

def turn(history,text,language='en'):
    response,ui=run(text,history,language)
    history.append({'role':'user','text':text})
    if response.follow_up_question:
        history.append({'role':'assistant','text':response.follow_up_question,'question_id':ui['question_id']})
    return response,ui

@pytest.mark.parametrize('text,complaint,question',[
 ('I have stomach ache','abdominal_pain','abdominal_severity'),
 ('My belly hurts','abdominal_pain','abdominal_severity'),
 ('Mujhe pet mein dard hai','abdominal_pain','abdominal_severity'),
 ('मुझे पेट में दर्द है','abdominal_pain','abdominal_severity'),
 ('I have a headache','headache','headache_sudden'),
 ('Mujhe sir mein dard hai','headache','headache_sudden'),
 ('सिर में दर्द है','headache','headache_sudden'),
 ('I have been vomiting','vomiting','blood_vomit'),
 ('मुझे उल्टी हो रही है','vomiting','blood_vomit'),
 ('I have loose motions','diarrhoea','keep_fluids'),
 ('मुझे दस्त हैं','diarrhoea','keep_fluids'),
 ('I am coughing','cough','breathing'),
 ('गले में खराश है','sore_throat','swallow_saliva'),
 ('It burns when I pee','urinary','urine_retention'),
 ('पेशाब में जलन है','urinary','urine_retention'),
 ('My back aches','back_pain','bladder_change'),
 ('कमर में दर्द है','back_pain','bladder_change'),
 ('My joints ache','joint_pain','symptom_severity'),
 ('I have an itchy rash','rash','airway_swelling'),
 ('मुझे चक्कर आते हैं','dizziness','one_sided_weakness'),
 ('I have an ankle injury','injury','symptom_severity'),
 ('I have eye pain','eye_problem','vision_loss'),
 ('My ear aches','ear_pain','symptom_severity'),
 ('I have toothache','dental_pain','airway_swelling'),
 ('I feel unusually tired','fatigue','symptom_severity'),
 ('I have an unfamiliar fluttering sensation','other','symptom_severity'),
])
def test_complaint_relevant_first_question(text,complaint,question):
    r,u=run(text)
    assert u['state']['facts']['complaint']==complaint
    assert u['question_id']==question
    assert r.follow_up_question and r.care_type is None and not r.matched_caregivers
    assert 'What help is needed' not in r.follow_up_question

def test_stomach_conversation_retains_answers_and_stops_at_four():
    h=[];questions=[]
    for message in ['I have stomach ache','mild','no','two days','lower left']:
        r,u=turn(h,message)
        if u['question_id']:questions.append(u['question_id'])
    assert questions==['abdominal_severity','abdominal_touch','symptom_duration','abdominal_location']
    assert len(questions)==len(set(questions))==4
    assert r.care_type=='teleconsultation' and r.urgency=='same_day'
    assert u['state']['facts']['duration_days']==2
    assert u['state']['facts']['pain_location']=='lower left'
    assert 'stomach pain' in r.reasoning and 'unclear' not in r.reasoning

def test_supplied_context_not_asked_again():
    r,u=run('Mild stomach pain in lower left for three days')
    assert u['question_id']=='abdominal_touch'
    assert u['state']['facts']['duration_days']==3
    h=[{'role':'user','text':'Mild stomach pain in lower left for three days'},{'role':'assistant','text':r.follow_up_question}]
    r,u=run('no',h)
    assert r.follow_up_question is None

@pytest.mark.parametrize('text,reason',[
 ('I suddenly developed severe stomach pain','Sudden severe abdominal pain'),
 ('My stomach hurts when I touch it','Abdominal pain on touch'),
 ('I am vomiting blood','Blood in vomit'),
 ('My stool is black and sticky','Black, sticky stool'),
 ('I suddenly got the worst headache of my life','Sudden extremely painful headache'),
 ('My tongue is swelling','Tongue or throat swelling'),
 ('I cannot swallow my saliva','Unable to swallow saliva'),
 ('I have back pain and new loss of bladder control','New bladder-control change'),
 ('I have back pain and numbness around my groin','Groin numbness'),
 ('I have lost my vision','Loss of vision'),
 ('My father suddenly became confused','New sudden confusion'),
 ('I have urinary pain and cannot pass any urine','Unable to pass urine'),
 ('My headache came on suddenly and is severe','Sudden extremely painful headache'),
 ('Sudden eye pain','Sudden-onset eye symptoms'),
 ('Pet ko chune par dard hota hai','Abdominal pain on touch'),
 ('Meri jeebh me sujan hai','Tongue or throat swelling'),
])
def test_extended_safety_without_fake_controlled_flags(text,reason):
    r,u=run(text)
    assert r.care_type=='emergency_112' and r.urgency=='emergency'
    assert r.follow_up_question is None and not r.matched_caregivers
    assert reason in r.reasoning
    assert r.red_flags==[]  # No controlled-vocabulary equivalent is fabricated.
    assert u['emergency_evidence']

@pytest.mark.parametrize('text',[
 'No vomiting blood; mild stomach ache',
 'No sudden worst headache; I have a mild headache',
 'What if someone has sudden severe stomach pain?',
 'Last year I had sudden severe stomach pain, now resolved',
 'This quoted example says my tongue is swelling',
 'My tongue is not swelling',
 'I have not been vomiting blood; mild stomach ache',
])
def test_extended_safety_negation_history_hypothetical(text):
    r,_=run(text);assert r.care_type!='emergency_112'

def test_yes_and_no_have_different_safety_effects():
    h=[];r,u=turn(h,'I have stomach ache');r,u=turn(h,'mild')
    assert u['question_id']=='abdominal_touch'
    positive,_=run('yes',h);negative,u=run('no',h)
    assert positive.care_type=='emergency_112'
    assert negative.care_type is None and u['question_id']=='symptom_duration'

def test_severe_pain_concern_is_immediate_then_sudden_answer_branches():
    h=[];r,u=turn(h,'I have severe stomach pain')
    assert 'prompt in-person' in r.reasoning and u['question_id']=='sudden_pain'
    yes,_=run('yes',h);no,_=run('no',h)
    assert yes.care_type=='emergency_112'
    assert no.care_type=='teleconsultation' and no.urgency=='same_day'
    assert not no.matched_caregivers and 'prompt in-person' in no.reasoning

def test_reverse_polarity_swallow_and_hydration():
    h=[];r,u=turn(h,'I have a sore throat');assert u['question_id']=='swallow_saliva'
    yes,_=run('yes',h);no,_=run('no',h)
    assert yes.care_type!='emergency_112' and no.care_type=='emergency_112'
    h=[];turn(h,'I have diarrhoea')
    r,u=run('no',h)
    assert r.urgency=='same_day' and not r.red_flags and not r.matched_caregivers
    assert 'keep fluids down' in r.reasoning

def test_limb_injury_weight_bearing_changes_pathway():
    h=[];turn(h,'I have an ankle injury');r,u=turn(h,'mild')
    assert u['question_id']=='bear_weight'
    r,u=run('no',h)
    assert r.urgency=='same_day' and not r.matched_caregivers
    assert 'weight bearing' in r.reasoning

def test_hindi_answers_and_hours():
    h=[];r,u=turn(h,'मुझे पेट में दर्द है',language='hi')
    assert 'पेट' in r.follow_up_question and u['answer_choices_hi']
    r,u=turn(h,'हल्का',language='hi');assert u['question_id']=='abdominal_touch'
    r,u=turn(h,'नहीं',language='hi');assert u['question_id']=='symptom_duration'
    r,u=turn(h,'दो घंटे',language='hi')
    assert u['state']['facts']['duration_days']==pytest.approx(2/24)

def test_duration_correction_associated_symptoms_and_no_diagnosis():
    h=[];turn(h,'I have mild stomach pain for three days');turn(h,'no')
    r,u=run('Correction: ten days, lower left, also nausea',h)
    assert u['state']['facts']['duration_days']==10
    assert 'dengue' not in r.reasoning and 'platelet' not in r.reasoning

def test_unknown_answers_never_count_as_negative_safety_screen():
    h=[]
    for text in ['I have stomach ache','not sure','not sure','not sure','not sure']:
        r,u=turn(h,text)
    assert r.follow_up_question is None
    assert 'unknown' in r.reasoning and not r.matched_caregivers

def test_emergency_later_and_correction():
    h=[];turn(h,'I have a mild headache');turn(h,'no')
    r,u=run('Now I am vomiting blood',h)
    assert r.care_type=='emergency_112'
    corrected=[{'role':'user','text':'I am vomiting blood'}]
    r,_=run('Transcription correction: no vomiting blood, I have mild stomach pain',corrected)
    assert r.care_type!='emergency_112'

def test_associated_complaint_emergency_is_never_hidden_by_primary():
    h=[{'role':'user','text':'I have fever for two days'}]
    r,_=run('Now I have sudden severe stomach pain',h)
    assert r.care_type=='emergency_112'
    r,_=run('My stomach hurts when I touch it',h)
    assert r.care_type=='emergency_112'

def test_associated_symptom_duration_is_not_transferred_to_main_complaint():
    h=[{'role':'user','text':'I have fever for ten days'}]
    state=replay(request('Now headache for two hours',h))
    assert state.facts.duration_days==10

def test_patient_change_resets_previous_broad_symptom_and_danger():
    h=[{'role':'user','text':'My father has sudden severe stomach pain'}]
    r,u=run('For my mother, mild ear pain',h)
    assert r.care_type!='emergency_112'
    assert u['state']['facts']['complaint']=='ear_pain'
    assert not u['emergency_evidence']

def test_known_service_request_does_not_get_generic_interview():
    r,u=run('Need prescribed wound dressing at home')
    assert r.care_type=='home_nursing' and r.follow_up_question is None

def test_extended_emergency_bypasses_provider_absence():
    r,_=asyncio.run(assess(request('I suddenly developed severe stomach pain')))
    assert r.care_type=='emergency_112'

def test_novel_wording_without_provider_gets_general_interview():
    # No text model: unfamiliar wording stays 'other' and gets the general
    # clarification interview instead of a model-filled complaint.
    r,u=asyncio.run(assess(request('I feel strange knots in my belly')))
    assert u['engine']=='rules_baseline' and r.follow_up_question is not None

def test_other_category_stays_other_without_provider():
    text='I have an abdominal discomfort'
    assert extract_local(text).complaint=='other'
    r,u=asyncio.run(assess(request(text)))
    assert u['engine']=='rules_baseline' and r.follow_up_question is not None

def test_local_denial_never_forces_routine_booking():
    r,u=asyncio.run(assess(request('No vomiting blood; I have stomach ache')))
    assert r.care_type is None and u['question_id']=='abdominal_severity'

def test_safety_preview_uses_same_rules_and_updates_corrections():
    from fastapi.testclient import TestClient
    from backend.app.main import app
    with TestClient(app) as c:
        assert c.post('/ui/safety',json=request('I am vomiting blood').model_dump()).json()['emergency_warning']
        assert not c.post('/ui/safety',json=request('No vomiting blood; mild stomach ache').model_dump()).json()['emergency_warning']

