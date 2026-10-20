from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, db, services


@asynccontextmanager
async def lifespan(app):
    db.initialize()
    yield


app = FastAPI(title='Marketing AI Agent', lifespan=lifespan)


@app.middleware('http')
async def local_only(request: Request, call_next):
    host = request.headers.get('host', '').split(':')[0]
    origin = request.headers.get('origin')
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
    return {**video, 'allowed': services.allowed(video)}


if (config.ROOT / 'dist').is_dir():
    app.mount('/', StaticFiles(directory=config.ROOT / 'dist', html=True), name='dashboard')
