"""Explicit per-complaint minimum information, not a medical clearance checklist.

Safety questions are relevant to each complaint. Some service/chronic pathways
only require context, not an unrelated universal emergency questionnaire. The
strict organiser schema has no review outcome; UI metadata carries that status.
"""
import re

# Every recognised family has an explicit policy. Values are configured question
# IDs: a known yes/no or a supplied scalar resolves an item; 'not sure' does not.
REQUIRED_QUESTIONS={
 'abdominal_pain':('abdominal_touch',),
 'headache':('headache_sudden','one_sided_weakness'),
 'vomiting':('blood_vomit','keep_fluids'),
 'diarrhoea':('keep_fluids','blood_stool'),
 'cough':('breathing','blood_cough'),
 'sore_throat':('swallow_saliva',),
 'urinary':('urine_retention',),
 'back_pain':('bladder_change','saddle_numbness'),
 'wound':('wound_leaking','wound_redness'),
 'injury':('symptom_severity','symptom_duration'),
 'knee_pain':('joint_swelling','joint_moving','bear_weight'),
 'shoulder_pain':('lifting_arm','joint_injury'),
 'ankle_pain':('joint_swelling','bear_weight'),
 'neck_pain':('joint_stiffness','joint_injury'),
 'wrist_pain':('joint_swelling','grip_difficulty'),
 'elbow_pain':('joint_swelling','bend_difficulty'),
 'hip_pain':('bear_weight','joint_injury'),
 'foot_pain':('joint_swelling','bear_weight'),
 'joint_pain':('symptom_severity','joint_swelling','joint_moving'),
 'diabetes':('sugar_check','foot_sore'),
 'catheter':('catheter_block','catheter_pain'),
 'nebulization':('breathing','nebulizer_home'),
 'vitals_check':('vitals_bp','vitals_sugar'),
 'post_surgical':('postop_redness',),
 'bedridden':('daily_care','bedsores'),
 'elderly_care':('daily_care','elderly_meds'),
 'menstrual':('heavy_bleeding','symptom_severity'),
 'anxiety':('immediate_harm',),
 'sleep_problem':('snoring','symptom_severity'),
 'hand_pain':('joint_swelling','grip_difficulty'),
 'muscle_pain':('symptom_severity','joint_injury'),
 'nasal':('symptom_severity','associated_fever'),
 'cardiac':('cardiac_chest','breathing'),
 'neuro':('one_sided_weakness','stroke_speech'),
 'kidney':('symptom_severity','symptom_duration'),
 'thyroid':('symptom_severity','symptom_duration'),
 'nutrition':('symptom_severity','symptom_duration'),
 'blood':('symptom_severity','symptom_duration'),
 'rash':('airway_swelling',),
 'dizziness':('one_sided_weakness','stroke_speech'),
 'eye_problem':('vision_loss',),
 'ear_pain':('hearing_sudden',),
 'dental_pain':('airway_swelling',),
 'fatigue':('symptom_severity','symptom_duration','symptom_age'),
 'fever':('age','breathing','fever_high','fluids_normal'),
 'other':(),
}

EXPLICIT_PROCEDURES={'dressing','injection_im','injection_iv','insulin','bp_sugar','lab'}

def reported_families(state):
    f=state.facts
    reported={v.name for v in f.associated_symptoms if v.status=='affirmed'}
    if f.complaint:reported.add(f.complaint)
    # Broad body-part recognisers also match mere location ('wound on my
    # hand'). That is not automatically an independent joint-pain complaint.
    if f.complaint=='wound' and not re.search(r'pain|hurts?|aches?|dard|दर्द',f.complaint_text or '',re.I):
        reported-={'knee_pain','shoulder_pain','ankle_pain','neck_pain','wrist_pain','elbow_pain','hip_pain','foot_pain','hand_pain'}
    return reported

