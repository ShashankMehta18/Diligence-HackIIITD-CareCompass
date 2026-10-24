"""Evidence-aware local baseline. Finite coverage; not clinical validation."""
import re
import unicodedata
from dataclasses import dataclass,field
from types import SimpleNamespace
from .schemas import Extraction, FlagEvidence,SymptomEvidence
from .complaints import BROAD_QUESTIONS,enrich,question_candidates,broad_concern,emergency_evidence,has

QUESTIONS = {
 'need': ('What help is needed: symptoms, home nursing, a lab test, or a doctor consultation?', 'किस मदद की ज़रूरत है: लक्षणों की जाँच, घर पर नर्सिंग, लैब टेस्ट या डॉक्टर से सलाह?'),
 'age': ('How old is the person with fever?', 'बुखार वाले व्यक्ति की उम्र कितनी है?'),
 'breathing': ('Is the person having difficulty breathing right now?', 'क्या अभी साँस लेने में तकलीफ़ हो रही है?'),
 'duration': ('How many days has the fever lasted?', 'बुखार कितने दिनों से है?'),
 'temperature': ('What is the measured temperature, including °C or °F?', 'तापमान कितना है? कृपया °C या °F भी बताएँ।'),
 'injection': ('What injection route is written on the prescription: IM, IV, or something else?', 'पर्चे पर इंजेक्शन का कौन सा तरीका लिखा है: IM, IV या कुछ और?'),
}
QUESTIONS.update({k:(q.en,q.hi) for k,q in BROAD_QUESTIONS.items()})

PATTERNS = {
 'chest_pain': r'chest\s+(?:pain|tightness)|(?:pain|tightness)\s+(?:in\s+)?(?:my\s+|the\s+)?chest|seene\s*(?:me|mein)?\s*(?:dard|pain)|सीने\s*(?:में)?\s*(?:तेज\s*)?दर्द',
 'breathlessness': r"(?:can.?t|cannot|unable to)\s+breathe|(?:difficulty|difficulties|trouble)\s+(?:in\s+)?breath(?:ing)?|breath(?:ing)?\s+(?:difficulty|difficulties|problem)|short(?:ness)?\s+of\s+breath|sa+a?ns\s+nahi\s+aa\s+rahi|sa+a?ns\s*(?:ki\s*)?(?:dikkat|takli+f)|सांस\s+नहीं\s+आ\s+रही|साँस\s+नहीं\s+आ\s+रही|(?:सांस|साँस)\s*(?:लेने\s*में|की)?\s*(?:तकलीफ|तकलीफ़|दिक्कत)",
 'unconsciousness': r'unconscious|unresponsive|not\s+responding|collapsed|response\s+nahi\s+de\s+rahe|बेहोश|जवाब\s+नहीं\s+दे\s+रहे',
 'severe_bleeding': r"(?:heavy|severe|uncontrolled)\s+bleeding|bleeding\s+(?:that\s+)?(?:won.?t|will not|does not|doesn.?t)\s+stop|bleeding\s+ruk\s+nahi|खून\s+नहीं\s+रुक|बहुत\s+खून",
 'stroke_symptoms': r'face\s+(?:is\s+)?droop(?:ing)?|slurred\s+speech|sudden\s+(?:one.sided|arm|leg)\s+weakness|chehra\s+tedha|चेहरा\s+टेढ़ा|अचानक\s+एक\s+तरफ\s+कमजोरी',
 'seizure': r'\bseizure\b|\bconvulsion|daura\s+(?:pad|aa)|दौरा\s+(?:पड़|आ)',
 'suicidal_ideation': r'(?:want|going|plan|planning)\s+to\s+(?:kill|hurt)\s+myself|end\s+my\s+life|suicidal|khudkushi|आत्महत्या|खुद\s+को\s+मार',
 'severe_dehydration': r'severe\s+dehydration|severely\s+dehydrated|बहुत\s+ज़्यादा\s+पानी\s+की\s+कमी',
}
NEGATIONS = {
 'chest_pain': r'no\s+(?:current\s+)?chest\s+pain|(?:not having|do not have|don.t have|does not have|doesn.t have)\s+(?:any\s+)?chest\s+pain|den(?:y|ies)\s+chest\s+pain|chest\s+pain\s+nahi|सीने\s*में\s*दर्द\s*नहीं',
 'breathlessness': r'no\s+(?:difficulty|trouble)\s+breathing|no\s+(?:breathlessness|shortness\s+of\s+breath)|breathing\s+(?:is\s+)?(?:fine|normal)|saans\s+(?:ki\s*)?(?:dikkat|taklif|takleef)\s+nahi|saans\s+lene\s+(?:me|mein)\s+(?:koi\s+)?(?:dikkat|takleef)\s+nahi|(?:सांस|साँस)\s*(?:लेने\s*में|की)?\s*(?:तकलीफ|तकलीफ़|दिक्कत)\s*नहीं',
 'unconsciousness': r'not\s+unconscious|not\s+unresponsive|बेहोश\s+नहीं',
 'severe_bleeding': r'no\s+(?:severe|heavy|uncontrolled)\s+bleeding|bleeding\s+(?:has\s+)?stopped|खून\s+रुक\s+गया',
 'stroke_symptoms': r'no\s+(?:slurred\s+speech|face\s+droop|stroke\s+symptoms)',
 'seizure': r'no\s+(?:current\s+)?seizure|not\s+having\s+a\s+seizure',
 'suicidal_ideation': r'not\s+suicidal|no\s+suicidal\s+(?:thoughts|ideation)',
 'severe_dehydration': r'no\s+severe\s+dehydration|not\s+severely\s+dehydrated',
}

