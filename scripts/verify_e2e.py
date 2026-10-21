"""실제 로컬 앱·YouTube API E2E. 외부 댓글 게시를 실행하지 않음."""
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'
BASE = os.environ.get('APP_URL', 'http://127.0.0.1:8000')


async def main():
    ARTIFACTS.mkdir(exist_ok=True)
    result = {'time': datetime.now().astimezone().isoformat(), 'base_url': BASE, 'external_posting': 'not_run', 'checks': []}
    async with async_playwright() as driver:
        chromium = await driver.chromium.launch(channel='chrome', headless=True)
        page = await chromium.new_page(viewport={'width': 1440, 'height': 1000})
        console_errors = []
        page.on('pageerror', lambda error: console_errors.append(str(error)))
        try:
            await page.goto(BASE)
            await page.evaluate("localStorage.setItem('marketing-ai:draft:expired-test',JSON.stringify({text:'expired',expiresAt:0}))")
            await page.reload()
            assert await page.evaluate("localStorage.getItem('marketing-ai:draft:expired-test')") is None
            await page.get_by_role('button', name='외롭여', exact=True).wait_for()
            await page.get_by_role('button', name='① 영상 불러오기').click()
            await page.locator('.video-item').first.wait_for(timeout=45000)
            videos = await page.locator('.video-item').count()
            assert videos > 0
            channels = {text.split(' · ')[0] for text in await page.locator('.video-info > span').all_text_contents()}
            assert len(channels) == 5, channels
            result['checks'].append({'live_youtube_list': videos, 'channels': len(channels)})
            await page.get_by_role('button', name='외롭여', exact=True).click()
            filtered = await page.locator('.video-item').count()
            assert 0 < filtered < videos
            await page.get_by_role('searchbox', name='영상 검색').fill('no-result-e2e-xyz')
            await page.get_by_text('조건에 맞는 영상이 없습니다.').wait_for()
            await page.get_by_role('searchbox', name='영상 검색').fill('')
            assert await page.locator('.video-item').count()==0
            await page.get_by_text('검색어를 입력하세요. 빈 검색어로 전체 목록을 조회하지 않습니다.').wait_for()
            for query in ['']:
                rejected=await page.request.get(BASE+'/api/videos',params={'q':query})
                assert rejected.status==422
            await page.get_by_role('button', name='전체 목록 보기', exact=True).click()
            assert await page.locator('.video-item').count()==videos
            await page.get_by_role('button',name='실행 취소',exact=True).click()
            assert await page.locator('.video-item').count()==0
            await page.get_by_role('button',name='전체 목록 보기',exact=True).click()
            result['checks'].append({'filter_and_empty_search': 'passed', 'empty_query_api':422})
            await page.get_by_text('더보기 · 영상 URL로 선택',exact=True).click()
            await page.get_by_role('textbox', name='YouTube 영상 링크').fill('https://youtu.be/akn-AvCeHBI')
            await page.get_by_role('button', name='링크 확인').click()
            await expect(page.locator('#draft')).not_to_have_value('',timeout=240000)
            assert await page.get_by_role('button',name='실행 취소',exact=True).count()==0
            draft = await page.locator('#draft').input_value()
            assert 40 <= len(draft) <= 120 and draft.startswith('[광고]') and '운명원' in draft
            await expect(page.locator('#analysis-title')).to_have_text('남자의 연애 작동원리')
            button = page.get_by_role('button', name='③ 댓글 달기', exact=True)
            assert await button.is_disabled()
            approval = page.get_by_role('checkbox', name='현재 본문을 확인했으며 광고 댓글 게시를 승인합니다.')
            await approval.check()
            assert await button.is_enabled()
            await page.locator('#draft').fill(draft + ' ')
            assert not await approval.is_checked()
            assert await button.is_disabled()
            await page.locator('#draft').fill('[광고] 운명원')
            await approval.check()
            assert await button.is_disabled()
            await page.locator('#draft').fill(draft)
            await page.get_by_role('button', name='수정 저장').click()
            await page.wait_for_timeout(300)
            result['checks'].append({'draft_edit_and_approval_reset': 'passed', 'draft_length': len(draft)})
            edited=draft.replace('운명원','운명원의')
            await page.locator('#draft').fill(edited)
            await expect(page.get_by_text('이 브라우저에 임시 저장됨 · 7일 보관',exact=True)).to_be_visible()
            assert await page.evaluate("JSON.parse(localStorage.getItem('marketing-ai:draft:akn-AvCeHBI')).text")==edited
            await page.reload()
            await page.get_by_text('더보기 · 영상 URL로 선택',exact=True).click()
            await page.get_by_role('textbox',name='YouTube 영상 링크').fill('https://youtu.be/akn-AvCeHBI')
            await page.get_by_role('button',name='링크 확인',exact=True).click()
            await expect(page.locator('#draft')).to_have_value(edited)
            assert not await page.get_by_role('checkbox').is_checked()
            await page.locator('#draft').fill(draft)
            await page.get_by_role('button',name='수정 저장').click()
            result['checks'].append({'local_draft_recovery_without_approval':'passed'})
            rejected = await page.request.post(BASE + '/api/posting-jobs', data={
                'video_id': 'akn-AvCeHBI', 'text': draft, 'approved': False})
            assert rejected.status == 422
            forbidden = await page.request.post(BASE + '/api/posting-jobs', data={
                'video_id': 'jNQXAC9IVRw', 'text': draft, 'approved': True})
            assert forbidden.status == 403
            invalid = await page.request.post(BASE + '/api/videos/resolve', data={'url': 'https://evil.example/watch?v=akn-AvCeHBI'})
            assert invalid.status == 422
            origin = await page.request.post(BASE + '/api/posting-jobs', headers={'Origin': 'https://evil.example'}, data={
                'video_id': 'akn-AvCeHBI', 'text': draft, 'approved': True})
            assert origin.status == 403
            result['checks'].append({'approval_required': 422, 'channel_denied': 403, 'invalid_url': 422, 'origin_denied': 403})
            for width in [1440, 1024, 390]:
                await page.set_viewport_size({'width': width, 'height': 1000})
                await page.evaluate("document.querySelector('.detail-scroll').scrollTop = 0")
                await page.evaluate('window.scrollTo(0,0)')
                await page.screenshot(path=ARTIFACTS / f'dashboard-{width}.png', full_page=True)
                scroll, client = await page.evaluate('[document.documentElement.scrollWidth, document.documentElement.clientWidth]')
                assert scroll <= client, f'가로 넘침: {width}, {scroll}>{client}'
            assert not console_errors, console_errors
            result['checks'].append({'responsive_1440_1024_390': 'passed', 'javascript_errors': 0})
            for route in ['/activities','/settings','/page-that-does-not-exist']:
                response=await page.goto(BASE+route)
                assert response.status==(404 if route.endswith('exist') else 200)
                await page.get_by_role('heading',level=1).wait_for()
                scroll,client=await page.evaluate('[document.documentElement.scrollWidth,document.documentElement.clientWidth]')
                assert scroll<=client
                assert await page.locator('input[placeholder],textarea[placeholder]').count()==0
            await page.get_by_role('link',name='영상 탐색으로 이동',exact=True).click()
            await page.get_by_role('heading',name='영상 탐색',exact=False).wait_for()
            for route in ['/','/activities','/settings','/api/health','/favicon.svg']:
                assert (await page.request.get(BASE+route)).status==200
            assert await page.locator('meta[name=description]').get_attribute('content')
            assert str(datetime.now().year) in await page.locator('.app-footer').inner_text()
            result['checks'].append({'all_mobile_pages_404_metadata_favicon_footer_links':'passed'})
            result['status'] = 'passed'
        except Exception as error:
            result['status'] = 'failed'
            result['error'] = (str(error) or type(error).__name__)[:1000]
            await page.screenshot(path=ARTIFACTS / 'e2e-failure.png', full_page=True)
            raise
        finally:
            (ARTIFACTS / 'e2e-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(result, ensure_ascii=False, indent=2))
            await chromium.close()


if __name__ == '__main__':
    asyncio.run(main())
