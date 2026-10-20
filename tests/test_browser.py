"""로컬 HTML 픽스처 검증. 실제 YouTube 게시 성공을 의미하지 않음."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from playwright.async_api import async_playwright

from backend import browser, config, db

TEXT = '[광고] 제목의 시간여행자처럼 다양한 이야기가 궁금하다면 운명원의 연애 사주 콘텐츠도 참고해 보세요.'


class BrowserWorkflow(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.path_patch = patch.object(config, 'DB_PATH', root / 'fixture.db')
        self.path_patch.start()
        self.screenshot_patch = patch.object(browser, 'SCREENSHOTS', root / 'captures')
        self.screenshot_patch.start()
        db.initialize()
        self.driver = await async_playwright().start()
        self.chromium = await self.driver.chromium.launch(channel='chrome', headless=True)
        self.context = await self.chromium.new_context()
        self.page = await self.context.new_page()
        self.page.set_default_timeout(10000)
        self.globals = [patch.object(browser, 'page', self.page), patch.object(browser, 'context', self.context)]
        for item in self.globals:
            item.start()
        self.submissions = []
        self.persist = True
        self.logged_in = True
        await self.page.route('https://www.youtube.com/**', self.route)

    async def asyncTearDown(self):
        await self.chromium.close()
        await self.driver.stop()
        for item in self.globals:
            item.stop()
        self.screenshot_patch.stop()
        self.path_patch.stop()
        self.directory.cleanup()

    async def route(self, route):
        if '/__fixture_post' in route.request.url:
            self.submissions.append(route.request.post_data_json)
            await route.fulfill(json={'ok': True})
            return
        posted = bool(self.submissions) and self.persist
        html = '''<!doctype html><html lang="ko"><head><meta charset="UTF-8"></head><body><ytd-masthead>HEADER</ytd-masthead>
<ytd-active-account-header-renderer hidden><div id="channel-handle">@fixture-handle</div></ytd-active-account-header-renderer>
<div id="comments"><ytd-comment-simplebox-renderer>
<div id="simplebox-placeholder" role="textbox">댓글 추가</div>
<div id="contenteditable-root" contenteditable="true" hidden></div>
<div id="submit-button"><button disabled>댓글</button></div>
</ytd-comment-simplebox-renderer><div id="threads"></div></div>
<script>
const text = TEXT;
const editor = document.querySelector('[contenteditable]');
const submit = document.querySelector('#submit-button button');
let events = 0;
document.querySelector('#simplebox-placeholder').onclick = () => { editor.hidden = false; editor.focus(); };
editor.oninput = () => {events++; submit.disabled = false;};
document.addEventListener('keydown', event => {if(event.key === 'Escape') document.querySelector('ytd-active-account-header-renderer').hidden = true;});
function showComment() {
const row = document.createElement('ytd-comment-thread-renderer');
const author = document.createElement('a'); author.id = 'author-text'; author.href = '/@fixture-handle'; author.textContent = 'fixture-handle';
const body = document.createElement('span'); body.id = 'content-text'; body.textContent = text;
const link = document.createElement('a'); link.href = '/watch?v=fixture0001&lc=fixtureComment'; link.textContent = '방금 전';
row.append(author, body, link); document.querySelector('#threads').append(row);
}
submit.onclick = async () => {await fetch('/__fixture_post',{method:'POST',body:JSON.stringify({text:editor.innerText,events}),headers:{'Content-Type':'application/json'}}); showComment();};
if (POSTED) showComment();
</script></body></html>'''.replace('TEXT', json.dumps(TEXT)).replace('POSTED', 'true' if posted else 'false')
        header = '<button id="avatar-btn" onclick="document.querySelector(\'ytd-active-account-header-renderer\').hidden=false">계정</button>' if self.logged_in else '<a href="/ServiceLogin">로그인</a>'
        await route.fulfill(content_type='text/html', body=html.replace('HEADER', header))

    def job(self):
        return db.reserve_job({'id': 'fixture0001', 'channel_id': next(iter(config.CHANNELS))}, TEXT, True)

    async def test_sequential_input_and_verified_reload(self):
        job = self.job()
        await browser.run_job(job)
        actual = db.get_job(job['id'])
        self.assertEqual(actual['status'], 'success', str(db.activities()['logs']) + '\n' + await self.page.locator('body').aria_snapshot())
        self.assertEqual(len(self.submissions), 1)
        self.assertEqual(self.submissions[0]['text'], TEXT)
        self.assertGreaterEqual(self.submissions[0]['events'], len(TEXT))
        self.assertIn('lc=fixtureComment', actual['comment_url'])

    async def test_uncertain_blocks_second_submission(self):
        self.persist = False
        job = self.job()
        await browser.run_job(job)
        self.assertEqual(db.get_job(job['id'])['status'], 'uncertain')
        with self.assertRaises(HTTPException):
            self.job()
        self.assertEqual(len(self.submissions), 1)

    async def test_login_required_stops_before_typing(self):
        self.logged_in = False
        job = self.job()
        await browser.run_job(job)
        actual = db.get_job(job['id'])
        self.assertEqual(actual['status'], 'failed')
        self.assertIn('로그인', actual['error'])
        self.assertEqual(self.submissions, [])
        self.assertTrue((browser.SCREENSHOTS / actual['screenshot']).is_file())