def normalise(text):
    return unicodedata.normalize('NFKC',text).casefold().translate(str.maketrans('०१२३४५६७८९','0123456789'))

def detect_flags(text):
    text=normalise(text)
    result={}
    for clause in re.split(r'[.!?;\n]|\bbut\b|\blekin\b|लेकिन|\band (?:now|later)\b',text):
        for flag,pattern in PATTERNS.items():
            neg = re.search(NEGATIONS.get(flag,r'(?!)'),clause)
            hits=list(re.finditer(pattern,clause))
            if not hits and not neg: continue
            historical=bool(re.search(r'\b(?:last year|years? ago|history of|used to|previously)\b|पिछले\s+साल|pehle',clause))
            hypothetical=bool(re.search(r'\b(?:what if|hypothetical|example|quoted|if someone|if i|if he|if she)\b|अगर|agar',clause))
            status='hypothetical' if hypothetical else 'historical' if historical else 'denied' if neg else 'affirmed'
            # Resolved explicit history is not an active symptom. Recent emergencies
            # are escalated separately when current safety remains unknown.
            if re.search(r'\b(?:resolved|no longer|gone now)\b',clause): status='historical'
            if flag not in result or status=='affirmed':
                result[flag]=FlagEvidence(flag=flag,status=status,quote=clause.strip())
    return list(result.values())

def number_days(text):
    t=normalise(text)
    words={'one':1,'two':2,'three':3,'four':4,'five':5,'ten':10,'ek':1,'do':2,'teen':3,'das':10,'एक':1,'दो':2,'तीन':3,'दस':10}
    # Last explicit duration wins: "not three days - ten days".
    hits=list(re.finditer(r'(\d+(?:\.\d+)?|one|two|three|four|five|ten|ek|do|teen|das|एक|दो|तीन|दस)\s*(days?|din|दिन|weeks?|हफ्ते)',t))
    if not hits: return None
    m=hits[-1];n=float(m[1]) if m[1][0].isdigit() else words[m[1]]
    return n*7 if m[2].startswith('week') or m[2]=='हफ्ते' else n

