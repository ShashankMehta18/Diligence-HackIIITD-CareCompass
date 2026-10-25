"""Finite multilingual warning-sign recognition, with per-mention polarity.

This is a source-informed prototype lexicon, not a clinical NLP model. See
docs/SAFETY_UPDATE.md for sources, limitations and evaluation provenance.
Inability ('cannot breathe', 'hosh nahi') is part of the warning itself; an
external denial ('not unconscious', 'behosh nahi') is a different assertion.
"""
import re
import unicodedata
from .schemas import FlagEvidence

def canonical(text):
    return unicodedata.normalize('NFKC',text).casefold().replace('’',"'").translate(str.maketrans('०१२३४५६७८९','0123456789'))

PATTERNS={
 'chest_pain':r"\bchest\s+(?:pain|tightness|pressure|heaviness)\b|\b(?:pain|pressure|tightness|heaviness)\s+(?:in\s+|on\s+)?(?:my\s+|the\s+)?chest\b|\b(?:seene?|chh?ati|chhaati)\s*(?:me|mein)?\s*(?:dard|pain|dabav|dabaav|jakdan)|(?:सीने|छाती)\s*(?:में)?\s*(?:तेज\s*)?(?:दर्द|दबाव|जकड़न)",
 'breathlessness':r"\b(?:can.?t|cannot|unable\s+to|struggl(?:e|ing)\s+to)\s+breathe\b|\b(?:difficulty|difficulties|trouble)\s+(?:in\s+)?breath(?:ing)?|\bbreath(?:ing)?\s+(?:difficulty|difficulties|problems?)\b|\bshort(?:ness)?\s+of\s+breath\b|\bbreathless\b|\bgasping(?:\s+for\s+(?:air|breath))?\b|\b(?:cannot|can't)\s+get\s+(?:enough|any)\s+air\b|\btrouble\s+catching\s+(?:my\s+|his\s+|her\s+)?breath\b|\bsa+a?n?s\s*(?:nahi|nahin|nai)\s+aa\s+rah[ai]\b|\bsa+a?n?s\s*(?:lene\s*(?:me|mein)\s*)?(?:ki\s*)?(?:bahut\s*)?(?:dikk?at|takli+f|takleef)|\bdam\s+(?:ghut|ghoot)\s+rah[ai]|(?:सांस|साँस)\s+नहीं\s+आ\s+रही|(?:सांस|साँस)\s*(?:लेने\s*में|की)?\s*(?:बहुत\s*)?(?:तकलीफ|तकलीफ़|दिक्कत)|दम\s*घुट\s*रहा",
 'unconsciousness':r"\bunconscious\b|\bunresponsive\b|\bnot\s+responding\b|\bcollapsed\b|\bpassed\s+out\b|\b(?:will\s+not|won't|cannot|can't)\s+wake\s+up\b|\bresponse\s+nahi\s+de\s+rahe|\bbehosh\b|\bhosh\s*(?:nahi|nahin|nai)\s+aa\s+rah[ai]|\b(?:awa+z\s+dene\s+par\s+)?jawab\s*(?:nahi|nahin)\s+de\s+rah[ea]|बेहोश|होश\s*नहीं\s*आ\s*रहा|(?:आवाज़\s*देने\s*पर\s*)?जवाब\s+नहीं\s+दे\s+रहे",
 'severe_bleeding':r"\b(?:heavy|severe|uncontrolled|profuse)\s+bleeding\b|\bbleeding\s+(?:heavily|profusely)\b|\bbleeding\s+(?:that\s+)?(?:won.?t|will\s+not|does\s+not|doesn.?t)\s+stop\b|\bblood\s+(?:is\s+)?(?:gushing|spurting|pouring)\b|\bbleeding\s+ruk\s+nahi|\b(?:bahut|bohot|bohut)\s+(?:khoon|khun)\b|\b(?:khoon|khun)\s*(?:beh\s*na\s*)?ruk\s*(?:nahi|nahin)|खून\s*नहीं\s*रुक|बहुत\s*खून|खून\s*फव्वारे\s*की\s*तरह",
 'stroke_symptoms':r"\b(?:face|side\s+of\s+(?:his\s+|her\s+|my\s+)?face)\s+(?:is\s+)?droop(?:ing)?|\b(?:slurred\s+speech|speech.{0,18}slurred|words\s+(?:are\s+)?slurred)\b|\bsudden\s+(?:one.sided|arm|leg)\s+weakness\b|\bsuddenly.{0,25}(?:left|right|one)\s+(?:arm|leg).{0,15}weak|\b(?:new|sudden)\s+weakness\s+(?:on|down)\s+one\s+side|\b(?:ek|aik)\s+taraf\s*(?:ka|ki|ke)?\s*(?:haath?|pair|bazu)\s+kaam\s*(?:nahi|nahin)\s+kar|\bchehra\s+tedha\b|\b(?:achanak\s+)?boli\s+ladkhada|चेहरा\s+टेढ़ा|अचानक\s+एक\s+तरफ\s+कमजोरी|(?:शरीर\s*के\s*)?एक\s*तरफ.{0,15}(?:हाथ|पैर).{0,12}काम\s*नहीं|अचानक.{0,20}बोलने\s*में\s*दिक्कत",
 'seizure':r'\bseizures?\b|\bconvuls(?:ion|ions|ing)\b|\bdaura\s+(?:pad|aa)|दौरा\s+(?:पड़|आ)',
 'suicidal_ideation':r"\b(?:want|going|plan|planning)\s+to\s+(?:kill|hurt)\s+myself\b|\bend\s+my\s+life\b|\bsuicidal\b|\bkhudkushi\b|आत्महत्या|खुद\s+को\s+मार",
 'severe_dehydration':r'\bsevere\s+dehydration\b|\bseverely\s+dehydrated\b|बहुत\s+ज़्यादा\s+पानी\s+की\s+कमी',
}

