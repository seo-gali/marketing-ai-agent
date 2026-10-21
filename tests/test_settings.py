import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from playwright.async_api import BrowserType

from backend import browser, config, db


class SettingsRules(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.patches = [patch.object(config, 'DB_PATH', root / 'settings.db'),
                        patch.object(config, 'PROFILE_ROOT', root / 'profiles'),
                        patch.object(config, 'PROFILE_PATH', root / 'profiles' / 'existing-youtube1')]
        for item in self.patches:
            item.start()
        db.initialize()
        self.video = {'id': 'fixture0001', 'channel_id': next(iter(config.CHANNELS))}
        self.text = '[광고] 상대의 마음이 달라지는 이유가 궁금하다면 운명원 연애 사주도 함께 참고해 보세요.'

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.directory.cleanup()

    def test_profiles_are_persistent_isolated_and_cannot_bypass_video_limit(self):
        original = config.PROFILE_PATH
        for name in ['유튜브2', '../../Default']:
            with self.assertRaises(HTTPException):
                db.reserve_job(self.video, self.text, True, name)
        db.add_profile('유튜브2')
        db.add_profile('유튜브3')
        db.initialize()
        self.assertEqual(db.profiles(), ['유튜브1', '유튜브2', '유튜브3'])
        self.assertEqual(config.profile_path('유튜브1'), original)
        self.assertEqual(len({config.profile_path(name) for name in db.profiles()}), 3)
        with self.assertRaises(HTTPException):
            db.add_profile('유튜브2')
        job = db.reserve_job(self.video, self.text, True, '유튜브2')
        self.assertEqual(job['profile'], '유튜브2')
        with self.assertRaises(HTTPException):
            db.reserve_job(self.video, self.text, True, '유튜브3')

    def test_deleted_history_keeps_quota_duplicate_guard_and_restores(self):
        job = db.reserve_job(self.video, self.text, True)
        with self.assertRaises(HTTPException):
            db.hide_history('jobs', job['id'])
        db.update_job(job['id'], 'success')
        deleted = db.hide_history('jobs', job['id'])
        db.initialize()
        current = db.activities()
        self.assertEqual(current['jobs'], [])
        self.assertEqual(current['total'], 0)
        self.assertEqual(current['quota']['used'], 1)
        self.assertIn(self.video['id'], current['blocked_video_ids'])
        self.assertEqual(db.get_job(job['id'])['status'], 'success')
        with self.assertRaises(HTTPException):
            db.reserve_job(self.video, self.text, True)
        self.assertEqual(db.restore_history(deleted['token'])['count'], 1)
        self.assertEqual(db.activities()['total'], 1)

    def test_independent_pages_and_bulk_undo_leave_new_logs_intact(self):
        for index in range(35):
            db.log('draft_saved', str(index))
        self.assertEqual(db.activities()['total_pages'], 1)
        self.assertFalse(db.activities()['has_more'])
        self.assertEqual(db.activities(kind='logs')['total_pages'], 2)
        self.assertEqual(len(db.activities(offset=30, kind='logs')['logs']), 5)
        deleted = db.hide_history('logs')
        db.log('analysis_complete', 'new')
        self.assertEqual(db.activities(kind='logs')['total'], 1)
        self.assertEqual(db.restore_history(deleted['token'])['count'], 35)
        self.assertEqual(db.activities(kind='logs')['total'], 36)


    async def test_manual_login_uses_only_the_requested_dedicated_folder(self):
        db.add_profile('유튜브2')
        with patch.object(browser, 'context', None), patch.object(Path, 'is_file', return_value=True), patch.object(browser.subprocess, 'Popen') as launch:
            await browser.login_profile('유튜브2')
        arguments = launch.call_args.args[0]
        self.assertIn(f'--user-data-dir={config.profile_path("유튜브2")}', arguments)
        self.assertNotIn(f'--user-data-dir={config.PROFILE_PATH}', arguments)
        self.assertFalse(any('remote-debugging' in value or 'AutomationControlled' in value for value in arguments))

    async def test_chrome_profile_switch_keeps_folders_separate(self):
        db.add_profile('유튜브2')
        original = BrowserType.launch_persistent_context

        async def headless(chromium, *args, **kwargs):
            kwargs['headless'] = True
            return await original(chromium, *args, **kwargs)

        with patch.object(BrowserType, 'launch_persistent_context', headless), patch.object(browser, 'context', None), patch.object(browser, 'page', None), patch.object(browser, 'driver', None), patch.object(browser, 'active_profile', '유튜브1'):
            try:
                first = await browser.ensure_open('유튜브1')
                await browser.context.add_cookies([{'name': 'fixture', 'value': 'one', 'domain': 'example.test', 'path': '/', 'expires': time.time() + 3600}])
                await browser.ensure_open('유튜브2')
                self.assertTrue(first.is_closed())
                self.assertEqual(await browser.context.cookies(), [])
                await browser.context.add_cookies([{'name': 'fixture', 'value': 'two', 'domain': 'example.test', 'path': '/', 'expires': time.time() + 3600}])
                await browser.ensure_open('유튜브1')
                self.assertEqual((await browser.context.cookies())[0]['value'], 'one')
            finally:
                await browser.close_profile()


if __name__ == '__main__':
    unittest.main()
