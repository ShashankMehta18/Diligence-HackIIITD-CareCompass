"""Complaint-specific follow-ups and specialty-aware matching, grounded in the
expanded roster (data/caregivers.csv: 100 caregivers, 40 specialist doctors
with supported_complaints). Each complaint must ask its own questions and
match doctors who actually support it, not any GP on the roster.
"""
import asyncio
import pytest
from backend.app.core import assess
from backend.app.schemas import Request
from backend.app.matching import ROSTER

BY_ID = {c['caregiver_id']: c for c in ROSTER}

def request(text, history=(), language='en'):
    return Request(user_input=text, language=language, location={'lat': 28.54, 'lng': 77.27},
                   conversation_history=list(history))

def run(text, history=(), language='en'):
    return asyncio.run(assess(request(text, history, language), mode='rules'))

def turn(history, text, language='en'):
    response, ui = run(text, history, language)
    history.append({'role': 'user', 'text': text})
    if response.follow_up_question:
        history.append({'role': 'assistant', 'text': response.follow_up_question,
                        'question_id': ui['question_id']})
    return response, ui

def drive(first, answers, language='en'):
    h = []
    r, u = run(first, h, language)
    first_q = u['question_id']
    h.append({'role': 'user', 'text': first})
    if r.follow_up_question:
        h.append({'role': 'assistant', 'text': r.follow_up_question,
                  'question_id': u['question_id']})
    for a in answers:
        r, u = turn(h, a, language)
    return r, u, first_q

def matched_doctors(r):
    return [BY_ID[m.caregiver_id] for m in r.matched_caregivers]

def supports(cg, *keys):
    return bool(set(cg.get('supported_complaints') or []) & set(keys))

@pytest.mark.parametrize('text,family,first_q', [
    ('I have knee pain', 'knee_pain', 'joint_swelling'),
    ('ghutne mein dard hai', 'knee_pain', 'joint_swelling'),
    ('my ankle hurts', 'ankle_pain', 'joint_swelling'),
    ('my shoulder hurts', 'shoulder_pain', 'lifting_arm'),
    ('my neck hurts', 'neck_pain', 'joint_stiffness'),
    ('my wrist hurts', 'wrist_pain', 'joint_swelling'),
    ('my elbow hurts', 'elbow_pain', 'joint_swelling'),
    ('my hip hurts', 'hip_pain', 'bear_weight'),
    ('my foot hurts', 'foot_pain', 'joint_swelling'),
    ('I have a wound on my hand', 'wound', 'wound_leaking'),
    ('I have diabetes', 'diabetes', 'sugar_check'),
    ('catheter is leaking', 'catheter', 'catheter_block'),
    ('need nebulization at home', 'nebulization', 'breathing'),
    ('post surgery care at home', 'post_surgical', 'postop_redness'),
    ('elderly care for my grandmother at home', 'elderly_care', 'daily_care'),
    ('I have a migraine', 'headache', 'headache_sudden'),
])
def test_complaint_specific_first_question(text, family, first_q):
    r, u = run(text)
    assert u['state']['facts']['complaint'] == family
    assert u['question_id'] == first_q
    assert r.follow_up_question and r.care_type is None

def test_knee_pain_matches_orthopedics_not_generalists():
    r, _, _ = drive('I have knee pain', ['no', 'no', 'no', 'two days'])
    assert r.care_type == 'teleconsultation'
    docs = matched_doctors(r)
    assert docs and all(supports(d, 'knee_pain', 'joint_pain') for d in docs)
    assert any(d['specialty'] == 'Orthopedics' for d in docs)
    assert not any('placeholder' in (d['specialty'] or '') for d in docs)

def test_ankle_pain_asks_weight_bearing():
    h = []
    r, u = turn(h, 'my ankle hurts')
    assert u['question_id'] == 'joint_swelling'
    r, u = turn(h, 'no')
    assert u['question_id'] == 'bear_weight'
    r, u = turn(h, 'yes')
    assert u['question_id'] == 'joint_injury'