def service_only(state):
    """Preserve plain service requests, without bypassing a co-reported symptom.

    Same-family procedural words ('wound dressing', 'BP check') can themselves
    trigger a complaint recogniser. They are not evidence of a new symptom.
    """
    f=state.facts
    if f.service not in EXPLICIT_PROCEDURES:return False
    allowed={
      'dressing':{'wound','diabetes','foot_pain'},
      'injection_im':set(),'injection_iv':set(),'insulin':{'diabetes'},
      'bp_sugar':{'vitals_check','cardiac','diabetes'},'lab':set(),
    }[f.service]
    reported=reported_families(state)
    if reported-allowed:return False
    clinical=[v for v in f.clinical_features if v.name not in {'bp_check_requested','sugar_check_requested'}]
    if f.fever or f.severity or clinical:return False
    symptom_words=r'palpitat|racing|pain|hurts?|dizz|faint|weak|breath|fever|vomit|bleed|leak|block|redness|swollen|सूजन|दर्द|बुखार|चक्कर'
    return not re.search(symptom_words,f.complaint_text or '',re.I)

def question_resolved(state,qid):
    from .complaints import BROAD_QUESTIONS
    f=state.facts
    if qid in ('breathing','cardiac_chest','stroke_speech','immediate_harm'):
        flag={'breathing':'breathlessness','cardiac_chest':'chest_pain','stroke_speech':'stroke_symptoms','immediate_harm':'suicidal_ideation'}[qid]
        item=state.flags.get(flag)
        return item is not None and item.status in ('affirmed','denied')
    if qid=='age':return f.age_months is not None
    spec=BROAD_QUESTIONS[qid]
    if spec.field:return getattr(f,spec.field) is not None
    if spec.feature:
        item=next((v for v in f.clinical_features if v.name==spec.feature),None)
        if spec.feature=='fever_with_complaint' and f.fever is not None:return True
        return item is not None and item.status in ('affirmed','denied')
    return False  # Service-choice questions must explicitly record the answer.

def safety_gaps(state):
    from .complaints import BROAD_QUESTIONS
    if getattr(state,'unresolved_service_intent',False):return [{'question_id':None,'kind':'uncertain_service_request','label':'The requested service is uncertain and needs human clarification.'}]
    if getattr(state,'extraction_conflicts',[]):return [{'question_id':'complaint_clarify','kind':'extraction_conflict','label':'The complaint interpretations disagree and need clarification.'}]
    uncertain=[v for v in getattr(state,'safety_findings',[]) if v.status=='unknown']
    if uncertain:return [{'question_id':None,'kind':'uncertain_warning','label':'A possible warning sign remains unclear.'}]
    if service_only(state):return []
    c=state.facts.complaint
    if c not in REQUIRED_QUESTIONS or c=='other':
        if not c and state.facts.service:return []
        return [{'question_id':None,'kind':'unclassified_complaint','label':'The presenting need is not sufficiently understood.'}]
    result=[]
    for q in REQUIRED_QUESTIONS[c]:
        if not question_resolved(state,q):
            spec=BROAD_QUESTIONS.get(q)
            label='The person’s age' if q=='age' else 'Current breathing difficulty' if q=='breathing' else spec.en
            result.append({'question_id':q,'kind':'context' if q in ('age','symptom_age','symptom_severity','symptom_duration') else 'safety_or_service_information','label':label})
    # A secondary complaint with its own unresolved screen cannot be cleared by
    # a procedure request. Full independent multi-complaint interviews remain
    # out of scope: the conservative result is human assessment.
    secondary=reported_families(state)-{c,'fever'}
    for other in sorted(secondary):
        if other not in REQUIRED_QUESTIONS:continue
        for q in REQUIRED_QUESTIONS[other]:
            if not question_resolved(state,q) and q not in {x['question_id'] for x in result}:
                result.append({'question_id':q,'kind':'secondary_complaint','label':f'Unresolved information for associated {other.replace("_"," ")}.'})
    return result
