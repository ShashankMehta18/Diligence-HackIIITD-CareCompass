import os
import re
from .schemas import Response
from .intake import replay,active_flags,concern,next_question,QUESTIONS,normalise,detect_flags,infer_question
from .matching import match,IDS,clock
from .config import MODE,POLICY_VERSION
from .providers import ProviderError
from .complaints import emergency_evidence,complete_enough,LABELS,BROAD_QUESTIONS,detect_features,question_candidates,FAMILY_KEYS,COMPLAINT_SERVICE,CHILD_KEYS,YES,NO
from .safety_policy import safety_gaps,question_resolved
from .assertions import UNCERTAIN

def language(req):
    requested=req.language.casefold()
    if requested in ('hi','hindi','hinglish'):return 'Hindi'
    if requested in ('en','english'):return 'English'
    return 'Hindi' if re.search(r'[\u0900-\u097f]|\b(?:papa|mummy|bukhar|chahiye|ghar|saans|nahi|hai|hain)\b',req.user_input.casefold()) else 'English'

def emergency(flags,evidence=None):
    names=', '.join([f.replace('_',' ') for f in flags]+(evidence or []))
    return Response(follow_up_question=None,care_type='emergency_112',urgency='emergency',red_flags=flags,reasoning=f'Reported active warning sign: {names}. Call 112 now and ask someone nearby for help. Do not wait for a home visit. No help has been dispatched.',matched_caregivers=[])

def local_answer(req,state):
    if not req.conversation_history or req.conversation_history[-1].role!='assistant':return False
    q=infer_question(req.conversation_history[-1]);t=normalise(req.user_input).strip(' .!')
    if q not in QUESTIONS:return False
    if re.fullmatch(YES+'|'+NO+r'|not sure|unknown|pata nahi|पता नहीं',t):return q not in ('need','symptom_detail','complaint_clarify')
    if q in ('symptom_severity','abdominal_severity') and t in ('mild','moderate','severe','हल्का','हल्के','मध्यम','बहुत तेज़','बहुत गंभीर'):return True
    if q in ('duration','symptom_duration') and re.fullmatch(r'(?:\d+(?:\.\d+)?|one|two|three|four|five|ten|एक|दो|तीन|चार|पाँच)\s*(?:days?|din|दिन|hours?|घंटे)?',t) and state.facts.duration_days is not None:return True
    if q in ('age','symptom_age') and re.fullmatch(r'\d+(?:\.\d+)?\s*(?:(?:years?|months?|साल|महीने)(?:\s*old)?)?',t) and state.facts.age_months is not None:return True
    return False

def localize(response,state,lang):
    if lang!='Hindi':return response
    if response.care_type=='emergency_112':reason='आपके बताए लक्षणों में आपातकालीन चेतावनी मिली है। अभी 112 पर कॉल करें और पास के व्यक्ति से मदद माँगें। घर की विज़िट या इस चैट का इंतज़ार न करें। कोई मदद भेजी नहीं गई है।'
    elif any(v.status=='unknown' for v in state.safety_findings):reason='संभावित चेतावनी की जानकारी अभी स्पष्ट नहीं है। अभी चिकित्सकीय सहायता लें; सामान्य बुकिंग का इंतज़ार न करें। तत्काल खतरे में 112 पर कॉल करें। कोई मदद भेजी नहीं गई है।'
    elif any(v.disposition=='urgent_assessment' and v.status in ('affirmed','recent_resolved') for v in state.safety_findings):reason='दवा की अधिक मात्रा की आशंका में अभी योग्य चिकित्सकीय सहायता लें। सामान्य या वर्चुअल बुकिंग का इंतज़ार न करें। इस चैट ने कोई सुरक्षित खुराक तय नहीं की है। कोई मदद भेजी नहीं गई है।'
    elif response.follow_up_question:reason='सही अगला कदम चुनने के लिए यह जानकारी चाहिए। जो लक्षण नहीं बताए गए हैं वे अज्ञात हैं।' if not concern(state) else 'इन लक्षणों के लिए शीघ्र चिकित्सकीय आकलन चाहिए। मदद लेने में इस चैट के कारण देर न करें।'
    elif safety_gaps(state) or concern(state):reason='ज़रूरी जानकारी अभी स्पष्ट नहीं है या लक्षणों के लिए चिकित्सकीय जाँच चाहिए। किसी चिकित्सक से शीघ्र आकलन कराएँ। यह चैट सामान्य घरेलू देखभाल की उपयुक्तता तय नहीं कर सकती। सामान्य बुकिंग रोकी गई है। कोई मदद भेजी नहीं गई है।'
    else:
        reason='आपकी बताई ज़रूरत के आधार पर अगला देखभाल विकल्प दिखाया गया है। यह बीमारी का निदान नहीं है और कोई वास्तविक बुकिंग नहीं की गई है।'
        if not response.matched_caregivers:reason+=' इस रोस्टर में उपयुक्त देखभालकर्ता नहीं मिला। चिकित्सकीय सहायता लें।'
    return response.model_copy(update={'reasoning':reason})

