"""실제 로컬 앱·YouTube API E2E. 외부 댓글 게시를 실행하지 않음."""
import asyncio
import json
import os
import re
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
            channel_ids=list((await (await page.request.get(BASE+'/api/health')).json())['channels'])
            fixture={'id':'fixture0001','channel_id':channel_ids[0],'channel':'외롭여','title':'분리된 채널 조회 검사','description':'','thumbnail':'','published_at':'2026-10-23','allowed':True}
            async def partial_list(route):
                selected=channel_ids[1] if '?channel=' in route.request.url else channel_ids[0]
                await route.fulfill(json={'videos':[{**fixture,'channel_id':selected}], 'warnings':[], 'loaded_channels':[selected]})
            await page.route('**/api/videos?**',partial_list)
            await page.route('**/api/videos',partial_list)
            await page.get_by_role('button',name='영상 불러오기',exact=True).click()
            await expect(page.locator('.video-item')).to_have_count(1)
            await page.get_by_role('searchbox',name='영상 검색').fill('없는 검색어')
            await page.get_by_role('button',name='리즈시절 LizTV',exact=True).click()
            await expect(page.get_by_role('searchbox',name='영상 검색')).to_have_value('')
            await expect(page.get_by_role('button',name='영상 불러오기',exact=True)).to_be_visible()
            async with page.expect_request(lambda request:'?channel=' in request.url):
                await page.get_by_role('button',name='영상 불러오기',exact=True).click()
            await expect(page.locator('.video-item')).to_have_count(1)
            await page.get_by_role('button',name='전체 채널',exact=True).click()
            await expect(page.locator('.video-item')).to_have_count(2)
            await page.unroute('**/api/videos?**',partial_list)
            await page.unroute('**/api/videos',partial_list)
            await page.evaluate("localStorage.removeItem('marketing-ai:filters')")
            await page.reload()
            result['checks'].append({'missing_channel_load_button_scoped_request_search_reset_and_merge':'passed'})
            await page.get_by_role('button', name='영상 불러오기', exact=True).click()
            await page.locator('.video-item').first.wait_for(timeout=45000)
            videos = await page.locator('.video-item').count()
            assert videos > 0
            channels = {text.split(' · ')[0] for text in await page.locator('.video-info > span').all_text_contents()}
            assert len(channels) == 5, channels
            result['checks'].append({'live_youtube_list': videos, 'channels': len(channels)})
            search_top=await page.locator('.search-form').evaluate('element=>element.getBoundingClientRect().top')
            listing=page.get_by_role('region',name='영상 목록',exact=True)
            await listing.focus()
            await page.keyboard.press('PageDown')
            async with asyncio.timeout(5):
                while await listing.evaluate('element=>element.scrollTop')==0:
                    await asyncio.sleep(.05)
            assert await page.locator('.main-panel').evaluate('element=>element.scrollTop===0&&element.scrollHeight<=element.clientHeight+1')
            assert await page.locator('.search-form').evaluate('element=>element.getBoundingClientRect().top')==search_top
            await page.screenshot(path=ARTIFACTS/'video-list-scroll.png',full_page=True)
            await listing.evaluate('element=>element.scrollTop=0')
            result['checks'].append({'video_list_keyboard_scroll_with_fixed_controls':'passed'})
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
            await page.get_by_role('button', name='전체 채널', exact=True).click()
            assert await page.locator('.video-item').count()==videos
            await page.get_by_role('button',name='실행 취소',exact=True).click()
            assert await page.locator('.video-item').count()==0
            await page.get_by_role('button',name='전체 채널',exact=True).click()
            result['checks'].append({'filter_and_empty_search': 'passed', 'empty_query_api':422})
            await page.get_by_role('button',name='채널 추가',exact=True).click()
            await page.get_by_role('textbox', name='YouTube 영상 링크').fill('https://youtu.be/FBGY7JIM-84')
            await page.get_by_role('button', name='링크 확인').click()
            await expect(page.locator('#draft')).not_to_have_value('',timeout=240000)
            assert await page.get_by_role('button',name='실행 취소',exact=True).count()==0
            draft = await page.locator('#draft').input_value()
            assert 40 <= len(draft) <= 120 and '운명원' in draft
            await expect(page.locator('#analysis-title')).to_have_text('회피형 후폭풍, 왜 늦을까? 그리워도 쉽게 돌아오지 못하는 이유 #러브커넥트 #연애심리치유 #유지연')
            await expect(page.locator('.video-item')).to_have_count(1)
            await page.get_by_role('button', name='전체 채널', exact=True).click()
            await expect(page.locator('.video-item')).to_have_count(videos)
            assert await page.locator('#video-url').count() == 0
            await page.get_by_role('button', name='채널 추가', exact=True).click()
            await expect(page.locator('#video-url')).to_be_visible()
            await expect(page.locator('.video-item')).to_have_count(1)
            result['checks'].append({'url_tab_and_results_isolated_from_channel_list':'passed'})
            button = page.get_by_role('button', name='댓글 달기', exact=True)
            assert await button.is_disabled()
            approval = page.get_by_role('checkbox', name='이 댓글의 게시를 승인합니다.')
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
            async with asyncio.timeout(5):
                while await page.evaluate("JSON.parse(localStorage.getItem('marketing-ai:draft:FBGY7JIM-84'))?.text") != edited:
                    await asyncio.sleep(.05)
            assert await page.evaluate("JSON.parse(localStorage.getItem('marketing-ai:draft:FBGY7JIM-84')).text")==edited
            await page.reload()
            await page.get_by_role('button',name='채널 추가',exact=True).click()
            await page.get_by_role('textbox',name='YouTube 영상 링크').fill('https://youtu.be/FBGY7JIM-84')
            await page.get_by_role('button',name='링크 확인',exact=True).click()
            await expect(page.locator('#draft')).to_have_value(edited)
            assert not await page.get_by_role('checkbox').is_checked()
            await page.locator('#draft').fill(draft)
            await page.get_by_role('button',name='수정 저장').click()
            result['checks'].append({'local_draft_recovery_without_approval':'passed'})
            detail=await (await page.request.get(BASE+'/api/videos/FBGY7JIM-84')).json()
            old={**detail,'analysis':{**detail['analysis'],'draft_version':0,'comment':edited,'generated_comment':draft}}
            async def old_manual_draft(route):
                await route.fulfill(json=old)
            async def fresh_generated_draft(route):
                await route.fulfill(json={**detail['analysis'],'comment':draft,'draft_version':10})
            await page.route('**/api/videos/FBGY7JIM-84',old_manual_draft)
            await page.route('**/api/videos/FBGY7JIM-84/analyze',fresh_generated_draft)
            await page.evaluate("localStorage.removeItem('marketing-ai:draft:FBGY7JIM-84')")
            await page.get_by_role('textbox',name='YouTube 영상 링크').fill('https://youtu.be/FBGY7JIM-84')
            await page.get_by_role('button',name='링크 확인',exact=True).click()
            await expect(page.locator('#draft')).to_have_value(edited)
            assert not await page.get_by_role('checkbox').is_checked()
            await page.unroute('**/api/videos/FBGY7JIM-84',old_manual_draft)
            await page.unroute('**/api/videos/FBGY7JIM-84/analyze',fresh_generated_draft)
            await page.locator('#draft').fill(draft)
            result['checks'].append({'manual_draft_preserved_when_old_analysis_is_regenerated':'passed'})
            analysis_started=asyncio.Event()
            release_analysis=asyncio.Event()

            async def delayed_analysis_failure(route):
                analysis_started.set()
                await release_analysis.wait()
                await route.fulfill(status=503,json={'detail':'검증용 분석 오류'})

            await page.route('**/api/videos/FBGY7JIM-84/analyze',delayed_analysis_failure)
            await page.get_by_role('button',name='초안 다시 생성',exact=True).click()
            await asyncio.wait_for(analysis_started.wait(),timeout=10)
            dialog=page.get_by_role('dialog',name='영상을 분석하고 있습니다',exact=True)
            await expect(dialog).to_be_visible()
            await expect(dialog.get_by_role('progressbar')).to_be_visible()
            await expect(dialog.locator('.analysis-elapsed')).to_contain_text('초 경과')
            await expect(dialog.locator('.analysis-elapsed')).not_to_have_text('0분 0초 경과', timeout=3000)
            navigation=await page.get_by_role('link',name='작업 이력',exact=True).bounding_box()
            await page.mouse.click(navigation['x']+navigation['width']/2,navigation['y']+navigation['height']/2)
            assert page.url.rstrip('/')==BASE
            for _ in range(3):
                await page.keyboard.press('Tab')
                assert await dialog.evaluate('element=>document.activeElement===document.body||element.contains(document.activeElement)')
            await page.keyboard.press('Escape')
            await expect(dialog).to_be_visible()
            await page.screenshot(path=ARTIFACTS/'analysis-loading.png',full_page=True)
            release_analysis.set()
            await expect(dialog).not_to_be_visible()
            await expect(page.get_by_role('alert')).to_contain_text('검증용 분석 오류')
            await expect(page.locator('#draft')).to_have_value(draft)
            await expect(page.locator('#draft-guidance')).to_contain_text('운명원 연애 사주에 대한 관심')
            await page.unroute('**/api/videos/FBGY7JIM-84/analyze')
            result['checks'].append({'analysis_loading_blocks_mouse_keyboard_and_unlocks_after_error_fixture':'passed'})
            rejected = await page.request.post(BASE + '/api/posting-jobs', data={
                'video_id': 'FBGY7JIM-84', 'text': draft, 'approved': False})
            assert rejected.status == 422
            forbidden = await page.request.post(BASE + '/api/posting-jobs', data={
                'video_id': 'jNQXAC9IVRw', 'text': draft, 'approved': True})
            assert forbidden.status == 403
            invalid = await page.request.post(BASE + '/api/videos/resolve', data={'url': 'https://evil.example/watch?v=FBGY7JIM-84'})
            assert invalid.status == 422
            origin = await page.request.post(BASE + '/api/posting-jobs', headers={'Origin': 'https://evil.example'}, data={
                'video_id': 'FBGY7JIM-84', 'text': draft, 'approved': True})
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
