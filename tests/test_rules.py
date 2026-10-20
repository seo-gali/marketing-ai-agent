import unittest

from fastapi import HTTPException

from backend.analysis import validate_comment
from backend.services import video_id


class InputRules(unittest.TestCase):
    def test_comment_trust_boundary(self):
        valid = '[광고] 제목의 시간여행자처럼 다양한 이야기가 궁금하다면 운명원의 연애 사주 콘텐츠도 참고해 보세요.'
        self.assertEqual(validate_comment(valid), valid)
        for invalid in [valid.replace('[광고] ', ''), valid.replace('운명원', '다른곳'),
                        valid + ' #광고', valid + ' https://example.com',
                        '[광고] 운명원', '[광고] ' + '운명원 ' * 40,
                        valid + ' 직접 상담받았어요.', valid + '\n한줄추가']:
            with self.subTest(text=invalid), self.assertRaises(HTTPException):
                validate_comment(invalid)

    def test_video_url_boundary(self):
        for url in ['DPFhGxGM8qQ', 'https://youtu.be/DPFhGxGM8qQ',
                    'https://www.youtube.com/watch?v=DPFhGxGM8qQ&hl=ko',
                    'https://youtube.com/shorts/DPFhGxGM8qQ']:
            self.assertEqual(video_id(url), 'DPFhGxGM8qQ')
        for url in ['http://youtu.be/DPFhGxGM8qQ', 'https://evil.test/watch?v=DPFhGxGM8qQ',
                    'https://youtube.com.evil.test/watch?v=DPFhGxGM8qQ', 'invalid']:
            with self.subTest(url=url), self.assertRaises(HTTPException):
                video_id(url)


if __name__ == '__main__':
    unittest.main()