def extract_local(text,question=None):
    t=normalise(text)
    x=Extraction(flags=detect_flags(text),evidence=[text])
    patient=re.search(r'\b(mother|father|wife|grandmother|grandfather|mummy|papa|dadi|dadaji)\b|माँ|पापा|पत्नी|दादी|दादाजी',t)
    if patient:
        identity=patient[0]
        aliases={'mummy':'mother','माँ':'mother','papa':'father','पापा':'father','पत्नी':'wife','dadi':'grandmother','दादी':'grandmother','dadaji':'grandfather','दादाजी':'grandfather'}
        x.patient=aliases.get(identity,identity)
    # Age is not duration: require an age unit plus old/age/context, or an age answer.
    age=re.search(r'(\d+(?:\.\d+)?)\s*[- ]?\s*(years?|months?|days?|saal|mahine|साल|महीने)\s*[- ]?\s*(?:old|का|की|के)',t)
    if question in ('age','symptom_age') and not age: age=re.search(r'(\d+(?:\.\d+)?)\s*(years?|months?|days?|saal|mahine|साल|महीने)?',t)
    if age:
        unit=age[2] or 'years';x.age_months=float(age[1])*(1/30.4375 if unit.startswith('day') else 1 if unit in ('month','months','mahine','महीने') else 12)
    x.duration_days=number_days(t)
    if question in ('age','symptom_age'): x.duration_days=None
    if question in ('duration','symptom_duration') and x.duration_days is None and re.fullmatch(r'\d+(?:\.\d+)?',t.strip()):x.duration_days=float(t)
    temperature=list(re.finditer(r'(\d{2,3}(?:\.\d+)?)\s*(?:°\s*([cf])|degrees?\s*([cf])?|\b([cf])\b)',t))
    if temperature:
        m=temperature[-1];x.temperature=float(m[1]);x.temperature_unit=next((v.upper() for v in m.groups()[1:] if v),None)
    elif question=='temperature':
        m=re.search(r'\d+(?:\.\d+)?',t)
        if m:x.temperature=float(m[0])
    if x.temperature is not None:
        x.temperature_timing='historical' if re.search(r'yesterday|last week|कल|बीते',t) and not re.search(r'now|currently|अभी',t) else 'current' if re.search(r'now|currently|अभी',t) else 'unknown'
    if re.search(r'worse|worsening|badh|बढ़',t):x.progression='worsening'
    elif re.search(r'improving|getting better|सुधार',t):x.progression='improving'
    onset=re.search(r'since\s+(?:this\s+)?(?:morning|yesterday|evening)|सुबह\s*से',t)
    if onset:x.onset=onset[0]
    for name,pattern in {'headache':r'headache|sar.*dard|सिर.*दर्द','joint_pain':r'joint pain|joint.*ache|jodon.*dard|जोड़ों.*दर्द','rash':r'\brash\b|चकत्ते','cough':r'\bcough\b|khansi|खांसी'}.items():
        hit=re.search(pattern,t)
        if hit:
            prefix=t[max(0,hit.start()-8):hit.start()]
            denied=bool(re.search(r'no\s*$|नहीं\s*$',prefix))
            x.associated_symptoms.append(SymptomEvidence(name=name,status='denied' if denied else 'affirmed',quote=text))
    for risk,pattern in {'pregnancy':r'pregnant|गर्भवती','diabetes':r'diabetes|diabetic|मधुमेह','immunosuppression':r'immunosuppress|chemotherapy'}.items():
        if re.search(pattern,t) and not re.search(r'(?:no|not)\s+(?:'+pattern+r')',t):x.risk_factors.append(risk)
    x.fever=True if re.search(r'fever|bukhar|बुखार',t) else None
    if re.search(r'no\s+fever|bukhar\s+nahi|बुखार\s+नहीं',t):x.fever=False
    if x.temperature is not None and x.temperature_unit and x.temperature_timing!='historical':
        x.fever=(x.temperature>=38 if x.temperature_unit=='C' else x.temperature>=100.4)
    if re.search(r'dressing|bedsore|ड्रेसिंग|पट्टी|घाव',t): x.service='dressing'
    elif re.search(r'insulin|इंसुलिन',t): x.service='insulin'
    elif re.search(r'\bim\b.*injection|injection.*\bim\b|\bim\b',t): x.service='injection_im'
    elif re.search(r'\biv\b|intravenous',t): x.service='injection_iv'
    elif re.search(r'injection|इंजेक्शन',t): x.service='injection_unknown'
    elif re.search(r'\bbp\b.*sugar|sugar.*\bbp\b|बीपी.*शुगर',t): x.service='bp_sugar'
    elif re.search(r'\b(?:cbc|thyroid|lab|sample|collection|test)\b|सीबीसी|थायराइड|टेस्ट|सैंपल|जांच.*खून',t): x.service='lab'
    elif re.search(r'consult|reports?|second opinion|doctor se|डॉक्टर.*(?:सलाह|बात)|रिपोर्ट|ओपिनियन|परामर्श',t): x.service='doctor'
    elif re.search(r'home\s+check|ghar\s+pe\s+check|घर\s*(?:पर|पे)?\s*(?:जांच|जाँच)|weak|कमजोर|fever.*cough|bukhar.*khansi|बुखार.*खांसी|ghar pe dikhana',t): x.service='home_assessment'
    if question=='breathing':
        if re.fullmatch(r'(?:yes|haan|han|हाँ|हां|ji)[.! ]*',t):x.flags=[FlagEvidence(flag='breathlessness',status='affirmed',quote=text)]
        elif re.fullmatch(r'(?:no|nahi|nahin|नहीं|नही)[.! ]*',t):x.flags=[FlagEvidence(flag='breathlessness',status='denied',quote=text)]
    return enrich(x,text,question)

