import asyncio,json
import httpx
import pytest
from backend.app.providers import GroqAccounts,ProviderError,strict_schema
from backend.app.schemas import Extraction,Request

def test_separate_accounts_and_exact_structured_payload(monkeypatch):
    monkeypatch.setenv('GROQ_TEXT_API_KEY','synthetic-text-key');monkeypatch.setenv('GROQ_AUDIO_API_KEY','synthetic-audio-key')
    async def scenario():
        p=GroqAccounts();assert p.text_client is not p.audio_client
        assert p.text_client.headers['Authorization']=='Bearer synthetic-text-key'
        assert p.audio_client.headers['Authorization']=='Bearer synthetic-audio-key'
        seen=[]
        async def text_handler(request):
            body=json.loads(request.content);seen.append(body)
            assert body['response_format']['json_schema']['strict'] is True
            return httpx.Response(200,json={'choices':[{'message':{'content':Extraction(service='doctor',evidence=['Want a doctor consultation']).model_dump_json()}}]})
        async def audio_handler(request):
            assert request.headers['Authorization']=='Bearer synthetic-audio-key'
            return httpx.Response(200,json={'text':'saans nahi aa rahi','segments':[]})
        await p.text_client.aclose();await p.audio_client.aclose()
        p.text_client=httpx.AsyncClient(transport=httpx.MockTransport(text_handler),base_url='https://synthetic.test/',headers={'Authorization':'Bearer synthetic-text-key'})
        p.audio_client=httpx.AsyncClient(transport=httpx.MockTransport(audio_handler),base_url='https://synthetic.test/',headers={'Authorization':'Bearer synthetic-audio-key'})
        try:
            x=await p.extract(Request(user_input='Want a doctor consultation',location={'lat':0,'lng':0}));assert x.service=='doctor'
            assert await p.transcribe(b'synthetic','x.wav','audio/wav','hi')=='saans nahi aa rahi'
        finally:await p.close()
    asyncio.run(scenario())

def test_malformed_output_and_bounded_retry():
    async def scenario():
        p=GroqAccounts();p.text_key='synthetic';calls=[]
        async def rate(request):calls.append(1);return httpx.Response(429,json={'error':'rate limited'})
        await p.text_client.aclose();p.text_client=httpx.AsyncClient(transport=httpx.MockTransport(rate),base_url='https://synthetic.test/')
        request=Request(user_input='Need help',location={'lat':0,'lng':0})
        try:
            with pytest.raises(ProviderError,match='rate_limit'):await p.extract(request)
            assert len(calls)==2
            async def malformed(r):return httpx.Response(200,json={'choices':[{'message':{'content':'{"care_type":"invented"}'}}]})
            await p.text_client.aclose();p.text_client=httpx.AsyncClient(transport=httpx.MockTransport(malformed),base_url='https://synthetic.test/')
            with pytest.raises(ProviderError,match='malformed_text_output'):await p.extract(request)
        finally:await p.close()
    asyncio.run(scenario())

