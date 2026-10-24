"""Synthetic conversation regressions; not clinical validation."""
import asyncio
import pytest
from tests.test_broad_intake import run,turn,request
from backend.app.core import assess
from backend.app.schemas import Extraction
from backend.app.intake import extract_local


@pytest.mark.parametrize('text,site',[
    ('I have pain in my knee','knee'),('My right knee hurts','knee'),
    ('There is an ache in my left knee','knee'),('Pain in knee','knee'),
    ('Mere ghutne mein dard hai','knee'),('मेरे घुटने में दर्द है','knee'),
    ('My ankles hurt','ankle'),('I have pain in my wrist','wrist'),
    ('My left shoulder aches','shoulder'),('I have pain in my hip','hip'),
    ('My elbow hurts','elbow'),('My foot hurts','foot'),
])
def test_anatomical_wording_selects_localised_questions(text,site):
    r,u=run(text)
    assert u['state']['facts']['complaint']=='joint_pain'
    assert u['state']['facts']['body_site']==site
    assert u['question_id']==site+'_severity'
    assert site in r.follow_up_question


def test_full_knee_flow_has_no_unrelated_breathing_question():
    h=[];questions=[]
    for text in ['I have pain in my knee','moderate','no','no','yes','yes','two days']:
        r,u=turn(h,text)
        if u['question_id']:questions.append(u['question_id'])
        assert 'breath' not in (r.follow_up_question or '').lower()
    assert questions==['knee_severity','knee_injury','knee_swelling','knee_weight','knee_movement','symptom_duration']
    assert r.care_type=='teleconsultation' and r.matched_caregivers
    assert u['state']['facts']['duration_days']==2
    assert len(questions)==len(set(questions))


def test_swelling_selects_relevant_hot_red_branch():
    h=[]
    for t in ['I have knee pain','mild','no']:
        r,u=turn(h,t)
    assert u['question_id']=='knee_swelling'
    r,u=turn(h,'yes')
    assert u['question_id']=='knee_hot_red'
    hot,_=run('yes',h);not_hot,u=run('no',h)
    assert hot.urgency=='same_day' and not hot.matched_caregivers
    assert 'prompt in-person' in hot.reasoning
    assert u['question_id']=='knee_weight' and not_hot.follow_up_question


@pytest.mark.parametrize('text',[
    'I have severe knee pain','My knee hurts and I cannot walk',
    'My knee hurts and I cannot bend it','My knee hurts and is locked',
    'My knee hurts and looks crooked','My knee hurts and my foot is numb',
    'My knee hurts and is hot and swollen','My knee hurts and I have fever',
    'I have pain in my wrist and cannot move it',
    'My knee hurts and is badly swollen',
])
def test_joint_warning_signs_get_prompt_assessment_without_routine_booking(text):
    r,u=run(text)
    assert r.care_type=='teleconsultation' and r.urgency=='same_day'
    assert not r.matched_caregivers and r.follow_up_question is None
    assert 'prompt in-person' in r.reasoning
    assert not r.red_flags  # Joint concern alone is not an invented ambulance flag.


def test_given_answers_skip_questions_including_natural_language_function():
    r,u=run('Mild knee pain for two days, no injury, no swelling; I can walk and bend my knee')
    assert r.follow_up_question is None and r.matched_caregivers
    f=u['state']['facts']
    assert f['severity']=='mild' and f['duration_days']==2
    known={v['name']:v['status'] for v in f['clinical_features']}
    assert all(known[k]=='denied' for k in ['recent_injury','joint_swelling','cannot_bear_weight','cannot_move_joint'])


def test_upper_limb_never_gets_lower_limb_function_question():
    h=[];questions=[]
    for t in ['My wrist hurts','mild','no','no','yes','two days']:
        r,u=turn(h,t)
        if r.follow_up_question:questions.append(r.follow_up_question)
    assert r.follow_up_question is None
    assert any('move your wrist' in q for q in questions)
    assert not any('weight' in q or 'stand' in q or 'breath' in q for q in questions)


def test_unknown_mobility_answers_do_not_enable_routine_booking():
    h=[]
    for t in ['I have knee pain']+['not sure']*6:
        r,u=turn(h,t)
    assert r.follow_up_question is None and not r.matched_caregivers
    assert 'unknown' in r.reasoning
    assert 'cannot_bear_weight' not in {v['name'] for v in u['state']['facts']['clinical_features']}


@pytest.mark.parametrize('text',[
    'No knee swelling or injury; mild knee pain',
    'My knee is not swollen; mild knee pain',
    'Last year my knee was hot and swollen, now resolved',
    'What if my knee is hot and swollen?',
])
def test_negation_history_and_hypothetical_do_not_trigger_joint_concern(text):
    r,u=run(text)
    assert u['concern'] is None and r.care_type!='emergency_112'