@dataclass
class State:
    facts: Extraction=field(default_factory=Extraction)
    flags: dict=field(default_factory=dict)
    evidence: list=field(default_factory=list)
    asked: list=field(default_factory=list)
    turns: int=0
    question: str | None=None
    possible_recent_emergency: bool=False
    contradictions: list=field(default_factory=list)
    established_emergencies: list=field(default_factory=list)
    additional_concerns: list=field(default_factory=list)
    def merge(self,x,text,index):
        new_patient=x.patient
        # Explicit new patient starts an independent assessment.
        if self.facts.patient and new_patient and self.facts.patient!=new_patient:
            self.facts=Extraction();self.flags={};self.evidence=[];self.asked=[];self.possible_recent_emergency=False;self.contradictions=[];self.established_emergencies=[];self.additional_concerns=[]
        correction=bool(re.search(r'correction|misheard|transcri|meant|actually|गलत|not .*but|नहीं.*बल्कि',normalise(text)))
        # A newly reported focal symptom must be safety-screened even when it is
        # associated with a different main complaint. Never transfer its pain
        # severity/duration to the original complaint just to fit one slot.
        independent=SimpleNamespace(facts=x)
        independent_danger=emergency_evidence(independent)
        independent_concern=broad_concern(independent)
        different=bool(self.facts.complaint and x.complaint and self.facts.complaint!=x.complaint and self.facts.complaint!='other' and not correction)
        for key in ['patient','age_months','duration_days','temperature','temperature_unit','temperature_timing','onset','progression','fever','service','complaint','complaint_text','severity','pain_location','sudden_onset']:
            value=getattr(x,key)
            previous=getattr(self.facts,key)
            if key=='complaint' and previous and previous!='other' and value and value!=previous and not correction:
                continue  # An associated symptom does not silently replace the main complaint.
            if different and key in ('duration_days','severity','pain_location','sudden_onset','onset'):continue
            if key in ('age_months','duration_days','temperature') and value is not None and previous is not None and value!=previous and not correction:
                self.contradictions.append({'field':key,'previous':previous,'latest':value,'turn':index,'status':'latest_user_value_retained_review_needed'})
            if value is not None: setattr(self.facts,key,value)
        symptoms={v.name:v for v in self.facts.associated_symptoms}
        symptoms.update({v.name:v for v in x.associated_symptoms})
        self.facts.associated_symptoms=list(symptoms.values())
        self.facts.risk_factors=sorted(set(self.facts.risk_factors+x.risk_factors))
        clinical={v.name:v for v in self.facts.clinical_features}
        for v in x.clinical_features:
            if v.name not in clinical or v.status=='affirmed' or correction or self.question in BROAD_QUESTIONS:
                clinical[v.name]=v
        self.facts.clinical_features=list(clinical.values())
        if has(self,'fever_with_complaint'):self.facts.fever=True
        elif has(self,'fever_with_complaint','denied') and x.fever is None:self.facts.fever=False
        if x.temperature is not None and x.temperature_unit is None:self.facts.temperature_unit=None
        for f in x.flags:
            if f.status=='affirmed' or f.flag not in self.flags or correction or self.question=='breathing':
                self.flags[f.flag]=f
        if any(f.status=='historical' for f in x.flags) and re.search(r'yesterday|earlier today|just now|कल|अभी',normalise(text)):
            self.possible_recent_emergency=True
        self.evidence.append({'turn':index,'text':text,'facts':x.model_dump(exclude_none=True)})
        reasons=sorted(set(emergency_evidence(self)+independent_danger))
        self.established_emergencies=reasons if correction else sorted(set(self.established_emergencies+reasons))
        if correction:self.additional_concerns=[]
        if different and independent_concern:self.additional_concerns.append(independent_concern)

