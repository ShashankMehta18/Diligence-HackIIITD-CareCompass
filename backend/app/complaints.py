"""Complaint-aware intake and reviewed-rule candidates, never a diagnostic engine.
See docs/BROAD_INTAKE.md for source-to-rule mappings and scope limitations.
All 'emergency' predicates require affirmative evidence, not keyword presence.
"""
import re
import unicodedata
from dataclasses import dataclass
from .schemas import ClinicalFinding,SymptomEvidence

def norm(s):
    return unicodedata.normalize('NFKC',s).casefold().translate(str.maketrans('०१२३४५६७८९','0123456789'))

BODY_SITES={
 'knee':r'\bknees?\b|\bghutn\w*\b|घुटन\w*',
 'ankle':r'\bankles?\b|\btakhn\w*\b|टखन\w*',
 'foot':r'\b(?:foot|feet)\b|पाँव|पांव',
 'hip':r'\bhips?\b|कूल्ह\w*',
 'leg':r'\blegs?\b|\bpair\b|पैर',
 'shoulder':r'\bshoulders?\b|\bkandh\w*\b|कंध\w*',
 'elbow':r'\belbows?\b|कोहनी',
 'wrist':r'\bwrists?\b|कलाई',
 'hand':r'\bhands?\b|\bhaath?\b|हाथ',
 'arm':r'\barms?\b|बाँह|बांह',
}
LIMB=r'(?:knees?|ankles?|foot|feet|hips?|legs?|shoulders?|elbows?|wrists?|hands?|arms?|ghutn\w*|pair|घुटन\w*|टखन\w*|पैर|कलाई|कंध\w*|हाथ|जोड़\w*)'

# Order gives focal complaints precedence over accompanying fever/fatigue.
COMPLAINT_PATTERNS={
 'abdominal_pain':r'(?:stomach|tummy|belly|abdom(?:en|inal))\s*(?:aches?|hurts?|pain|cramp)|(?:pain|ache|cramp).{0,18}(?:stomach|tummy|belly|abdomen)|\b(?:pet|pait)\b.{0,16}(?:dard|pain)|पेट.{0,12}(?:दर्द|ऐंठन)',
 'headache':r'head\s*ache|head\s+pain|(?:sar|sir)\s*(?:me|mein)?\s*dard|सिर.{0,10}दर्द',
 'vomiting':r'\bvomit(?:ing|ed|s)?\b|throw(?:ing)?\s+up|\bulti\b|उल्टी',
 'diarrhoea':r'diarrh(?:oe|e)a|loose\s*(?:motions?|stools?)|watery\s*(?:stools?|poo)|दस्त|पतला\s*पाखाना',
 'sore_throat':r'sore\s*throat|throat\s*pain|pain.{0,18}throat|gale?\s*(?:me|mein)?\s*(?:dard|kharash)|गले.{0,12}(?:दर्द|खराश)',
 'cough':r'\bcough(?:ing)?\b|khansi|खांसी|खाँसी',
 'urinary':r'(?:burn(?:s|ing)?|pain|hurt).{0,20}(?:urinat|pee)|(?:urinat|pee).{0,20}(?:burn(?:s|ing)?|pain|hurt)|urinary|peshab.{0,15}(?:jalan|dard)|पेशाब.{0,12}(?:जलन|दर्द|नहीं)',
 'back_pain':r'back\s*(?:ache|pain)|pain.{0,12}back|kamar.{0,12}dard|कमर.{0,12}दर्द|पीठ.{0,12}दर्द',
 'joint_pain':rf'joints?\s*(?:pain|aches?|hurt)|{LIMB}.{{0,25}}(?:pain|aches?|hurts?|dard|दर्द)|(?:pain|ache|hurt|dard|दर्द).{{0,25}}{LIMB}|jodon.{{0,12}}dard|जोड़ों.{{0,12}}दर्द',
 'rash':r'\brash\b|itch(?:y|ing)\s*skin|skin\s*itch|चकत्ते|खुजली',
 'dizziness':r'\bdizz(?:y|iness)\b|light.?headed|chakkar|चक्कर',
 'eye_problem':r'eye\s*(?:pain|ache|red|problem)|(?:pain|ache).{0,18}\beyes?\b|(?:red|painful|sore)\s*eye|vision\s*(?:loss|problem)|आँख.{0,12}(?:दर्द|लाल)|आंख.{0,12}दर्द',
 'ear_pain':r'ear\s*(?:ache|pain)|(?:pain|ache).{0,18}\bears?\b|kaan.{0,10}dard|कान.{0,12}दर्द',
 'dental_pain':r'tooth\s*(?:ache|pain)|(?:pain|ache).{0,18}\b(?:tooth|teeth)\b|dental\s*pain|daant.{0,12}dard|दाँत.{0,12}दर्द|दांत.{0,12}दर्द',
 'injury':r'\binjur(?:y|ed)\b|sprain|twisted\s*(?:(?:my|the|his|her|left|right)\s*)*(?:ankle|knee|wrist|foot|arm)|\bcut\b|चोट|मोच',
 'fatigue':r'\bfatigue\b|\bweak(?:ness)?\b|\btired\b|कमजोर|थकान',
 'fever':r'\bfever\b|bukhar|बुखार',
}