NEGATIONS={
 'chest_pain':r"no\s+(?:current\s+)?chest\s+(?:pain|pressure|tightness)|(?:do\s+not|don't|doesn't|does\s+not)\s+have\s+(?:any\s+)?chest\s+pain|(?:सीने|छाती)\s*में\s*(?:दर्द|दबाव)\s*नहीं",
 'breathlessness':r"no\s+(?:difficulty|trouble)\s+breathing|no\s+(?:breathlessness|shortness\s+of\s+breath)|breathing\s+(?:is\s+)?(?:fine|normal)|saans\s+(?:ki\s*)?(?:dikkat|taklif|takleef)\s+nahi|dam\s+nahi\s+ghut\s+raha|(?:सांस|साँस)\s*(?:लेने\s*में|की)?\s*(?:कोई\s*)?(?:तकलीफ|तकलीफ़|दिक्कत)\s*नहीं",
 'unconsciousness':r"(?:not|isn't|is\s+not)\s+(?:unconscious|unresponsive)|behosh\s+(?:nahi|nahin)|बेहोश\s*नहीं",
 'severe_bleeding':r'no\s+(?:severe|heavy|uncontrolled)\s+bleeding|bleeding\s+(?:has\s+)?stopped|खून\s*(?:बहना\s*)?(?:रुक|बंद)\s*गया',
 'stroke_symptoms':r'no\s+(?:slurred\s+speech|face\s+droop|stroke\s+symptoms)',
 'seizure':r'no\s+(?:current\s+)?seizure|not\s+having\s+a\s+seizure',
 'suicidal_ideation':r'not\s+suicidal|no\s+suicidal\s+(?:thoughts|ideation)',
 'severe_dehydration':r'no\s+severe\s+dehydration|not\s+severely\s+dehydrated',
}

HISTORY=r'\b(?:last\s+year|last\s+week|months?\s+ago|years?\s+ago|history\s+of|used\s+to|previously|resolved|no\s+longer|gone\s+now)\b|पिछले\s*साल|\bpehle\b'
HYPOTHETICAL=r"\b(?:what\s+if|hypothetical|example|quoted|if\s+(?:someone|i|he|she))\b|अगर|\bagar\b"
UNCERTAIN=r"\b(?:not\s+sure|don't\s+know|do\s+not\s+know|cannot\s+tell|can't\s+tell|maybe|might\s+be|pata\s+nahi)\b|पता\s*नहीं"
PREFIX_DENIAL=r"(?:\bno|\bnot|\bnever|\bwithout|\bdenies|\bdeny|\bdon't|\bdoesn't|\bisn't|\baren't)\s+(?:(?:any|currently|having|have|has|a|an|been|feeling|experiencing|sudden|severe|current|really|gasping|for|air)\s+)*$"

def mention_status(clause,hit,flag):
    if re.search(HYPOTHETICAL,clause):return 'hypothetical'
    if re.search(HISTORY,clause):return 'historical'
    if re.search(UNCERTAIN,clause):return 'hypothetical'  # unresolved, never a denial
    negatives=list(re.finditer(NEGATIONS.get(flag,r'(?!)'),clause))
    if any(n.start()<=hit.start() and n.end()>=hit.end() for n in negatives):return 'denied'
    before=clause[max(0,hit.start()-85):hit.start()]
    if re.search(r'\b(?:no|not|without)\b',before) and re.search(r'\b(?:or|nor)\s*$',before):return 'denied'
    after=clause[hit.end():hit.end()+35]
    if re.search(PREFIX_DENIAL,before) or re.search(r'^\s*(?:nahi|nahin|nai|नहीं|नही)(?:\s|$)',after):return 'denied'
    return 'affirmed'

def detect(text):
    result={}
    # Current statements after an explicit contrast receive a fresh scope.
    clauses=re.split(r'[.!?;,\n]|\bbut\b|\blekin\b|लेकिन|\band\s+(?:now|then|later)\b',text,flags=re.I)
    inherited=None
    for original in clauses:
        clause=canonical(original)
        if re.search(HYPOTHETICAL,clause):inherited='hypothetical'
        elif re.search(HISTORY,clause):inherited='historical'
        elif re.search(r'^(?:\s*(?:and\s+)?)(?:now|currently|abhi|अभी)\b',clause):inherited=None
        for flag,pattern in PATTERNS.items():
            hits=list(re.finditer(pattern,clause))
            statuses=[]
            for i,h in enumerate(hits):
                status=inherited or mention_status(clause,h,flag)
                if i and statuses[-1]=='denied' and re.fullmatch(r'\s*(?:or|and|nor)\s*',clause[hits[i-1].end():h.start()]):status='denied'
                statuses.append(status)
            if not hits and re.search(NEGATIONS.get(flag,r'(?!)'),clause):
                statuses=['hypothetical' if re.search(HYPOTHETICAL,clause) else 'historical' if re.search(HISTORY,clause) else 'denied']
            for status in statuses:
                if flag not in result or status=='affirmed':
                    result[flag]=FlagEvidence(flag=flag,status=status,quote=text.strip() if inherited else original.strip())
    return list(result.values())