def infer_question(turn):
    if turn.question_id in QUESTIONS:return turn.question_id
    text=turn.follow_up_question or turn.text or turn.content or ''
    for q,versions in QUESTIONS.items():
        if text in versions:return q
    t=normalise(text)
    if 'how old' in t or 'उम्र' in t:return 'age'
    if 'how many days' in t or 'कितने दिनों' in t:return 'duration'
    if 'difficulty breathing' in t or 'साँस लेने' in t:return 'breathing'
    return None

def replay(req):
    state=State()
    for i,turn in enumerate(req.conversation_history):
        if turn.role=='assistant':
            state.question=infer_question(turn)
            if state.question:state.asked.append(state.question)
        else:
            t=turn.text or turn.content or ''
            state.merge(extract_local(t,state.question),t,i)
            state.question=None
            state.turns+=1
    state.merge(extract_local(req.user_input,state.question),req.user_input,len(req.conversation_history))
    return state

def active_flags(state):
    flags={k for k,v in state.flags.items() if v.status=='affirmed'}
    f=state.facts
    # Conservative organiser pathway; NHS guidance requires urgent assessment,
    # not an assertion that all infant fevers require an ambulance.
    if f.age_months is not None and f.age_months<3 and f.fever:
        flags.add('high_fever_infant')
    if has(state,'new_one_sided_weakness'):flags.add('stroke_symptoms')
    return sorted(flags)

def concern(state):
    f=state.facts
    expanded=broad_concern(state)
    if expanded:return expanded
    if state.additional_concerns:return state.additional_concerns[-1]
    high=f.temperature is not None and f.temperature_timing!='historical' and ((f.temperature_unit=='F' and f.temperature>=103) or (f.temperature_unit=='C' and f.temperature>=39.4))
    if f.fever and ((f.duration_days or 0)>=5 or high):
        return 'The prolonged or high fever needs prompt medical assessment. Do not wait for this chat to finish to arrange care.'
    if state.possible_recent_emergency:return 'A recently resolved warning sign still needs prompt medical assessment; do not assume it is safe because it stopped.'
    return None

def next_question(state):
    f=state.facts
    if len(state.asked)>=4:return None
    # Explicit procedures bypass unrelated symptom interviews.
    if f.service=='injection_unknown' and 'injection' not in state.asked:return 'injection'
    if f.service in ('dressing','injection_im','injection_iv','insulin','bp_sugar','lab'):return None
    if f.complaint and f.complaint!='fever':
        candidates=question_candidates(state)
        return candidates[0] if candidates else None
    if f.service=='doctor' and not f.fever:return None
    if f.fever:
        if concern(state) and 'breathlessness' not in state.flags and 'breathing' not in state.asked:return 'breathing'
        if f.age_months is None and 'age' not in state.asked:return 'age'
        if 'breathlessness' not in state.flags and 'breathing' not in state.asked:return 'breathing'
        if f.duration_days is None and 'duration' not in state.asked:return 'duration'
        if f.service is None and f.temperature is not None and f.temperature_unit is None and 'temperature' not in state.asked:return 'temperature'
        return None
    if f.service:return None
    return 'need' if 'need' not in state.asked else None

