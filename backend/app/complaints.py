"""Complaint-aware intake and source-informed rule candidates, never a diagnostic engine.
See docs/BROAD_INTAKE.md for source-to-rule mappings and scope limitations.
All 'emergency' predicates require affirmative evidence, not keyword presence.
"""
import re
import unicodedata
from dataclasses import dataclass
from .schemas import ClinicalFinding,SymptomEvidence

def norm(s):
    from .emergency_language import canonical
    return canonical(s)

# Order gives focal complaints precedence over accompanying fever/fatigue.
COMPLAINT_PATTERNS={
 'abdominal_pain':r'(?:stomach|tummy|belly|abdom(?:en|inal))\s*(?:aches?|hurts?|pain|cramp)|(?:pain|ache|cramp).{0,18}(?:stomach|tummy|belly|abdomen)|gastric|bloat|\bgas\b|heartburn|reflux|jaundice|hemorrhoid|piles|hernia|anal\s*pain|\b(?:pet|pait)\b.{0,16}(?:dard|pain)|पेट.{0,12}(?:दर्द|ऐंठन)',
 'headache':r'migraine|head\s*ache|head\s+pain|(?:sar|sir)\s*(?:me|mein)?\s*dard|सिर.{0,10}दर्द',
 'vomiting':r'\bvomit(?:ing|ed|s)?\b|throw(?:ing)?\s+up|nausea|nauseous|\bulti\b|उल्टी',
 'diarrhoea':r'diarrh(?:oe|e)a|loose\s*(?:motions?|stools?)|watery\s*(?:stools?|poo)|दस्त|पतला\s*पाखाना',
 'sore_throat':r'throat.{0,12}(?:is\s*)?sore|sore\s*throat|throat\s*pain|hoarse|tonsil|difficulty\s*swallowing|dry\s*mouth|gale?\s*(?:me|mein)?\s*(?:dard|kharash)|गले.{0,12}(?:दर्द|खराश)',
 'cough':r'\bcough(?:ing)?\b|khansi|खांसी|खाँसी',
 'urinary':r'\btesticles?\b|\bscrot(?:um|al)\b|अंडकोष|अण्डकोष|(?:sting\w*|discomfort).{0,30}(?:urine|urinat|pee)|(?:urine|urinat|pee).{0,30}(?:sting\w*|discomfort)|(?:burn(?:s|ing)?|pain|hurt).{0,30}(?:urine|urinat|pee)|(?:urine|urinat|pee).{0,30}(?:burn|pain|hurt)|(?:burn(?:s|ing)?|pain|hurt).{0,20}(?:urinat|pee)|(?:urinat|pee).{0,20}(?:burn(?:s|ing)?|pain|hurt)|urinary|frequent\s*urinat|leakage|incontinence|kidney\s*stone|testicular|erectile|peshab.{0,15}(?:jalan|dard)|पेशाब.{0,12}(?:जलन|दर्द|नहीं)',
 'back_pain':r'(?:lower|upper)?\s*back\s*(?:aches?|hurts?|pain)|back\s*(?:ache|pain)|pain.{0,12}back|kamar.{0,12}dard|कमर.{0,12}दर्द|पीठ.{0,12}दर्द',
 'wound':r'\bwounds?\b|dressing|zakham|ज़ख्म|\bcuts?\b|\bburns?\b|\bbites?\b|\bstings?\b|घाव',
 'injury':r'\b(?:fell|fallen)\b|bruise.{0,18}(?:after|fall|hit)|\binjur(?:y|ed)\b|sprain|twisted\s*(?:ankle|knee)|\bcut\b|चोट|मोच',
 'knee_pain':r'knee|ghutne|ghutna|घुटने|घुटना',
 'shoulder_pain':r'shoulder|kandh|कंध',
 'ankle_pain':r'ankle|takhna|टखना',
 'neck_pain':r'\bneck\b|gardan|गर्दन',
 'wrist_pain':r'wrist|kalai|कलाई',
 'elbow_pain':r'elbow|kohni|कोहनी',
 'hip_pain':r'\bhip\b|koolha|कूल्हा',
 'foot_pain':r'\bfoot\b|\bpair\b|पैर|\bheel\b|\bedi\b|toe|toenail|एड़ी',
 'joint_pain':r'joints?\s*(?:pain|aches?|hurt)|jodon.{0,12}dard|जोड़ों.{0,12}दर्द',
 'diabetes':r'diabet|madhumeh|मधुमेह|(?:high|raised)\s*sugar|sugar\s*(?:high|badha)',
 'catheter':r'catheter|कैथेटर',
 'nebulization':r'nebuliz|नेब्युलाइज़र|नेबुलाइजर',
 'vitals_check':r'vitals|bp\s*check|sugar\s*check|blood\s*pressure\s*check|बीपी\s*चेक|शुगर\s*चेक',
 'post_surgical':r'post\s*(?:surgery|surgical)|after\s*surgery|surgery\s*(?:care|wound)|operation\s*(?:ke\s*baad|care)|stitches|tanke|टांके',
 'bedridden':r'bedridden|bistar|बिस्तर\s*(?:par|pe)?\s*(?:pada|padi)',
 'elderly_care':r'elderly|buzurg|बुज़ुर्ग|old\s*age\s*care',
 'menstrual':r'menstrual|periods?|pelvic|vaginal\s*discharge|breast\s*lump|मासिक',
 'anxiety':r'anxiety|anxious|low\s*mood|depress|ghabrahat|घबराहट',
 'sleep_problem':r'(?:cannot|can.t|unable to|difficulty).{0,12}sleep|sleep.{0,12}(?:badly|poorly)|sleep\s*problem|insomnia|neend|नींद|snoring|kharrate|खर्राटे',
 'hand_pain':r'\bhand\b|\bfingers?\b|\bthumbs?\b|ungli|उंगली',
 'muscle_pain':r'muscle|cramp|\bcalf\b|\brib\b',
 'nasal':r'nose|nasal|sinus|\bsmell\b|nosebleed|sneeze|runny|common\s*cold',
 'cardiac':r'heart.{0,35}(?:skips?|misses?)\s*(?:a\s*)?beats?|palpitat|racing\s*heart|heartbeat|blood\s*pressure|\bbp\b',
 'neuro':r'सुन्न|\bsunn?\b|numb|tingling|tremor|shaking|memory|faint|balance|nerve\s*pain',
 'kidney':r'kidney',
 'thyroid':r'thyroid',
 'nutrition':r'(?:lost|losing|gained|gaining)\s*weight|weight\s*(?:loss|gain)|diet|nutrition',
 'blood':r'anemia|anaemia|pale\s*skin|bruis|prolonged\s*bleeding',
 'rash':r'\brash\b|itch(?:y|ing)\s*skin|skin\s*itch|scalp|dandruff|hair\s*loss|\bmole\b|eczema|psoriasis|\bboil\b|hives|sweat|nail|चकत्ते|खुजली',
 'dizziness':r'\bdizz(?:y|iness)\b|light.?headed|chakkar|चक्कर',
 'eye_problem':r'eyes?.{0,18}(?:itch|water|red|sore)|\beye(?:ball)?s?\b.{0,30}(?:blood|bleed|injur)|(?:blood|bleed).{0,35}\beye(?:ball)?s?\b|(?:आँख|आंख|aankh|ankh).{0,30}(?:खून|चोट|दर्द|khoon|chot)|eye\s*(?:pain|ache|red|problem)|(?:red|painful|sore)\s*eye|vision\s*(?:loss|problem)|blurred|dry\s*eyes|watery\s*eyes|eyelid|stye|eye\s*discharge|light\s*sensitivity|eye\s*injur|आँख.{0,12}(?:दर्द|लाल)|आंख.{0,12}दर्द',
 'ear_pain':r'ear\s*(?:ache|pain)|ear\s*discharge|hearing|ringing|tinnitus|blocked\s*ear|ear\s*pressure|earwax|kaan.{0,10}dard|कान.{0,12}दर्द',
 'dental_pain':r'tooth\s*(?:ache|pain)|dental\s*pain|cavity|cavities|bleeding\s*gums|swollen\s*gums|bad\s*breath|broken\s*tooth|chipped\s*tooth|\bjaw\b|daant.{0,12}dard|दाँत.{0,12}दर्द|दांत.{0,12}दर्द',
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
 'other':('reported symptoms','बताए गए लक्षण'),
 'wound':('wound','घाव'),'knee_pain':('knee pain','घुटने का दर्द'),
 'shoulder_pain':('shoulder pain','कंधे का दर्द'),'ankle_pain':('ankle pain','टखने का दर्द'),
 'neck_pain':('neck pain','गर्दन का दर्द'),'wrist_pain':('wrist pain','कलाई का दर्द'),
 'elbow_pain':('elbow pain','कोहनी का दर्द'),'hip_pain':('hip pain','कूल्हे का दर्द'),
 'foot_pain':('foot pain','पैर का दर्द'),'diabetes':('diabetes','मधुमेह'),
 'catheter':('catheter care','कैथेटर की देखभाल'),'nebulization':('nebulization','नेब्युलाइज़ेशन'),
 'vitals_check':('vitals check','वाइटल्स की जाँच'),'post_surgical':('post-surgical care','ऑपरेशन के बाद की देखभाल'),
 'bedridden':('bedridden care','बिस्तर पर देखभाल'),'elderly_care':('elderly care','बुज़ुर्गों की देखभाल'),
 'menstrual':('menstrual problem','मासिक धर्म की समस्या'),'anxiety':('anxiety','घबराहट'),
 'sleep_problem':('sleep problem','नींद की समस्या'),
 'hand_pain':('hand pain','हाथ का दर्द'),'muscle_pain':('muscle pain','मांसपेशियों का दर्द'),
 'nasal':('nose or sinus problem','नाक या साइनस की समस्या'),
 'cardiac':('heart or blood pressure concern','दिल या ब्लड प्रेशर की चिंता'),
 'neuro':('nerve-related symptoms','नसों से जुड़े लक्षण'),
 'kidney':('kidney concern','किडनी की समस्या'),'thyroid':('thyroid concern','थायराइड की समस्या'),
 'nutrition':('weight or nutrition concern','वज़न या पोषण की चिंता'),
 'blood':('blood-related symptoms','खून से जुड़े लक्षण')}

