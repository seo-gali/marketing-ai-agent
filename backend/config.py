import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env', encoding='utf-8-sig')


def local_path(value: str) -> Path:
    return (ROOT / value).resolve()


YOUTUBE_KEY = os.getenv('YOUTUBE_API_KEY', '')
OLLAMA_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434').rstrip('/')
ollama_address = urlparse(OLLAMA_URL)
if ollama_address.hostname not in {'localhost', '127.0.0.1', '::1'} or ollama_address.scheme not in {'http', 'https'} or ollama_address.username or ollama_address.password or ollama_address.query or ollama_address.fragment:
    raise ValueError('OLLAMA_BASE_URL must use a local host')
MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5-coder:7b')
if not MODEL.strip():
    raise ValueError('OLLAMA_MODEL must not be empty')
database_url = os.getenv('DATABASE_URL', 'sqlite:///./data/marketing-agent.db')
if not database_url.startswith('sqlite:///'):
    raise ValueError('Only SQLite is supported')
DB_PATH = local_path(database_url.removeprefix('sqlite:///'))
PROFILE_PATH = local_path(os.getenv('CHROME_USER_DATA_DIR', './local/chrome-profiles/youtube1'))
PROFILE_ROOT = ROOT / 'local' / 'chrome-profiles'
if not PROFILE_PATH.is_relative_to(PROFILE_ROOT.resolve()):
    raise ValueError('Chrome profile must be inside local/chrome-profiles')
DAILY_MAX = min(10, max(1, int(os.getenv('DAILY_MAX_COMMENTS', '10'))))
MIN_CHARS = max(40, int(os.getenv('COMMENT_MIN_CHARS', '40')))
MAX_CHARS = min(120, int(os.getenv('COMMENT_MAX_CHARS', '120')))
if MIN_CHARS > MAX_CHARS:
    raise ValueError('Invalid comment length limits')
TEST_IDS = frozenset(filter(None, (v.strip() for v in os.getenv('TEST_VIDEO_IDS', '').split(','))))
CHANNELS = {
    'UCxlc0Ky0aWoD8uI09ad44Tg': '외롭여',
    'UC-ee_ziASM251TMXe3P3VZA': '리즈시절 LizTV',
    'UC09L3JxGVcn7SKLa-pjTEmw': '러브커넥트 유지연',
    'UCVdtDW-HF4KluixGaBAcI4w': '연애데이터 노노',
    'UCkGl2jieOVhGiHPdXF77Yyw': '심리조각',
}
