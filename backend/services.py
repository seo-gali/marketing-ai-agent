import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException

from . import config


def request_json(url: str, payload=None, timeout=20, headers=None):
    request = Request(url, data=None if payload is None else json.dumps(payload).encode(),
                      headers=headers or ({'Content-Type': 'application/json'} if payload is not None else {}))
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as error:
        reason = 'upstream_error'
        try:
            detail = json.loads(error.read())
            reason = detail.get('error', {}).get('errors', [{}])[0].get('reason', reason)
        except (ValueError, AttributeError, IndexError):
            pass
        raise HTTPException(502, f'외부 API 응답 오류 ({error.code}, {reason})') from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise HTTPException(503, '외부 서비스 연결 실패 또는 응답 시간 초과') from None


def health():
    try:
        tags = request_json(config.OLLAMA_URL + '/api/tags', timeout=5)
        models = [item['name'] for item in tags.get('models', [])]
        ollama = 'ready' if config.MODEL in models else 'model_missing'
    except HTTPException:
        ollama = 'unavailable'
    return {'status': 'ok', 'ollama': ollama, 'model': config.MODEL,
            'youtube': 'configured' if config.YOUTUBE_KEY else 'missing_key',
            'daily_max': config.DAILY_MAX, 'min_chars': config.MIN_CHARS,
            'max_chars': config.MAX_CHARS, 'channels': config.CHANNELS,
            'test_video_ids': sorted(config.TEST_IDS)}
