import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from fastapi import HTTPException

from backend.analysis import validate_comment
from backend.services import video_id
from backend import db, config


class InputRules(unittest.TestCase):
    def test_comment_trust_boundary(self):
        valid = '[광고] 제목의 시간여행자처럼 다양한 이야기가 궁금하다면 운명원의 연애 사주 콘텐츠도 참고해 보세요.'
        self.assertEqual(validate_comment(valid), valid)
        self.assertEqual(validate_comment(valid.removeprefix('[광고] ')+' [광고]'), valid.removeprefix('[광고] ')+' [광고]')
        self.assertEqual(validate_comment(valid.removeprefix('[광고] ')), valid.removeprefix('[광고] '))
        for invalid in [valid.replace('운명원', '다른곳'),
                        valid + ' #광고', valid + ' https://example.com',
                        '[광고] 운명원', '[광고] ' + '운명원 ' * 40,
                        valid + ' 직접 상담받았어요.', valid + '\n한줄추가']:
            with self.subTest(text=invalid), self.assertRaises(HTTPException):
                validate_comment(invalid)
        for suffix in [' bit.ly/test', ' ｂｉｔ．ｌｙ/test', ' b\u200bit.ly/test']:
            with self.assertRaises(HTTPException):
                validate_comment(valid + suffix)
        with self.assertRaises(HTTPException):
            validate_comment('중년 싱글이 겪는 이혼과 사별의 고통을 어떻게 극복할지 궁금하네. 운명원 연애 사주 보니 내가 맞을 인연은 언제 찾아올까?')

    def test_video_url_boundary(self):
        for url in ['DPFhGxGM8qQ', 'https://youtu.be/DPFhGxGM8qQ',
                    'https://www.youtube.com/watch?v=DPFhGxGM8qQ&hl=ko',
                    'https://youtube.com/shorts/DPFhGxGM8qQ']:
            self.assertEqual(video_id(url), 'DPFhGxGM8qQ')
        for url in ['http://youtu.be/DPFhGxGM8qQ', 'https://evil.test/watch?v=DPFhGxGM8qQ',
                    'https://youtube.com.evil.test/watch?v=DPFhGxGM8qQ', 'invalid']:
            with self.subTest(url=url), self.assertRaises(HTTPException):
                video_id(url)


class PostingRules(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path_patch = patch.object(config, 'DB_PATH', Path(self.directory.name) / 'rules.db')
        self.path_patch.start()
        db.initialize()
        self.video = {'id': 'fixture0001', 'channel_id': next(iter(config.CHANNELS))}
        self.text = '[광고] 제목의 시간여행자처럼 다양한 이야기가 궁금하다면 운명원의 연애 사주 콘텐츠도 참고해 보세요.'

    def tearDown(self):
        self.path_patch.stop()
        self.directory.cleanup()

    def test_allowlist_approval_and_profile(self):
        for video, approved, profile in [({'id': 'outsider001', 'channel_id': 'forbidden'}, True, '유튜브1'),
                                          (self.video, False, '유튜브1'), (self.video, True, '유튜브2')]:
            with self.assertRaises(HTTPException):
                db.reserve_job(video, self.text, approved, profile)
        self.assertEqual(db.activities()['quota']['used'], 0)

    def test_concurrent_duplicate_and_quota(self):
        def reserve(_):
            try:
                return db.reserve_job(self.video, self.text, True)['id']
            except HTTPException:
                return None
        with ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(sum(result is not None for result in pool.map(reserve, range(4))), 1)
        for index in range(2, 11):
            db.reserve_job({**self.video, 'id': f'fixture{index:04}'}, self.text.replace('다양한', f'{index}번째'), True)
        self.assertEqual(db.activities()['quota']['used'], 10)
        with self.assertRaises(HTTPException):
            db.reserve_job({**self.video, 'id': 'fixture0012'}, self.text.replace('다양한', '열두번째'), True)

    def test_restart_and_uncertainty(self):
        before = db.reserve_job(self.video, self.text, True)
        db.recover_jobs()
        self.assertEqual(db.get_job(before['id'])['status'], 'failed')
        after = db.reserve_job(self.video, self.text, True)
        db.mark_submission(after['id'])
        db.initialize()
        db.recover_jobs()
        self.assertEqual(db.get_job(after['id'])['status'], 'uncertain')
        with self.assertRaises(HTTPException):
            db.reserve_job(self.video, self.text, True)
        self.assertEqual(len(db.activities()['jobs']), 2)

    def test_midnight_quota_recheck(self):
        with patch.object(db, 'today', return_value='2026-10-19'):
            old = db.reserve_job(self.video, self.text, True)
        with patch.object(config, 'DAILY_MAX', 1):
            db.reserve_job({**self.video, 'id': 'fixture0002'}, self.text.replace('다양한', '두번째'), True)
            with self.assertRaises(HTTPException):
                db.mark_submission(old['id'])

    def test_history_is_bounded_and_paginated(self):
        for index in range(20):
            db.log('fixture',str(index))
        first=db.activities(limit=7,kind='logs')
        second=db.activities(offset=7,limit=7,kind='logs')
        self.assertEqual(len(first['logs']),7)
        self.assertTrue(first['has_more'])
        self.assertEqual(first['total_pages'],3)
        self.assertFalse({item['id'] for item in first['logs']} & {item['id'] for item in second['logs']})


if __name__ == '__main__':
    unittest.main()
