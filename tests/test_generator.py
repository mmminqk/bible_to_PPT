"""
tests/test_generator.py

pptx_generator.generator 및 constants 모듈 단위 테스트:
- 스타일 딥 머지 (get_full_style) 및 색상 정규화
- Presentation 객체 생성 및 슬라이드 구성
- 블랙 슬라이드 삽입
"""

import unittest
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PG_DIR = os.path.join(ROOT_DIR, 'pptx_generator')
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if PG_DIR not in sys.path:
    sys.path.insert(0, PG_DIR)

from pptx_generator.constants import get_full_style, normalize_color, DEFAULT_STYLE
from pptx_generator.generator import (
    add_scripture_to_ppt,
    insert_black_slides,
    detect_shape_mapping,
)


class TestGenerator(unittest.TestCase):

    def test_normalize_color(self):
        self.assertEqual(normalize_color("#1F3337"), "1F3337")
        self.assertEqual(normalize_color("1F3337"), "1F3337")
        self.assertEqual(normalize_color(""), "")

    def test_get_full_style_fallback(self):
        # 빈 값 전달 시 기본 스타일 완전 복원
        full = get_full_style(None)
        self.assertIn('kor_title', full)
        self.assertIn('kor_body', full)
        self.assertIn('eng_title', full)
        self.assertIn('eng_body', full)
        self.assertEqual(full['kor_title']['font'], DEFAULT_STYLE['kor_title']['font'])

        # 일부 키만 전달된 경우
        partial = {'kor_title': {'size': 40, 'color': '#FF0000'}}
        merged = get_full_style(partial)
        # 지정한 값 반영
        self.assertEqual(merged['kor_title']['size'], 40.0)
        self.assertEqual(merged['kor_title']['color'], 'FF0000')
        # 지정하지 않은 값은 기본값 유지
        self.assertEqual(merged['kor_title']['font'], DEFAULT_STYLE['kor_title']['font'])
        self.assertEqual(merged['kor_body']['size'], DEFAULT_STYLE['kor_body']['size'])

    def test_add_scripture_to_ppt(self):
        tmpl_path = os.path.join(ROOT_DIR, 'pptx_template', 'template.pptx')
        if not os.path.isfile(tmpl_path):
            self.skipTest("template.pptx 파일이 없어 테스트를 건너뜁니다.")

        verse_texts = [
            ("창세기 1:1\n", "1 태초에 하나님이 천지를 창조하시니라", []),
            ("창세기 1:2\n", "2 땅이 혼돈하고 공허하며...", []),
        ]
        verse_texts_eng = [
            ("Genesis 1:1\n", "1 In the beginning, God created...", []),
            ("Genesis 1:2\n", "2 The earth was without form...", []),
        ]

        prs = add_scripture_to_ppt(
            template_path=tmpl_path,
            verse_texts=verse_texts,
            verse_texts_eng=verse_texts_eng,
            style=None,  # 스타일 생략 시에도 크래시 없이 기본 스타일로 생성되는지 검증
            return_prs=True,
        )

        self.assertIsNotNone(prs)
        # 슬라이드가 최소 2장 생성되어야 함
        self.assertGreaterEqual(len(prs.slides), 2)

    def test_insert_black_slides(self):
        tmpl_path = os.path.join(ROOT_DIR, 'pptx_template', 'template.pptx')
        if not os.path.isfile(tmpl_path):
            self.skipTest("template.pptx 파일이 없어 테스트를 건너뜁니다.")

        verse_texts = [
            ("창세기 1:1\n", "1 태초에 하나님이 천지를 창조하시니라", []),
        ]
        verse_texts_eng = [
            ("Genesis 1:1\n", "1 In the beginning...", []),
        ]

        prs = add_scripture_to_ppt(
            template_path=tmpl_path,
            verse_texts=verse_texts,
            verse_texts_eng=verse_texts_eng,
            return_prs=True,
        )
        initial_count = len(prs.slides)
        # 1개 그룹 뒤에 검은 슬라이드 1장 삽입
        insert_black_slides(prs, [initial_count])
        self.assertEqual(len(prs.slides), initial_count + 1)


if __name__ == '__main__':
    unittest.main()
