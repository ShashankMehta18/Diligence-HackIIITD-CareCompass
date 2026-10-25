"""300-caregiver roster upgrade (data/caregivers.csv): the roster is a strict
superset of the old 100 (first 100 rows identical), and the new granular keys
route each complaint to the right new specialists. Pediatrics doctors support
only child_* keys, so they can never appear in an adult pool.
"""
import asyncio
from backend.app.core import assess
from backend.app.schemas import Request
from backend.app.matching import ROSTER, match
from backend.app.complaints import FAMILY_KEYS, CHILD_KEYS

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
    h.append({'role': 'user', 'text': first})
    if r.follow_up_question:
        h.append({'role': 'assistant', 'text': r.follow_up_question,
                  'question_id': u['question_id']})
    for a in answers:
        r, u = turn(h, a, language)
    return r, u

def direct(keys):
    req = Request(user_input='x', language='en', location={'lat': 28.54, 'lng': 77.27})
    return match(req, 'teleconsultation', 'doctor', 'en', complaint_keys=set(keys))

def supports(cg, *keys):
    return bool(set(cg.get('supported_complaints') or []) & set(keys))

def test_roster_is_300_superset():
    assert len(ROSTER) == 300
    assert sum(1 for r in ROSTER if r['active']) == 287
    assert [r['caregiver_id'] for r in ROSTER[:100]] == [f'CG_{i:03d}' for i in range(1, 101)]
    doctors = [r for r in ROSTER if r['role'] == 'doctor']
    assert len(doctors) == 218
    assert all(r['specialty'] and r['supported_complaints'] for r in doctors)
    assert len({r['caregiver_id'] for r in ROSTER}) == 300
    assert any(r['specialty'] == 'Oncology' for r in doctors)
    assert any(r['specialty'] == 'Diabetology' for r in doctors)
    assert any(r['specialty'] == 'Psychology and Counselling' for r in doctors)
    assert any(r['specialty'] == 'Wound Care and Dressing' for r in ROSTER if r['role'] == 'medic')

def test_child_keys_live_in_family_key_sets():
    assert 'child_cough' in FAMILY_KEYS['cough']
    assert 'child_rash' in FAMILY_KEYS['rash']
    assert 'child_nutrition' in FAMILY_KEYS['nutrition']
    assert 'child_digestive_problem' in FAMILY_KEYS['abdominal_pain']
    assert 'child_digestive_problem' in FAMILY_KEYS['vomiting']
    assert 'child_digestive_problem' in FAMILY_KEYS['diarrhoea']
    assert 'child_general_symptoms' in FAMILY_KEYS['fatigue']
    assert CHILD_KEYS >= {'child_fever', 'child_cough', 'child_general_symptoms', 'child_digestive_problem',
                          'child_rash', 'child_nutrition', 'child_growth_concern',
                          'vaccination_followup', 'pediatric_followup'}

def test_body_part_keys_route_to_orthopedics():
    for key in ('ankle_pain', 'elbow_pain'):
        _, cards = direct({key})
        assert cards, key
        assert all(supports(BY_ID[c['caregiver_id']], key) for c in cards), key
        assert {c['specialty'] for c in cards} == {'Orthopedics'}, key

def test_diabetes_routes_to_diabetology_or_endocrinology():
    _, cards = direct({'diabetes'})
    assert cards
    assert all(supports(BY_ID[c['caregiver_id']], 'diabetes') for c in cards)
    assert {c['specialty'] for c in cards} <= {'Diabetology', 'Endocrinology'}

def test_menstrual_irregular_routes_to_gynobs():
    _, cards = direct({'irregular_periods'})
    assert cards
    assert all(supports(BY_ID[c['caregiver_id']], 'irregular_periods') for c in cards)
    assert {c['specialty'] for c in cards} == {'Gynecology and Obstetrics'}

def test_child_keys_route_to_pediatrics_only():
    for key in ('child_cough', 'child_rash', 'child_nutrition'):
        _, cards = direct({key})
        assert cards, key
        assert all(supports(BY_ID[c['caregiver_id']], key) for c in cards), key
        assert {c['specialty'] for c in cards} == {'Pediatrics'}, key

def test_adult_rash_and_cough_exclude_pediatrics():
    # Pediatrics doctors support only child_* keys, so no adult pool can
    # contain them regardless of ranking.
    r, _ = drive('I have a rash', ['no', 'no', 'two days'])
    assert r.care_type == 'teleconsultation'
    assert r.matched_caregivers
    assert all(BY_ID[m.caregiver_id]['specialty'] != 'Pediatrics' for m in r.matched_caregivers)
    r, _ = drive('I am coughing', ['no', 'no', 'two days', 'no'])
    assert r.care_type == 'teleconsultation'
    assert r.matched_caregivers
    assert all(BY_ID[m.caregiver_id]['specialty'] != 'Pediatrics' for m in r.matched_caregivers)

def test_child_cough_flow_completes_with_matches():
    r, _ = drive('my 5 year old child has a cough', ['no', 'no', 'two days', 'no'])
    assert r.care_type == 'teleconsultation'
    assert r.matched_caregivers

def test_medic_cards_carry_specialty_field():
    r, ui = drive('I need someone to change my prescribed wound dressing at home',
                  ['no', 'no', 'two days'])
    assert r.care_type == 'home_nursing'
    assert r.matched_caregivers
    assert ui['caregivers']
    assert all('specialty' in c for c in ui['caregivers'])

def test_rash_wordings_recognised_as_rash():
    from backend.app.intake import extract_local
    for text in ('I have rashes', 'I have itching', 'I have rashes and itching',
                 'I have skin infection', 'mere ko khujli hai', 'I have pimples'):
        assert extract_local(text).complaint == 'rash', text

def test_rash_flow_matches_skin_specialists():
    r, _ = drive('I have rashes', ['no', 'no', 'two days'])
    assert r.care_type == 'teleconsultation'
    assert r.matched_caregivers
    assert {BY_ID[m.caregiver_id]['specialty'] for m in r.matched_caregivers} <= {'Dermatology', 'Allergy and Clinical Immunology'}

def test_scores_differentiate_by_rating_not_roster_order():
    # Teleconsultation scores used to cap at 1.0 for every doctor (a bonus
    # applied to all), so ties fell to roster order and the demo rows always
    # won. Ratings must now decide, letting named doctors surface.
    r, _ = drive('I have knee pain', ['no', 'no', 'no', 'two days'])
    assert r.care_type == 'teleconsultation'
    assert r.matched_caregivers
    assert len({m.score for m in r.matched_caregivers}) > 1
    assert any(not BY_ID[m.caregiver_id]['name'].startswith('Demo Specialist')
               for m in r.matched_caregivers)
