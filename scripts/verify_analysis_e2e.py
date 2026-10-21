"""실제 영상·Ollama·화면 근거·광고 초안의 사용자 경로 검사. 외부 게시 미실행."""
import asyncio
import json
import re
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
            await page.get_by_text('더보기 · 영상 URL로 선택', exact=True).click()
            for video_id in ['akn-AvCeHBI', 'DvxMfC_KjX0']:
                await page.get_by_role('textbox', name='YouTube 영상 링크').fill('https://youtu.be/' + video_id)
                async with page.expect_response(lambda response: response.url.endswith('/api/videos/resolve') and response.request.method == 'POST') as resolved:
                    await page.get_by_role('button', name='링크 확인', exact=True).click()
                metadata = await (await resolved.value).json()
                assert metadata['id'] == video_id
                await expect(page.locator('#analysis-title')).to_have_text(metadata['title'])
                detail = await (await page.request.get(BASE + '/api/videos/' + video_id)).json()
                if not detail['analysis']:
                    async with asyncio.timeout(300):
                        while video_id not in analysis_responses:
                            await asyncio.sleep(.2)
                    response = analysis_responses[video_id]
                    assert response.ok, await response.text()
                await expect(page.locator('#draft')).to_have_value(re.compile(r'^\[광고\]'), timeout=10000)
                await expect(page.get_by_role('button', name='초안 다시 생성', exact=True)).to_be_enabled(timeout=10000)
                response = await page.request.get(BASE + '/api/videos/' + video_id)
                assert response.status == 200
                data = await response.json()
                analysis = data['analysis']
                assert analysis['scene_verified'], analysis['warnings']
                assert analysis['source_basis'] in {'frame_ocr', 'transcript'}
                comment = analysis['comment']
                assert 40 <= len(comment) <= 120
                assert comment.startswith('[광고]') and '운명원 연애 사주' in comment
                assert analysis['quote'] in comment
                assert '해결해' not in comment and '보장' not in comment and '콘텐츠 소개입니다' not in comment
                source = next(item for item in analysis['sources'] if item['type'] in {'frame_ocr', 'transcript'} and item['id'] in analysis['source_ids'] and analysis['quote'] in item['text'])
                assert source['timestamp'] in comment
                if source.get('capture'):
                    assert (await page.request.get(BASE + '/api/screenshots/' + source['capture'])).status == 200
                    await expect(page.get_by_role('link', name='영상 화면 캡처 ↗').first).to_be_visible()
                assert not await page.get_by_role('checkbox').is_checked()
                result['videos'].append({'id': video_id, 'title': data['title'], 'concern': analysis['concern'], 'comment': comment, 'quote': analysis['quote'], 'source': source, 'warnings': analysis['warnings']})
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
