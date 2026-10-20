import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime

from . import config


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec='milliseconds')


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
