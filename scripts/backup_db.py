"""로컬 DB의 일관된 백업. 원본 DB를 변경하지 않음."""
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend import config

if __name__=='__main__':
    if not config.DB_PATH.is_file():
        raise SystemExit('DB가 없습니다. 앱을 먼저 실행하세요.')
    directory=config.ROOT/'local'/'backups'
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/(datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.db')
    with sqlite3.connect(config.DB_PATH.as_uri()+'?mode=ro',uri=True) as source, sqlite3.connect(target) as destination:
        source.backup(destination)
        assert destination.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    print('로컬 백업 완료:',target.relative_to(config.ROOT))
