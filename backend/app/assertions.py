"""Shared assertion scope. Finite language handling, not clinical validation."""
import re
from .emergency_language import canonical

HYPOTHETICAL=r'\b(?:what if|hypothetical|example|quoted|if someone|if i|if he|if she|if swallowed|if ingested|label says|general question|writing a story)\b|अगर|\bagar\b'
REMOTE=r'\b(?:last year|last week|\w+ years? ago|\w+ months? ago|history of|used to)\b|पिछले\s*साल|\w+\s*साल\s*पहले'
RECENT=r'\b(?:just now|earlier today|today|(?:\d+|one|two|three|ten|twenty|thirty|sixty)\s*(?:minutes?|mins?|hours?|hrs?)\s*ago|last hour|past hour)\b|(?:एक|दो|तीन|दस|बीस|\d+)\s*(?:मिनट|घंटे?)\s*पहले|अभी|आज|abhi|aaj'
CURRENT=r'^\s*(?:(?:and|but|lekin)\s+)?(?:now|currently|today|abhi|aaj|अभी|अब|आज)(?:\s|$)'
UNCERTAIN=r"\b(?:not sure|don't know|do not know|cannot tell|can't tell|pata nahi|unknown)\b|पता\s*नहीं"
DENIAL=r"(?:\bno|\bnot|\bwithout|\bdenies|\bnever|\bdidn't|\bdid not|\bhasn't|\bhaven't|\bdon't|\bdoesn't|\bisn't|\bwasn't|\bwas not|\bhas not|\bhad not|\bnothing)\s+(?:(?:any|have|has|had|having|currently|sudden|suddenly|severe|new|a|an|been|ever|really|accidentally|trouble|difficulty|swallowed|taken|touched|sharp|foreign|object|glass|metal|shard|fragment)\s+)*$"

def clauses(text):
    """Retain history/example scope across a comma; explicit current scope resets."""
    inherited=None
    for raw in re.split(r'[.!?;,\n]|\bbut\b|\blekin\b|लेकिन',text,flags=re.I):
        t=canonical(raw)
        if not t.strip():continue
        if re.search(CURRENT,t):inherited=None
        if re.search(HYPOTHETICAL,t):inherited='hypothetical'
        elif re.search(REMOTE,t):inherited='historical'
        yield raw,t,inherited

def status(text,hit,inherited=None,uncertainty=True):
    if inherited:return inherited
    if re.search(HYPOTHETICAL,text):return 'hypothetical'
    if re.search(REMOTE,text):return 'historical'
    before=text[max(0,hit.start()-90):hit.start()]
    after=text[hit.end():hit.end()+36]
    if re.search(DENIAL,before) or re.search(r'^\s*(?:nahi|nahin|nai|नहीं|नही)(?:\s|$)',after):return 'denied'
    # Coordinated denial of different concepts: no chest pain OR trouble breathing.
    start=re.search(r'\b(?:no|not|without)\b',before)
    if start and re.search(r'\b(?:or|nor)\s*(?:any\s*)?$',before) and not re.search(r'\b(?:but|now|have developed|started)\b',before[start.end():]):return 'denied'
    if uncertainty and re.search(UNCERTAIN,text):return 'unknown'
    if re.search(r'\b(?:resolved|no longer|gone now|stopped)\b|अब\s*ठीक',text):return 'recent_resolved' if recent_event(text) else 'historical'
    return 'affirmed'

def recent_event(text):
    values={'one':1,'two':2,'three':3,'ten':10,'twenty':20,'thirty':30,'sixty':60}
    m=re.search(r'\b(\d+|one|two|three|ten|twenty|thirty|sixty)\s*(minutes?|mins?|hours?|hrs?)\s*ago',text)
    if m:
        n=float(m[1]) if m[1].isdigit() else values[m[1]]
        return n<= (24 if m[2].startswith(('hour','hr')) else 1440)
    return bool(re.search(RECENT,text))