LABELS={
 'abdominal_pain':('stomach pain','पेट दर्द'),'headache':('headache','सिरदर्द'),
 'vomiting':('vomiting','उल्टी'),'diarrhoea':('diarrhoea','दस्त'),'cough':('cough','खाँसी'),
 'sore_throat':('sore throat','गले में दर्द'),'urinary':('urinary symptoms','पेशाब की तकलीफ़'),
 'back_pain':('back pain','पीठ दर्द'),'joint_pain':('joint pain','जोड़ों में दर्द'),
 'rash':('rash or itching','चकत्ते या खुजली'),'dizziness':('dizziness','चक्कर'),
 'injury':('injury','चोट'),'eye_problem':('eye symptoms','आँख की तकलीफ़'),
 'ear_pain':('ear pain','कान दर्द'),'dental_pain':('tooth pain','दाँत दर्द'),
 'fatigue':('weakness or tiredness','कमज़ोरी या थकान'),'fever':('fever','बुखार'),
 'other':('reported symptoms','बताए गए लक्षण')}

FEATURE_PATTERNS={
 'abdominal_tenderness':r'(?:stomach|tummy|abdomen|belly).{0,35}(?:hurt|pain).{0,16}(?:touch|press)|(?:touch|press).{0,25}(?:stomach|tummy|abdomen).{0,20}(?:hurt|pain)|पेट.{0,12}(?:छूने|दबाने).{0,12}दर्द|pet.{0,12}(?:chune|dabane).{0,12}dard',
 'vomiting_blood':r'vomit(?:ing|ed)?\s*(?:bright\s*red\s*)?blood|blood\s+in\s+(?:my\s+|the\s+)?vomit|vomit.{0,12}coffee\s*ground|खून\s*की\s*उल्टी|उल्टी.{0,10}खून|ulti.{0,10}khoon',
 'black_sticky_stool':r'black\s*(?:and\s*)?(?:sticky|tarry)\s*(?:stools?|poo)|black\s*stools?.{0,12}sticky|(?:stools?|poo).{0,12}black.{0,12}(?:sticky|tarry)',
 'blood_in_stool':r'blood\s+in\s+(?:my\s+|the\s+)?(?:stool|poo)|stools?.{0,10}blood|पाखान.{0,12}खून',
 'sudden_worst_headache':r'(?:sudden|suddenly|thunderclap).{0,35}(?:worst|severe|extremely\s*painful).{0,12}headache|worst\s*headache.{0,30}(?:sudden|seconds)|अचानक.{0,12}(?:बहुत\s*तेज|तेज).{0,12}सिर.{0,8}दर्द',
 'new_one_sided_weakness':r'(?:new|sudden).{0,12}(?:one.side|one side).{0,12}weak|अचानक.{0,8}एक\s*तरफ.{0,8}कमजोर',
 'vision_loss':r'(?:lost|loss\s*of|losing).{0,12}(?:my\s*)?vision|(?:cannot|can.t)\s*see|अचानक.{0,12}दिखाई\s*नहीं',
 'new_confusion':r'(?:sudden|suddenly|new).{0,12}confus|अचानक.{0,10}उलझन',
 'airway_swelling':r'(?:tongue|throat|lips?).{0,20}(?:swell|swollen)|(?:swelling|swollen).{0,15}(?:tongue|throat|lips?)|गले.{0,12}सूजन|जीभ.{0,12}सूज|(?:gale|gala|jeebh).{0,12}sujan',
 'cannot_swallow_saliva':r'(?:cannot|can.t|unable\s*to)\s*swallow\s*(?:my\s*)?saliva|लार.{0,8}निगल.{0,8}नहीं',
 'bladder_change':r'(?:new|sudden).{0,25}(?:bladder|bowel).{0,20}(?:control|accident)|(?:lost|losing).{0,12}(?:bladder|bowel)\s*control',
 'saddle_numbness':r'numb(?:ness)?.{0,20}(?:genitals|groin|anus|between\s*(?:my\s*)?legs)',
 'can_keep_fluids':r'(?:can|able\s*to)\s*keep\s*(?:water|fluids?|drinks?)\s*down',
 'urine_retention':r'(?:cannot|can.t|unable\s*to)\s*(?:pee|pass\s*(?:any\s*)?urine|urinate)(?:\s*at\s*all)?|पेशाब\s*बिल्कुल\s*नहीं',
 'flank_pain':r'(?:pain|ache).{0,12}(?:my\s*)?(?:side|flank)|flank\s*pain',
 'blood_in_urine':r'blood\s*in\s*(?:my\s*)?urine|पेशाब.{0,10}खून',
 'fever_with_complaint':r'\bfever\b|bukhar|बुखार',
 'cannot_bear_weight':r'(?:cannot|can.t|unable\s*to)\s*(?:bear\s*weight|stand\s*on|walk\s*on)',
 'nonblanching_rash':r'rash.{0,30}(?:does\s*not|doesn.t)\s*fade|non.?blanching\s*rash',
 'ear_discharge':r'(?:fluid|pus|discharge).{0,25}(?:ear)|ear.{0,25}(?:discharge|leaking\s*fluid)|कान.{0,15}(?:पानी|मवाद|बहना)',
 'hearing_change':r'(?:lost|loss\s*of|reduced|change\s*in).{0,15}hearing|(?:cannot|can.t|hard\s*to|difficulty).{0,12}hear|सुनाई.{0,10}(?:कम|नहीं)',
 'dental_swelling':r'(?:swollen|swelling).{0,20}(?:gum|cheek|jaw)|(?:gum|cheek|jaw).{0,20}(?:swollen|swelling)|(?:मसूड़|गाल|जबड़).{0,15}सूज',
}

