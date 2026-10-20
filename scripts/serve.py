import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == '__main__':
    # Windows Playwright용 Proactor 이벤트 루프 유지
    uvicorn.run('backend.main:app', host='127.0.0.1', port=8000, loop='asyncio', workers=1)
