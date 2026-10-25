"""Complaint-independent, source-mapped safety intents, run on every user turn.

Finite prototype coverage. No diagnoses or clearance; clinician review pending.
Rule evidence retains polarity/time and never enters the controlled flag enum
unless it actually maps to a supported flag. See docs/SAFETY_0_5.md.
"""
import re
from dataclasses import dataclass,asdict
from .assertions import clauses,status,RECENT,recent_event

SOURCES={
 'eye':'https://www.nhs.uk/conditions/eye-injuries/',
 'stroke':'https://www.nhs.uk/conditions/stroke/symptoms/',
 'toxic':'https://www.nhs.uk/conditions/poisoning/',
 'testicular':'https://www.nhs.uk/symptoms/testicle-pain/',
 'medication':'https://www.nhs.uk/medicines/paracetamol-for-adults/',
}
EYE=r'\beyes?\b|eyeball|आँख|आंख|\baankh\b|\bankh\b'
BLOOD=r'\bblood\b|bleed(?:ing)?|खून|khoon|khun'
CHEMICAL=r'toilet (?:bowl )?cleaner|bleach|oven cleaner|drain cleaner|acid|alkali|corrosive|chemical|ब्लीच|तेजाब|रसायन|chemical|tezab'
EXPOSURE=r'(?:in|into)\s+(?:(?:my|his|her|the|left|right)\s+){0,3}eyes?\b|splash|spil(?:l|t)|got into|went into|in my eye|in the eye|in his eye|in her eye|आँख.{0,16}(?:गया|पड़ा)|आंख.{0,16}(?:गया|पड़ा)|aankh.{0,16}(?:gaya|pada)|pad gaya|छींट|gir gaya'
INJURY=r'injur|hit|struck|trauma|ball|punched|चोट|chot|लगा|लगने'
VISION=r'blurr|vision.{0,12}(?:chang|worse|lost)|cannot see|can.t see|धुंध|दिखाई.{0,10}(?:कम|नहीं)|dhundh|dikh.{0,12}(?:nahi|kam)'
PENETRATE=r'pierc|penetrat|stuck through|punctur|धँस|घुस|धंस|ghus|धातु|metal shard|sharp.{0,12}(?:stuck|in)'
FOCAL=r'one side|one.side|left side|right side|left.{0,15}(?:arm|leg|face)|right.{0,15}(?:arm|leg|face)|एक\s*(?:तरफ|ओर)|बाय[ाँाीें]|दाय[ाँाीें]|\b(?:ek|aik)\s*(?:taraf|side)|body ki (?:left|right) side'
NUMB=r'lost\s+(?:feeling|sensation)|loss\s+of\s+(?:feeling|sensation)|(?:cannot|can.t)\s*feel|numb|weak|सुन्न|कमजोर|sunn?|kamzor'
ACUTE=r'sudden|suddenly|new|just now|अचानक|अभी|अब|achanak|abhi|aaj'
SPEECH=r'(?:cannot|can.t|unable to).{0,10}speak clearly|speech.{0,16}slurr|slurr.{0,10}(?:words|speech)|words.{0,15}slurr|बोली.{0,10}लड़खड़ा|बोलने.{0,10}दिक्कत|bol.{0,12}(?:ladkh|dikkat)'
FACE=r'face.{0,25}(?:droop|dropped)|chehra.{0,10}tedha|चेहरा.{0,12}टेढ़ा'
TOXIN=r'\bpoison\b|bleach|pesticide|insecticide|rat poison|cleaning (?:fluid|product)|toilet (?:bowl )?cleaner|paint thinner|petrol|gasoline|drain cleaner|detergent|corrosive|acid|kerosene|ब्लीच|कीटनाशक|जहर|ज़हर|तेजाब|phenyl|फिनाइल|zeher|zahar|chuhe.{0,15}marne.{0,10}dawa|चूहे.{0,15}मारने.{0,10}दवा'
INGEST=r'swallow|drank|drink|ingest|consum|पी\s*(?:लिया|गया|ली)|खा\s*लिया|निगल|pi\s*(?:liya|li)|pee\s*liya|nigal|kha\s*(?:li|liya)'
TESTICLE=r'testicles?|testicular|scrot(?:um|al)|अंडकोष|अण्डकोष|andkosh'
PAIN=r'pain|ache|दर्द|dard'
SEVERE=r'severe|unbearable|extreme|बहुत\s*तेज|असहनीय|bahut\s*tez'

@dataclass
class Finding:
    rule_id:str
    status:str
    disposition:str
    quote:str
    source_url:str
    reason:str
    flag:str|None=None
    def dump(self):return asdict(self)