# Family -> expanded-roster complaint keys (data/caregivers.csv, supported_complaints).
# A doctor matches only when their supported complaints overlap the family keys.
# None means "not a doctor-matched family" (medic/phlebotomist care, or unknown
# complaint where the previous any-doctor behaviour is kept).
FAMILY_KEYS={
 'abdominal_pain':{'stomach_pain','digestive_problem','acidity','constipation','liver_concern','hernia_concern','abdominal_surgical_concern'},
 'headache':{'headache','migraine'},
 'vomiting':set(),'diarrhoea':{'diarrhoea','digestive_problem'},
 'cough':{'cough','asthma','wheezing','breathing_problem','chronic_lung_concern'},
 'sore_throat':{'sore_throat','throat_problem','sinus_symptoms','nose_problem','voice_problem'},
 'urinary':{'urinary_problem','urination_pain','kidney_stone','prostate_concern','urinary_related_kidney_concern'},
 'back_pain':{'back_pain'},'wound':None,
 'knee_pain':{'knee_pain','joint_pain'},'shoulder_pain':{'shoulder_pain','joint_pain'},
 'ankle_pain':{'joint_pain','sports_injury'},'neck_pain':{'joint_pain','muscle_pain'},
 'wrist_pain':{'joint_pain','sports_injury'},'elbow_pain':{'joint_pain'},
 'hip_pain':{'joint_pain','muscle_pain'},'foot_pain':{'joint_pain','muscle_pain'},
 'joint_pain':{'joint_pain','inflammatory_joint_concern','autoimmune_concern'},
 'diabetes':{'diabetes','diabetes_followup'},
 'catheter':None,'nebulization':None,'vitals_check':None,'post_surgical':None,
 'bedridden':None,'elderly_care':None,
 'menstrual':{'menstrual_problem','women_health','pregnancy_concern','pregnancy_followup'},
 'anxiety':{'anxiety','low_mood','mental_health_concern','sleep_problem'},
 'sleep_problem':{'sleep_problem','snoring_concern','suspected_sleep_apnea'},
 'hand_pain':{'joint_pain','muscle_pain'},'muscle_pain':{'muscle_pain','sports_injury'},
 'nasal':{'sinus_symptoms','nose_problem','allergy_concern'},
 'cardiac':{'palpitations','blood_pressure','heart_concern','blood_pressure_followup'},
 'neuro':{'numbness','tremor','dizziness'},
 'kidney':{'kidney_problem','chronic_kidney_concern','urinary_related_kidney_concern'},
 'thyroid':{'thyroid_problem','hormonal_concern'},
 'nutrition':{'nutrition_concern','weight_change','diet_planning'},
 'blood':{'blood_disorder_concern'},
 'rash':{'rash','itching','skin_problem','acne','hair_loss','nail_problem'},
 'dizziness':{'dizziness'},
 'injury':{'sports_injury','bone_injury','exercise_injury','muscle_pain','wound_assessment'},
 'eye_problem':{'eye_pain','red_eye','vision_problem','eye_irritation','eye_problem','eye_redness'},
 'ear_pain':{'ear_pain','hearing_problem'},
 'dental_pain':{'toothache','gum_problem','mouth_ulcer','dental_problem','wisdom_tooth','jaw_problem','dental_injury'},
 'fatigue':{'fatigue','weakness','general_symptoms'},
 'fever':{'fever','persistent_fever','child_fever','general_symptoms'},
 'other':None}

