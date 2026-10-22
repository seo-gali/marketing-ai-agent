import asyncio
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from backend import config, db, main, services
from backend.cancellation import Cancellation, AnalysisCancelled


class CancellationRules(unittest.IsolatedAsyncioTestCase):
    async def test_request_cancellation_disconnects_the_upstream(self):
        ready = threading.Event()
        disconnected = threading.Event()
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200)
                self.send_header('Content-Length', '1000')
                self.end_headers()
                self.wfile.flush()
                ready.set()
                self.connection.settimeout(3)
                if self.connection.recv(1) == b'':
                    disconnected.set()
            def log_message(self, *_):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        control = Cancellation()
        task = asyncio.create_task(asyncio.to_thread(services.request_json, f'http://127.0.0.1:{server.server_port}/api/chat', {'model':'fixture'}, cancellation=control))
        try:
            self.assertTrue(await asyncio.to_thread(ready.wait, 3))
            self.assertTrue(control.cancel())
            with self.assertRaises(AnalysisCancelled):
                await asyncio.wait_for(task, 2)
            self.assertTrue(await asyncio.to_thread(disconnected.wait, 1))
            with self.assertRaises(AnalysisCancelled):
                control.commit(lambda: self.fail('Cancelled result must not be saved'))
            completed = Cancellation()
            self.assertEqual(completed.commit(lambda: 'saved'), 'saved')
            self.assertFalse(completed.cancel())
        finally:
            server.shutdown()
            server.server_close()

    async def test_cancel_endpoint_stops_collection_and_keeps_previous_draft(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(config, 'DB_PATH', Path(directory)/'fixture.db'):
            db.initialize()
            video = {'id':'fixture0001','title':'연애 고민','description':'','channel_id':next(iter(config.CHANNELS)),'channel':'fixture','thumbnail':'','published_at':db.now()}
            db.save_videos([video])
            previous={'concern':'기존 고민','comment':'기존 초안','scene_verified':True}
            db.save_analysis(video['id'], previous)
            before=db.get_analysis(video['id'])
            collecting=asyncio.Event()
            stopped=asyncio.Event()
            async def collect(*args, **kwargs):
                collecting.set()
                try:
                    await asyncio.sleep(60)
                finally:
                    stopped.set()
            with patch.object(services,'fetch_video',return_value=video), patch.object(main.browser,'collect_video_evidence',side_effect=collect), patch.object(main.analysis,'generate') as model:
                task=asyncio.create_task(main.analyze_video(video['id']))
                await asyncio.wait_for(collecting.wait(), 2)
                response=await asyncio.wait_for(main.cancel_analysis(video['id']), 2)
                self.assertEqual(response['status'], 'cancelled')
                with self.assertRaises(HTTPException) as raised:
                    await task
                self.assertEqual(raised.exception.status_code, 409)
                self.assertTrue(stopped.is_set())
                self.assertFalse(main.active_analyses)
                model.assert_not_called()
            self.assertEqual(db.get_analysis(video['id']), before)

    async def test_channel_query_is_scoped_and_rejects_unknown_channels(self):
        channel = next(iter(config.CHANNELS))
        with patch.object(services,'discover',return_value=([],[])) as discover, patch.object(db,'save_videos'):
            result = main.get_videos(q=None, channel=channel)
            discover.assert_called_once_with(channel)
            self.assertEqual(result['loaded_channels'], [channel])
        with patch.object(services,'discover') as discover, self.assertRaises(HTTPException):
            main.get_videos(q=None, channel='unknown')
        discover.assert_not_called()


if __name__ == '__main__':
    unittest.main()