async def assess(req,providers=None,mode=None,reference_time=None):
    state=replay(req);lang=language(req);used='rules_baseline';cards=[]
    flags=active_flags(state)
    extra=sorted(set(state.established_emergencies+emergency_evidence(state)))
    # Fast path does not depend on provider connectivity or model latency.
    if flags or extra:
        response=localize(emergency(flags,extra),state,lang)
        return response,metadata(state,response,used,cards,reference_time)
    from .safety_screen import actionable
    if any(v.status=='unknown' for v in state.safety_findings):
        response=Response(follow_up_question=None,care_type='teleconsultation',urgency='same_day',red_flags=[],matched_caregivers=[],reasoning='A possible warning sign remains unclear. Seek urgent human clinical assessment now; do not wait for routine booking. For immediate danger call 112. No help has been dispatched.')
        response=localize(response,state,lang)
        return response,metadata(state,response,used,cards,reference_time)
    if any(v.disposition=='urgent_assessment' for v in actionable(state.safety_findings)):
        response=Response(follow_up_question=None,care_type='teleconsultation',urgency='same_day',red_flags=[],matched_caregivers=[],reasoning=concern(state)+' Seek urgent professional assessment now; a routine or virtual booking must not delay care. No help has been dispatched.')
        response=localize(response,state,lang)
        return response,metadata(state,response,used,cards,reference_time)
    selected=mode or MODE
    live=selected=='live' or (selected=='auto' and providers is not None and bool(providers.text_key))
    if live and local_answer(req,state):
        live=False;used='rules_contextual_answer'
    if live:
        if providers is None:raise ProviderError('text_not_configured')
        extracted=await providers.extract(req)
        current_texts=[e['text'] for e in state.evidence if 'text' in e]
        valid_quote=lambda q:bool(q.strip()) and any(q in text for text in current_texts)
        extracted.evidence=[q for q in extracted.evidence if valid_quote(q)]
        extracted.flags=[v for v in extracted.flags if valid_quote(v.quote)]
        extracted.clinical_features=[v for v in extracted.clinical_features if valid_quote(v.quote)]
        previous=infer_question(req.conversation_history[-1]) if req.conversation_history and req.conversation_history[-1].role=='assistant' else None
        if previous not in state.asked:previous=None
        previous_spec=BROAD_QUESTIONS.get(previous)
        if state.facts.complaint=='other' and extracted.complaint and extracted.complaint!='other' and extracted.evidence:
            state.facts.complaint=extracted.complaint
            state.facts.complaint_text=extracted.complaint_text or state.facts.complaint_text
        elif extracted.complaint and state.facts.complaint and extracted.complaint!=state.facts.complaint and extracted.evidence:
            # A grounded disagreement is explicit uncertainty, not a silent
            # overwrite of a known complaint or a falsely cleared pathway.
            state.extraction_conflicts.append({'local':state.facts.complaint,'model':extracted.complaint})
        # Preserve locally parsed/corrected facts. Groq fills missing structured
        # facts rather than undoing local evidence or mandatory safety.
        for key in ['body_site','trigger','patient','age_months','duration_days','temperature','temperature_unit','temperature_timing','onset','progression','fever','service','complaint','complaint_text','severity','pain_location','sudden_onset']:
            if extracted.evidence and getattr(state.facts,key) is None:
                setattr(state.facts,key,getattr(extracted,key))
        seen={v.name for v in state.facts.associated_symptoms}
        state.facts.associated_symptoms.extend(v for v in extracted.associated_symptoms if v.name not in seen and any(v.quote in e.get('text','') for e in state.evidence))
        known={v.name for v in state.facts.clinical_features}
        for v in extracted.clinical_features:
            if v.name not in known:
                short=bool(re.fullmatch(YES+'|'+NO,normalise(v.quote).strip(' .!')))
                if short and (not previous_spec or previous_spec.feature!=v.name):continue
                if re.search(UNCERTAIN,normalise(v.quote)):continue
                local=detect_features(v.quote)
                if v.status=='denied' and not any(f.name==v.name and f.status=='denied' for f in local):continue
                if not any(f.name==v.name and f.status!=v.status for f in local):state.facts.clinical_features.append(v)
        for f in extracted.flags:
            if f.status=='affirmed':
                short=bool(re.fullmatch(YES+'|'+NO,normalise(f.quote).strip(' .!')))
                target='breathlessness' if previous=='breathing' else previous_spec.flag if previous_spec else None
                if short and target!=f.flag:continue
                if re.search(UNCERTAIN,normalise(f.quote)):continue
                local=detect_flags(f.quote)
                # A known local negation/historical/hypothetical interpretation
                # vetoes model affirmation. Unknown wording may be understood by Groq.
                if not any(v.flag==f.flag and v.status!='affirmed' for v in local):
                    if f.flag not in state.flags or state.flags[f.flag].status=='affirmed':state.flags[f.flag]=f
        used='groq_text_live'
        state.evidence.append({'source':'groq','quotes':extracted.evidence})
    flags=active_flags(state)
    extra=sorted(set(state.established_emergencies+emergency_evidence(state)))
    if flags or extra:response=emergency(flags,extra)
    else:
        question='complaint_clarify' if state.extraction_conflicts and len(state.asked)<4 and 'complaint_clarify' not in state.asked else next_question(state)
        if question:
            text=QUESTIONS[question][1 if lang=='Hindi' else 0]
            reason=concern(state) or 'More information is needed to choose a defensible care pathway; unmentioned symptoms remain unknown.'
            response=Response(follow_up_question=text,care_type=None,urgency=None,red_flags=[],reasoning=reason,matched_caregivers=[])
        else:
            f=state.facts
            # Complaint-implied service: "post surgery care" needs a medic even
            # though no explicit procedure word was stated.
            service=f.service or COMPLAINT_SERVICE.get(f.complaint)
            if service in ('dressing','injection_im','injection_iv','injection_unknown','insulin','catheter','nebulization','post_surgical','elderly'):care='home_nursing'
            elif service=='lab':care='lab_test_home'
            elif service=='bp_sugar' or service=='home_assessment':care='paramedic_home_visit'
            else:care='teleconsultation'
            if concern(state):care='teleconsultation'
            urgency='scheduled' if care=='lab_test_home' else 'same_day'
            # Contract lacks urgent in-person physician care. Keep explicit concern.
            if concern(state):service='doctor'
            gaps=safety_gaps(state)
            unsupported=bool(gaps)
            if unsupported:care='teleconsultation';urgency='same_day';service='doctor'
            future=bool(re.search(r'tomorrow|kal\s+subah|कल\s+सुबह|next\s+week',normalise(req.user_input)))
            keys=FAMILY_KEYS.get(f.complaint)
            if keys is not None and (f.age_months is None or f.age_months>=216):
                keys=set(keys)-CHILD_KEYS
            if unsupported or concern(state):matches,cards=[],[]
            else:matches,cards=match(req,care,service,lang,reference_time,scheduled_future=future,complaint_keys=keys)
            reasons={'home_nursing':'The requested procedure fits home nursing; only staff with explicitly supported procedural skills can be matched.','lab_test_home':'A home sample-collection service was requested; no new test is being ordered.','paramedic_home_visit':'The reported need fits a same-day home assessment by a Medic.','teleconsultation':'A clinician consultation is the available assessment pathway; this is not a diagnosis.'}
            reason=concern(state) or reasons[care]
            if f.complaint:
                complaint=LABELS.get(f.complaint,LABELS['other'])[0]
                reason=concern(state) or f'You reported {complaint}. A clinician should assess this complaint; this is care navigation, not a diagnosis.'
            if not f.service and not f.fever and not f.complaint and not concern(state):reason='The need remains unclear after clarification. Seek human clinical assessment; this prototype cannot establish that home care is suitable.'
            if f.service in ('insulin','injection_unknown'):reason+=' The roster does not establish eligibility for this injection route; no procedure booking is offered. Confirm with a qualified clinician.'
            if concern(state):reason+=' Arrange prompt in-person assessment when needed; a virtual consultation must not delay it.'
            if unsupported:
                reason+=' Important safety information remains unknown. Seek human clinical assessment; this chat cannot establish a safe routine pathway.'
            if unsupported or concern(state):
                matches=[];cards=[]  # No routine booking for unresolved/urgent assessment.
            if unsupported or concern(state):reason+=' Routine caregiver matching is withheld pending human assessment.'
            elif not matches:reason+=' No eligible caregiver is available under the roster and reference-clock assumptions.'
            if future:reason+=' Future availability is not supplied; listed caregivers are candidates only, with booking disabled.'
            response=Response(follow_up_question=None,care_type=care,urgency=urgency,red_flags=[],reasoning=reason,matched_caregivers=matches)
    assert all(m.caregiver_id in IDS for m in response.matched_caregivers)
    response=localize(response,state,lang)
    return response,metadata(state,response,used,cards,reference_time)