# Complaint -> home service used at the final step when no explicit service was
# stated (e.g. "post surgery care" needs a medic, not a teleconsultation).
COMPLAINT_SERVICE={
 'wound':'dressing','catheter':'catheter','nebulization':'nebulization',
 'post_surgical':'post_surgical','bedridden':'elderly','elderly_care':'elderly'}

# Roster keys that only apply to children; never matched for adults or when
# the age is unknown (a generalist is the safe match then).
CHILD_KEYS={'child_fever','child_cough','child_general_symptoms','child_digestive_problem'}

FEATURE_PATTERNS={
 'abdominal_tenderness':r'(?:stomach|tummy|abdomen|belly).{0,35}(?:hurt|pain).{0,16}(?:touch|press)|(?:touch|press).{0,25}(?:stomach|tummy|abdomen).{0,20}(?:hurt|pain)|पेट.{0,12}(?:छूने|दबाने).{0,12}दर्द|pet.{0,12}(?:chune|dabane).{0,12}dard',
 'vomiting_blood':r'vomit(?:ing|ed)?\s*(?:bright\s*red\s*)?blood|blood\s+in\s+(?:my\s+|the\s+)?vomit|vomit.{0,12}coffee\s*ground|खून\s*की\s*उल्टी|उल्टी.{0,10}खून|ulti.{0,10}khoon',
 'black_sticky_stool':r'black\s*(?:and\s*)?(?:sticky|tarry)\s*(?:stools?|poo)|black\s*stools?.{0,12}sticky|(?:stools?|poo).{0,12}black.{0,12}(?:sticky|tarry)',
 'blood_in_stool':r'blood\s+in\s+(?:my\s+|the\s+)?(?:stool|poo)|stools?.{0,10}blood|पाखान.{0,12}खून',
 'sudden_worst_headache':r'(?:sudden|suddenly|thunderclap).{0,35}(?:worst|severe|extremely\s*painful).{0,12}headache|worst\s*headache.{0,30}(?:sudden|seconds)|अचानक.{0,12}(?:बहुत\s*तेज|तेज).{0,12}सिर.{0,8}दर्द',
 'new_one_sided_weakness':r'(?:new|sudden).{0,12}(?:one.side|one side).{0,12}weak|अचानक.{0,8}एक\s*तरफ.{0,8}कमजोर',
 'vision_loss':r'(?:lost|loss\s*of|losing).{0,12}(?:my\s*)?vision|(?:cannot|can.t)\s*see|अचानक.{0,12}दिखाई\s*नहीं',
 'new_confusion':r'(?:sudden|suddenly|new).{0,12}confus|अचानक.{0,10}उलझन',
 'airway_swelling':r'(?:tongue|throat|lips?).{0,20}(?:swell|swollen)|(?:swelling|swollen).{0,15}(?:tongue|throat|lips?)|(?:face|chehra).{0,15}(?:swell|swollen)|swollen\s*(?:face|lips?)|गले.{0,12}सूजन|जीभ.{0,12}सूज|(?:gale|gala|jeebh).{0,12}sujan',
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
 'coughing_blood':r'cough(?:ing)?\s*(?:up\s*)?blood|blood\s+in\s+(?:my\s*)?cough|खांसी.{0,12}खून|khansi.{0,12}khoon',
 'sudden_hearing_loss':r'sudden.{0,25}hearing\s*loss|hearing\s*loss.{0,25}sudden|अचानक.{0,15}सुनाई\s*(?:कम|नहीं)',
}

