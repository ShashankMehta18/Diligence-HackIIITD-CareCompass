"""Build the fixed, developer-authored challenge suite, not clinical ground truth.

Cases are separate from organiser templates. Translation/negation variants share
scenario IDs and must never be split across training/test partitions. This suite
was authored before this safety patch and is used for development regression;
it is NOT an independent clinical or blind held-out benchmark.
"""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CASES=[]

def add(group,language,text,expected,**extra):
    CASES.append(dict(id=f'safety-{len(CASES)+1:03}',scenario_id=group,language=language,
                      user_input=text,expected=expected,**extra))

PHRASES={
 'unconsciousness':[
  ('en','My father has passed out and will not wake up'),
  ('en','She is unconscious and not responding to me'),
  ('en','He is unresponsive even when I call his name'),
  ('hi','पापा बेहोश हो गए हैं और उठ नहीं रहे'),
  ('hi','वह आवाज़ देने पर जवाब नहीं दे रहे हैं'),
  ('hinglish','papa behosh ho gaye'),
  ('hinglish','mummy ko hosh nahi aa raha'),
  ('hinglish','woh awaaz dene par jawab nahi de rahe'),
 ],
 'breathlessness':[
  ('en','I am gasping for air and struggling to breathe'),
  ('en','I cannot get enough air into my lungs'),
  ('en','I am having trouble catching my breath right now'),
  ('hi','मेरा दम घुट रहा है और साँस नहीं आ रही'),
  ('hi','मुझे सांस लेने में बहुत दिक्कत हो रही है'),
  ('hinglish','dam ghut raha hai'),
  ('hinglish','saas nahi aa rahi hai'),
  ('hinglish','saans lene mein bahut dikkat ho rahi hai'),
 ],
 'severe_bleeding':[
  ('en','There is a deep cut and blood is gushing out'),
  ('en','Blood is spurting from the wound and will not stop'),
  ('en','The wound is bleeding heavily despite pressure'),
  ('hi','घाव से बहुत खून बह रहा है और रुक नहीं रहा'),
  ('hi','कटने के बाद खून फव्वारे की तरह निकल रहा है'),
  ('hinglish','bahut khoon beh raha hai aur ruk nahi raha'),
  ('hinglish','cut se khoon ruk nahin raha'),
  ('hinglish','zakhm se bohot khun nikal raha hai'),
 ],
 'stroke_symptoms':[
  ('en','Suddenly my left arm is weak and I cannot lift it'),
  ('en','One side of his face is drooping and his words are slurred'),
  ('en','My speech suddenly became slurred'),
  ('hi','अचानक शरीर के एक तरफ का हाथ काम नहीं कर रहा'),
  ('hi','अचानक चेहरा टेढ़ा हो गया और बोलने में दिक्कत है'),
  ('hinglish','ek taraf ka haath kaam nahi kar raha'),
  ('hinglish','achanak chehra tedha ho gaya'),
  ('hinglish','achanak boli ladkhada rahi hai'),
 ],
 'chest_pain':[
  ('en','There is pressure in my chest right now'),
  ('en','I have chest pain and a tight feeling in my chest'),
  ('en','I feel a crushing pain in my chest'),
  ('hi','मेरे सीने में दबाव और दर्द है'),
  ('hi','अभी छाती में दर्द हो रहा है'),
  ('hinglish','mere seene mein dabav aur dard hai'),
  ('hinglish','chhati mein dard ho raha hai'),
  ('hinglish','seene me jakdan ho rahi hai'),
 ],
 'seizure':[
  ('en','He is having a seizure now'),
  ('en','She is convulsing on the floor'),
  ('en','My child is having convulsions right now'),
  ('hi','उन्हें अभी दौरा पड़ रहा है'),
  ('hi','अभी बच्चे को दौरा आ रहा है'),
  ('hinglish','abhi daura pad raha hai'),
  ('hinglish','bacche ko daura aa raha hai'),
  ('hinglish','mere bhai ko abhi seizure ho raha hai'),
 ],
}
for flag,phrases in PHRASES.items():
    for index,(lang,text) in enumerate(phrases):
        group=f'{flag}-{index//3+1}'
        add(group,lang,text,dict(emergency=True,flag=flag,routine_matching_allowed=False),kind='active_warning')
        add(group,lang,'Hypothetical example: '+text,dict(emergency=False),kind='hypothetical_control')
        add(group,lang,'Last year, '+text+'; this is resolved history, not a current problem.',dict(emergency=False),kind='historical_control')