HISTORICAL=r'\b(?:last\s*year|years?\s*ago|history\s*of|used\s*to|resolved|no\s*longer)\b|पिछले\s*साल'
HYPOTHETICAL=r'\b(?:what\s*if|hypothetical|example|quoted|if\s*(?:someone|i|he|she))\b|अगर|agar'

def status_of(text,hit,name=None):
    if re.search(HYPOTHETICAL,text):return 'hypothetical'
    if re.search(HISTORICAL,text):return 'historical'
    if name=='airway_swelling' and re.search(r'(?:not|no)\s*(?:swell|swollen)|(?:swelling|swollen)\s*(?:nahi|नहीं)',hit[0]):return 'denied'
    before=text[max(0,hit.start()-38):hit.start()];after=text[hit.end():hit.end()+18]
    # Match-aware scope: "no vomiting blood" is denied, whereas the 'cannot'
    # embedded in inability-to-swallow/urinate is the affirmative danger sign.
    if re.search(r'(?:\bno\b|\bnot\b|\bdenies\b|\bwithout\b)\s*(?:(?:any|been|having|currently|ever|sudden|severe|worst|mild|current|a|very|extremely)\s*)*$',before) or re.search(r'^\s*(?:nahi|nahin|नहीं)',after):return 'denied'
    return 'affirmed'

def detect_features(text):
    result={}
    for clause in re.split(r'[,;!?\n]|\.(?!\d)|\bbut\b|लेकिन|\blekin\b|\band\s+now\b',norm(text)):
        for name,p in FEATURE_PATTERNS.items():
            m=re.search(p,clause)
            if m:
                status=status_of(clause,m,name)
                if name not in result or status=='affirmed':result[name]=ClinicalFinding(name=name,status=status,quote=text)
        # Negative polarity is the information for this positively-worded field.
        if re.search(r'(?:cannot|can.t|unable\s*to)\s*keep\s*(?:water|fluids?|drinks?)\s*down|पानी.{0,10}(?:रुकता\s*नहीं|नहीं\s*रुक)',clause):
            result['can_keep_fluids']=ClinicalFinding(name='can_keep_fluids',status='denied',quote=text)
    return list(result.values())

