"""키보드·접근성 구조 검사. NVDA/JAWS 실기기 심사를 대체하지 않음."""
import asyncio
import json
import re
from pathlib import Path

from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:8000'


def luminance(color):
    rgb=[int(value)/255 for value in re.findall(r'\d+',color)[:3]]
    linear=[value/12.92 if value<=.04045 else ((value+.055)/1.055)**2.4 for value in rgb]
    return sum(value*weight for value,weight in zip(linear,[.2126,.7152,.0722]))


async def main():
    result={'checks':[],'screen_reader_device':'not_run','status':'failed'}
    async with async_playwright() as driver:
        chromium=await driver.chromium.launch(channel='chrome',headless=True)
        page=await chromium.new_page(viewport={'width':390,'height':900},reduced_motion='reduce')
        try:
            await page.goto(BASE)
            await page.keyboard.press('Tab')
            assert await page.locator('.skip-link').evaluate('(element)=>element===document.activeElement')
            await page.keyboard.press('Enter')
            assert await page.locator('#main-content').evaluate('(element)=>element===document.activeElement')
            await page.keyboard.press('Shift+Tab')
            # 모바일 메뉴를 키보드로 찾아 열기
            await page.goto(BASE)
            for _ in range(3):
                await page.keyboard.press('Tab')
            assert await page.locator('#menu-toggle').evaluate('(element)=>element===document.activeElement')
            outline=await page.locator('#menu-toggle').evaluate("element=>getComputedStyle(element).outlineWidth")
            assert outline!='0px'
            await page.keyboard.press('Enter')
            assert await page.locator('#menu-toggle').get_attribute('aria-expanded')=='true'
            await page.keyboard.press('Tab')
            await page.keyboard.press('Tab')
            assert await page.get_by_role('link',name='작업 이력',exact=True).evaluate('(element)=>element===document.activeElement')
            await page.keyboard.press('Enter')
            await page.get_by_role('heading',name='작업 이력',exact=True).wait_for()
            assert await page.locator('#main-content').evaluate('(element)=>element===document.activeElement')
            await page.locator('#menu-toggle').focus()
            await page.keyboard.press('Enter')
            await page.keyboard.press('Escape')
            assert await page.locator('#menu-toggle').get_attribute('aria-expanded')=='false'
            result['checks'].append('skip_link_mobile_menu_enter_escape_focus_visible')
            snapshots={}
            for route in ['/','/activities','/settings','/not-a-page']:
                await page.goto(BASE+route)
                assert await page.locator('main').count()==1
                assert await page.locator('h1').count()==1
                assert await page.locator('html').get_attribute('lang')=='ko'
                for field in await page.locator('input:not([type=hidden]),textarea,select').all():
                    control_id=await field.get_attribute('id')
                    assert await field.get_attribute('aria-label') or (control_id and await page.locator(f'label[for="{control_id}"]').count())
                snapshots[route]=await page.locator('body').aria_snapshot()
                assert await page.locator('button').evaluate_all("elements => elements.filter(e => e.offsetWidth && e.offsetHeight).every(e=>!!(e.getAttribute('aria-label')||e.textContent.trim()))")
            result['checks'].append('landmarks_headings_labels_and_accessibility_tree')
            await page.goto(BASE)
            contrasts={}
            for selector,background in [('.heading p','rgb(255,255,255)'),('.eyebrow','rgb(255,255,255)'),('.btn.primary.full-load',None)]:
                colors=await page.locator(selector).first.evaluate("element=>({color:getComputedStyle(element).color,background:getComputedStyle(element).backgroundColor})")
                first=luminance(colors['color']);second=luminance(background or colors['background'])
                ratio=(max(first,second)+.05)/(min(first,second)+.05)
                assert ratio>=4.5,(selector,ratio)
                contrasts[selector]=round(ratio,2)
            result['contrast_samples']=contrasts
            assert await page.locator('.soft-count').evaluate("element=>getComputedStyle(element).animationName")=='none'
            result['checks'].append('sample_text_contrast_and_reduced_motion')
            # 의도적으로 잘못된 응답을 넣어 오류 복구 화면만 검사
            fault=await chromium.new_page()
            await fault.route(BASE+'/api/health',lambda route:route.fulfill(json={'channels':{'bad':{'invalid':'shape'}}}))
            await fault.goto(BASE)
            await fault.get_by_role('heading',name='화면을 표시하지 못했습니다').wait_for()
            assert await fault.get_by_role('button',name='새로고침',exact=True).count()==1
            await fault.close()
            result['checks'].append('error_boundary_fixture_recovery')
            await page.goto((ROOT/'docs'/'index.html').as_uri())
            assert await page.locator('main').count()==1
            assert await page.locator('h1').count()==1
            for link in await page.locator('a[href]:not([href^="#"])').all():
                assert (ROOT/'docs'/await link.get_attribute('href')).resolve().is_file()
            for width in [390,1440]:
                await page.set_viewport_size({'width':width,'height':900})
                assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            await page.keyboard.press('Tab')
            await page.keyboard.press('Enter')
            assert await page.locator('#main').evaluate('(element)=>element===document.activeElement')
            await page.screenshot(path=str(ROOT/'artifacts'/'docs-overview.png'),full_page=True)
            snapshots['docs/index.html']=await page.locator('body').aria_snapshot()
            result['checks'].append('html_overview_links_mobile_and_skip_link')
            (ROOT/'artifacts'/'accessibility-tree.json').write_text(json.dumps(snapshots,ensure_ascii=False,indent=2),encoding='utf-8')
            result['status']='passed'
        finally:
            (ROOT/'artifacts'/'accessibility-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(result,ensure_ascii=False,indent=2))
            await chromium.close()


if __name__=='__main__':
    asyncio.run(main())
