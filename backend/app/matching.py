import csv
import math
from datetime import datetime
from zoneinfo import ZoneInfo
from .config import DATA,REFERENCE_TIME
from .schemas import Match

def haversine(a,b,c,d):
    a,b,c,d=map(math.radians,[a,b,c,d])
    x=math.sin((c-a)/2)**2+math.cos(a)*math.cos(c)*math.sin((d-b)/2)**2
    return 12742*math.asin(min(1,math.sqrt(x)))

def load_roster():
    result=[]
    with (DATA/'caregivers.csv').open() as f:
        for row in csv.DictReader(f):
            row['active']=row['active'].strip().lower()=='true'
            for key in ['base_lat','base_lng','max_radius_km','rating']:row[key]=float(row[key])
            for key in ['skills','languages']:row[key]=row[key].split(';')
            result.append(row)
    if len({x['caregiver_id'] for x in result})!=len(result):raise ValueError('Duplicate caregiver IDs')
    return result

ROSTER=load_roster()
IDS={r['caregiver_id'] for r in ROSTER}
REQUIRED={'dressing':{'wound_dressing'},'injection_im':{'injection_im'},'injection_iv':{'injection_iv'},'bp_sugar':{'bp_sugar_check'},'lab':{'sample_collection'},'doctor':{'teleconsultation'}}

def clock(value=None):
    t=value or REFERENCE_TIME
    return datetime.now(ZoneInfo('Asia/Kolkata')) if t=='now' else datetime.fromisoformat(t).astimezone(ZoneInfo('Asia/Kolkata'))

def match(req,care,service,language,reference_time=None,scheduled_future=False):
    if care=='emergency_112':return [],[]
    # No roster evidence for insulin/subcutaneous injections. Never substitute IM.
    if service in ('insulin','injection_unknown'):return [],[]
    role={'home_nursing':'medic','paramedic_home_visit':'medic','lab_test_home':'phlebotomist','teleconsultation':'doctor'}[care]
    required=REQUIRED.get(service,set())
    if care=='teleconsultation':required={'teleconsultation'}
    if care=='lab_test_home':required={'sample_collection'}
    now=clock(reference_time); hhmm=now.strftime('%H:%M');rank=[]
    for cg in ROSTER:
        if not cg['active'] or cg['role']!=role or required-set(cg['skills']):continue
        if not scheduled_future and cg['free_until']<=hhmm:continue
        distance=None if care=='teleconsultation' else haversine(req.location.lat,req.location.lng,cg['base_lat'],cg['base_lng'])
        if distance is not None and distance>cg['max_radius_km']:continue
        l=float(language in cg['languages'])
        p=1.0 if distance is None else max(0,1-distance/cg['max_radius_km'])
        s=1.0  # All essential skills have already passed the eligibility filter.
        score=round(.35*l+.30*p+.20*s+.15*cg['rating']/5,6)
        slot='Future availability unconfirmed' if scheduled_future else f"Available {max(hhmm,cg['free_from'])}-{cg['free_until']} IST at reference time"
        parts=[f"{language} listed" if l else f"{language} not listed; language preference not met"]
        parts.append('Virtual consultation' if distance is None else f'{distance:.1f} km away; within {cg["max_radius_km"]:g} km radius')
        parts.extend([('Required skills: '+', '.join(sorted(required))) if required else 'Compatible home-assessment role',slot,f'Rating {cg["rating"]:g}/5'])
        reason='; '.join(parts)
        rank.append((score,distance or 0,cg,reason,slot))
    rank.sort(key=lambda r:(-r[0],r[1],r[2]['caregiver_id']))
    matches=[Match(caregiver_id=r[2]['caregiver_id'],score=r[0],reason=r[3]) for r in rank[:3]]
    cards=[{**{k:r[2][k] for k in ['caregiver_id','name','role','languages','skills','rating','free_from','free_until']},'distance_km':round(r[1],2) if care!='teleconsultation' else None,'slot':r[4],'bookable':not scheduled_future} for r in rank[:3]]
    return matches,cards

