import time
from collections import defaultdict, deque

from starlette.responses import JSONResponse


class LocalSecurity:
    def __init__(self, app):
        self.app = app
        self.requests = defaultdict(deque)

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = {key.decode('latin-1').lower(): value.decode('latin-1') for key, value in scope['headers']}
        host = headers.get('host', '').split(':')[0]
        origin = headers.get('origin')
        peer = (scope.get('client') or ('',))[0]
        path, method = scope['path'], scope['method']

        async def secured_send(message):
            if message['type'] == 'http.response.start':
                extra = [(b'x-frame-options', b'DENY'), (b'x-content-type-options', b'nosniff'),
                         (b'referrer-policy', b'no-referrer'), (b'cache-control', b'no-store'),
                         (b'permissions-policy', b'camera=(), microphone=(), geolocation=()')]
                policy = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' https://i.ytimg.com https://yt3.ggpht.com data:; connect-src 'self'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; object-src 'none'"
                if path in {'/docs', '/redoc'}:
                    policy = policy.replace("script-src 'self'", "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net").replace("style-src 'self'", "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net")
                extra.append((b'content-security-policy', policy.encode()))
                replaced = {key for key, _ in extra}
                message['headers'] = [(key, value) for key, value in message.get('headers', []) if key.lower() not in replaced] + extra
            await send(message)

        async def reject(code, detail, retry=False):
            response = JSONResponse({'detail': detail}, status_code=code, headers={'Retry-After': '60'} if retry else None)
            await response(scope, receive, secured_send)

        if peer not in {'127.0.0.1', '::1', 'testclient'} or host not in {'127.0.0.1', 'localhost', 'testserver'}:
            return await reject(403, '로컬 접근만 허용됩니다.')
        if headers.get('sec-fetch-site') == 'cross-site' or (origin and origin not in {
            'http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:8000', 'http://localhost:8000'}):
            return await reject(403, '허용되지 않은 요청 출처입니다.')
        if path.startswith('/api/'):
            category, maximum = 'read', 180
            if path == '/api/videos' or path == '/api/videos/resolve':
                category, maximum = 'discovery', 10
            elif method == 'POST' and path.endswith('/analyze'):
                category, maximum = 'analysis', 4
            elif method == 'POST' and path == '/api/posting-jobs':
                category, maximum = 'posting', 10
            elif method not in {'GET', 'HEAD'}:
                category, maximum = 'write', 30
            bucket = self.requests[(peer, category)]
            current = time.monotonic()
            while bucket and current - bucket[0] >= 60:
                bucket.popleft()
            if len(bucket) >= maximum:
                return await reject(429, '요청이 많습니다. 1분 후 다시 시도하세요.', retry=True)
            bucket.append(current)
            if method not in {'GET', 'HEAD'}:
                body = bytearray()
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    chunk = message.get('body', b'')
                    if len(body) + len(chunk) > 16384:
                        return await reject(413, '요청 본문은 16KB 이하여야 합니다.')
                    body.extend(chunk)
                    if not message.get('more_body', False):
                        break
                if body and headers.get('content-type', '').split(';')[0].strip().lower() != 'application/json':
                    return await reject(415, 'JSON 요청만 허용됩니다.')
                consumed = False

                async def replay():
                    nonlocal consumed
                    if not consumed:
                        consumed = True
                        return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                    return await receive()

                return await self.app(scope, replay, secured_send)
        return await self.app(scope, receive, secured_send)