def limb_features(text,question=None):
    """Interpret limb findings only with a limb or a limb-specific question.

    Match the finding word itself so 'knee is not swollen' scopes the denial
    correctly. Findings about other body regions must not populate this screen.
    """
    result={}
    contextual=question in LIMB_QUESTION_IDS or bool(re.search(LIMB+r'|\bjoint\b',norm(text)))
    for clause in re.split(r'[,;!?\n]|\.(?!\d)|\bbut\b|लेकिन|\blekin\b',norm(text)):
        if re.search(r'\b(?:throat|tongue|lips?|ear|eye|cheek|gum|jaw|abdomen)\b|गले|जीभ|कान|आँख|आंख|मसूड़|जबड़',clause) and not re.search(LIMB,clause):continue
        if not contextual and not re.search(LIMB+r'|\bjoint\b',clause):continue
        for name,pattern in {
            'recent_injury':r'\binjur(?:y|ed)\b|\bfall(?:ing|en)?\b|\bfell\b|\btwist(?:ed)?\b|\bsprain\b|\baccident\b|चोट|मोच|गिर(?:ने|ा|ी)|gir\w*|chot',
            'joint_swelling':r'\b(?:swelling|swollen)\b|\bsujan\b|सूजन|सूज',
            'joint_severe_swelling':r'\b(?:badly|very|severely|extremely)\s*swollen|\b(?:severe|large)\s*(?:amounts?\s*of\s*)?swelling|बहुत\s*(?:सूजन|सूज)',
            'joint_hot_red':r'\b(?:hot|warm|red|redness)\b|गर्म|लाल',
            'cannot_move_joint':r'(?:cannot|can.t|unable\s*to|not\s*able\s*to)\s*(?:bend|straighten|move|use)|(?:मोड़|हिला).{0,12}नहीं|(?:mod|hila).{0,15}nahi',
            'joint_locking':r'\b(?:locks?|locking|locked)\b|\bgiv(?:es?|ing)\s*way\b|अटक|फँस',
            'limb_deformity':r'\b(?:deformed|misshapen)\b|changed\s*shape|looks?\s*crooked|टेढ़',
            'limb_numbness':r'\bnumb(?:ness)?\b|pins\s*and\s*needles|सुन्न',
            'cannot_bear_weight':r'(?:cannot|can.t|unable\s*to|not\s*able\s*to)\s*(?:walk|stand|bear\s*weight|put\s*(?:any\s*)?weight)|चल.{0,12}नहीं|chal.{0,15}nahi',
        }.items():
            m=re.search(pattern,clause)
            if m:
                status=status_of(clause,m,name)
                prefix=clause[:m.start()]
                if status=='affirmed' and re.search(r'(?:\bno|\bnot)\s+(?:(?:my|the|recent|any|'+LIMB+r'|joint)\s+)*$',prefix):status='denied'
                if status=='affirmed' and re.search(r'\bno\b[^,;.!?]{0,45}\b(?:or|and)\s*$',prefix):status='denied'
                result[name]=ClinicalFinding(name=name,status=status,quote=text)
        # Positive function answers explicitly deny the corresponding inability.
        for name,pattern in {
            'cannot_bear_weight':r'\b(?:can|able\s*to)\s*(?:walk|stand|bear\s*weight|put\s*weight)|चल\s*सक|chal\s*sak',
            'cannot_move_joint':r'\b(?:can|able\s*to)\s*(?:walk\s*and\s*)?(?:bend|straighten|move|use)|मोड़\s*सक|हिला\s*सक|hila\s*sak|mod\s*sak',
        }.items():
            m=re.search(pattern,clause)
            if m and status_of(clause,m)=='affirmed' and name not in result:
                result[name]=ClinicalFinding(name=name,status='denied',quote=text)
    return list(result.values())

@dataclass(frozen=True)
class Question:
    en: str
    hi: str
    field: str | None = None
    feature: str | None = None
    yes_affirms: bool = True
    choices: tuple = ('Yes','No','Not sure')

