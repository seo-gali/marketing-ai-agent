from contextlib import asynccontextmanager
import asyncio
import re

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse, FileResponse
from pydantic import StrictBool
from fastapi.staticfiles import StaticFiles

from . import config, db, services, analysis, browser


@asynccontextmanager
async def lifespan(app):
    db.initialize()
    db.recover_jobs()
    try:
        yield
    finally:
        await browser.shutdown()


app = FastAPI(title='Marketing AI Agent', lifespan=lifespan)


@app.middleware('http')
async def local_only(request: Request, call_next):
    host = request.headers.get('host', '').split(':')[0]
    origin = request.headers.get('origin')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        return JSONResponse({'detail': '허용되지 않은 요청 출처입니다.'}, status_code=403)
    if host not in {'127.0.0.1', 'localhost', 'testserver'}:
        return JSONResponse({'detail': '로컬 접근만 허용됩니다.'}, status_code=403)
    if origin and origin not in {'http://127.0.0.1:5173', 'http://localhost:5173',
                                 'http://127.0.0.1:8000', 'http://localhost:8000'}:
        return JSONResponse({'detail': '허용되지 않은 요청 출처입니다.'}, status_code=403)
    return await call_next(request)


@app.get('/api/health')
def get_health():
    return services.health()


class ResolveRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


@app.get('/api/videos')
def get_videos():
    videos, warnings = services.discover()
    db.save_videos(videos)
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
    return {**video, 'allowed': services.allowed(video), 'analysis': db.get_analysis(video_id)}


@app.post('/api/videos/{video_id}/analyze')
def analyze_video(video_id: str):
    try:
        video = services.fetch_video(video_id)
        db.save_videos([video])
        result = analysis.generate(video)
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
def get_activities():
    return db.activities()


@app.get('/api/posting-jobs/{job_id}')
def get_posting_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, '작업을 찾을 수 없습니다.')
    return job


class BrowserRequest(BaseModel):
    video_id: str | None = None


@app.post('/api/browser/open')
async def open_browser(body: BrowserRequest):
    video_id = services.video_id(body.video_id) if body.video_id else None
    return await browser.open_profile(video_id)


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
    app.mount('/', StaticFiles(directory=config.ROOT / 'dist', html=True), name='dashboard')
