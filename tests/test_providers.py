import asyncio
import httpx
import pytest
from backend.app.providers import SarvamAudio,ProviderError

def test_sarvam_key_header_and_language_mapping(monkeypatch):
    monkeypatch.setenv('SARVAM_API_KEY','synthetic-sarvam-key')
    async def scenario():
        p=SarvamAudio();assert p.key=='synthetic-sarvam-key'
        assert p.client.headers['api-subscription-key']=='synthetic-sarvam-key'
        seen=[]
        async def handler(request):
            seen.append(request.content)
            return httpx.Response(200,json={'transcript':'saans nahi aa rahi','language_code':'hi-IN'})
        await p.client.aclose()
        p.client=httpx.AsyncClient(transport=httpx.MockTransport(handler),base_url='https://synthetic.test/')
        try:
            assert await p.transcribe(b'synthetic','x.wav','audio/wav','hi')=='saans nahi aa rahi'
            assert b'saarika' in seen[0] and b'hi-IN' in seen[0]
            assert await p.transcribe(b'synthetic','x.wav','audio/wav','auto')=='saans nahi aa rahi'
            assert b'language_code' not in seen[1]
        finally:await p.close()
    asyncio.run(scenario())

def test_sarvam_errors_and_bounded_retry(monkeypatch):
    monkeypatch.delenv('SARVAM_API_KEY',raising=False)
    async def scenario():
        p=SarvamAudio();p.key=''
        with pytest.raises(ProviderError,match='audio_not_configured'):
            await p.transcribe(b'x','x.wav','audio/wav','hi')
        p.key='synthetic';calls=[]
        async def rate(request):calls.append(1);return httpx.Response(429,json={'error':'rate limited'})
        await p.client.aclose();p.client=httpx.AsyncClient(transport=httpx.MockTransport(rate),base_url='https://synthetic.test/')
        try:
            with pytest.raises(ProviderError,match='rate_limit'):await p.transcribe(b'x','x.wav','audio/wav','hi')
            assert len(calls)==2
            async def denied(r):return httpx.Response(401,json={'error':'bad key'})
            await p.client.aclose();p.client=httpx.AsyncClient(transport=httpx.MockTransport(denied),base_url='https://synthetic.test/')
            with pytest.raises(ProviderError,match='credentials'):await p.transcribe(b'x','x.wav','audio/wav','hi')
            async def empty(r):return httpx.Response(200,json={'transcript':'   '})
            await p.client.aclose();p.client=httpx.AsyncClient(transport=httpx.MockTransport(empty),base_url='https://synthetic.test/')
            with pytest.raises(ProviderError,match='no_speech'):await p.transcribe(b'x','x.wav','audio/wav','hi')
            async def malformed(r):return httpx.Response(200,json={'no_transcript':True})
            await p.client.aclose();p.client=httpx.AsyncClient(transport=httpx.MockTransport(malformed),base_url='https://synthetic.test/')
            with pytest.raises(ProviderError,match='malformed_audio_output'):await p.transcribe(b'x','x.wav','audio/wav','hi')
        finally:await p.close()
    asyncio.run(scenario())