BROAD_QUESTIONS={
 'symptom_age':Question('How old is the person with these symptoms?','इन लक्षणों वाले व्यक्ति की उम्र कितनी है?',field='age_months',choices=()),
 'symptom_severity':Question('How severe are the symptoms: mild, moderate, or severe?','लक्षण कितने गंभीर हैं: हल्के, मध्यम या बहुत गंभीर?',field='severity',choices=('Mild','Moderate','Severe')),
 'abdominal_severity':Question('How severe is the stomach pain: mild, moderate, or severe?','पेट दर्द कितना है: हल्का, मध्यम या बहुत तेज़?',field='severity',choices=('Mild','Moderate','Severe')),
 'sudden_pain':Question('Did the pain start suddenly?','क्या दर्द अचानक शुरू हुआ?',field='sudden_onset'),
 'abdominal_touch':Question('Does touching your abdomen cause pain?','क्या पेट को छूने पर दर्द होता है?',feature='abdominal_tenderness'),
 'abdominal_location':Question('Where in your abdomen is the pain strongest?','पेट में किस जगह दर्द सबसे ज़्यादा है?',field='pain_location',choices=()),
 'symptom_duration':Question('How long have you had these symptoms?','ये लक्षण कितने समय से हैं?',field='duration_days',choices=()),
 'headache_sudden':Question('Did this headache become extremely painful within seconds or minutes?','क्या यह सिरदर्द कुछ सेकंड या मिनटों में बहुत तेज़ हो गया?',feature='sudden_worst_headache'),
 'one_sided_weakness':Question('Have you developed new weakness on one side of your body?','क्या शरीर के एक तरफ़ नई कमज़ोरी हुई है?',feature='new_one_sided_weakness'),
 'blood_vomit':Question('Have you vomited any blood?','क्या उल्टी में खून आया है?',feature='vomiting_blood'),
 'blood_stool':Question('Have you noticed blood in your stool?','क्या मल में खून आया है?',feature='blood_in_stool'),
 'keep_fluids':Question('Can you keep water or other fluids down?','क्या पानी या दूसरे तरल पदार्थ पीने पर पेट में रुक रहे हैं?',feature='can_keep_fluids'),
 'swallow_saliva':Question('Can you swallow your saliva normally?','क्या आप अपनी लार सामान्य रूप से निगल पा रहे हैं?',feature='cannot_swallow_saliva',yes_affirms=False),
 'airway_swelling':Question('Is your tongue or throat swelling?','क्या जीभ या गले में सूजन हो रही है?',feature='airway_swelling'),
 'vision_loss':Question('Have you lost vision in either eye?','क्या किसी आँख से दिखना बंद हो गया है?',feature='vision_loss'),
 'bladder_change':Question('Have you developed new loss of bladder control with the back pain?','क्या पीठ दर्द के साथ पेशाब पर नियंत्रण में नई समस्या हुई है?',feature='bladder_change'),
 'saddle_numbness':Question('Have you developed numbness around your groin or genitals?','क्या जाँघों के बीच या जननांगों के आसपास सुन्नपन हुआ है?',feature='saddle_numbness'),
 'urine_retention':Question('Are you completely unable to pass urine?','क्या पेशाब बिल्कुल नहीं हो रहा है?',feature='urine_retention'),
 'flank_pain':Question('Do you also have pain in your side or flank?','क्या शरीर के बगल या कमर के एक तरफ़ भी दर्द है?',feature='flank_pain'),
 'associated_fever':Question('Have you also developed a fever?','क्या साथ में बुखार भी हुआ है?',feature='fever_with_complaint'),
 'bear_weight':Question('Can you put weight on the injured limb?','क्या चोट वाले हाथ या पैर पर भार डाल पा रहे हैं?',feature='cannot_bear_weight',yes_affirms=False),
 'symptom_detail':Question('What symptom is bothering you most?','कौन सा लक्षण सबसे ज़्यादा परेशान कर रहा है?',field='complaint_text',choices=()),
 'symptom_change':Question('Are the symptoms getting worse, improving, or staying the same?','क्या लक्षण बढ़ रहे हैं, कम हो रहे हैं या वैसे ही हैं?',field='progression',choices=('Getting worse','Improving','Staying the same')),
 'joint_site':Question('Which joint or part of the arm or leg is painful?','किस जोड़ या हाथ-पैर के किस हिस्से में दर्द है?',field='body_site',choices=()),
 'ear_discharge':Question('Is any fluid or pus coming out of the painful ear?','क्या दर्द वाले कान से पानी या मवाद निकल रहा है?',feature='ear_discharge'),
 'hearing_change':Question('Has your hearing changed or become reduced with the ear pain?','क्या कान दर्द के साथ सुनाई देना कम हुआ है या बदला है?',feature='hearing_change'),
 'dental_swelling':Question('Is there swelling around the painful tooth, gum, cheek or jaw?','क्या दर्द वाले दाँत, मसूड़े, गाल या जबड़े के आसपास सूजन है?',feature='dental_swelling'),
}

# Concrete wording doubles as a stable replay key; neither UI nor model needs
# to invent a question. Upper-limb questions never ask about standing on an arm.
LIMB_QUESTION_IDS={'joint_site','bear_weight'}
SITE_LABELS={'knee':('knee','घुटने'),'ankle':('ankle','टखने'),'foot':('foot','पाँव'),'hip':('hip','कूल्हे'),'leg':('leg','पैर'),'shoulder':('shoulder','कंधे'),'elbow':('elbow','कोहनी'),'wrist':('wrist','कलाई'),'hand':('hand','हाथ'),'arm':('arm','बाँह'),'joint':('affected joint','दर्द वाले जोड़')}
LOWER_LIMB={'knee','ankle','foot','hip','leg'}
for site,(en,hi) in SITE_LABELS.items():
    specs={
        'severity':Question(f'How severe is the pain in your {en}: mild, moderate, or severe?',f'{hi} में दर्द कितना है: हल्का, मध्यम या बहुत तेज़?',field='severity',choices=('Mild','Moderate','Severe')),
        'injury':Question(f'Did the {en} pain start after an injury, fall or twist?',f'क्या {hi} का दर्द चोट, गिरने या मुड़ने के बाद शुरू हुआ?',feature='recent_injury'),
        'swelling':Question(f'Is there swelling around your {en}?',f'क्या {hi} के आसपास सूजन है?',feature='joint_swelling'),
        'hot_red':Question(f'Is the skin around your painful {en} hot or red?',f'क्या दर्द वाले {hi} के आसपास की त्वचा गर्म या लाल है?',feature='joint_hot_red'),
        'movement':Question(f'Can you bend, straighten or move your {en}?',f'क्या आप {hi} को मोड़, सीधा या हिला पा रहे हैं?',feature='cannot_move_joint',yes_affirms=False),
        'weight':Question(f'Can you stand and put weight on the leg with the painful {en}?',f'क्या आप दर्द वाले {hi} की तरफ़ के पैर पर खड़े होकर भार डाल पा रहे हैं?',feature='cannot_bear_weight',yes_affirms=False),
    }
    for suffix,spec in specs.items():
        key=f'{site}_{suffix}';BROAD_QUESTIONS[key]=spec;LIMB_QUESTION_IDS.add(key)