HISTORICAL=r'\b(?:last\s*year|years?\s*ago|history\s*of|used\s*to|resolved|no\s*longer)\b|पिछले\s*साल'
HYPOTHETICAL=r'\b(?:what\s*if|hypothetical|example|quoted|if\s*(?:someone|i|he|she))\b|अगर|agar'

def status_of(text,hit,name=None):
    from .assertions import status
    if name=='airway_swelling' and re.search(r'(?:not|no)\s*(?:swell|swollen)|(?:swelling|swollen)\s*(?:nahi|नहीं)',hit[0]):return 'denied'
    parsed=status(text,hit)
    return 'hypothetical' if parsed=='unknown' else 'historical' if parsed=='recent_resolved' else parsed

def detect_features(text):
    result={}
    from .assertions import clauses
    for raw,clause,inherited in clauses(text):
        for name,p in FEATURE_PATTERNS.items():
            m=re.search(p,clause)
            if m:
                status=inherited or status_of(clause,m,name)
                if name not in result or status=='affirmed':result[name]=ClinicalFinding(name=name,status=status,quote=text)
        # Negative polarity is the information for this positively-worded field.
        if re.search(r'(?:cannot|can.t|unable\s*to)\s*keep\s*(?:water|fluids?|drinks?)\s*down|पानी.{0,10}(?:रुकता\s*नहीं|नहीं\s*रुक)',clause):
            result['can_keep_fluids']=ClinicalFinding(name='can_keep_fluids',status='denied',quote=text)
    return list(result.values())

