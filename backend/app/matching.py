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
            row['specialty']=(row.get('specialty') or '').strip()
            row['supported_complaints']=[s.strip() for s in (row.get('supported_complaints') or '').split(';') if s.strip()]
            result.append(row)
    if len({x['caregiver_id'] for x in result})!=len(result):raise ValueError('Duplicate caregiver IDs')
    return result

ROSTER=load_roster()
IDS={r['caregiver_id'] for r in ROSTER}
REQUIRED={'dressing':{'wound_dressing'},'injection_im':{'injection_im'},'injection_iv':{'injection_iv'},'bp_sugar':{'bp_sugar_check'},'lab':{'sample_collection'},'doctor':{'teleconsultation'},'catheter':{'catheter_care'},'nebulization':{'nebulization'},'post_surgical':{'post_surgical_care'},'elderly':{'elderly_care'}}

def display_specialty(cg):
    spec=cg.get('specialty') or ''
    return 'General Medicine' if 'placeholder' in spec else spec

# Designated specialists per complaint family, from the user's symptom
# mapping database (data/symptom_mapping.csv). Tier 1 ranks first; other
# presenting-key supporters fill remaining slots. Families not listed
# have no tier preference.
FAMILY_SPECIALTIES={
    'knee_pain':{'Orthopedics','Rheumatology','Sports Medicine'},
    'rash':{'Dermatology','Allergy and Clinical Immunology'},
    'headache':{'Neurology'},
    'muscle_pain':{'Sports Medicine','Physical Medicine and Rehabilitation','Orthopedics'},
    'nasal':{'ENT (Otolaryngology)','Allergy and Clinical Immunology'},
    'cardiac':{'Cardiology'},
    'neuro':{'Neurology'},
}

def presenting_keys(keys):
    # Follow-up and review keys qualify a doctor for follow-up care, not for
    # a first presentation: a doctor supporting ONLY such a key must not
    # outrank doctors supporting the presenting complaint itself.
    present={k for k in keys if not (k.endswith('_followup') or k.startswith('chronic_') or k.endswith('_review'))}
    return present or set(keys)

def clock(value=None):
    t=value or REFERENCE_TIME
    return datetime.now(ZoneInfo('Asia/Kolkata')) if t=='now' else datetime.fromisoformat(t).astimezone(ZoneInfo('Asia/Kolkata'))

def match(req,care,service,language,reference_time=None,scheduled_future=False,complaint_keys=None,complaint=None,is_child=False):
    if care=='emergency_112':return [],[]
    # No roster evidence for insulin/subcutaneous injections. Never substitute IM.
    if service in ('insulin','injection_unknown'):return [],[]
    role={'home_nursing':'medic','paramedic_home_visit':'medic','lab_test_home':'phlebotomist','teleconsultation':'doctor'}[care]
    required=REQUIRED.get(service,set())
    if care=='teleconsultation':required={'teleconsultation'}
    if care=='lab_test_home':required={'sample_collection'}
    # Specialty eligibility for doctors: only doctors whose supported complaints
    # overlap the complaint family may match. When no specialist supports it,
    # generalist doctors (general_symptoms / initial_assessment) are the fallback.
    # complaint_keys=None (unknown complaint, service-only consult) keeps the
    # previous any-doctor behaviour.
    doctor_ids=None
    if role=='doctor' and complaint_keys is not None:
        keys=set(complaint_keys)
        pool_keys=presenting_keys(keys)
        specific={cg['caregiver_id'] for cg in ROSTER if cg['role']=='doctor' and pool_keys & set(cg.get('supported_complaints') or [])}
        generalist={cg['caregiver_id'] for cg in ROSTER if cg['role']=='doctor' and {'general_symptoms','initial_assessment'} & set(cg.get('supported_complaints') or [])}
        doctor_ids=specific or generalist
    designated=FAMILY_SPECIALTIES.get(complaint,set()) if complaint else set()
    family_child={k for k in complaint_keys if k.startswith('child_')} if complaint_keys else set()
    now=clock(reference_time); hhmm=now.strftime('%H:%M');rank=[]
    for cg in ROSTER:
        if not cg['active'] or cg['role']!=role or required-set(cg['skills']):continue
        if doctor_ids is not None and cg['caregiver_id'] not in doctor_ids:continue
        if not scheduled_future and cg['free_until']<=hhmm:continue
        distance=None if care=='teleconsultation' else haversine(req.location.lat,req.location.lng,cg['base_lat'],cg['base_lng'])
        if distance is not None and distance>cg['max_radius_km']:continue
        l=float(language in cg['languages'])
        p=1.0 if distance is None else max(0,1-distance/cg['max_radius_km'])
        s=1.0  # All essential skills have already passed the eligibility filter.
        # No bonus: every roster specialty is a real specialty name, so a bonus
        # would apply to all doctors equally and only push scores into the 1.0
        # cap, hiding rating differences and letting roster order decide ties.
        score=round(.35*l+.30*p+.20*s+.15*cg['rating']/5,6)
        slot='Future availability unconfirmed' if scheduled_future else f"Available {max(hhmm,cg['free_from'])}-{cg['free_until']} IST at reference time"
        parts=[f"{language} listed" if l else f"{language} not listed; language preference not met"]
        if cg.get('specialty'):parts.append(f"Specialty: {display_specialty(cg)}")
        parts.append('Virtual consultation' if distance is None else f'{distance:.1f} km away; within {cg["max_radius_km"]:g} km radius')
        parts.extend([('Required skills: '+', '.join(sorted(required))) if required else 'Compatible home-assessment role',slot,f'Rating {cg["rating"]:g}/5'])
        reason='; '.join(parts)
        supported=set(cg.get('supported_complaints') or [])
        if is_child and family_child & supported:tier=0
        elif cg.get('specialty') in designated:tier=1
        else:tier=2
        rank.append((tier,score,distance or 0,cg,reason,slot))
    rank.sort(key=lambda r:(r[0],-r[1],r[2],r[3]['caregiver_id']))
    matches=[Match(caregiver_id=r[3]['caregiver_id'],score=r[1],reason=r[4]) for r in rank[:3]]
    cards=[{**{k:r[3][k] for k in ['caregiver_id','name','role','languages','skills','rating','free_from','free_until']},'specialty':display_specialty(r[3]),'distance_km':round(r[2],2) if care!='teleconsultation' else None,'slot':r[5],'bookable':not scheduled_future} for r in rank[:3]]
    return matches,cards