def test_unknown_joint_location_is_clarified_then_used():
    h=[];r,u=turn(h,'My joints ache')
    assert u['question_id']=='joint_site'
    r,u=turn(h,'right knee')
    assert u['question_id']=='knee_severity'


def test_hindi_knee_flow_and_contextual_reversed_answers():
    h=[]
    for text in ['मेरे घुटने में दर्द है','हल्का','नहीं','नहीं']:
        r,u=turn(h,text,language='hi')
    assert u['question_id']=='knee_weight' and 'पैर' in r.follow_up_question
    r,u=run('नहीं',h,language='hi')
    assert r.urgency=='same_day' and not r.matched_caregivers
    assert 'weight' in r.reasoning


def test_late_breathlessness_is_still_an_emergency_after_knee_questions():
    h=[]
    for text in ['I have pain in my knee','mild','no']:
        turn(h,text)
    r,_=run('Now I cannot breathe',h)
    assert r.care_type=='emergency_112' and r.red_flags==['breathlessness']
    assert not r.follow_up_question and not r.matched_caregivers


def test_no_answer_to_injury_does_not_become_breathlessness():
    h=[];turn(h,'I have knee pain');turn(h,'mild')
    r,u=run('no',h)
    assert u['question_id']=='knee_swelling'
    assert not u['state']['warning_signs']


def test_model_cannot_turn_answer_to_knee_question_into_breathlessness():
    from backend.app.schemas import FlagEvidence
    h=[];turn(h,'I have knee pain');turn(h,'mild')
    class Stub:
        text_key='synthetic'
        async def extract(self,r):
            return Extraction(flags=[FlagEvidence(flag='breathlessness',status='affirmed',quote='yes')],evidence=['yes'])
    r,u=asyncio.run(assess(request('yes',h),Stub(),mode='live'))
    assert r.care_type!='emergency_112' and u['question_id']=='knee_swelling'


def test_other_body_swelling_is_not_knee_swelling():
    x=extract_local('My knee hurts, and my cheek is swollen')
    assert 'joint_swelling' not in {v.name for v in x.clinical_features}


@pytest.mark.parametrize('text',[
    'I have stomach ache','I have a headache','I have been vomiting',
    'I have diarrhoea','I have a sore throat','It burns when I pee',
    'My back aches','I have knee pain','I have a rash','I am dizzy',
    'I have an ankle injury','I have eye pain','My ear aches',
    'I have toothache','I feel unusually tired',
])
def test_nonrespiratory_pathways_do_not_fall_back_to_breathing(text):
    h=[]
    for message in [text]+['not sure']*6:
        r,u=turn(h,message)
        assert u['question_id']!='breathing'
        if not r.follow_up_question:break


@pytest.mark.parametrize('text,question',[
    ('My ear aches','ear_discharge'),
    ('My ear aches, no ear discharge','hearing_change'),
    ('I have toothache, no tongue swelling','dental_swelling'),
])
def test_other_families_get_specific_followups(text,question):
    r,u=run(text);assert u['question_id']==question


@pytest.mark.parametrize('text',[
    'My ear aches and fluid is coming out of my ear',
    'My ear aches and I have reduced hearing',
    'My tooth aches and my cheek is swollen',
])
def test_new_ear_and_dental_findings_get_assessment(text):
    r,u=run(text)
    assert r.urgency=='same_day' and not r.matched_caregivers
    assert u['concern']


def test_model_fills_site_without_changing_question_policy():
    text='I have a painful patella'
    class Stub:
        text_key='synthetic'
        async def extract(self,r):
            return Extraction(complaint='joint_pain',body_site='knee',complaint_text=text,evidence=[text])
    r,u=asyncio.run(assess(request(text),Stub(),mode='live'))
    assert u['question_id']=='knee_severity' and 'knee' in r.follow_up_question


def test_twisted_knee_is_recognised_as_injury():
    x=extract_local('I twisted my knee')
    assert x.complaint=='injury' and x.body_site=='knee'


@pytest.mark.parametrize('text,complaint,question',[
    ('I have pain in my ear','ear_pain','ear_discharge'),
    ('I have pain in my eye','eye_problem','vision_loss'),
    ('I have pain in my tooth','dental_pain','airway_swelling'),
    ('I have pain in my throat','sore_throat','swallow_saliva'),
])
def test_pain_in_body_part_wording_does_not_fall_back_to_generic_menu(text,complaint,question):
    r,u=run(text)
    assert u['state']['facts']['complaint']==complaint and u['question_id']==question