@dataclass(frozen=True)
class Question:
    en: str
    hi: str
    field: str | None = None
    feature: str | None = None
    yes_affirms: bool = True
    choices: tuple = ('Yes','No','Not sure')
    service: str | None = None   # a "yes" answer requests this home service
    flag: str | None = None

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
 'complaint_clarify':Question('Please clarify the main symptom and the body area affected.','कृपया मुख्य लक्षण और शरीर की जगह स्पष्ट करें।',field='complaint_text',choices=()),
 'symptom_detail':Question('What symptom is bothering you most?','कौन सा लक्षण सबसे ज़्यादा परेशान कर रहा है?',field='complaint_text',choices=()),
 'symptom_change':Question('Are the symptoms getting worse, improving, or staying the same?','क्या लक्षण बढ़ रहे हैं, कम हो रहे हैं या वैसे ही हैं?',field='progression',choices=('Getting worse','Improving','Staying the same')),
 # Body-part and care-need questions: each family asks its own questions.
 'joint_swelling':Question('Is there swelling around the painful joint?','क्या दर्द वाले जोड़ के आसपास सूजन है?',feature='joint_swelling'),
 'joint_moving':Question('Is it difficult to move the painful joint?','क्या दर्द वाले जोड़ को हिलाने में दिक्कत है?',feature='joint_movement_difficulty'),
 'joint_injury':Question('Did the pain start after an injury or a fall?','क्या दर्द चोट या गिरने के बाद शुरू हुआ?',feature='joint_injury_onset'),
 'lifting_arm':Question('Is it difficult to lift the arm on the painful side?','क्या दर्द वाली तरफ़ का हाथ उठाने में दिक्कत है?',feature='arm_lifting_difficulty'),
 'joint_stiffness':Question('Is the joint stiff?','क्या जोड़ अकड़ गया है?',feature='joint_stiffness'),
 'arm_pain':Question('Does the pain go into the arm?','क्या दर्द हाथ तक जा रहा है?',feature='radiating_arm_pain'),
 'leg_pain':Question('Does the pain go down the leg?','क्या दर्द पैर तक जा रहा है?',feature='radiating_leg_pain'),
 'grip_difficulty':Question('Is it difficult to grip things with the painful hand?','क्या दर्द वाले हाथ से चीज़ें पकड़ने में दिक्कत है?',feature='grip_difficulty'),
 'bend_difficulty':Question('Is it difficult to bend the painful joint?','क्या दर्द वाले जोड़ को मोड़ने में दिक्कत है?',feature='joint_bending_difficulty'),
 'fever_high':Question('Is the fever above 102°F (39°C)?','क्या बुखार 102°F (39°C) से ज़्यादा है?',feature='high_fever'),
 'fluids_normal':Question('Is the person able to eat and drink normally?','क्या व्यक्ति सामान्य रूप से खा-पी रहा है?',feature='poor_intake',yes_affirms=False),
 'wound_leaking':Question('Is the wound open or leaking?','क्या घाव खुला है या उससे कुछ निकल रहा है?',feature='wound_leaking'),
 'wound_redness':Question('Is there redness or swelling around the wound?','क्या घाव के आसपास लाली या सूजन है?',feature='wound_redness'),
 'sugar_check':Question('Do you need a blood sugar check at home?','क्या घर पर ब्लड शुगर चेक चाहिए?',feature='sugar_check_requested',service='bp_sugar'),
 'foot_sore':Question('Is there a foot sore or wound that is not healing?','क्या पैर में कोई घाव है जो भर नहीं रहा?',feature='diabetic_foot_wound',service='dressing'),
 'foot_wound':Question('Is there any wound on the painful foot?','क्या दर्द वाले पैर पर कोई घाव है?',service='dressing'),
 'catheter_block':Question('Is there blockage or leakage from the catheter?','क्या कैथेटर में ब्लॉकेज या लीकेज है?',feature='catheter_blockage'),
 'catheter_pain':Question('Is there pain or burning with the catheter?','क्या कैथेटर से दर्द या जलन है?',feature='catheter_pain'),
 'nebulizer_home':Question('Is a nebulizer machine available at home?','क्या घर पर नेब्युलाइज़र मशीन है?',feature='nebulizer_available'),
 'vitals_bp':Question('Should blood pressure be checked?','क्या ब्लड प्रेशर चेक करना है?',feature='bp_check_requested',service='bp_sugar'),
 'vitals_sugar':Question('Should blood sugar be checked?','क्या ब्लड शुगर चेक करना है?',feature='sugar_check_requested',service='bp_sugar'),
 'postop_redness':Question('Is there redness or leaking from the surgical wound?','क्या ऑपरेशन के घाव से लाली या रिसाव है?',feature='surgical_wound_issue'),
 'postop_stitches':Question('Is this for stitch removal?','क्या यह टांके कटवाने के लिए है?',feature='stitch_removal'),
 'bedsores':Question('Are there any bedsores?','क्या कोई बेडसोर (बिस्तर के घाव) हैं?',feature='bedsores'),
 'daily_care':Question('Is daily care needed?','क्या रोज़ाना देखभाल चाहिए?',feature='daily_care_needed'),
 'elderly_meds':Question('Is medicine management needed?','क्या दवाओं का प्रबंधन चाहिए?',feature='medicine_management'),
 'heavy_bleeding':Question('Is the bleeding heavy?','क्या ब्लीडिंग ज़्यादा हो रही है?',feature='heavy_bleeding'),
 'sleep_with':Question('Is sleep also disturbed?','क्या नींद भी खराब है?',feature='sleep_disturbed'),
 'snoring':Question('Is there loud snoring or pauses in breathing during sleep?','क्या नींद में ज़ोर से खर्राटे आते हैं या सांस रुकती है?',feature='sleep_apnea_signs'),
 'blood_cough':Question('Are you coughing up any blood?','क्या खांसी में खून आ रहा है?',feature='coughing_blood'),
 'hearing_sudden':Question('Have you developed any sudden hearing loss?','क्या सुनाई देना अचानक कम हुआ है?',feature='sudden_hearing_loss'),
 'cardiac_chest':Question('Do you have chest pain, pressure or tightness with the heart symptoms?','क्या दिल की तकलीफ़ के साथ सीने में दर्द, दबाव या जकड़न है?',flag='chest_pain'),
 'stroke_speech':Question('Have you suddenly developed a drooping face or difficulty speaking?','क्या अचानक चेहरा टेढ़ा हुआ है या बोलने में दिक्कत हुई है?',flag='stroke_symptoms'),
 'immediate_harm':Question('Are you in immediate danger of harming yourself right now?','क्या अभी आपको खुद को नुकसान पहुँचाने का तत्काल खतरा है?',flag='suicidal_ideation'),
}

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
    # Resolve overlapping lexical matches using the stated location/context.
    # Do not let 'back of my neck' become a lower-back complaint or urinary
    # burning create a fictitious skin wound as a secondary complaint.
    suppressed=set()
    if 'neck_pain' in found and 'back_pain' in found and re.search(r'back\s+of\s+(?:my\s+|the\s+)?neck',t) and not re.search(r'(?:lower|upper)\s+back',t):suppressed.add('back_pain')
    if 'urinary' in found and 'wound' in found and not re.search(r'\b(?:wound|cut|skin|burn wound|bite|sting)\b|घाव',t):suppressed.add('wound')
    if 'neuro' in found and 'hand_pain' in found and re.search(r'numb|tingl|सुन्न|sunn',t):suppressed.add('hand_pain')
    found=[v for v in found if v not in suppressed]
    x.associated_symptoms=[v for v in x.associated_symptoms if v.name not in suppressed]
    if found:
        x.complaint=found[0];x.complaint_text=text[:300]
        x.body_site={'urinary':'urinary tract','neck_pain':'neck','back_pain':'back','hand_pain':'hand/fingers','knee_pain':'knee','eye_problem':'eye','ear_pain':'ear','abdominal_pain':'abdomen','testicular':'testicle'}.get(x.complaint)
        if x.complaint=='urinary' and re.search(r'testicles?|testicular|scrot|अंडकोष|अण्डकोष',t):x.body_site='testicle/scrotum'
        if re.search(r'(?:pass|passing)\s*urine|urinat|pee|पेशाब|peshab',t) and x.complaint=='urinary':x.trigger='passing urine'
        elif re.search(r'after meals?|after eating|खाने के बाद',t):x.trigger='after meals'
        elif re.search(r'after.{0,18}(?:injur|fall|fell)|गिरने',t):x.trigger='after injury/fall'
        elif re.search(r'when.{0,20}(?:walk|move|grip|raise)|हिलाने',t):x.trigger='movement'

    elif not x.service and re.search(r'\b(?:i (?:have|feel)|my .{0,20}(?:hurts|aches)|symptoms?)\b|मुझे|तकलीफ',t) and not re.search(HYPOTHETICAL,t):
        x.complaint='other';x.complaint_text=text[:300]
    x.clinical_features=detect_features(text)
    # Severity belongs to an affirmative reported complaint or a severity answer.
    if found or question in ('symptom_severity','abdominal_severity'):
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
        if q.feature and answer is not None:
            affirmative=answer==q.yes_affirms
            x.clinical_features=[f for f in x.clinical_features if f.name!=q.feature]+[ClinicalFinding(name=q.feature,status='affirmed' if affirmative else 'denied',quote=text)]
        if q.service and answer:x.service=q.service
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
    from .safety_screen import actionable
    f=state.facts;reasons=[v.reason for v in actionable(getattr(state,'safety_findings',[])) if v.disposition=='emergency']
    always={'vomiting_blood':'Blood in vomit','black_sticky_stool':'Black, sticky stool','sudden_worst_headache':'Sudden extremely painful headache','vision_loss':'Loss of vision','new_confusion':'New sudden confusion','airway_swelling':'Tongue or throat swelling','cannot_swallow_saliva':'Unable to swallow saliva'}
    for name,description in always.items():
        if has(state,name):reasons.append(description)
    if has(state,'abdominal_tenderness'):reasons.append('Abdominal pain on touch')
    if f.complaint=='abdominal_pain':
        if f.severity=='severe' and f.sudden_onset is True:reasons.append('Sudden severe abdominal pain')
    if f.complaint=='headache' and f.severity=='severe' and f.sudden_onset is True:reasons.append('Sudden extremely painful headache')
    if f.complaint=='eye_problem' and f.sudden_onset is True and re.search(r'pain|दर्द|dard',f.complaint_text or '',re.I):reasons.append('Sudden-onset eye pain')
    present={f.complaint}|{v.name for v in f.associated_symptoms if v.status=='affirmed'}
    if 'back_pain' in present:
        if has(state,'bladder_change'):reasons.append('New bladder-control change with back pain')
        if has(state,'saddle_numbness'):reasons.append('Groin numbness with back pain')
    if has(state,'urine_retention') and present & {'abdominal_pain','urinary'}:reasons.append('Unable to pass urine')
    if has(state,'nonblanching_rash') and f.fever:reasons.append('Fever with a non-fading rash')
    if f.complaint=='urinary' and 'testicular' in (f.complaint_text or '').lower() and f.severity=='severe' and f.sudden_onset is True:reasons.append('Sudden severe testicular pain')
    return reasons

