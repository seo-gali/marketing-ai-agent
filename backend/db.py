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
