import asyncio
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import re
import tempfile
import time
from fastapi import FastAPI,File,Form,HTTPException,UploadFile,Request as HTTPRequest
from fastapi.responses import FileResponse,JSONResponse
from fastapi.staticfiles import StaticFiles
from .config import ROOT,MAX_AUDIO_BYTES,REFERENCE_TIME
from .core import assess
from .intake import detect_flags,extract_local,State,active_flags,replay
from .complaints import emergency_evidence
from .providers import SarvamAudio,ProviderError
from .schemas import Request,Response

@asynccontextmanager
async def lifespan(app):
    app.state.providers=SarvamAudio()
    yield
    await app.state.providers.close()

app = FastAPI(
    title="CareCompass · Diligence",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

class SizeLimit:
    """Bound request bytes before JSON/multipart parsing, including chunked bodies."""
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http' or scope['method'] not in ('POST','PUT','PATCH'):
            return await self.app(scope,receive,send)
        limit=MAX_AUDIO_BYTES+65536 if scope['path']=='/transcribe' else 160000
        body=bytearray()
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            body.extend(message.get('body',b''))
            if len(body)>limit:
                response=JSONResponse({'detail':'Upload/request too large'},status_code=413)
                return await response(scope,receive,send)
            if not message.get('more_body',False):break
        sent=False
        async def replay_receive():
            nonlocal sent
            if sent:return await receive()
            sent=True
            return {'type':'http.request','body':bytes(body),'more_body':False}
        await self.app(scope,replay_receive,send)

app.add_middleware(SizeLimit)

@app.middleware('http')
async def headers(request,call_next):
    response=await call_next(request)
    response.headers['Cache-Control']='no-store'
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['Permissions-Policy']='microphone=(self), geolocation=(self)'
    response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; media-src 'self' blob:; frame-ancestors 'none'; base-uri 'self'"
    if request.url.path in ("/docs", "/docs/oauth2-redirect"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        )


    return response

@app.exception_handler(ProviderError)
async def provider_error(request,error):
    return JSONResponse(status_code=503,content={'detail':{'code':error.kind,'message':'Assessment/transcription unavailable. Try again or seek human clinical assessment. For immediate danger call 112. No help has been dispatched.'}})

@app.get('/health')
async def health(request:HTTPRequest):
    p=request.app.state.providers
    return {'status':'ok','text_mode':'rules_baseline','audio_mode':'live_configured_not_verified' if p.key else 'unavailable_no_key','reference_time':REFERENCE_TIME,'synthetic_demo':True,'version':'0.2.0'}

@app.post('/triage',response_model=Response)
async def triage(body:Request,request:HTTPRequest):
    try:
        result,_=await asyncio.wait_for(assess(body),timeout=35)
        return result
    except asyncio.TimeoutError:raise ProviderError('text_deadline')

@app.post('/ui/triage')
async def ui_triage(body:Request,request:HTTPRequest):
    try:
        result,meta=await asyncio.wait_for(assess(body),timeout=35)
        return {'response':result.model_dump(),'ui':meta}
    except asyncio.TimeoutError:raise ProviderError('text_deadline')

@app.post('/ui/safety')
async def preview_safety(body:Request):
    # Local-only check for an editable transcript; never calls any transcription provider.
    state=replay(body);flags=active_flags(state)
    evidence=sorted(set(state.established_emergencies+emergency_evidence(state)))
    return {'emergency_warning':bool(flags or evidence),'red_flags':flags,'emergency_evidence':evidence,'engine':'local_safety_preview'}

async def validate_audio(content):
    # Decode using FFmpeg to validate the media, duration and actual signal.
    # Private temporary files are removed even on errors; no audio logging.
    with tempfile.TemporaryDirectory(prefix='carecompass-audio-') as tmp:
        path=Path(tmp)/'upload.bin';path.write_bytes(content)
        try:
            proc=await asyncio.create_subprocess_exec('ffprobe','-v','error','-select_streams','a:0','-show_entries','stream=codec_type:format=duration','-of','json',str(path),stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            try:out,_=await asyncio.wait_for(proc.communicate(),timeout=8)
            except asyncio.TimeoutError:
                proc.kill();await proc.wait();raise HTTPException(422,'Audio validation timed out')
            if proc.returncode:raise HTTPException(422,'Invalid audio container')
            info=json.loads(out)
            if not info.get('streams'):raise HTTPException(422,'No audio track found')
            duration=info.get('format',{}).get('duration')
            if duration is not None and not .1<=float(duration)<=65:raise HTTPException(422,'Record between 0.1 and 60 seconds')
            proc=await asyncio.create_subprocess_exec('ffmpeg','-nostdin','-v','info','-i',str(path),'-t','66','-vn','-af','volumedetect','-f','null','-',stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
            try:_,err=await asyncio.wait_for(proc.communicate(),timeout=10)
            except asyncio.TimeoutError:
                proc.kill();await proc.wait();raise HTTPException(422,'Audio decoding timed out')
            if proc.returncode:raise HTTPException(422,'Audio could not be decoded')
            text=err.decode(errors='replace')
            vol=re.search(r'max_volume:\s*(-?\d+(?:\.\d+)?|-inf)\s*dB',text)
            if vol and (vol[1]=='-inf' or float(vol[1])< -50):raise HTTPException(422,'No audible speech. Please try again or type your message.')
            times=re.findall(r'time=(\d+):(\d+):(\d+(?:\.\d+)?)',text)
            if times and sum(float(v)*m for v,m in zip(times[-1],(3600,60,1)))>65:raise HTTPException(422,'Audio exceeds 60 seconds')
        except FileNotFoundError:raise HTTPException(503,'FFmpeg/ffprobe is required for secure audio validation. Install it or use Docker.')

@app.post('/transcribe')
async def transcribe(request:HTTPRequest,file:UploadFile=File(...),language:str=Form('auto')):
    try:
        content=await file.read(MAX_AUDIO_BYTES+1)
        if len(content)>MAX_AUDIO_BYTES:raise HTTPException(413,'Audio exceeds 10 MiB')
        mime=(file.content_type or '').split(';')[0]
        suffix={'audio/webm':'.webm','video/webm':'.webm','audio/wav':'.wav','audio/x-wav':'.wav','audio/ogg':'.ogg','audio/mpeg':'.mp3','audio/mp4':'.m4a','video/mp4':'.mp4','audio/flac':'.flac','audio/x-flac':'.flac'}.get(mime)
        if not suffix:raise HTTPException(415,'Unsupported recording format')
        if not content:raise HTTPException(422,'The recording is empty')
        p=request.app.state.providers
        if not p.key:raise ProviderError('audio_not_configured')
        await validate_audio(content)
        try:transcript=await asyncio.wait_for(p.transcribe(content,'recording'+suffix,mime,language),timeout=45)
        except asyncio.TimeoutError:raise ProviderError('audio_deadline')
        state=State();state.merge(extract_local(transcript),transcript,0)
        flags=active_flags(state);extra=emergency_evidence(state)
        return {'transcript':transcript,'emergency_warning':bool(flags or extra),'detected_warning_signs':flags,'emergency_evidence':extra,'engine':'sarvam_audio_live','requires_confirmation':True}
    finally:await file.close()

app.mount('/assets',StaticFiles(directory=ROOT/'frontend'),name='assets')

@app.get('/',include_in_schema=False)
async def index():return FileResponse(ROOT/'frontend'/'index.html')

@app.get('/explorer', include_in_schema=False)
async def docs():
    return FileResponse(ROOT / 'frontend' / 'docs.html')