def broad_concern(state):
    from .safety_screen import actionable
    urgent=[v.reason for v in actionable(getattr(state,'safety_findings',[])) if v.disposition=='urgent_assessment']
    if urgent:return urgent[-1]+'. Do not wait for routine booking or for this chat to finish.'
    f=state.facts;c=f.complaint
    if c=='abdominal_pain' and 'pregnancy' in f.risk_factors:return 'Abdominal pain during pregnancy needs prompt in-person medical assessment.'
    if c=='abdominal_pain' and f.pain_location and 'lower right' in f.pain_location and f.progression=='worsening':return 'Worsening lower-right abdominal pain needs prompt in-person medical assessment.'
    if c in ('abdominal_pain','headache','back_pain','eye_problem','dental_pain','ear_pain') and f.severity=='severe':return 'The reported severe pain needs prompt in-person medical assessment.'
    if has(state,'can_keep_fluids','denied'):return 'Being unable to keep fluids down needs prompt medical assessment for dehydration risk.'
    if has(state,'blood_in_stool') or has(state,'blood_in_urine'):return 'Reported blood needs prompt in-person medical assessment.'
    if c=='urinary' and f.body_site=='testicle/scrotum':return 'Reported testicular symptoms need prompt in-person clinical assessment; this chat cannot establish a routine care pathway.'
    if c=='urinary' and (f.fever or has(state,'flank_pain')):return 'Urinary symptoms with fever or flank pain need prompt in-person medical assessment.'
    if has(state,'coughing_blood'):return 'Coughing up blood needs prompt medical assessment.'
    if has(state,'sudden_hearing_loss'):return 'Sudden hearing loss needs urgent same-day assessment.'
    if c=='catheter' and has(state,'catheter_blockage'):return 'Reported catheter blockage or leakage needs prompt advice from a clinician or community nurse; routine booking must not delay assessment.'
    if c=='post_surgical' and has(state,'surgical_wound_issue'):return 'Reported redness or leakage from a surgical wound needs prompt clinical assessment.'
    if c=='diabetes' and has(state,'diabetic_foot_wound'):return 'A non-healing foot wound with diabetes needs prompt clinical assessment.'
    if c=='menstrual' and has(state,'heavy_bleeding'):return 'Reported heavy menstrual bleeding needs clinical assessment; this chat cannot establish that routine home care is suitable.'
    if c in ('knee_pain','joint_pain','injury') and has(state,'joint_movement_difficulty'):return 'Reported difficulty moving the painful joint needs prompt in-person assessment.'
    if c in ('injury','ankle_pain','knee_pain','foot_pain','hip_pain','wrist_pain') and has(state,'cannot_bear_weight'):return 'An injury that prevents weight bearing needs prompt in-person assessment.'
    if f.age_months is not None and f.age_months<3 and c and c!='fever':return 'New symptoms in a very young infant need prompt clinician assessment; this prototype cannot establish suitability for home care.'
    return None

