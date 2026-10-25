"""Sarvam speech-to-text for voice input. Text triage is local-only; no text
model is called. The API key lives in .env and is never logged."""
import asyncio
import os
import httpx
from .config import ROOT  # Ensures .env is loaded for CLI providers as well.

class ProviderError(Exception):
    def __init__(self,kind):self.kind=kind;super().__init__(kind)

# Sarvam language codes for the app's language options. 'auto' sends no code
# so Sarvam detects the spoken language itself.
LANGUAGE_CODES={'en':'en-IN','hi':'hi-IN'}

class SarvamAudio:
    def __init__(self):
        self.key=os.getenv('SARVAM_API_KEY','')
        self.model=os.getenv('SARVAM_STT_MODEL','saarika:v2.5')
        self.client=httpx.AsyncClient(base_url='https://api.sarvam.ai/',headers={'api-subscription-key':self.key},timeout=httpx.Timeout(45,connect=5),follow_redirects=False)

    async def close(self):
        await self.client.aclose()

    async def post(self,path,**kwargs):
        for attempt in range(2):
            try:
                result=await self.client.post(path,**kwargs)
            except httpx.TimeoutException:
                if attempt==1:raise ProviderError('timeout')
                await asyncio.sleep(.3);continue
            except httpx.RequestError:raise ProviderError('unavailable')
            if result.status_code in (429,500,502,503,504):
                if attempt==0:
                    await asyncio.sleep(.4);continue
                raise ProviderError('rate_limit' if result.status_code==429 else 'unavailable')
            if result.status_code in (401,403):raise ProviderError('credentials')
            if result.status_code>=400:raise ProviderError('request_rejected')
            try:return result.json()
            except ValueError:raise ProviderError('malformed_response')
        raise ProviderError('unavailable')

    async def transcribe(self,content,filename,mime,language):
        if not self.key:raise ProviderError('audio_not_configured')
        data={'model':self.model}
        code=LANGUAGE_CODES.get(language)
        if code:data['language_code']=code
        raw=await self.post('speech-to-text',files={'file':(filename,content,mime)},data=data)
        if not isinstance(raw.get('transcript'),str):raise ProviderError('malformed_audio_output')
        text=raw['transcript'].strip()
        if not text:raise ProviderError('no_speech')
        return text
