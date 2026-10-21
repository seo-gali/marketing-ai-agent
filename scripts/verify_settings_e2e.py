"""격리된 SQLite·실제 FastAPI·Chrome의 설정/이력 검사. 외부 댓글 게시 미실행."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from urllib.error import URLError
from urllib.request import urlopen

from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import config, db

BASE = 'http://127.0.0.1:5173'
ARTIFACTS = ROOT / 'artifacts'


async def verify():
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', 5173)) == 0:
            raise RuntimeError('격리 검사 전 5173 포트의 개발 서버를 종료하세요.')
    ARTIFACTS.mkdir(exist_ok=True)
    result = {'status': 'failed', 'database': 'isolated', 'external_posting': 'not_run', 'checks': []}
    with tempfile.TemporaryDirectory(prefix='settings-e2e-', dir=ROOT / 'local') as directory:
        assert Path(directory).resolve().is_relative_to(ROOT / 'local')
        original_db = config.DB_PATH
        config.DB_PATH = Path(directory) / 'fixture.db'
        db.initialize()
        video = {'id': 'fixture0001', 'title': '검증용 게시 작업 · 외부 게시 없음', 'channel_id': next(iter(config.CHANNELS)),
                 'channel': '검증용', 'published_at': db.now(), 'thumbnail': '', 'description': ''}
        db.save_videos([video])
        text = '[광고] 상대의 마음이 달라지는 이유가 궁금하다면 운명원 연애 사주도 함께 참고해 보세요.'
        job = db.reserve_job(video, text, True)
        db.update_job(job['id'], 'success')
        for index in range(36):
            db.log('draft_saved', f'검증용 활동 {index}', video['id'])
        environment = {**os.environ, 'DATABASE_URL': 'sqlite:///' + config.DB_PATH.as_posix(), 'PYTHONIOENCODING': 'utf-8'}
        log = (ARTIFACTS / 'settings-e2e-server.log').open('w', encoding='utf-8')
        server = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '5173', '--loop', 'asyncio'],
                                  cwd=ROOT, env=environment, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            for _ in range(60):
                try:
                    with urlopen(BASE, timeout=1) as response:
                        if response.status == 200:
                            break
                except (URLError, OSError):
                    await asyncio.sleep(.25)
            else:
                raise RuntimeError('격리 FastAPI 실행 실패')
            async with async_playwright() as driver:
                chrome = await driver.chromium.launch(channel='chrome', headless=True)
                page = await chrome.new_page(viewport={'width': 1440, 'height': 1000})
                posting = []
                page_errors = []
                page.on('request', lambda request: posting.append(request.url) if request.method == 'POST' and request.url.endswith('/api/posting-jobs') else None)
                page.on('pageerror', lambda error: page_errors.append(str(error)))
                try:
                    await page.goto(BASE + '/settings')
                    await expect(page.get_by_role('heading', name='환경 설정', exact=True)).to_be_visible()
                    assert await page.locator('.app-footer a[href="/api/health"]').count() == 0
                    assert await page.locator('a[href="/api/health"]').count() == 0
                    await expect(page.get_by_role('button', name='API 상태 확인', exact=True)).to_be_visible()
                    async with page.expect_response('**/api/health') as refreshed:
                        await page.get_by_role('button', name='API 상태 확인', exact=True).click()
                    assert (await refreshed.value).status == 200
                    await expect(page.locator('.api-connection .status-dot')).to_have_class('status-dot on')
                    await expect(page.locator('.api-connection')).to_contain_text('API 연결됨')
                    await page.route('**/api/health', lambda route: route.fulfill(status=503, json={'detail':'검증용 오류'}))
                    await page.get_by_role('button', name='API 상태 확인', exact=True).click()
                    await expect(page.locator('.api-connection .status-dot')).to_have_class('status-dot off')
                    await expect(page.locator('.api-connection')).to_contain_text('API 연결 실패')
                    await page.unroute('**/api/health')
                    await page.get_by_role('button', name='API 상태 확인', exact=True).click()
                    await expect(page.locator('.api-connection .status-dot')).to_have_class('status-dot on')
                    assert len(chrome.contexts[0].pages) == 1
                    result['checks'].append('api_check_200_green_503_red_retry_without_new_tab')
                    for name in ['유튜브2', '유튜브3']:
                        await page.get_by_role('button', name=name + ' 추가', exact=True).click()
                        await expect(page.get_by_role('radio', name=name, exact=False)).to_be_visible()
                    assert await (await page.request.get(BASE + '/api/profiles')).json() == ['유튜브1', '유튜브2', '유튜브3']
                    await page.get_by_role('radio', name='유튜브1', exact=False).focus()
                    await page.keyboard.press('ArrowDown')
                    await expect(page.get_by_role('radio', name='유튜브2', exact=False)).to_be_checked()
                    await page.get_by_role('button', name='다크', exact=True).click()
                    await expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
                    await page.reload()
                    await expect(page.get_by_role('radio', name='유튜브2', exact=False)).to_be_checked()
                    await expect(page.locator('html')).to_have_attribute('data-theme', 'dark')
                    await page.screenshot(path=ARTIFACTS / 'settings-dark.png', full_page=True)
                    await page.evaluate("localStorage.setItem('marketing-ai:draft:fixture',JSON.stringify({text:'임시 댓글',expiresAt:Date.now()+100000}));localStorage.setItem('marketing-ai:filters','{}')")
                    await page.get_by_role('button', name='임시 초안 삭제', exact=True).click()
                    assert await page.evaluate("localStorage.getItem('marketing-ai:draft:fixture')") is None
                    assert await page.evaluate("localStorage.getItem('marketing-ai:theme')") == 'dark'
                    assert await page.evaluate("localStorage.getItem('marketing-ai:filters')") is not None
                    await page.get_by_role('button', name='라이트', exact=True).click()
                    await page.screenshot(path=ARTIFACTS / 'settings-light.png', full_page=True)
                    result['checks'].append('sidebar_status_refresh_profiles_and_theme_persistence_draft_only_clear')

                    await page.get_by_role('link', name='작업 이력', exact=True).click()
                    await expect(page.locator('.history-row')).to_have_count(1)
                    assert await page.get_by_role('button', name='2페이지', exact=True).count() == 0
                    await page.get_by_role('button', name='검증용 게시 작업 · 외부 게시 없음 게시 이력 삭제', exact=True).click()
                    await expect(page.get_by_text('표시할 게시 작업이 없습니다.', exact=True)).to_be_visible()
                    current = await (await page.request.get(BASE + '/api/activities')).json()
                    assert current['quota']['used'] == 1 and video['id'] in current['blocked_video_ids']
                    assert (await page.request.get(BASE + '/api/posting-jobs/' + job['id'])).ok
                    await expect(page.locator('#global-message')).to_be_focused()
                    await page.keyboard.press('Tab')
                    await expect(page.get_by_role('button', name='실행 취소', exact=True)).to_be_focused()
                    await page.keyboard.press('Enter')
                    await expect(page.locator('.history-row')).to_have_count(1)
                    await page.screenshot(path=ARTIFACTS / 'history-posting.png', full_page=True)
                    await page.get_by_role('button', name='활동 기록', exact=True).click()
                    await page.get_by_role('button', name='2페이지', exact=True).click()
                    await expect(page.get_by_role('button', name='2페이지', exact=True)).to_have_attribute('aria-current', 'page')
                    assert await page.get_by_text('표시할 게시 작업이 없습니다.', exact=True).count() == 0
                    await page.get_by_role('button', name='활동 기록 비우기', exact=True).click()
                    await expect(page.get_by_text('표시할 활동 기록이 없습니다.', exact=True)).to_be_visible()
                    assert await page.get_by_role('button', name='2페이지', exact=True).count() == 0
                    await page.get_by_role('button', name='실행 취소', exact=True).click()
                    await expect(page.locator('.history-row')).to_have_count(30)
                    await page.screenshot(path=ARTIFACTS / 'history-activities.png', full_page=True)
                    result['checks'].append('separate_pages_delete_undo_and_posting_guards_unchanged')

                    failures = [True]

                    async def fail_once(route):
                        if failures[0]:
                            failures[0] = False
                            await route.fulfill(status=503, json={'detail': '검증용 일시적 연결 오류'})
                        else:
                            await route.continue_()

                    await page.route('**/api/activities?kind=*', fail_once)
                    await page.reload()
                    await expect(page.get_by_role('alert')).to_contain_text('검증용 일시적 연결 오류')
                    await page.get_by_role('button', name='다시 불러오기', exact=True).click()
                    await expect(page.locator('.history-row')).to_have_count(1)
                    result['checks'].append('history_connection_error_and_retry')
                    for width in [1440, 390]:
                        await page.set_viewport_size({'width': width, 'height': 1000})
                        for route in ['/activities', '/settings']:
                            await page.goto(BASE + route)
                            await page.get_by_role('heading', level=1).wait_for()
                            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                            assert await page.locator('.app-footer').evaluate('element=>{const link=element.querySelector("a");return Math.abs(element.getBoundingClientRect().right-parseFloat(getComputedStyle(element).paddingRight)-link.getBoundingClientRect().right)<1}')
                    await page.get_by_role('button', name='메뉴 열기', exact=True).click()
                    await expect(page.get_by_role('button', name='연결 상태 새로고침', exact=True)).to_be_visible()
                    await page.screenshot(path=ARTIFACTS / 'settings-mobile.png', full_page=True)
                    assert not posting and not page_errors, (posting, page_errors)
                    result['checks'].append('desktop_mobile_menu_and_zero_external_posts_or_page_errors')
                    result['status'] = 'passed'
                except Exception as error:
                    result['error'] = (str(error) or type(error).__name__)[:1500]
                    await page.screenshot(path=ARTIFACTS / 'settings-e2e-failure.png', full_page=True)
                    raise
                finally:
                    await chrome.close()
        finally:
            server.terminate()
            server.wait(timeout=15)
            log.close()
            config.DB_PATH = original_db
            (ARTIFACTS / 'settings-e2e-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(verify())
