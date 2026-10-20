import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend.main import get_videos
from backend.security import LocalSecurity


class SecurityBoundary(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.upstream_calls=0

        async def upstream(scope, receive, send):
            self.upstream_calls+=1
            payload=(await receive()).get('body', b'') if scope['method']=='POST' else b''
            await send({'type':'http.response.start','status':200,'headers':[]})
            await send({'type':'http.response.body','body':payload})
        self.app=LocalSecurity(upstream)

    async def request(self,path='/api/videos',method='GET',body=b'',headers=None,peer='127.0.0.1',chunks=None):
        messages=[]
        parts=list(chunks or [body])
        async def receive():
            part=parts.pop(0) if parts else b''
            return {'type':'http.request','body':part,'more_body':bool(parts)}
        async def send(message):
            messages.append(message)
        scope={'type':'http','method':method,'path':path,'client':(peer,12345),
               'headers':[(b'host',b'127.0.0.1:8000')]+list((headers or {}).items())}
        await self.app(scope,receive,send)
        return messages

    async def test_rate_limit_prevents_upstream_calls(self):
        for _ in range(10):
            self.assertEqual((await self.request())[0]['status'],200)
        rejected=await self.request()
        self.assertEqual(rejected[0]['status'],429)
        self.assertEqual(self.upstream_calls,10)
        self.assertIn((b'retry-after',b'60'),rejected[0]['headers'])

    async def test_chunked_body_limit_json_and_replay(self):
        rejected=await self.request('/api/drafts/fixture0001','POST',headers={b'content-type':b'application/json'},chunks=[b'a'*10000,b'b'*10000])
        self.assertEqual(rejected[0]['status'],413)
        self.assertEqual(self.upstream_calls,0)
        wrong=await self.request('/api/drafts/fixture0001','POST',b'{}',{b'content-type':b'text/plain'})
        self.assertEqual(wrong[0]['status'],415)
        valid=await self.request('/api/drafts/fixture0001','POST',b'{}',{b'content-type':b'application/json'})
        self.assertEqual(valid[0]['status'],200)
        self.assertEqual(valid[1]['body'],b'{}')

    async def test_origin_peer_and_security_headers(self):
        self.assertEqual((await self.request(headers={b'origin':b'https://evil.example'}))[0]['status'],403)
        self.assertEqual((await self.request(peer='198.51.100.1'))[0]['status'],403)
        self.assertEqual((await self.request(headers={b'origin':b'\xffevil'}))[0]['status'],403)
        result=await self.request('/')
        headers=dict(result[0]['headers'])
        self.assertEqual(headers[b'x-frame-options'],b'DENY')
        self.assertIn(b"frame-ancestors 'none'",headers[b'content-security-policy'])
        self.assertEqual(headers[b'cache-control'],b'no-store')

    def test_empty_search_does_not_call_youtube(self):
        with patch('backend.services.discover') as discover:
            for value in ['', '   ', '\u3000', '\u200b']:
                with self.assertRaises(HTTPException):
                    get_videos(value)
            discover.assert_not_called()
