from contextlib import asynccontextmanager
import asyncio
import re
import unicodedata
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from fastapi.responses import FileResponse
from pydantic import StrictBool
from fastapi.staticfiles import StaticFiles

from . import config, db, services, analysis, browser
from .security import LocalSecurity


@asynccontextmanager
async def lifespan(app):
    db.initialize()
    db.recover_jobs()
    try:
        yield
    finally:
        await browser.shutdown()


app = FastAPI(title='Marketing AI Agent', lifespan=lifespan)
app.add_middleware(LocalSecurity)


@app.get('/api/health')
def get_health():
    return services.health()


class ResolveRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


@app.get('/api/videos')
def get_videos(q: str | None = Query(default=None, max_length=100)):
    if q is not None and (not unicodedata.normalize('NFKC', q).strip() or any(unicodedata.category(character) in {'Cc', 'Cf'} for character in q)):
        raise HTTPException(422, '검색어를 입력하세요. 전체 조회는 영상 불러오기를 사용하세요.')
    videos, warnings = services.discover()
    db.save_videos(videos)
    if q is not None:
        videos = [video for video in videos if q.strip().casefold() in (video['title'] + ' ' + video['channel']).casefold()]
    return {'videos': [{**video, 'allowed': services.allowed(video)} for video in videos], 'warnings': warnings}


@app.post('/api/videos/resolve')
def resolve_video(body: ResolveRequest):
    video = services.fetch_video(body.url)
    db.save_videos([video])
    return {**video, 'allowed': services.allowed(video)}


@app.get('/api/videos/{video_id}')
def get_video(video_id: str):
    video = db.get_video(services.video_id(video_id))
    if not video:
        raise HTTPException(404, '영상이 없습니다.')
    return {**video, 'allowed': services.allowed(video), 'analysis': db.get_analysis(video_id), 'posting_job': db.video_job(video_id)}


@app.post('/api/videos/{video_id}/analyze')
async def analyze_video(video_id: str):
    try:
        video = await asyncio.to_thread(services.fetch_video, video_id)
        db.save_videos([video])
        transcript, warnings = await browser.collect_video_evidence(video)
        result = await asyncio.to_thread(analysis.generate, video, transcript, warnings)
        db.log('analysis_complete', '실제 Ollama 분석 및 초안 저장', video['id'])
        return result
    except HTTPException as error:
        db.log('analysis_failed', error.detail, video_id)
        raise


class DraftRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


@app.put('/api/drafts/{video_id}')
def update_draft(video_id: str, body: DraftRequest):
    if not db.get_video(services.video_id(video_id)):
        raise HTTPException(404, '영상이 없습니다.')
    text = analysis.validate_comment(body.text)
    if db.duplicate_draft(video_id, text):
        raise HTTPException(422, '다른 영상과 같은 댓글입니다.')
    db.save_draft(video_id, text)
    db.log('draft_saved', '검증한 댓글 수정 저장', video_id)
    return {'comment': text}


@app.get('/api/activities')
def get_activities(offset: int = Query(default=0, ge=0, le=100000), limit: int = Query(default=30, ge=1, le=100), kind: Literal['jobs', 'logs'] = 'jobs'):
    return db.activities(offset, limit, kind)


class HistoryDeletion(BaseModel):
    kind: Literal['jobs', 'logs']
    id: str | None = Field(default=None, pattern=r'^(?:[a-f0-9]{32}|[0-9]{1,20})$')


@app.delete('/api/activities')
def delete_history(body: HistoryDeletion):
    return db.hide_history(body.kind, body.id)


class HistoryRestore(BaseModel):
    token: str = Field(pattern=r'^[a-f0-9]{32}$')


@app.post('/api/activities/restore')
def restore_history(body: HistoryRestore):
    return db.restore_history(body.token)


class ProfileRequest(BaseModel):
    name: Literal['유튜브1', '유튜브2', '유튜브3']


@app.get('/api/profiles')
def get_profiles():
    return db.profiles()


@app.post('/api/profiles')
def add_profile(body: ProfileRequest):
    return db.add_profile(body.name)


@app.post('/api/profiles/login')
async def login_profile(body: ProfileRequest):
    return await browser.login_profile(body.name)


@app.get('/api/posting-jobs/{job_id}')
def get_posting_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, '작업을 찾을 수 없습니다.')
    return job


class BrowserRequest(BaseModel):
    video_id: str | None = None
    profile: Literal['유튜브1', '유튜브2', '유튜브3'] = '유튜브1'


@app.post('/api/browser/open')
async def open_browser(body: BrowserRequest):
    video_id = services.video_id(body.video_id) if body.video_id else None
    return await browser.open_profile(video_id, body.profile)


@app.post('/api/browser/close')
async def close_browser():
    return await browser.close_profile()


@app.get('/api/browser/status')
async def browser_status():
    return await browser.status()


class PostingRequest(BaseModel):
    video_id: str
    text: str = Field(min_length=1, max_length=2000)
    approved: StrictBool
    profile: str = '유튜브1'


@app.post('/api/posting-jobs', status_code=202)
async def post_comment(body: PostingRequest):
    try:
        analysis.validate_comment(body.text)
        if body.approved is not True:
            raise HTTPException(422, '댓글 본문을 검토하고 광고 게시를 승인하세요.')
        video = await asyncio.to_thread(services.fetch_video, body.video_id)
        if browser.lock.locked():
            raise HTTPException(409, '다른 Chrome 작업이 진행 중입니다.')
        db.save_videos([video])
        job = db.reserve_job(video, body.text, body.approved, body.profile)
        browser.start_job(job)
        return job
    except HTTPException as error:
        db.log('rejected', error.detail, body.video_id)
        raise


@app.get('/api/screenshots/{filename}')
def get_screenshot(filename: str):
    if not re.fullmatch(r'[a-f0-9]{32}(?:-typed)?\.png', filename):
        raise HTTPException(404, '캡처가 없습니다.')
    path = browser.SCREENSHOTS / filename
    if not path.is_file():
        raise HTTPException(404, '캡처가 없습니다.')
    return FileResponse(path, headers={'Cache-Control': 'no-store'})


if (config.ROOT / 'dist').is_dir():
    app.mount('/assets', StaticFiles(directory=config.ROOT / 'dist' / 'assets'), name='assets')

    @app.get('/favicon.svg', include_in_schema=False)
    def favicon():
        return FileResponse(config.ROOT / 'dist' / 'favicon.svg')

    @app.get('/{path:path}', include_in_schema=False)
    def dashboard(path: str):
        if path.startswith('api/'):
            raise HTTPException(404, 'API 경로를 찾을 수 없습니다.')
        return FileResponse(config.ROOT / 'dist' / 'index.html', status_code=200 if path in {'', 'activities', 'settings'} else 404)
