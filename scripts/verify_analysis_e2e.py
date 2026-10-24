"""실제 영상·Ollama·화면 근거·광고 초안의 사용자 경로 검사. 외부 게시 미실행."""
import asyncio
import json
import re
import sys
from time import perf_counter
from pathlib import Path

from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8000'


async def main():
    result = {'status': 'failed', 'external_posting': 'not_run', 'videos': []}
    async with async_playwright() as driver:
        browser = await driver.chromium.launch(channel='chrome', headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 1000})
        posting_requests = []
        analysis_responses = {}
        page.on('request', lambda request: posting_requests.append(request.url) if request.method == 'POST' and request.url.endswith('/api/posting-jobs') else None)
        page.on('response', lambda response: analysis_responses.update({response.url.split('/')[-2]: response}) if response.request.method == 'POST' and response.url.endswith('/analyze') else None)
        try:
            await page.goto(BASE)
            await page.get_by_role('button',name='채널 추가',exact=True).click()
            for video_id in ['FBGY7JIM-84', 'DvxMfC_KjX0', 'VDflnx7Cn1o']:
                selection_started = perf_counter()
                await page.get_by_role('textbox', name='YouTube 영상 링크').fill('https://youtu.be/' + video_id)
                async with page.expect_response(lambda response: response.url.endswith('/api/videos/resolve') and response.request.method == 'POST') as resolved:
                    await page.get_by_role('button', name='링크 확인', exact=True).click()
                metadata = await (await resolved.value).json()
                assert metadata['id'] == video_id
                await expect(page.locator('#analysis-title')).to_have_text(metadata['title'])
                detail = await (await page.request.get(BASE + '/api/videos/' + video_id)).json()
                old_captures = (detail['analysis'] or {}).get('captures', [])
                generated_on_select = not detail['analysis'] or detail['analysis'].get('draft_version') != 10
                if generated_on_select:
                    async with asyncio.timeout(600):
                        while video_id not in analysis_responses:
                            await asyncio.sleep(.2)
                    first = analysis_responses[video_id]
                    assert first.ok, await first.text()
                    detail = await (await page.request.get(BASE + '/api/videos/' + video_id)).json()
                    await expect(page.get_by_role('button', name='초안 다시 생성', exact=True)).to_be_enabled(timeout=10000)
                initial_seconds = round(perf_counter() - selection_started, 2)
                if video_id == 'FBGY7JIM-84' and '--regenerate' in sys.argv and detail['analysis']:
                    previous = await page.locator('#draft').input_value()
                    await page.get_by_role('button', name='초안 다시 생성', exact=True).click()
                    await expect(page.get_by_role('dialog')).to_be_visible()
                    async with asyncio.timeout(60):
                        while True:
                            activity = await (await page.request.get(BASE + '/api/activities')).json()
                            if any(row['video_id'] == video_id and row['stage'] == 'analysis_progress' and row['detail'] == '댓글 초안 작성 중' for row in activity['logs'][:1]):
                                break
                            await asyncio.sleep(.5)
                    await asyncio.sleep(.15)
                    cancelling = perf_counter()
                    async with page.expect_response(lambda response: response.url.endswith('/analyze/cancel')) as cancelled:
                        await page.get_by_role('button', name='취소', exact=True).click()
                    cancellation_response = await cancelled.value
                    assert cancellation_response.ok and (await cancellation_response.json())['status'] == 'cancelled'
                    await expect(page.get_by_role('dialog')).not_to_be_visible()
                    await expect(page.locator('#draft')).to_have_value(previous)
                    unchanged = await (await page.request.get(BASE + '/api/videos/' + video_id)).json()
                    assert unchanged['analysis']['created_at'] == detail['analysis']['created_at']
                    result['real_cancellation'] = {'status': 'passed', 'seconds': round(perf_counter() - cancelling, 2), 'previous_draft_preserved': True}
                    analysis_responses.pop(video_id, None)
                regenerate = '--regenerate' in sys.argv and not generated_on_select
                started = perf_counter()
                if detail['analysis'] and regenerate:
                    analysis_responses.pop(video_id, None)
                    await page.get_by_role('button', name='초안 다시 생성', exact=True).click()
                if regenerate:
                    async with asyncio.timeout(600):
                        while video_id not in analysis_responses:
                            await asyncio.sleep(.2)
                    response = analysis_responses[video_id]
                    assert response.ok, await response.text()
                await expect(page.locator('#draft')).to_have_value(re.compile('운명원'), timeout=10000)
                await expect(page.get_by_role('button', name='초안 다시 생성', exact=True)).to_be_enabled(timeout=10000)
                generation_seconds = initial_seconds if generated_on_select else round(perf_counter() - started, 2)
                response = await page.request.get(BASE + '/api/videos/' + video_id)
                assert response.status == 200
                data = await response.json()
                analysis = data['analysis']
                await expect(page.locator('.concern-box')).to_have_text(analysis['concern'])
                assert await page.locator('.concern-box').evaluate('element=>element.scrollHeight<=element.clientHeight+1')
                assert analysis['source_basis'] in {'frame_ocr', 'transcript', 'metadata'}
                comment = analysis['comment']
                assert 40 <= len(comment) <= 120
                assert not re.search(r'\[(?:광고|유료광고|협찬)\]', comment) and '운명원' in comment and '사주' in comment
                assert analysis.get('draft_version') == 10
                assert '해결해' not in comment and '보장' not in comment and '콘텐츠 소개입니다' not in comment
                source = next(item for item in analysis['sources'] if item['id'] in analysis['source_ids'] and analysis['quote'] in item['text'])
                if source.get('timestamp'):
                    seconds = 0
                    for part in source['timestamp'].split(':'):
                        seconds = seconds * 60 + int(part)
                    assert f'&t={seconds}s' in analysis['evidence'][0]['url']
                assert not re.search(r'\d{1,2}:\d{2}|화면의|제목의|참고해 보세요', comment)
                timed = [item for item in analysis['sources'] if item['type'] in {'frame_ocr', 'transcript'}]
                captures = analysis.get('captures', [])
                if video_id == 'FBGY7JIM-84':
                    assert any(int(item['timestamp'].split(':')[0]) >= 8 for item in captures), captures
                if source.get('capture'):
                    assert (await page.request.get(BASE + '/api/screenshots/' + source['capture'])).status == 200
                    capture = page.locator('.evidence-capture').first
                    await capture.scroll_into_view_if_needed()
                    await expect(capture).to_have_js_property('complete', True)
                    assert await capture.evaluate('element=>element.naturalWidth>0')
                await expect(page.locator('.scene-grid figure')).to_have_count(3)
                assert await page.locator('.analysis-metadata,.source-notes').count() == 0
                assert not await page.get_by_role('checkbox').is_checked()
                reused = bool(captures) and captures == old_captures
                result['videos'].append({'id': video_id, 'regenerated': generated_on_select or video_id in analysis_responses, 'generation_seconds': generation_seconds, 'evidence_reused': reused, 'title': data['title'], 'concern': analysis['concern'], 'comment': comment, 'quote': analysis['quote'], 'source': source, 'warnings': analysis['warnings']})
                await page.screenshot(path=ROOT / 'artifacts' / f'grounded-{video_id}.png', full_page=True)
            assert result['videos'][0]['comment'] != result['videos'][1]['comment']
            for width in [1440, 390]:
                await page.set_viewport_size({'width': width, 'height': 1000})
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not posting_requests
            result['status'] = 'passed'
        except Exception as error:
            result['error'] = (str(error) or type(error).__name__)[:1500]
            await page.screenshot(path=ROOT / 'artifacts' / 'grounded-e2e-failure.png', full_page=True)
            raise
        finally:
            (ROOT / 'artifacts' / 'grounded-e2e-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(result, ensure_ascii=False, indent=2))
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