YES=r'(?:yes|yeah|haan|han|ji|हाँ|हां|जी)'
NO=r'(?:no|nope|nahi|nahin|नहीं|नही)'

def enrich(x,text,question=None):
    t=norm(text).strip()
    found=[]
    for name,pattern in COMPLAINT_PATTERNS.items():
        hits=list(re.finditer(pattern,t))
        if hits:
            statuses=[status_of(t,m) for m in hits]
            status='affirmed' if 'affirmed' in statuses else statuses[-1]
            if status=='affirmed':found.append(name)
            if name not in {v.name for v in x.associated_symptoms}:
                x.associated_symptoms.append(SymptomEvidence(name=name,status=status if status in ('affirmed','denied') else 'unknown',quote=text))
    if found:x.complaint=found[0];x.complaint_text=text[:300]
    elif not x.service and re.search(r'\b(?:i (?:have|feel)|my .{0,20}(?:hurts|aches)|symptoms?)\b|मुझे|तकलीफ',t) and not re.search(HYPOTHETICAL,t):
        x.complaint='other';x.complaint_text=text[:300]
    clinical={v.name:v for v in detect_features(text)}
    clinical.update({v.name:v for v in limb_features(text,question)})
    x.clinical_features=list(clinical.values())
    if x.complaint in ('joint_pain','injury') or question in LIMB_QUESTION_IDS:
        for site,pattern in BODY_SITES.items():
            if re.search(pattern,t):x.body_site=site;break
    # Severity belongs to an affirmative reported complaint or a severity answer.
    if found or (question in BROAD_QUESTIONS and BROAD_QUESTIONS[question].field=='severity'):
        for value,pattern in [('severe',r'\b(?:severe|unbearable|extreme|worst)\b|बहुत\s*तेज|बहुत\s*गंभीर|असहनीय'),('moderate',r'\bmoderate\b|मध्यम'),('mild',r'\bmild\b|हल्का|हल्के')]:
            m=re.search(pattern,t)
            if m and status_of(t,m)=='affirmed':x.severity=value;break
        score=re.search(r'\b(10|[0-9])\s*/\s*10\b',t)
        if score:x.severity='severe' if int(score[1])>=7 else 'moderate' if int(score[1])>=4 else 'mild'
    onsets=[status_of(t,m) for m in re.finditer(r'\b(?:sudden|suddenly)\b|अचानक|achanak',t)]
    if 'affirmed' in onsets:x.sudden_onset=True
    elif 'denied' in onsets or re.search(r'gradual|not\s*sudden|अचानक\s*नहीं',t):x.sudden_onset=False
    locations=[('lower right',r'lower\s*right|दाईं\s*नीचे|दाहिने\s*निचले'),('lower left',r'lower\s*left|बाईं\s*नीचे'),('upper right',r'upper\s*right'),('upper left',r'upper\s*left'),('upper abdomen',r'upper\s*(?:abdomen|stomach)'),('lower abdomen',r'lower\s*(?:abdomen|stomach)'),('around the navel',r'navel|belly\s*button|नाभि')]
    for value,pattern in locations:
        if re.search(pattern,t):x.pain_location=value;break
    # Duration supports hours/minutes, word numbers and Devanagari digits; age
    # replies are handled separately so 2 months old is never 2 months of pain.
    if question not in ('age','symptom_age'):
        hours=list(re.finditer(r'(\d+(?:\.\d+)?|one|two|three|four|six|एक|दो|तीन|चार)\s*(hours?|hrs?|minutes?|mins?|घंटे|घंटों|मिनट)',t))
        if hours:
            m=hours[-1];words={'one':1,'two':2,'three':3,'four':4,'six':6,'एक':1,'दो':2,'तीन':3,'चार':4}
            n=float(m[1]) if m[1][0].isdigit() else words[m[1]]
            x.duration_days=n/(1440 if m[2].startswith(('min','मिनट')) else 24)
    q=BROAD_QUESTIONS.get(question)
    if q:
        answer=True if re.fullmatch(YES+r'[.! ]*',t) else False if re.fullmatch(NO+r'[.! ]*',t) else None
        if q.feature and answer is not None and q.feature not in {v.name for v in x.clinical_features}:
            affirmative=answer==q.yes_affirms
            x.clinical_features=[f for f in x.clinical_features if f.name!=q.feature]+[ClinicalFinding(name=q.feature,status='affirmed' if affirmative else 'denied',quote=text)]
        if q.field=='sudden_onset' and answer is not None:x.sudden_onset=answer
        if q.field=='complaint_text':x.complaint_text=text[:300];x.complaint=x.complaint or 'other'
        if q.field=='pain_location' and len(t)<100 and not re.fullmatch(r'not sure|unknown|पता नहीं',t):x.pain_location=x.pain_location or text
    if re.search(r'staying\s*the\s*same|unchanged|वैसे\s*ही',t):x.progression='unchanged'
    return x

