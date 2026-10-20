import asyncio
import re
import unicodedata
import uuid
from urllib.parse import urlparse

from fastapi import HTTPException
from playwright.async_api import async_playwright, Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from . import config, db

lock = asyncio.Lock()
driver = None
context = None
page = None
tasks = set()
SCREENSHOTS = config.ROOT / 'local' / 'screenshots'


def normalize(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


async def ensure_open():
    global driver, context, page
    if context and page and not page.is_closed():
        return page
    if driver:
        await driver.stop()
    config.PROFILE_PATH.mkdir(parents=True, exist_ok=True)
    driver = await async_playwright().start()
    context = await driver.chromium.launch_persistent_context(
        config.PROFILE_PATH, channel='chrome', headless=False, locale='ko-KR',
        args=['--lang=ko-KR'], viewport={'width': 1365, 'height': 900})
    page = context.pages[0] if context.pages else await context.new_page()
    page.set_default_timeout(15000)
    return page


async def screenshot(name=None):
    if not page or page.is_closed():
        return None
    SCREENSHOTS.mkdir(parents=True, exist_ok=True)
    filename = (name or uuid.uuid4().hex) + '.png'
    try:
        await page.screenshot(path=SCREENSHOTS / filename, full_page=False, timeout=8000)
        return filename
    except PlaywrightError:
        return None


async def check_access():
    if not page or page.is_closed():
        raise HTTPException(409, '전용 Chrome이 닫혔습니다. 다시 열어 주세요.')
    blocked = page.locator('iframe[src*="recaptcha"], iframe[src*="hcaptcha"], #captcha-form, form[action*="/sorry/"]')
    for item in await blocked.all():
        if await item.is_visible():
            raise HTTPException(409, 'CAPTCHA 또는 접근 제한 감지. 사용자가 직접 조치해야 합니다.')
    enforcement = page.locator('ytd-enforcement-message-view-model')
    if await enforcement.count() and await enforcement.first.is_visible():
        raise HTTPException(409, 'YouTube 접근 제한 화면입니다. 사용자가 직접 확인해야 합니다.')
    if urlparse(page.url).hostname not in {'youtube.com', 'www.youtube.com', 'm.youtube.com'}:
        raise HTTPException(409, 'YouTube 계정 로그인 또는 인증 확인을 직접 완료해 주세요.')
    await page.locator('#avatar-btn, ytd-masthead a[href*="ServiceLogin"]').first.wait_for(state='visible', timeout=20000)
    if not await page.locator('#avatar-btn').count():
        raise HTTPException(409, '유튜브1 전용 Chrome에서 사용자가 직접 로그인해야 합니다.')


async def status():
    opened = bool(page and not page.is_closed())
    signed_in = False
    reason = '전용 Chrome을 열어 로그인하세요.'
    if opened:
        try:
            await check_access()
            signed_in, reason = True, ''
        except HTTPException as error:
            reason = error.detail
        except PlaywrightError:
            reason = '브라우저 화면 전환 중입니다. 잠시 후 확인하세요.'
    return {'open': opened, 'signed_in': signed_in, 'needs_action': reason, 'busy': lock.locked(), 'profile': '유튜브1'}


async def open_profile(video_id=None):
    global page
    if lock.locked():
        raise HTTPException(409, '브라우저 작업이 진행 중입니다.')
    async with lock:
        try:
            already_open = bool(context and page and not page.is_closed())
            await ensure_open()
            if already_open:
                page = await context.new_page()
                page.set_default_timeout(15000)
            current = page
            await current.goto(f'https://www.youtube.com/watch?v={video_id}&hl=ko' if video_id else 'https://www.youtube.com/?hl=ko', wait_until='domcontentloaded')
            await current.locator('ytd-masthead').wait_for()
            result = await status()
            result['busy'] = False
            if result['needs_action']:
                result['screenshot'] = await screenshot()
            return result
        except PlaywrightError:
            capture = await screenshot()
            db.log('browser_failed', '전용 Chrome 실행/페이지 이동 실패' + (f' · {capture}' if capture else ''))
            raise HTTPException(503, 'Chrome 실행 또는 YouTube 이동 실패. 프로필 사용 중 여부와 네트워크를 확인하세요.') from None


async def close_profile():
    global driver, context, page
    if lock.locked():
        raise HTTPException(409, '게시 작업 중에는 브라우저를 닫을 수 없습니다.')
    async with lock:
        if context:
            await context.close()
        if driver:
            await driver.stop()
        context = page = driver = None
    return {'open': False}


async def account_handle():
    await page.locator('#avatar-btn').click()
    handle = page.locator('ytd-active-account-header-renderer #channel-handle')
    await handle.wait_for(state='visible')
    value = normalize(await handle.inner_text()).lstrip('@')
    await page.keyboard.press('Escape')
    if not value:
        raise HTTPException(409, '현재 계정의 채널 핸들을 확인할 수 없습니다. 게시하지 않습니다.')
    return value.casefold()


async def find_comment(text, handle):
    for row in await page.locator('ytd-comment-thread-renderer').all():
        body = row.locator('#content-text').first
        author = row.locator('#author-text').first
        if not await body.count() or not await author.count():
            continue
        if normalize(await body.inner_text()) != normalize(text):
            continue
        author_path = urlparse(await author.get_attribute('href') or '').path
        from urllib.parse import unquote
        if unquote(author_path).strip('/').lstrip('@').casefold() != handle:
            continue
        link = row.locator('a[href*="lc="]').first
        if await link.count():
            href = await link.get_attribute('href')
            if href:
                from urllib.parse import urljoin
                return urljoin('https://www.youtube.com', href)
    return None


async def run_job(job):
    async with lock:
        attempted = False
        try:
            db.update_job(job['id'], 'opening')
            await ensure_open()
            db.update_job(job['id'], 'navigating')
            await page.goto(f"https://www.youtube.com/watch?v={job['video_id']}&hl=ko", wait_until='domcontentloaded')
            await page.locator('ytd-masthead').wait_for()
            await check_access()
            handle = await account_handle()
            await page.locator('#comments').scroll_into_view_if_needed()
            placeholder = page.locator('ytd-comment-simplebox-renderer #simplebox-placeholder')
            await placeholder.wait_for(state='visible', timeout=25000)
            if await find_comment(job['text'], handle):
                db.update_job(job['id'], 'uncertain', error='같은 계정·본문의 기존 댓글 감지. 중복 게시하지 않습니다.', screenshot=await screenshot(job['id']))
                return
            await placeholder.click()
            editor = page.locator('ytd-comment-simplebox-renderer #contenteditable-root[contenteditable="true"]')
            await editor.wait_for(state='visible')
            if normalize(await editor.inner_text()):
                raise HTTPException(409, '댓글 입력창에 기존 내용이 있습니다. 덮어쓰지 않고 중단합니다.')
            db.update_job(job['id'], 'typing')
            await editor.press_sequentially(job['text'], delay=85)
            if normalize(await editor.inner_text()) != normalize(job['text']):
                raise HTTPException(409, '실제 입력된 본문이 승인한 댓글과 일치하지 않습니다.')
            await screenshot(job['id'] + '-typed')
            await check_access()
            submit = page.locator('ytd-comment-simplebox-renderer #submit-button').get_by_role('button', name=re.compile(r'^댓글$|^Comment$'))
            if not await submit.is_enabled():
                raise HTTPException(409, '댓글 게시 버튼이 비활성 상태입니다.')
            db.mark_submission(job['id'])
            attempted = True
            await submit.click()
            db.update_job(job['id'], 'verifying')
            for _ in range(15):
                await check_access()
                comment_url = await find_comment(job['text'], handle)
                if comment_url:
                    await page.reload(wait_until='domcontentloaded')
                    await page.locator('#comments').scroll_into_view_if_needed()
                    await page.locator('ytd-comment-thread-renderer').first.wait_for(timeout=15000)
                    if await find_comment(job['text'], handle):
                        db.update_job(job['id'], 'success', comment_url=comment_url, screenshot=await screenshot(job['id']))
                        return
                    break
                await asyncio.sleep(1)
            db.update_job(job['id'], 'uncertain', error='게시 시도 후 재로드한 화면에서 계정·본문·댓글 링크를 확인하지 못했습니다. 자동 재게시하지 않습니다.', screenshot=await screenshot(job['id']))
        except asyncio.CancelledError:
            db.update_job(job['id'], 'uncertain' if attempted else 'failed', error='서버 종료로 브라우저 작업 중단', screenshot=await screenshot(job['id']))
            raise
        except (HTTPException, PlaywrightError, OSError) as error:
            stage = db.get_job(job['id'])['status']
            category = '화면 요소 또는 응답 대기 시간 초과' if isinstance(error, PlaywrightTimeoutError) else '화면 조작 실패'
            reason = error.detail if isinstance(error, HTTPException) else f'Chrome {category} (단계: {stage}). 로그인·댓글 허용·네트워크·프로필 사용 중 여부를 확인하세요.'
            db.update_job(job['id'], 'uncertain' if attempted else 'failed', error=reason, screenshot=await screenshot(job['id']))
        except Exception:
            db.update_job(job['id'], 'uncertain' if attempted else 'failed', error='브라우저 내부 오류. 확인 후 다시 시작하세요.', screenshot=await screenshot(job['id']))


def start_job(job):
    task = asyncio.create_task(run_job(job))
    tasks.add(task)
    task.add_done_callback(tasks.discard)


async def shutdown():
    for task in list(tasks):
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    await close_profile()
