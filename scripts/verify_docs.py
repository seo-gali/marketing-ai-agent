"""소개 페이지·탭·실제 Markdown 문서·팝업 검사. DOCS_URL 지정 시 게시본 검사."""
import asyncio
import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts'


class DocsHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        prefix = '/marketing-ai-agent'
        if not self.path.startswith(prefix + '/'):
            return self.send_error(404)
        self.path = self.path[len(prefix):]
        return super().do_GET()

    def log_message(self, *_):
        pass


async def verify(base, published):
    result = {'url': base, 'status': 'failed', 'checks': []}
    ARTIFACTS.mkdir(exist_ok=True)
    async with async_playwright() as driver:
        browser = await driver.chromium.launch(channel='chrome', headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        if not published:
            async def local_markdown(route):
                path = route.request.url.split('/marketing-ai-agent/main/', 1)[1]
                allowed = {'README.md', 'docs/demo-scenario.md', 'docs/results/verification.md', 'docs/results/security-audit.md', 'docs/results/accessibility.md'}
                if path not in allowed:
                    return await route.abort()
                await route.fulfill(content_type='text/plain; charset=utf-8', body=(ROOT / path).read_text(encoding='utf-8'))
            await page.route('https://raw.githubusercontent.com/seo-gali/marketing-ai-agent/main/**', local_markdown)
        try:
            response = await page.goto(base)
            assert response.status == 200
            await expect(page).to_have_title('프로젝트 소개 · Marketing AI Agent')
            intro = page.get_by_role('tab', name='프로젝트 소개', exact=True)
            status = page.get_by_role('tab', name='앱 점검 현황', exact=True)
            await expect(intro).to_have_attribute('aria-selected', 'true')
            await expect(page.locator('#status-panel')).to_be_hidden()
            await intro.focus()
            await page.keyboard.press('ArrowRight')
            await expect(status).to_be_focused()
            await expect(status).to_have_attribute('aria-selected', 'true')
            await page.keyboard.press('Home')
            await expect(intro).to_be_focused()
            for asset in ['favicon.svg', 'style.css', 'app.js']:
                assert (await page.request.get(base + asset)).status == 200
            await page.screenshot(path=ARTIFACTS / 'project-introduction.png', full_page=True)
            result['checks'].append('project_title_tabs_keyboard_and_project_path_assets')

            dialog = page.get_by_role('dialog')
            body = page.locator('#document-content')
            install = page.get_by_role('button', name='설치·실행 방법', exact=True)
            await install.focus()
            await page.keyboard.press('Enter')
            await expect(dialog).to_be_visible()
            await expect(body).to_have_attribute('aria-busy', 'false', timeout=20000)
            await expect(body.get_by_role('heading', name='Marketing AI Agent', exact=True)).to_be_visible()
            assert await body.locator('table').count() >= 1
            assert await body.locator('pre code').count() >= 1
            await expect(page.get_by_role('button', name='문서 닫기', exact=True)).to_be_focused()
            await page.keyboard.press('Shift+Tab')
            assert await page.locator('#document-source').evaluate('element=>element===document.activeElement')
            await page.keyboard.press('Tab')
            await expect(page.get_by_role('button', name='문서 닫기', exact=True)).to_be_focused()
            await page.keyboard.press('Escape')
            await expect(dialog).to_be_hidden()
            await expect(install).to_be_focused()
            result['checks'].append('live_readme_tables_code_focus_trap_escape_and_focus_restore')
            await page.get_by_role('button', name='촬영 시나리오', exact=True).click()
            await expect(body).to_have_attribute('aria-busy', 'false', timeout=20000)
            await expect(body.get_by_role('heading', name='시연 영상 촬영안', exact=True)).to_be_visible()
            assert await body.locator('table').count() == 1
            assert await body.locator('pre code').count() >= 1
            await page.get_by_role('button', name='문서 닫기', exact=True).click()
            result['checks'].append('demo_script_timeline_and_flow_in_markdown_dialog')

            await status.click()
            for label, heading in [('구현·실행 결과', '구현 및 검증 결과'), ('보안 감사', '보안 감사'), ('접근성 검수', '접근성·사용성 검수')]:
                await page.get_by_role('button', name=label, exact=True).click()
                await expect(body).to_have_attribute('aria-busy', 'false', timeout=20000)
                await expect(body.get_by_role('heading', name=heading, exact=True)).to_be_visible()
                assert await body.locator('table').count() >= 1
                await page.get_by_role('button', name='문서 닫기', exact=True).click()
            result['checks'].append('three_live_markdown_reports_in_dialog')

            for width in [1440, 390]:
                await page.set_viewport_size({'width': width, 'height': 900})
                for tab in [intro, status]:
                    await tab.click()
                    assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                await page.screenshot(path=ARTIFACTS / f'project-status-{width}.png', full_page=True)
            await intro.click()
            await install.click()
            await expect(body).to_have_attribute('aria-busy', 'false', timeout=20000)
            assert await body.evaluate('element=>element.scrollWidth<=element.clientWidth')
            assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            await page.screenshot(path=ARTIFACTS / 'project-readme-mobile.png', full_page=True)
            await page.keyboard.press('Escape')
            result['checks'].append('mobile_panels_and_markdown_without_horizontal_overflow')

            # 네트워크 오류와 악성 Markdown 응답은 브라우저 내부 픽스처로만 검사
            raw = 'https://raw.githubusercontent.com/seo-gali/marketing-ai-agent/main/README.md'
            await page.route(raw, lambda route: route.abort())
            await install.click()
            await expect(body.get_by_role('alert')).to_be_visible()
            await expect(body.get_by_role('button', name='다시 시도')).to_be_visible()
            await page.unroute(raw)
            payload = '# Safe heading\n\n<img src=x onerror="window.docsInjected=1">\n\n[run](javascript:alert(1))\n\n**bold** and `code`\n\n| key | value |\n|---|---|\n| a | b |'
            await page.route(raw, lambda route: route.fulfill(body=payload, headers={'Content-Type': 'text/plain; charset=utf-8', 'Access-Control-Allow-Origin': '*'}))
            await body.get_by_role('button', name='다시 시도').click()
            await expect(body.get_by_role('heading', name='Safe heading')).to_be_visible()
            assert await body.locator('img,script,a[href^="javascript:"]').count() == 0
            assert await body.locator('strong').count() == 1
            assert await page.evaluate('window.docsInjected===undefined')
            assert not errors, errors
            result['checks'].append('network_error_retry_and_markdown_xss_boundary_fixture')
            result['status'] = 'passed'
        except Exception as error:
            result['error'] = (str(error) or type(error).__name__)[:1000]
            await page.screenshot(path=ARTIFACTS / 'docs-failure.png', full_page=True)
            raise
        finally:
            name = 'docs-pages-result.json' if published else 'docs-e2e-result.json'
            (ARTIFACTS / name).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(result, ensure_ascii=False, indent=2))
            await browser.close()


if __name__ == '__main__':
    published = os.getenv('DOCS_URL')
    server = None
    try:
        if not published:
            server = ThreadingHTTPServer(('127.0.0.1', 0), partial(DocsHandler, directory=str(ROOT / 'docs')))
            threading.Thread(target=server.serve_forever, daemon=True).start()
        base = published or f'http://127.0.0.1:{server.server_port}/marketing-ai-agent/'
        asyncio.run(verify(base.rstrip('/') + '/', bool(published)))
    finally:
        if server:
            server.shutdown()
            server.server_close()