def features(state):return {x.name:x for x in state.facts.clinical_features}

def has(state,name,status='affirmed'):
    f=features(state).get(name)
    return f is not None and f.status==status

def emergency_evidence(state):
    f=state.facts;reasons=[]
    always={'vomiting_blood':'Blood in vomit','black_sticky_stool':'Black, sticky stool','sudden_worst_headache':'Sudden extremely painful headache','vision_loss':'Loss of vision','new_confusion':'New sudden confusion','airway_swelling':'Tongue or throat swelling','cannot_swallow_saliva':'Unable to swallow saliva'}
    for name,description in always.items():
        if has(state,name):reasons.append(description)
    if has(state,'abdominal_tenderness'):reasons.append('Abdominal pain on touch')
    if f.complaint=='abdominal_pain':
        if f.severity=='severe' and f.sudden_onset is True:reasons.append('Sudden severe abdominal pain')
    if f.complaint=='headache' and f.severity=='severe' and f.sudden_onset is True:reasons.append('Sudden extremely painful headache')
    if f.complaint=='eye_problem' and f.sudden_onset is True:reasons.append('Sudden-onset eye symptoms')
    present={f.complaint}|{v.name for v in f.associated_symptoms if v.status=='affirmed'}
    if 'back_pain' in present:
        if has(state,'bladder_change'):reasons.append('New bladder-control change with back pain')
        if has(state,'saddle_numbness'):reasons.append('Groin numbness with back pain')
    if has(state,'urine_retention') and present & {'abdominal_pain','urinary'}:reasons.append('Unable to pass urine')
    if has(state,'nonblanching_rash') and f.fever:reasons.append('Fever with a non-fading rash')
    return reasons

def broad_concern(state):
    f=state.facts;c=f.complaint
    if c=='abdominal_pain' and 'pregnancy' in f.risk_factors:return 'Abdominal pain during pregnancy needs prompt in-person medical assessment.'
    if c=='abdominal_pain' and f.pain_location and 'lower right' in f.pain_location and f.progression=='worsening':return 'Worsening lower-right abdominal pain needs prompt in-person medical assessment.'
    if c in ('abdominal_pain','headache','back_pain','eye_problem','dental_pain','ear_pain') and f.severity=='severe':return 'The reported severe pain needs prompt in-person medical assessment.'
    if has(state,'can_keep_fluids','denied'):return 'Being unable to keep fluids down needs prompt medical assessment for dehydration risk.'
    if has(state,'blood_in_stool') or has(state,'blood_in_urine'):return 'Reported blood needs prompt in-person medical assessment.'
    if c=='urinary' and (f.fever or has(state,'flank_pain')):return 'Urinary symptoms with fever or flank pain need prompt in-person medical assessment.'
    if c=='injury' and has(state,'cannot_bear_weight'):return 'An injury that prevents weight bearing needs prompt in-person assessment.'
    if c in ('joint_pain','injury'):
        site=SITE_LABELS.get(f.body_site,('joint or injured area',''))[0]
        if f.severity=='severe':return f'The reported severe {site} pain needs prompt in-person assessment.'
        if has(state,'cannot_bear_weight'):return f'Being unable to put weight on the painful {site} needs prompt in-person assessment.'
        if has(state,'joint_severe_swelling'):return f'The reported marked swelling of the {site} needs prompt in-person assessment.'
        if any(has(state,k) for k in ('cannot_move_joint','joint_locking','limb_deformity','limb_numbness')):return f'The reported movement, shape or sensation problem in the {site} needs prompt in-person assessment.'
        if has(state,'joint_hot_red') or f.fever is True:return f'A painful {site} with heat, redness or fever needs prompt in-person assessment.'
    if c=='ear_pain' and (has(state,'ear_discharge') or has(state,'hearing_change')):return 'Ear pain with discharge or changed hearing needs prompt in-person assessment.'
    if c=='dental_pain' and has(state,'dental_swelling'):return 'Tooth pain with gum, cheek or jaw swelling needs prompt dental assessment.'
    if f.age_months is not None and f.age_months<3 and c and c!='fever':return 'New symptoms in a very young infant need prompt clinician assessment; this prototype cannot establish suitability for home care.'
    return None