def metadata(state,response,used,cards,reference_time):
    question=None
    if response.follow_up_question:
        question=next((k for k,v in QUESTIONS.items() if response.follow_up_question in v),None)
    q=BROAD_QUESTIONS.get(question)
    choices=list(q.choices) if q else ['Yes','No','Not sure'] if question=='breathing' else []
    labels={'Yes':'हाँ','No':'नहीं','Not sure':'पता नहीं','Mild':'हल्का','Moderate':'मध्यम','Severe':'बहुत तेज़','Getting worse':'बढ़ रहे हैं','Improving':'कम हो रहे हैं','Staying the same':'वैसे ही हैं'}
    gaps=safety_gaps(state)
    status='emergency' if response.care_type=='emergency_112' else 'clarification' if response.follow_up_question else 'needs_human_assessment' if gaps or concern(state) else 'care_pathway'
    return {'assessment_status':status,'unresolved_information':gaps,'routine_booking_allowed':status=='care_pathway','engine':used,'policy_version':POLICY_VERSION,'question_id':question,'answer_choices':choices,'answer_choices_hi':[labels.get(v,v) for v in choices],'concern':concern(state),'emergency_evidence':sorted(set(state.established_emergencies+emergency_evidence(state))),'reference_time':clock(reference_time).isoformat(),'caregivers':cards,'state':{'facts':state.facts.model_dump(exclude_none=True),'warning_signs':{k:v.model_dump() for k,v in state.flags.items()},'asked_question_ids':state.asked,'contradictions':state.contradictions,'extraction_conflicts':state.extraction_conflicts,'safety_findings':[v.dump() for v in state.safety_findings],'understanding':{'complaint':state.facts.complaint,'body_site':state.facts.body_site,'trigger':state.facts.trigger,'duration_days':state.facts.duration_days,'sudden_onset':state.facts.sudden_onset},'evidence':state.evidence},'booking':'simulated_only','clinical_validation':False}

