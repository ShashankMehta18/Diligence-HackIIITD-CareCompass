from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.providers import ProviderError

def payload(text):return {'user_input':text,'language':'auto','location':{'lat':28.54,'lng':77.27},'conversation_history':[]}

def test_api_contract_and_ui():
    with TestClient(app) as c:
        assert c.get('/').status_code==200
        assert c.get('/docs').status_code==200
        assert c.get('/assets/app.js').status_code==200
        assert c.get('/health').json()['synthetic_demo']
        assert c.get('/openapi.json').status_code==200
        r=c.post('/triage',json=payload('saans nahi aa rahi'))
        assert r.status_code==200 and r.json()['care_type']=='emergency_112'
        assert set(r.json())=={'care_type','urgency','red_flags','reasoning','matched_caregivers','follow_up_question'}
        assert c.post('/triage',json={**payload('help'),'location':{'lat':999,'lng':0}}).status_code==422
        assert c.post('/triage',json=payload(' ')).status_code==422
        assert c.post('/ui/triage',json=payload('Need wound dressing')).json()['ui']['booking']=='simulated_only'

def test_audio_no_key_is_honest_and_bad_type():
    with TestClient(app) as c:
        c.app.state.providers.audio_key=''
        r=c.post('/transcribe',files={'file':('audio.webm',b'not audio','audio/webm')})
        assert r.status_code==503 and r.json()['detail']['code']=='audio_not_configured'
        assert c.post('/transcribe',files={'file':('bad.txt',b'bad','text/plain')}).status_code==415

def test_request_limit():
    with TestClient(app) as c:
        r=c.post('/triage',content=b'x'*160001,headers={'Content-Type':'application/json'})
        assert r.status_code==413

def test_provider_rate_limit_response():
    with TestClient(app) as c:
        p=c.app.state.providers;p.text_key='fake'
        async def fail(r):raise ProviderError('rate_limit')
        p.extract=fail
        assert c.post('/triage',json=payload('I have fever')).status_code==503
        assert c.post('/triage',json=payload('I cannot breathe')).json()['care_type']=='emergency_112'

