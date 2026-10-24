"""Symptom-mapping database coverage (data/symptom_mapping.csv, 177 rows):
new complaint families from the mapping must ask their own questions and
route to the mapping's specialist (or the closest roster specialty).
"""
import asyncio
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

def matched(r):
    return [BY_ID[m.caregiver_id] for m in r.matched_caregivers]

def supports(cg, *keys):
    return bool(set(cg.get('supported_complaints') or []) & set(keys))

def test_hand_finger_pain_routes_to_orthopedics():
    r, u, first_q = drive('my finger hurts', ['no', 'no', 'no', 'two days'])
    assert u['state']['facts']['complaint'] == 'hand_pain'
    assert first_q == 'joint_swelling'
    assert r.care_type == 'teleconsultation'
    docs = matched(r)
    assert docs and all(supports(d, 'joint_pain', 'muscle_pain') for d in docs)

def test_muscle_and_calf_pain_routes_to_sports_medicine():
    r, u, _ = drive('I have muscle pain in my calf', ['mild', 'no', 'three days'])
    assert u['state']['facts']['complaint'] == 'muscle_pain'
    assert r.care_type == 'teleconsultation'
    docs = matched(r)
    assert docs and all(supports(d, 'muscle_pain', 'sports_injury') for d in docs)

def test_nasal_congestion_routes_to_ent():
    r, u, _ = drive('I have nasal congestion', ['mild', 'no', 'two days'])
    assert u['state']['facts']['complaint'] == 'nasal'
    assert r.care_type == 'teleconsultation'
    docs = matched(r)
    assert docs and all(supports(d, 'sinus_symptoms', 'nose_problem', 'allergy_concern') for d in docs)

def test_palpitations_route_to_cardiology():
    r, u, _ = drive('my heart is racing and I feel palpitations', ['mild', 'two days'])
    assert u['state']['facts']['complaint'] == 'cardiac'
    assert r.care_type == 'teleconsultation'
    docs = matched(r)
    assert docs and all(supports(d, 'palpitations', 'blood_pressure', 'heart_concern') for d in docs)

def test_numbness_routes_to_neurology():
    r, u, _ = drive('my fingers feel numb and tingling', ['mild', 'two days'])
    assert u['state']['facts']['complaint'] == 'neuro'
    assert r.care_type == 'teleconsultation'
    docs = matched(r)
    assert docs and all(supports(d, 'numbness', 'tremor', 'dizziness') for d in docs)

def test_kidney_thyroid_nutrition_blood_route_to_specialists():
    cases = [
        ('I have kidney disease', 'kidney', ('kidney_problem', 'chronic_kidney_concern', 'urinary_related_kidney_concern')),
        ('I have thyroid problems', 'thyroid', ('thyroid_problem', 'hormonal_concern')),
        ('I have unexplained weight loss', 'nutrition', ('nutrition_concern', 'weight_change', 'diet_planning')),
        ('I have unusual bruising', 'blood', ('blood_disorder_concern',)),
    ]
    for text, family, keys in cases:
        r, u, _ = drive(text, ['mild', 'two days'])
        assert u['state']['facts']['complaint'] == family, text
        assert r.care_type == 'teleconsultation', text
        docs = matched(r)
        assert docs and all(supports(d, *keys) for d in docs), text

def test_coughing_blood_blocks_routine_booking():
    r, u, _ = drive('I am coughing', ['no', 'yes'])
    assert u['state']['asked_question_ids'][1] == 'blood_cough'
    assert r.care_type == 'teleconsultation'
    assert not r.matched_caregivers
    assert 'prompt' in r.reasoning.lower()

def test_sudden_hearing_loss_blocks_routine_booking():
    r, u, _ = drive('my hearing has suddenly become weak', ['mild', 'yes'])
    assert r.care_type == 'teleconsultation'
    assert not r.matched_caregivers
    assert 'urgent' in r.reasoning.lower()

def test_extended_skin_eye_ear_dental_throat_patterns():
    cases = [
        ('I have hair loss', 'rash'),
        ('I have a stye on my eyelid', 'eye_problem'),
        ('my ears are ringing', 'ear_pain'),
        ('I have a cavity in my tooth', 'dental_pain'),
        ('my voice is hoarse', 'sore_throat'),
        ('I feel nauseous', 'vomiting'),
        ('I have bloating and gas', 'abdominal_pain'),
    ]
    for text, family in cases:
        r, u = run(text)
        assert u['state']['facts']['complaint'] == family, text
        assert r.follow_up_question, text