def test_fever_asks_fever_questions_not_just_demographics():
    r, u, first_q = drive('I have a fever', ['25 years old', 'no', 'no', 'yes'])
    assert first_q == 'age'
    assert r.care_type == 'teleconsultation'
    asked = u['state']['asked_question_ids']
    assert 'fever_high' in asked and 'fluids_normal' in asked
    docs = matched_doctors(r)
    assert docs and all(supports(d, 'fever', 'persistent_fever', 'general_symptoms') for d in docs)
    assert not any(d['specialty'] == 'Pediatrics' for d in docs)

def test_child_fever_can_match_pediatrics():
    r, u, _ = drive('My 5 year old child has fever', ['no', 'no', 'yes', 'two days'])
    assert r.care_type == 'teleconsultation'
    assert any(d['specialty'] == 'Pediatrics' for d in matched_doctors(r))

def test_diabetes_sugar_check_routes_to_paramedic():
    r, _, _ = drive('I have diabetes', ['yes'])
    assert r.care_type == 'paramedic_home_visit'
    assert all('bp_sugar_check' in BY_ID[m.caregiver_id]['skills'] for m in r.matched_caregivers)

def test_diabetes_without_sugar_check_gets_foot_question():
    r, u, _ = drive('I have diabetes', ['no'])
    assert u['question_id'] == 'foot_sore'

def test_wound_symptom_gets_wound_questions_and_medic():
    r, _, _ = drive('I have a wound on my hand', ['no', 'no', 'two days'])
    assert r.care_type == 'home_nursing'
    assert r.matched_caregivers
    assert all('wound_dressing' in BY_ID[m.caregiver_id]['skills'] for m in r.matched_caregivers)

def test_migraine_matches_neurology():
    r, _, _ = drive('I have a migraine', ['no', 'no', 'mild', 'two days'])
    assert r.care_type == 'teleconsultation'
    docs = matched_doctors(r)
    assert docs and all(supports(d, 'headache', 'migraine') for d in docs)
    assert any(d['specialty'] == 'Neurology' for d in docs)

def test_complaint_without_specialist_falls_back_to_generalists():
    r, _, _ = drive('I have been vomiting', ['no', 'yes', 'two days', '25 years old'])
    assert r.care_type == 'teleconsultation'
    docs = matched_doctors(r)
    assert docs and all(supports(d, 'general_symptoms', 'initial_assessment') for d in docs)

def test_unknown_complaint_gets_no_routine_booking():
    # Pre-existing honest design: an unclassified complaint is never
    # "complete enough", so no routine booking is offered.
    r, _, _ = drive('I have an unfamiliar fluttering sensation', ['mild', 'two days', 'same'])
    assert r.care_type == 'teleconsultation'
    assert not r.matched_caregivers
    assert 'human clinical assessment' in r.reasoning

def test_catheter_nebulization_post_surgical_elderly_match_medics():
    cases = [
        ('catheter is leaking', ['yes', 'no', 'two days'], 'catheter_care'),
        ('need nebulization at home', ['no', 'yes', 'two days'], 'nebulization'),
        ('post surgery care at home', ['no', 'no', 'two days'], 'post_surgical_care'),
        ('elderly care for my grandmother at home', ['yes', 'yes', 'two days'], 'elderly_care'),
    ]
    for text, answers, skill in cases:
        r, _, _ = drive(text, answers)
        assert r.care_type == 'home_nursing', text
        assert r.matched_caregivers, text
        assert all(skill in BY_ID[m.caregiver_id]['skills'] for m in r.matched_caregivers), text

def test_generic_joint_pain_keeps_severity_first():
    r, u = run('My joints ache')
    assert u['state']['facts']['complaint'] == 'joint_pain'
    assert u['question_id'] == 'symptom_severity'