QUESTION_PLANS={
      'abdominal_pain':['abdominal_severity','abdominal_touch','symptom_duration','abdominal_location'],
      'headache':['headache_sudden','one_sided_weakness','symptom_severity','symptom_duration'],
      'vomiting':['blood_vomit','keep_fluids','symptom_duration','symptom_age'],
      'diarrhoea':['keep_fluids','blood_stool','symptom_duration','symptom_age'],
      'cough':['breathing','blood_cough','symptom_duration','associated_fever','symptom_age'],
      'sore_throat':['swallow_saliva','associated_fever','symptom_duration','symptom_age'],
      'urinary':['urine_retention','associated_fever','flank_pain','symptom_duration'],
      'back_pain':['bladder_change','saddle_numbness','leg_pain','symptom_severity','symptom_duration'],
      'wound':['wound_leaking','wound_redness','symptom_duration'],
      'knee_pain':['joint_swelling','joint_moving','bear_weight','joint_injury','symptom_duration'],
      'shoulder_pain':['lifting_arm','joint_injury','joint_stiffness','symptom_duration'],
      'ankle_pain':['joint_swelling','bear_weight','joint_injury','symptom_duration'],
      'neck_pain':['joint_stiffness','arm_pain','joint_injury','symptom_duration'],
      'wrist_pain':['joint_swelling','grip_difficulty','joint_injury','symptom_duration'],
      'elbow_pain':['joint_swelling','bend_difficulty','joint_injury','symptom_duration'],
      'hip_pain':['bear_weight','joint_injury','joint_stiffness','symptom_duration'],
      'foot_pain':['joint_swelling','bear_weight','foot_wound','symptom_duration'],
      'joint_pain':['symptom_severity','joint_swelling','joint_moving','symptom_duration'],
      'diabetes':['sugar_check','foot_sore','symptom_duration'],
      'catheter':['catheter_block','catheter_pain','symptom_duration'],
      'nebulization':['breathing','nebulizer_home','symptom_duration'],
      'vitals_check':['vitals_bp','vitals_sugar','symptom_duration'],
      'post_surgical':['postop_redness','postop_stitches','symptom_duration'],
      'bedridden':['daily_care','bedsores','symptom_duration'],
      'elderly_care':['daily_care','elderly_meds','symptom_duration'],
      'menstrual':['heavy_bleeding','symptom_severity','symptom_duration'],
      'anxiety':['immediate_harm','sleep_with','symptom_severity','symptom_duration'],
      'sleep_problem':['snoring','symptom_severity','symptom_duration'],
      'hand_pain':['joint_swelling','grip_difficulty','joint_injury','symptom_duration'],
      'muscle_pain':['symptom_severity','joint_injury','symptom_duration'],
      'nasal':['symptom_severity','associated_fever','symptom_duration'],
      'cardiac':['cardiac_chest','breathing','symptom_severity','symptom_duration'],
      'neuro':['one_sided_weakness','stroke_speech','symptom_severity','symptom_duration'],
      'kidney':['symptom_severity','symptom_duration'],
      'thyroid':['symptom_severity','symptom_duration'],
      'nutrition':['symptom_severity','symptom_duration'],
      'blood':['symptom_severity','symptom_duration'],
      'rash':['airway_swelling','associated_fever','symptom_duration'],
      'dizziness':['one_sided_weakness','stroke_speech','symptom_severity','symptom_duration'],
      'injury':['symptom_severity','symptom_duration'],
      'eye_problem':['vision_loss','symptom_severity','symptom_duration'],
      'ear_pain':['symptom_severity','hearing_sudden','associated_fever','symptom_duration'],
      'dental_pain':['airway_swelling','symptom_severity','symptom_duration'],
      'fatigue':['symptom_severity','symptom_duration','symptom_age'],
      'other':['symptom_detail','symptom_severity','symptom_duration','symptom_change'],
    }

