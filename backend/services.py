import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode, urlparse, parse_qs
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


def youtube(resource, **params):
    if not config.YOUTUBE_KEY:
        raise HTTPException(503, 'YouTube API 키가 없습니다. .env의 YOUTUBE_API_KEY를 설정하세요.')
    return request_json('https://www.googleapis.com/youtube/v3/' + resource + '?' + urlencode(params),
                        headers={'X-Goog-Api-Key': config.YOUTUBE_KEY})


def video_id(value):
    value = value.strip()
    if re.fullmatch(r'[A-Za-z0-9_-]{11}', value):
        return value
    url = urlparse(value)
    if url.scheme == 'https' and url.hostname in {'www.youtube.com', 'youtube.com', 'm.youtube.com', 'youtu.be'}:
        if url.hostname == 'youtu.be':
            candidate = url.path.strip('/')
        elif url.path == '/watch':
            candidate = parse_qs(url.query).get('v', [''])[0]
        elif url.path.startswith(('/shorts/', '/live/')):
            candidate = url.path.split('/')[2]
        else:
            candidate = ''
        if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate):
            return candidate
    raise HTTPException(422, '올바른 HTTPS YouTube 영상 URL 또는 11자리 ID를 입력하세요.')


def normalize_video(item):
    snippet = item['snippet']
    thumbnails = snippet.get('thumbnails', {})
    return {'id': item['id'], 'channel_id': snippet['channelId'], 'title': snippet['title'],
            'channel': snippet['channelTitle'], 'published_at': snippet['publishedAt'],
            'thumbnail': thumbnails.get('medium', thumbnails.get('default', {})).get('url', ''),
            'description': snippet.get('description', '')}


def fetch_video(value):
    items = youtube('videos', part='snippet', id=video_id(value)).get('items', [])
    if not items:
        raise HTTPException(404, '접근 가능한 영상을 찾을 수 없습니다.')
    return normalize_video(items[0])


def allowed(video):
    return video['channel_id'] in config.CHANNELS or video['id'] in config.TEST_IDS


def discover():
    channels = youtube('channels', part='contentDetails', id=','.join(config.CHANNELS)).get('items', [])
    warnings = [f'{name}: 채널을 찾을 수 없습니다.' for key, name in config.CHANNELS.items()
                if key not in {item['id'] for item in channels}]

    def uploads(channel):
        try:
            result = youtube('playlistItems', part='contentDetails', maxResults=8,
                             playlistId=channel['contentDetails']['relatedPlaylists']['uploads'])
            return [item['contentDetails']['videoId'] for item in result.get('items', [])], None
        except HTTPException as error:
            return [], f"{config.CHANNELS[channel['id']]}: {error.detail}"

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(uploads, channels))
    ids = [item for items, _ in results for item in items]
    warnings.extend(warning for _, warning in results if warning)
    videos = [normalize_video(item) for item in youtube('videos', part='snippet', id=','.join(ids)).get('items', [])] if ids else []
    return sorted(videos, key=lambda video: video['published_at'], reverse=True), warnings
