import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

from backend import analysis, browser, config, db, main, services


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
                       'quote': '가장 이해가 안 되는 순간',
                       'comment': '“가장 이해가 안 되는 순간”이라는 말이 와닿네요. 상대 마음은 자꾸 바뀌는데 내 인연은 어떤지 운명원 연애 사주로 보고 싶어요.'}
        self.summary_schemas = []

    def tearDown(self):
        self.db_patch.stop()
        self.root_patch.stop()
        self.directory.cleanup()

    def generate(self):
        def answer(url, payload, **kwargs):
            if 'quote' in payload['format']['properties']:
                self.summary_schemas.append(payload['format'])
            value = {'valid': True, 'reason': ''} if 'valid' in payload['format']['properties'] else self.result
            return {'message': {'content': json.dumps(value, ensure_ascii=False)}}
        with patch.object(services, 'youtube', return_value={'items': []}), patch.object(services, 'request_json', side_effect=answer):
            return analysis.generate(self.video, self.rows, ['화면 OCR 테스트 픽스처'])

    def test_exact_quote_timestamp_and_capture_are_preserved(self):
        self.rows.append({**self.rows[0], 'text': '을 먼저 판단하거든요', 'timestamp': '1:40', 'start_seconds': 100})
        result = self.generate()
        self.assertNotIn('을 먼저 판단하거든요', self.summary_schemas[0]['properties']['quote']['enum'])
        self.assertTrue(result['scene_verified'])
        self.assertEqual(result['source_basis'], 'frame_ocr')
        self.assertEqual(result['evidence'][0]['quote'], self.result['quote'])
        self.assertEqual(result['evidence'][0]['capture'], 'a' * 32 + '.png')
        self.assertNotIn('0:33', result['comment'])
        self.assertIn('&t=33s', result['evidence'][0]['url'])
        self.assertEqual(result['comment'], self.result['comment'])

    def test_fabricated_quote_is_rejected_without_saving(self):
        self.result['quote'] = '원문에 없는 새로운 발언'
        with self.assertRaises(HTTPException):
            self.generate()
        self.assertIsNone(db.get_analysis(self.video['id']))

    def test_description_alone_does_not_generate_a_viewer_comment(self):
        with patch.object(services, 'request_json') as model:
            with self.assertRaises(HTTPException) as raised:
                analysis.generate(self.video, [], ['공개 자막 미확보'])
        self.assertIn('영상 발언', raised.exception.detail)
        self.assertIsNone(db.get_analysis(self.video['id']))
        model.assert_not_called()
        with patch.object(services, 'fetch_video', return_value=self.video), patch.object(browser, 'start_job') as posting:
            with self.assertRaises(HTTPException) as blocked:
                asyncio.run(main.post_comment(main.PostingRequest(video_id=self.video['id'], text=self.result['comment'], approved=True)))
        self.assertEqual(blocked.exception.status_code, 422)
        posting.assert_not_called()

    def test_generic_advertising_is_rejected(self):
        self.result['concern'] = '운명원 콘텐츠 소개가 궁금할까?'
        with self.assertRaises(HTTPException):
            self.generate()

    def test_valid_question_does_not_require_a_specific_ending(self):
        self.result['concern'] = '상대가 달라진 이유가 궁금해요?'
        result = self.generate()
        self.assertEqual(result['concern'], self.result['concern'])
        self.result['comment'] = '“가장 이해가 안 되는 순간”이 자꾸 생기는 걸 보면 인연은 복잡하네요. 운명원 연애 사주로 내 마음의 답을 찾고 싶어요.'
        self.assertIn('찾고 싶어요', self.generate()['comment'])
        self.result['concern'] = '신데렐라가 무도회에서 유리 구두를 흘린 일을 두고 상대에게 의도적으로 다가간 행동인지, 우연한 계기로 시작된 인연인지 어떻게 구분할 수 있을까요?'
        self.assertGreater(len(self.result['concern']), 60)
        self.assertEqual(self.generate()['concern'], self.result['concern'])

    def test_generated_report_style_comment_is_rejected(self):
        for text in [
            '[광고] 0:33 화면의 “가장 이해가 안 되는 순간”. 상대의 마음이 궁금하다면 운명원 연애 사주도 참고해 보세요.',
            '가장 이해가 안 되는 순간, 내 인연의 시기가 궁금해지는 이야기로 이어 운명원 연애 사주를 보고 싶은 마음을 표현하세요. [광고]',
        ]:
            with self.subTest(text=text), self.assertRaises(HTTPException):
                self.result['comment'] = text
                self.generate()

    def test_generated_prose_is_saved_without_an_advertising_suffix(self):
        result = self.generate()
        self.assertEqual(result['comment'], self.result['comment'])
        self.assertNotIn('[광고]', result['comment'])

    def test_generated_body_uses_the_full_character_limit(self):
        body = self.result['comment'] + ' '
        budget = config.MAX_CHARS
        self.assertEqual(analysis.DraftResult.model_json_schema()['properties']['comment']['maxLength'], budget)
        self.result['comment'] = body.ljust(budget + 1, '음')
        with self.assertRaises(HTTPException):
            self.generate()
        self.assertIsNone(db.get_analysis(self.video['id']))
        self.result['comment'] = body.ljust(budget, '음')
        self.assertEqual(len(self.generate()['comment']), config.MAX_CHARS)

    def test_unavailable_model_is_not_retried_as_invalid_prose(self):
        with patch.object(services, 'youtube', return_value={'items': []}), patch.object(services, 'request_json', side_effect=HTTPException(503, '모델 연결 실패')) as request:
            with self.assertRaises(HTTPException) as raised:
                analysis.generate(self.video, self.rows)
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(request.call_count, 1)

    def test_invented_personal_context_is_not_saved_after_review_failure(self):
        self.result['comment'] = '“가장 이해가 안 되는 순간”이라는 말이 와닿네요. 제 여자친구와 기혼 남자의 관계가 궁금해서 운명원 연애 사주로 보고 싶어요.'
        def answer(url, payload, **kwargs):
            value = {'valid': False, 'reason': '자료에 없는 기혼 남자와 현재 연인 추가'} if 'valid' in payload['format']['properties'] else self.result
            return {'message': {'content': json.dumps(value, ensure_ascii=False)}}
        with patch.object(services, 'youtube', return_value={'items': []}), patch.object(services, 'request_json', side_effect=answer):
            with self.assertRaises(HTTPException) as raised:
                analysis.generate(self.video, self.rows)
        self.assertIn('댓글 내용 검토', raised.exception.detail)
        self.assertIsNone(db.get_analysis(self.video['id']))

    def test_model_quote_escaping_and_brand_spacing_are_normalized(self):
        expected = self.result['comment'].replace('“', '"').replace('”', '"')
        self.result['comment'] = expected.replace('"', r'\"').replace('운명원', '운명 원')
        self.assertEqual(self.generate()['comment'], expected)

    def test_reaction_does_not_have_to_copy_the_caption(self):
        self.rows[0]['text'] = '가장 이해가 안 되는 순간이에요'
        self.result['quote'] = self.rows[0]['text']
        self.result['comment'] = '상대 태도가 처음이랑 달라지면 혼자 해석만 하게 될 듯ㅠ 마음 읽기는 너무 어렵네. 운명원 연애 사주로 난 어떤 사람이랑 맞을지 궁금해진다'
        result = self.generate()
        self.assertEqual(result['quote'], self.rows[0]['text'])
        self.assertIn(result['quote'], self.rows[0]['text'])
        self.assertNotIn(result['quote'], result['comment'])
        self.assertEqual(result['evidence'][0]['quote'], result['quote'])

    def test_quote_position_is_not_fixed(self):
        self.result['comment'] = '내 인연은 어떤지 운명원 연애 사주도 궁금해지네요. 상대 마음이 “가장 이해가 안 되는 순간”이라니 참 복잡하네요.'
        self.assertEqual(self.generate()['comment'], self.result['comment'])

    def test_frame_sources_are_not_merged_and_ocr_path_is_bounded(self):
        rows = self.rows + [{**self.rows[0], 'timestamp': '0:38', 'start_seconds': 38, 'text': '두 번째 화면의 자막입니다.', 'capture': 'b' * 32 + '.png'}]
        sources = analysis.transcript_sources(self.video['id'], rows)
        self.assertEqual(len(sources), 2)
        self.assertNotEqual(sources[0]['capture'], sources[1]['capture'])
        with patch.object(services.subprocess, 'run') as process, self.assertRaises(ValueError):
            services.ocr_frame(Path(self.directory.name) / 'outside.png')
        process.assert_not_called()

    def evidence_cache(self):
        return {'draft_version': 4, 'warnings': ['표본 분석'], 'sources': [
            {'type': 'title', 'text': self.video['title']},
            {'type': 'description', 'text': self.video['description']},
            *[{'type': 'frame_ocr', 'text': self.rows[0]['text'], 'timestamp': f'{index}:33', 'capture': 'a' * 32 + '.png'} for index in range(8)],
        ]}

    def test_reanalysis_reuses_captures_without_opening_chrome(self):
        folder = Path(self.directory.name) / 'captures'
        folder.mkdir()
        (folder / ('a' * 32 + '.png')).write_bytes(b'fixture')
        with patch.object(browser, 'SCREENSHOTS', folder), patch.object(db, 'get_analysis', return_value=self.evidence_cache()), patch.object(browser, 'async_playwright') as chrome:
            rows, warnings = asyncio.run(browser.collect_video_evidence(self.video))
        self.assertEqual(len(rows), 8)
        self.assertEqual(rows[-1]['start_seconds'], 453)
        self.assertEqual(warnings, ['표본 분석'])
        chrome.assert_not_called()

    def test_old_partial_changed_or_missing_evidence_is_not_reused(self):
        folder = Path(self.directory.name) / 'captures'
        folder.mkdir()
        (folder / ('a' * 32 + '.png')).write_bytes(b'fixture')
        for kind in ['old', 'partial', 'changed', 'missing']:
            cached = self.evidence_cache()
            if kind == 'old':
                cached['draft_version'] = 1
            elif kind == 'partial':
                cached['sources'] = cached['sources'][:5]
            elif kind == 'changed':
                cached['sources'][1]['text'] = '변경 전 설명'
            with self.subTest(kind=kind), patch.object(db, 'get_analysis', return_value=cached), patch.object(browser, 'SCREENSHOTS', folder if kind != 'missing' else folder / 'missing'):
                self.assertIsNone(browser.cached_video_evidence(self.video))

    def test_vision_reads_only_local_capture_and_filters_non_caption_output(self):
        image = config.ROOT / 'local' / 'screenshots' / ('c' * 32 + '.png')
        image.parent.mkdir(parents=True)
        image.write_bytes(b'fixture-image')
        responses = [{'capabilities': ['completion', 'vision']}, {'message': {'content': json.dumps({'lines': ['과거의 이별 장면을 재해석한다', '구독', 42]})}}]
        with patch.object(services, 'request_json', side_effect=responses) as request, patch.object(services.subprocess, 'run') as shell:
            self.assertEqual(services.ocr_frame(image), ['과거의 이별 장면을 재해석한다'])
        self.assertEqual(request.call_count, 2)
        self.assertTrue(request.call_args.args[1]['messages'][0]['images'])
        shell.assert_not_called()


if __name__ == '__main__':
    unittest.main()