def question_candidates(state):
    f=state.facts;c=f.complaint
    if not c or c=='fever':return []
    # An established urgent recommendation should not wait for an interview.
    # One severity-related safety question can still change it to emergency.
    if c=='abdominal_pain' and f.severity=='severe' and f.sudden_onset is None:return ['sudden_pain']
    if broad_concern(state):return []
    plans=QUESTION_PLANS
    plan=plans[c]
    if c=='injury' and re.search(r'ankle|knee|foot|leg|arm|wrist|टखने|पैर|घुटने',norm(f.complaint_text or '')):
        plan=['symptom_severity','bear_weight','symptom_duration']
    if c=='abdominal_pain' and has(state,'vomiting_blood'):return []
    if c=='abdominal_pain' and any(v.name=='vomiting' and v.status=='affirmed' for v in f.associated_symptoms):plan=['blood_vomit']+plan
    result=[]
    known=features(state)
    for q in plan:
        if q in state.asked:continue
        if q=='breathing' or BROAD_QUESTIONS[q].flag:
            from .safety_policy import question_resolved
            if not question_resolved(state,q):result.append(q)
            continue
        spec=BROAD_QUESTIONS[q]
        if spec.field and getattr(f,spec.field) is not None:continue
        if spec.feature and (spec.feature in known and known[spec.feature].status in ('affirmed','denied') or spec.feature=='fever_with_complaint' and f.fever is not None):continue
        result.append(q)
    return result

def complete_enough(state):
    from .safety_policy import safety_gaps
    return not safety_gaps(state)
