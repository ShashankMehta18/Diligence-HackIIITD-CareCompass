from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

CareType = Literal['paramedic_home_visit','home_nursing','lab_test_home','teleconsultation','emergency_112']
Urgency = Literal['emergency','same_day','scheduled']
Flag = Literal['chest_pain','breathlessness','unconsciousness','severe_bleeding','stroke_symptoms','seizure','high_fever_infant','suicidal_ideation','severe_dehydration']

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)

class Location(Strict):
    lat: float = Field(ge=-90,le=90)
    lng: float = Field(ge=-180,le=180)

class HistoryTurn(BaseModel):
    # Dataset demonstrations contain partial assistant responses. Extra response
    # fields may be replayed, but never become trusted clinical state.
    model_config = ConfigDict(extra='allow')
    role: Literal['user','assistant']
    text: str | None = Field(default=None,max_length=6000)
    content: str | None = Field(default=None,max_length=6000)
    follow_up_question: str | None = Field(default=None,max_length=2000)
    question_id: str | None = Field(default=None,max_length=80)

class Request(Strict):
    user_input: str = Field(min_length=1,max_length=6000)
    language: str = Field(default='auto',max_length=30)
    location: Location
    conversation_history: list[HistoryTurn] = Field(default_factory=list,max_length=40)

    @model_validator(mode='after')
    def nonblank(self):
        if not self.user_input.strip(): raise ValueError('user_input must contain text')
        return self

class Match(Strict):
    caregiver_id: str
    score: float = Field(ge=0,le=1)
    reason: str

class Response(Strict):
    follow_up_question: str | None
    care_type: CareType | None
    urgency: Urgency | None
    red_flags: list[Flag]
    reasoning: str
    matched_caregivers: list[Match]

    @model_validator(mode='after')
    def invariant(self):
        if self.red_flags or self.care_type=='emergency_112' or self.urgency=='emergency':
            if self.care_type!='emergency_112' or self.urgency!='emergency' or self.matched_caregivers or self.follow_up_question is not None:
                raise ValueError('Emergency invariant failed')
        elif self.follow_up_question is not None:
            if not self.follow_up_question.strip() or self.care_type is not None or self.urgency is not None or self.matched_caregivers:
                raise ValueError('Clarification invariant failed')
        elif self.care_type is None or self.urgency is None:
            raise ValueError('Final route requires care and urgency')
        return self

class FlagEvidence(Strict):
    flag: Flag
    status: Literal['affirmed','denied','historical','hypothetical']
    quote: str

class SymptomEvidence(Strict):
    name: str = Field(min_length=1,max_length=80)
    status: Literal['affirmed','denied','unknown']
    quote: str

Complaint = Literal['abdominal_pain','headache','vomiting','diarrhoea','cough','sore_throat','urinary','back_pain','joint_pain','rash','dizziness','injury','eye_problem','ear_pain','dental_pain','fatigue','fever','other']
BodySite = Literal['knee','ankle','foot','hip','leg','shoulder','elbow','wrist','hand','arm']
Feature = Literal['abdominal_tenderness','vomiting_blood','black_sticky_stool','blood_in_stool','sudden_worst_headache','new_one_sided_weakness','vision_loss','new_confusion','airway_swelling','cannot_swallow_saliva','bladder_change','saddle_numbness','can_keep_fluids','urine_retention','flank_pain','blood_in_urine','fever_with_complaint','cannot_bear_weight','nonblanching_rash','recent_injury','joint_swelling','joint_severe_swelling','joint_hot_red','cannot_move_joint','joint_locking','limb_deformity','limb_numbness','ear_discharge','hearing_change','dental_swelling']

class ClinicalFinding(Strict):
    name: Feature
    status: Literal['affirmed','denied','historical','hypothetical']
    quote: str = Field(min_length=1,max_length=6000)

class Extraction(Strict):
    complaint: Complaint | None = None
    complaint_text: str | None = Field(default=None,max_length=300)
    severity: Literal['mild','moderate','severe'] | None = None
    body_site: BodySite | None = None
    pain_location: str | None = Field(default=None,max_length=160)
    sudden_onset: bool | None = None
    clinical_features: list[ClinicalFinding] = Field(default_factory=list,max_length=30)
    patient: str | None = None
    age_months: float | None = Field(default=None,ge=0,le=1440)
    duration_days: float | None = Field(default=None,ge=0,le=36500)
    temperature: float | None = Field(default=None,ge=0,le=150)
    temperature_unit: Literal['C','F'] | None = None
    temperature_timing: Literal['current','historical','unknown'] | None = None
    onset: str | None = None
    progression: Literal['worsening','improving','unchanged'] | None = None
    fever: bool | None = None
    service: Literal['dressing','injection_im','injection_iv','injection_unknown','insulin','bp_sugar','lab','doctor','home_assessment'] | None = None
    flags: list[FlagEvidence] = Field(default_factory=list)
    associated_symptoms: list[SymptomEvidence] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)

