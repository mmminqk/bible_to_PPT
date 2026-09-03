"""
tests/test_loader.py

pptx_generator.loader 모듈 단위 테스트:
- 슬라이드 용량 추정
- 청크 라벨 병합 (merge_labels)
- 청크 단일화 판단 (should_unify_chunk)
- 성경 데이터 로드 및 구절 추출 (개역개정, ESV)
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

from pptx_generator.constants import BIBLE_BOOKS
from pptx_generator.loader import (
    estimate_slide_capacity,
    merge_labels,
    should_unify_chunk,
    load_kor_bible,
    parse_scripture_file,
    extract_passages_grouped,
    extract_with_canonical_labels,
)


class TestLoader(unittest.TestCase):

    def test_estimate_slide_capacity(self):
        # 한글 기본 크기(26pt) 시 기본 용량(140자)
        cap_kor = estimate_slide_capacity(26, is_english=False)
        self.assertEqual(cap_kor, 140)

        # 영어 기본 크기(18pt) 시 기본 용량(280자)
        cap_eng = estimate_slide_capacity(18, is_english=True)
        self.assertEqual(cap_eng, 280)

        # 폰트 크기가 커지면 용량은 줄어들어야 함
        cap_large = estimate_slide_capacity(36, is_english=False)
        self.assertLess(cap_large, cap_kor)

    def test_merge_labels(self):
        # 같은 장 내 연장
        self.assertEqual(
            merge_labels("창세기 1:1-3", "창세기 1:4"),
            "창세기 1:1-4"
        )
        self.assertEqual(
            merge_labels("요한계시록 21:1-3", "요한계시록 21:4-7"),
            "요한계시록 21:1-7"
        )
        # 장을 넘어가는 경우
        self.assertEqual(
            merge_labels("창세기 1:1-31", "창세기 2:1-3"),
            "창세기 1:1-2:3"
        )
        # 단일 절
        self.assertEqual(
            merge_labels("시편 23:1", "시편 23:1"),
            "시편 23:1"
        )

    def test_should_unify_chunk(self):
        # 2개 이상 슬라이드로 나뉘고 단일 ref인 경우 -> True
        self.assertTrue(should_unify_chunk(["창 1:1-31"], 3))
        # 1개 슬라이드인 경우 -> False
        self.assertFalse(should_unify_chunk(["창 1:1-3"], 1))
        # 세미콜론이 포함된 경우 -> False
        self.assertFalse(should_unify_chunk(["창 1:1; 1:3"], 2))

    def test_bible_data_extract(self):
        kor_dir = os.path.join(ROOT_DIR, 'text_DB', '개역개정-text')
        if not os.path.isdir(kor_dir):
            self.skipTest("한글 성경 폴더가 없어 테스트를 건너뜁니다.")

        kor_data = load_kor_bible(kor_dir, BIBLE_BOOKS)
        self.assertIn("창세기", kor_data)
        self.assertGreater(len(kor_data["창세기"]), 0)

        # 창세기 1:1 구절 추출 테스트
        entries = extract_passages_grouped(kor_data, [["창 1:1"]])
        self.assertEqual(len(entries), 1)
        label, body, _ = entries[0]
        self.assertIn("창세기 1:1", label)
        self.assertIn("태초에", body)


if __name__ == '__main__':
    unittest.main()