def question_candidates(state):
    f=state.facts;c=f.complaint
    if not c or c=='fever':return []
    # An established urgent recommendation should not wait for an interview.
    # One severity-related safety question can still change it to emergency.
    if c=='abdominal_pain' and f.severity=='severe' and f.sudden_onset is None:return ['sudden_pain']
    if broad_concern(state):return []
    plans={
      'abdominal_pain':['abdominal_severity','abdominal_touch','symptom_duration','abdominal_location'],
      'headache':['headache_sudden','one_sided_weakness','symptom_severity','symptom_duration'],
      'vomiting':['blood_vomit','keep_fluids','symptom_duration','symptom_age'],
      'diarrhoea':['keep_fluids','blood_stool','symptom_duration','symptom_age'],
      'cough':['breathing','symptom_duration','associated_fever','symptom_age'],
      'sore_throat':['swallow_saliva','associated_fever','symptom_duration','symptom_age'],
      'urinary':['urine_retention','associated_fever','flank_pain','symptom_duration'],
      'back_pain':['bladder_change','saddle_numbness','symptom_severity','symptom_duration'],
      'joint_pain':['joint_site','joint_severity','joint_injury','joint_swelling','joint_movement','symptom_duration'],
      'rash':['airway_swelling','associated_fever','symptom_duration'],
      'dizziness':['one_sided_weakness','symptom_severity','symptom_duration'],
      'injury':['symptom_severity','symptom_duration'],
      'eye_problem':['vision_loss','symptom_severity','symptom_duration'],
      'ear_pain':['ear_discharge','hearing_change','symptom_severity','symptom_duration'],
      'dental_pain':['airway_swelling','dental_swelling','symptom_severity','symptom_duration'],
      'fatigue':['symptom_severity','symptom_duration','symptom_age'],
      'other':['symptom_detail','symptom_severity','symptom_duration','symptom_change'],
    }
    plan=plans[c]
    if c=='joint_pain' or c=='injury' and f.body_site:
        site=f.body_site or 'joint'
        # Injury starts with functional safety. Otherwise begin with pain and
        # mechanism; swelling opens a relevant hot/red screen, never breathing.
        function=[f'{site}_weight'] if site in LOWER_LIMB else []
        if c=='injury':
            plan=['symptom_severity']+(['bear_weight'] if site in LOWER_LIMB else [])+[f'{site}_swelling',f'{site}_movement','symptom_duration']
        else:
            plan=(['joint_site'] if not f.body_site else [])+[f'{site}_severity',f'{site}_injury',f'{site}_swelling']+function+[f'{site}_movement','symptom_duration']
        if has(state,'joint_swelling'):plan=[f'{site}_hot_red']+plan
    if c=='abdominal_pain' and has(state,'vomiting_blood'):return []
    if c=='abdominal_pain' and any(v.name=='vomiting' and v.status=='affirmed' for v in f.associated_symptoms):plan=['blood_vomit']+plan
    result=[]
    known=features(state)
    for q in plan:
        if q in state.asked:continue
        if q=='breathing':
            if 'breathlessness' not in state.flags:result.append(q)
            continue
        spec=BROAD_QUESTIONS[q]
        if spec.field and getattr(f,spec.field) is not None:continue
        if spec.feature and (spec.feature in known or spec.feature=='fever_with_complaint' and f.fever is not None):continue
        result.append(q)
    return result

def question_limit(state):
    # Localised musculoskeletal pain needs mechanism plus function; keep the
    # original four-question cap for the other complaint families.
    return 6 if state.facts.complaint in ('joint_pain','injury') else 4

def complete_enough(state):
    """Unresolved answers are not converted into reassuring negative screens."""
    c=state.facts.complaint
    if not c:return False
    critical={'abdominal_pain':['abdominal_tenderness'],'headache':['sudden_worst_headache','new_one_sided_weakness'],'vomiting':['vomiting_blood','can_keep_fluids'],'diarrhoea':['can_keep_fluids','blood_in_stool'],'sore_throat':['cannot_swallow_saliva'],'urinary':['urine_retention'],'back_pain':['bladder_change','saddle_numbness'],'rash':['airway_swelling'],'eye_problem':['vision_loss'],'dental_pain':['airway_swelling']}.get(c,[])
    known=features(state)
    if c in ('joint_pain','injury'):
        if c=='joint_pain' and not state.facts.body_site:return False
        critical+=['cannot_move_joint']
        if state.facts.body_site in LOWER_LIMB:critical+=['cannot_bear_weight']
        if has(state,'joint_swelling'):critical+=['joint_hot_red']
    if c=='ear_pain':critical+=['ear_discharge','hearing_change']
    if c=='dental_pain':critical+=['dental_swelling']
    if c=='cough' and 'breathlessness' not in state.flags:return False
    return c!='other' and all(k in known and known[k].status in ('affirmed','denied') for k in critical)
