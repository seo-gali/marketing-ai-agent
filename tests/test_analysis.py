import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from backend import analysis, config, db, services


class GroundedDraft(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.root_patch = patch.object(config, 'ROOT', root)
        self.db_patch = patch.object(config, 'DB_PATH', root / 'test.db')
        self.root_patch.start()
        self.db_patch.start()
        db.initialize()
        self.video = {'id': 'fixture0001', 'title': '남자의 연애 작동원리', 'description': '처음과 달라지는 마음',
                      'channel_id': next(iter(config.CHANNELS)), 'channel': 'fixture', 'published_at': '2026-10-21', 'thumbnail': ''}
        db.save_videos([self.video])
        self.rows = [{'type': 'frame_ocr', 'timestamp': '0:33', 'start_seconds': 33,
                      'text': '가장 이해가 안 되는 순간!', 'capture': 'a' * 32 + '.png'}]
        self.result = {'concern': '연애 초반과 달라진 상대의 태도를 어떻게 이해할까?', 'source_ids': ['timed-0'],
                       'quote': '가장 이해가 안 되는 순간'}

    def tearDown(self):
        self.db_patch.stop()
        self.root_patch.stop()
        self.directory.cleanup()

    def generate(self):
        with patch.object(services, 'youtube', return_value={'items': []}), patch.object(services, 'request_json', return_value={'message': {'content': json.dumps(self.result, ensure_ascii=False)}}):
            return analysis.generate(self.video, self.rows, ['화면 OCR 테스트 픽스처'])

    def test_exact_quote_timestamp_and_capture_are_preserved(self):
        result = self.generate()
        self.assertTrue(result['scene_verified'])
        self.assertEqual(result['source_basis'], 'frame_ocr')
        self.assertEqual(result['evidence'][0]['quote'], self.result['quote'])
        self.assertEqual(result['evidence'][0]['capture'], 'a' * 32 + '.png')
        self.assertIn('0:33', result['comment'])
        self.assertIn(self.result['concern'][:-1], result['comment'])
        self.assertIn('운명원 연애 사주도 참고해 보세요.', result['comment'])

    def test_fabricated_quote_is_rejected_without_saving(self):
        self.result['quote'] = '원문에 없는 새로운 발언'
        with self.assertRaises(HTTPException):
            self.generate()
        self.assertIsNone(db.get_analysis(self.video['id']))

    def test_generic_advertising_is_rejected(self):
        self.result['concern'] = '운명원 콘텐츠 소개가 궁금할까?'
        with self.assertRaises(HTTPException):
            self.generate()

    def test_valid_question_does_not_require_a_specific_ending(self):
        self.result['concern'] = '상대가 달라진 이유가 궁금해요?'
        result = self.generate()
        self.assertIn('“상대가 달라진 이유가 궁금해요”가 고민이라면', result['comment'])

    def test_frame_sources_are_not_merged_and_ocr_path_is_bounded(self):
        rows = self.rows + [{**self.rows[0], 'timestamp': '0:38', 'start_seconds': 38, 'text': '두 번째 화면의 자막입니다.', 'capture': 'b' * 32 + '.png'}]
        sources = analysis.transcript_sources(self.video['id'], rows)
        self.assertEqual(len(sources), 2)
        self.assertNotEqual(sources[0]['capture'], sources[1]['capture'])
        with patch.object(services.subprocess, 'run') as process, self.assertRaises(ValueError):
            services.ocr_frame(Path(self.directory.name) / 'outside.png')
        process.assert_not_called()


if __name__ == '__main__':
    unittest.main()