DENIALS=[
 ('en','I have no chest pressure or chest pain'),
 ('en','I am not gasping for air; my breathing is normal'),
 ('en','My father is not unconscious; he is awake and responding'),
 ('en','No blood is gushing out; it was a small scratch'),
 ('en','I do not have slurred speech or sudden arm weakness'),
 ('en','I am not having a seizure'),
 ('hi','पापा बेहोश नहीं हैं, वह बात कर रहे हैं'),
 ('hi','सांस लेने में कोई दिक्कत नहीं है'),
 ('hi','सीने में दर्द नहीं है'),
 ('hi','खून बहना बंद हो गया है'),
 ('hinglish','papa behosh nahi hain woh baat kar rahe hain'),
 ('hinglish','dam nahi ghut raha hai'),
 ('hinglish','seene mein dard nahi hai'),
 ('hinglish','saans ki dikkat nahi hai'),
 ('en','I feel mild knee pain after walking'),
 ('en','My shoulder hurts when I lift my arm after exercise'),
 ('en','My face looks normal and I can speak normally'),
 ('en','I feel tired after a long day'),
]
for index,(lang,text) in enumerate(DENIALS):
    add(f'nonemergency-control-{index}',lang,text,dict(emergency=False),kind='denial_or_lookalike')

UNKNOWN_COMPLAINTS=[
 ('dizziness','I am dizzy'),('cardiac','I have palpitations'),
 ('neuro','I have tingling'),('fatigue','I feel unusually tired'),
 ('injury','I have an injury'),('knee_pain','My knee hurts'),
 ('shoulder_pain','My shoulder hurts'),('ankle_pain','My ankle hurts'),
 ('neck_pain','My neck hurts'),('wrist_pain','My wrist hurts'),
 ('elbow_pain','My elbow hurts'),('hip_pain','My hip hurts'),
 ('foot_pain','My foot hurts'),('hand_pain','My finger hurts'),
 ('joint_pain','My joints ache'),('muscle_pain','I have muscle pain'),
 ('abdominal_pain','My belly hurts'),('headache','I have a headache'),
 ('vomiting','I am vomiting'),('diarrhoea','I have diarrhoea'),
 ('cough','I am coughing'),('sore_throat','My throat is sore'),
 ('urinary','It burns when I pee'),('back_pain','My back aches'),
 ('wound','I have a wound'),('diabetes','I have diabetes'),
 ('catheter','My catheter is leaking'),('nebulization','I need nebulization'),
 ('vitals_check','I need a vitals check'),('post_surgical','Post surgery care'),
 ('bedridden','I need bedridden care'),('elderly_care','I need elderly care'),
 ('menstrual','I have menstrual problems'),('anxiety','I feel anxious'),
 ('sleep_problem','I have a sleep problem'),('nasal','I have nasal congestion'),
 ('kidney','I have kidney disease'),('thyroid','I have thyroid problems'),
 ('nutrition','I have unexplained weight loss'),('blood','I have unusual bruising'),
 ('rash','I have a rash'),('eye_problem','I have eye pain'),
 ('ear_pain','My ear aches'),('dental_pain','I have toothache'),
 ('fever','I have a fever'),('other','I have an unfamiliar fluttering sensation'),
]
for complaint,text in UNKNOWN_COMPLAINTS:
    add(f'unknown-{complaint}','en',text,dict(emergency=False,routine_matching_allowed=False,human_review_required=True),
        kind='unresolved_conversation',answers=['not sure']*6,expected_complaint=complaint)

for index,(text,care) in enumerate([
 ('Need prescribed wound dressing at home','home_nursing'),
 ('Need an IM injection at home','home_nursing'),
 ('Need BP and sugar checked at home','paramedic_home_visit'),
 ('Need a CBC home sample collection','lab_test_home'),
]):
    add(f'explicit-service-{index}','en',text,dict(emergency=False,care_type=care,routine_matching_allowed=True),kind='service_control')

for index,(first,later,flag) in enumerate([
 ('My knee hurts','Now I am gasping for air','breathlessness'),
 ('My wrist hurts','abhi papa behosh ho gaye','unconsciousness'),
 ('I have a rash','Now blood is gushing out of a cut','severe_bleeding'),
 ('I have a fever','Now my speech suddenly became slurred','stroke_symptoms'),
]):
    add(f'late-warning-{index}','en',first,dict(emergency=True,flag=flag,routine_matching_allowed=False),kind='late_warning',answers=[later])

if __name__=='__main__':
    path=ROOT/'cases.jsonl'
    path.write_text(''.join(json.dumps(c,ensure_ascii=False)+'\n' for c in CASES))
    manifest=dict(version='safety-challenges-1',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  cases=len(CASES),scenario_groups=len({c['scenario_id'] for c in CASES}),
                  provenance='Developer/AI-authored before patch; independent of organiser data, NOT clinician-reviewed or blind held-out.',
                  usage='Development regression. Do not train on this file or claim clinical accuracy from its results.',
                  languages=['en','hi','hinglish'])
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2))
