import sqlite3
import json
import uuid
from contextlib import contextmanager
from datetime import datetime

from . import config


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec='milliseconds')


def today() -> str:
    return datetime.now().astimezone().date().isoformat()


@contextmanager
def connect():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(config.DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize():
    with connect() as connection:
        connection.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY, channel_id TEXT NOT NULL, title TEXT NOT NULL,
                channel TEXT NOT NULL, published_at TEXT NOT NULL, thumbnail TEXT NOT NULL,
                description TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS analyses (
                video_id TEXT PRIMARY KEY REFERENCES videos(id), data TEXT NOT NULL,
                model TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS comment_drafts (
                video_id TEXT PRIMARY KEY REFERENCES videos(id), text TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS posting_jobs (
                id TEXT PRIMARY KEY, video_id TEXT NOT NULL, profile TEXT NOT NULL,
                text TEXT NOT NULL, status TEXT NOT NULL, local_day TEXT NOT NULL,
                created_at TEXT NOT NULL, finished_at TEXT, error TEXT, screenshot TEXT,
                comment_url TEXT, submission_attempted INTEGER NOT NULL DEFAULT 0
            );
            CREATE UNIQUE INDEX IF NOT EXISTS one_post_per_video ON posting_jobs(video_id)
                WHERE status <> 'failed';
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT, video_id TEXT,
                stage TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL
            );
        ''')


def save_videos(videos):
    with connect() as connection:
        connection.executemany('''INSERT INTO videos VALUES (:id, :channel_id, :title,
            :channel, :published_at, :thumbnail, :description)
            ON CONFLICT(id) DO UPDATE SET title=excluded.title, channel_id=excluded.channel_id,
            channel=excluded.channel, published_at=excluded.published_at,
            thumbnail=excluded.thumbnail, description=excluded.description''', videos)


def get_video(video_id):
    with connect() as connection:
        row = connection.execute('SELECT * FROM videos WHERE id=?', (video_id,)).fetchone()
        return dict(row) if row else None


def get_analysis(video_id):
    with connect() as connection:
        row = connection.execute('SELECT * FROM analyses WHERE video_id=?', (video_id,)).fetchone()
        draft = connection.execute('SELECT text FROM comment_drafts WHERE video_id=?', (video_id,)).fetchone()
        return {**json.loads(row['data']), 'model': row['model'], 'created_at': row['created_at'],
                'comment': draft['text'] if draft else ''} if row else None


def save_analysis(video_id, data):
    with connect() as connection:
        connection.execute('INSERT OR REPLACE INTO analyses VALUES (?,?,?,?)',
                           (video_id, json.dumps(data, ensure_ascii=False), config.MODEL, now()))
        connection.execute('INSERT OR REPLACE INTO comment_drafts VALUES (?,?,?)',
                           (video_id, data['comment'], now()))


def save_draft(video_id, text):
    with connect() as connection:
        connection.execute('INSERT OR REPLACE INTO comment_drafts VALUES (?,?,?)', (video_id, text, now()))


def duplicate_draft(video_id, text):
    with connect() as connection:
        return connection.execute('SELECT 1 FROM comment_drafts WHERE video_id<>? AND text=?',
                                  (video_id, text)).fetchone() is not None


def log(stage, detail, video_id=None, job_id=None):
    with connect() as connection:
        connection.execute('INSERT INTO activity_logs(job_id,video_id,stage,detail,created_at) VALUES (?,?,?,?,?)',
                           (job_id, video_id, stage, detail, now()))


def reserve_job(video, text, approved, profile='유튜브1'):
    from fastapi import HTTPException
    from .analysis import validate_comment
    from .services import allowed
    text = validate_comment(text)
    if approved is not True:
        raise HTTPException(422, '광고 댓글 본문에 대한 명시적인 게시 승인이 필요합니다.')
    if profile != '유튜브1':
        raise HTTPException(422, '유튜브1 전용 프로필만 지원합니다.')
    if not allowed(video):
        raise HTTPException(403, '허용 채널 또는 등록된 본인 테스트 영상에만 게시할 수 있습니다.')
    if duplicate_draft(video['id'], text):
        raise HTTPException(422, '다른 영상과 같은 댓글을 게시할 수 없습니다.')
    with connect() as connection:
        connection.execute('BEGIN IMMEDIATE')
        if connection.execute("SELECT 1 FROM posting_jobs WHERE video_id=? AND status<>'failed'", (video['id'],)).fetchone():
            raise HTTPException(409, '이미 게시되었거나 진행 중 또는 확인 불가인 영상입니다. 재게시하지 않습니다.')
        count = connection.execute("SELECT count(*) FROM posting_jobs WHERE local_day=? AND status<>'failed'", (today(),)).fetchone()[0]
        if count >= config.DAILY_MAX:
            raise HTTPException(409, '일일 게시 상한에 도달했습니다. 진행 중·확인 불가 작업도 포함합니다.')
        job_id = uuid.uuid4().hex
        connection.execute('''INSERT INTO posting_jobs(id,video_id,profile,text,status,local_day,created_at)
                              VALUES (?,?,?,?,?,?,?)''', (job_id, video['id'], profile, text, 'queued', today(), now()))
        connection.execute('INSERT INTO activity_logs(job_id,video_id,stage,detail,created_at) VALUES (?,?,?,?,?)',
                           (job_id, video['id'], 'queued', '광고 본문 승인 및 게시 제한 확인', now()))
    return get_job(job_id)


def get_job(job_id):
    with connect() as connection:
        row = connection.execute('SELECT * FROM posting_jobs WHERE id=?', (job_id,)).fetchone()
        return dict(row) if row else None


def update_job(job_id, status, *, error=None, screenshot=None, comment_url=None):
    with connect() as connection:
        connection.execute('''UPDATE posting_jobs SET status=?,error=?,screenshot=COALESCE(?,screenshot),
            comment_url=COALESCE(?,comment_url),finished_at=? WHERE id=?''',
                           (status, error, screenshot, comment_url,
                            now() if status in {'success', 'failed', 'uncertain'} else None, job_id))
        row = connection.execute('SELECT video_id FROM posting_jobs WHERE id=?', (job_id,)).fetchone()
        connection.execute('INSERT INTO activity_logs(job_id,video_id,stage,detail,created_at) VALUES (?,?,?,?,?)',
                           (job_id, row['video_id'], status, error or status, now()))


def mark_submission(job_id):
    from fastapi import HTTPException
    with connect() as connection:
        connection.execute('BEGIN IMMEDIATE')
        row = connection.execute('SELECT * FROM posting_jobs WHERE id=?', (job_id,)).fetchone()
        if not row or row['submission_attempted'] or row['status'] in {'success', 'failed', 'uncertain'}:
            raise HTTPException(409, '이미 제출을 시도했거나 종료된 작업입니다.')
        count = connection.execute("SELECT count(*) FROM posting_jobs WHERE local_day=? AND status<>'failed' AND id<>?", (today(), job_id)).fetchone()[0]
        if count >= config.DAILY_MAX:
            raise HTTPException(409, '게시 직전 일일 상한에 도달했습니다.')
        connection.execute("UPDATE posting_jobs SET submission_attempted=1,local_day=?,status='submitting' WHERE id=?", (today(), job_id))
        connection.execute('INSERT INTO activity_logs(job_id,video_id,stage,detail,created_at) VALUES (?,?,?,?,?)',
                           (job_id, row['video_id'], 'submitting', '게시 클릭 직전 제출 시도 기록', now()))


def recover_jobs():
    with connect() as connection:
        rows = connection.execute("SELECT * FROM posting_jobs WHERE status NOT IN ('success','failed','uncertain')").fetchall()
    for row in rows:
        update_job(row['id'], 'uncertain' if row['submission_attempted'] else 'failed',
                   error='서버 재시작으로 작업 중단. 제출 시도 후 작업은 자동 재게시하지 않습니다.')


def activities():
    with connect() as connection:
        jobs = [dict(row) for row in connection.execute('''SELECT j.*,v.title FROM posting_jobs j
                LEFT JOIN videos v ON v.id=j.video_id ORDER BY j.created_at DESC LIMIT 100''')]
        logs = [dict(row) for row in connection.execute('SELECT * FROM activity_logs ORDER BY id DESC LIMIT 150')]
        used = connection.execute("SELECT count(*) FROM posting_jobs WHERE local_day=? AND status<>'failed'", (today(),)).fetchone()[0]
        blocked = [row[0] for row in connection.execute("SELECT video_id FROM posting_jobs WHERE status<>'failed'")]
        return {'jobs': jobs, 'logs': logs, 'quota': {'used': used, 'max': config.DAILY_MAX, 'day': today()}, 'blocked_video_ids': blocked}
