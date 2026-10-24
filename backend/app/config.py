import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data'
MODE = os.getenv('TEXT_MODE','auto')  # auto, rules, live
REFERENCE_TIME = os.getenv('REFERENCE_TIME','2026-10-24T08:00:00+05:30')
MAX_AUDIO_BYTES = 10 * 1024 * 1024
POLICY_VERSION = 'carecompass-demo-0.1'

