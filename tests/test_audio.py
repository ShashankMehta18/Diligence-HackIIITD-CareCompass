import asyncio,io,math,shutil,struct,wave
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from backend.app.main import app,validate_audio

def sound(silent=False):
    b=io.BytesIO()
    with wave.open(b,'wb') as w:
        w.setnchannels(1);w.setsampwidth(2);w.setframerate(16000)
        w.writeframes(b''.join(struct.pack('<h',0 if silent else int(5000*math.sin(2*math.pi*440*i/16000))) for i in range(16000)))
    return b.getvalue()

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='Install FFmpeg for audio validation tests')
def test_real_decode_silence_and_invalid_file():
    asyncio.run(validate_audio(sound()))
    with pytest.raises(HTTPException) as e:asyncio.run(validate_audio(sound(True)))
    assert e.value.status_code==422
    with pytest.raises(HTTPException):asyncio.run(validate_audio(b'not audio'))

@pytest.mark.skipif(not shutil.which('ffmpeg'),reason='Install FFmpeg for audio validation tests')
def test_transcription_adapter_and_warning_with_stub_only():
    with TestClient(app) as c:
        p=c.app.state.providers;p.audio_key='synthetic'
        async def stub(*args):return 'saans nahi aa rahi'
        p.transcribe=stub
        r=c.post('/transcribe',files={'file':('sample.wav',sound(),'audio/wav')})
        assert r.status_code==200 and r.json()['emergency_warning'] and r.json()['requires_confirmation']