def screen(text):
    findings=[];eye_context=False;injury_context=False;pending_focal=False
    for raw,t,inherited in clauses(text):
        previous_focal=pending_focal;pending_focal=False
        def emit(rule,pattern,source,reason,flag=None,disposition='emergency',uncertainty=True):
            hit=re.search(pattern,t)
            if not hit:return
            polarity=status(t,hit,inherited,uncertainty)
            supports={
                'eye_chemical':[CHEMICAL,EXPOSURE], 'eye_injury_vision':[INJURY,VISION],
                'eye_severe_pain':[PAIN,SEVERE], 'focal_neurology':[FOCAL,NUMB],
                'toxic_ingestion':[TOXIN,INGEST], 'acute_testicular_pain':[TESTICLE,PAIN,SEVERE,ACUTE],
            }.get(rule,[])
            for component in supports:
                part=re.search(component,t)
                if part and status(t,part,inherited,uncertainty)=='denied':polarity='denied'
            if rule=='face_droop' and re.search(r'face.{0,16}(?:not|isn.t|wasn.t).{0,8}(?:droop|drop)',t):polarity='denied'
            if rule=='eye_injury_vision' and re.search(r'no (?:change|vision change)|unchanged|vision.{0,10}(?:normal|fine|not changed)',t):polarity='denied'
            if rule=='eye_discharge_blood' and re.search(r'not\s*bleed|(?:blood|खून|khoon).{0,6}(?:नहीं|nahi)',t):polarity='denied'
            # The caller composes affirmative evidence below; no blanket
            # keyword-to-emergency route for eye, numbness or medication alone.
            findings.append(Finding(rule,polarity,disposition,raw.strip(),SOURCES[source],reason,flag))
        eye=re.search(EYE,t)
        if eye and status(t,eye,inherited)=='affirmed':eye_context=True
        injury=re.search(INJURY,t)
        if eye_context and injury and status(t,injury,inherited)=='affirmed':injury_context=True
        if eye or eye_context and re.search(VISION,t):
            if re.search(CHEMICAL,t) and re.search(EXPOSURE,t):
                emit('eye_chemical',EXPOSURE,'eye','Possible harmful chemical exposure to the eye')
            if re.search(PENETRATE,t):emit('eye_penetrating',PENETRATE,'eye','Possible penetrating eye injury')
            # A red spot ON the white is not blood coming OUT of the eye.
            blood_flow=r'(?:blood|pus).{0,32}(?:coming|running|flow|ooz|leak|out|from)|(?:eye|aankh|ankh).{0,35}(?:bleed|खून.{0,12}(?:निकल|बह)|khoon.{0,14}(?:nikal|beh))|(?:आँख|आंख).{0,35}खून.{0,15}(?:निकल|बह)'
            if re.search(blood_flow,t):emit('eye_discharge_blood',blood_flow,'eye','Reported blood or pus coming from the eye')
            if injury_context and re.search(VISION,t):emit('eye_injury_vision',VISION,'eye','Reported vision change after eye injury')
            if re.search(SEVERE,t) and re.search(PAIN,t):emit('eye_severe_pain',SEVERE,'eye','Reported severe eye pain')
        if previous_focal and (re.search(ACUTE,t) or recent_event(t)) and re.search(r'this|it|started|began|शुरू',t):
            findings.append(Finding('focal_neurology',inherited or 'affirmed','emergency',text.strip(),SOURCES['stroke'],'New one-sided numbness or weakness','stroke_symptoms'))
        if re.search(FOCAL,t) and re.search(NUMB,t) and not inherited:
            m=re.search(NUMB,t)
            pending_focal=status(t,m)=='affirmed'
        if re.search(FOCAL,t) and re.search(NUMB,t) and (re.search(ACUTE,t) or recent_event(t)):
            emit('focal_neurology',NUMB,'stroke','New or recently resolved one-sided numbness or weakness','stroke_symptoms')
        if re.search(SPEECH,t) and (re.search(ACUTE,t) or recent_event(t)):
            emit('acute_speech',SPEECH,'stroke','New or recently resolved speech difficulty','stroke_symptoms')
        if re.search(FACE,t):emit('face_droop',FACE,'stroke','Reported facial droop','stroke_symptoms')
        if re.search(TOXIN,t) and re.search(INGEST,t):
            emit('toxic_ingestion',INGEST,'toxic','Possible ingestion of a harmful substance',uncertainty=False)
        if re.search(TESTICLE,t) and re.search(PAIN,t) and re.search(ACUTE,t) and re.search(SEVERE,t):
            emit('acute_testicular_pain',TESTICLE,'testicular','Sudden severe testicular pain')
        # Urgent human review, not a toxic-dose calculation or automatic
        # ambulance claim. A high tablet count never establishes a safe dose.
        medicine=r'paracetamol|acetaminophen|medicine|medication|tablets?|pills?|दवा|गोलियाँ|गोलियां'
        excess=r'overdose|too many|more than (?:prescribed|recommended)|handful|extra doses|ज्यादा.{0,12}दवा|बहुत.{0,12}गोलि'
        high_count=r'\b(?:9|[1-9]\d+|nine|ten|eleven|twelve|twenty)\s+(?:paracetamol\s+)?(?:tablets?|pills?)\b'
        if re.search(medicine,t) and (re.search(excess,t) or re.search(high_count,t) and (recent_event(t) or re.search(r'at once|together|one dose',t))):
            emit('medication_excess',excess+'|'+high_count,'medication','Possible excess medication needs urgent professional assessment now',disposition='urgent_assessment')
    return findings

def actionable(findings):
    return [f for f in findings if f.status in ('affirmed','recent_resolved')]
