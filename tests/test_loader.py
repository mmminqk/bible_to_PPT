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
    estimate_verse_lines,
    estimate_chunk_height_pt,
    partition_verses,
    merge_labels,
    should_unify_chunk,
    load_kor_bible,
    parse_scripture_file,
    extract_passages_grouped,
    extract_passages_grouped_eng,
    extract_with_canonical_labels,
)


class TestLoader(unittest.TestCase):

    def test_estimate_slide_capacity(self):
        # 한글 기본 크기(26pt) 시 기본 용량(200자)
        cap_kor = estimate_slide_capacity(26, is_english=False)
        self.assertEqual(cap_kor, 200)

        # 영어 기본 크기(18pt) 시 기본 용량(400자)
        cap_eng = estimate_slide_capacity(18, is_english=True)
        self.assertEqual(cap_eng, 400)

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

    def test_esv_data_extract_natural_abbreviations(self):
        esv_file = os.path.join(ROOT_DIR, 'text_DB', 'ESV-text', 'ESV_cleaned.txt')
        if not os.path.isfile(esv_file):
            self.skipTest("ESV 파일이 없어 테스트를 건너뜁니다.")

        eng_data = parse_scripture_file(esv_file)

        # 1. 고전 13:4-7 -> 1 Cor 13:4-7 (청킹 시 1 Cor 13:4-...)
        entries = extract_passages_grouped_eng(eng_data, [["고전 13:4-7"]])
        self.assertGreater(len(entries), 0)
        label, body, _ = entries[0]
        self.assertTrue(label.startswith("1 Cor 13:4"))
        self.assertIn("Love is patient", body)

        # 2. 요 3:16 -> John 3:16
        entries_john = extract_passages_grouped_eng(eng_data, [["요 3:16"]])
        self.assertEqual(len(entries_john), 1)
        label_j, body_j, _ = entries_john[0]
        self.assertTrue(label_j.startswith("John 3:16"))
        self.assertIn("God so loved the world", body_j)

        # 3. 룻 1:16 -> Ruth 1:16
        entries_ruth = extract_passages_grouped_eng(eng_data, [["룻 1:16"]])
        self.assertGreater(len(entries_ruth), 0)
        label_r, body_r, _ = entries_ruth[0]
        self.assertTrue(label_r.startswith("Ruth 1:16"))
        self.assertIn("where you go I will go", body_r)

        # 4. 출 3:14 -> Exod 3:14
        entries_exod = extract_passages_grouped_eng(eng_data, [["출 3:14"]])
        self.assertEqual(len(entries_exod), 1)
        label_e, body_e, _ = entries_exod[0]
        self.assertTrue(label_e.startswith("Exod 3:14"))
        self.assertIn("I AM WHO I AM", body_e)

        # 5. 한/영 동기화 추출 (extract_with_canonical_labels)
        kor_dir = os.path.join(ROOT_DIR, 'text_DB', '개역개정-text')
        if os.path.isdir(kor_dir):
            kor_data = load_kor_bible(kor_dir, BIBLE_BOOKS)
            k_res, e_res = extract_with_canonical_labels(kor_data, eng_data, [["고전 13:4-7"]])
            self.assertGreater(len(k_res), 0)
            self.assertEqual(len(k_res), len(e_res))
            self.assertEqual(k_res[0][0], "고린도전서 13:4-7")
            self.assertEqual(e_res[0][0], "1 Cor 13:4-7")

    def test_partition_verses_avoid_orphan(self):
        # 1. 텍스트박스 실제 가용 높이를 활용하여 불필요한 슬라이드 분할 및 공백 방지
        # 예: 2줄 + 2줄 + 1줄 구절 -> 2슬라이드로 쪼개지 않고 1슬라이드에 모두 배치
        v3 = [
            '1 사랑은 오래 참고 사랑은 온유하며 시기하지 아니하며 사랑은 자랑하지 아니하며 교만하지 아니하며',
            '2 무례히 행하지 아니하며 자기의 유익을 구하지 아니하며 성내지 아니하며 악한 것을 생각하지 아니하며',
            '3 불의를 기뻐하지 아니하며 진리와 함께 기뻐하고',
        ]
        chunks3 = partition_verses(v3, kor_font_size=26)
        self.assertEqual(chunks3, [[0, 1, 2]])

        # 2. 창세기 1:1-4 실제 구절 (총 4절, 한글 7줄 / 영어 7줄)
        # 텍스트박스 수직 높이를 활용하여 오버랩 없이 1슬라이드([[0, 1, 2, 3]]) 안에 수납
        v4 = [
            '1 태초에 하나님이 천지를 창조하시니라',
            '2 땅이 혼돈하고 공허하며 흑암이 깊음 위에 있고 하나님의 영은 수면 위에 운행하시니라',
            '3 하나님이 이르시되 빛이 있으라 하시니 빛이 있었고',
            '4 빛이 하나님이 보시기에 좋았더라 하나님이 빛과 어둠을 나누사',
        ]
        chunks4 = partition_verses(v4, kor_font_size=26)
        self.assertEqual(chunks4, [[0, 1, 2, 3]])

        # 2-1. 창세기 1:1-5 (총 5절, 10줄 -> 1슬라이드에 넣으면 영어 텍스트박스와 오버랩 발생)
        # 2슬라이드로 분할하되 마지막 5절만 홀로 남지 않도록 [[0, 1, 2], [3, 4]]로 분할
        v5_gen = v4 + ['5 하나님이 빛을 낮이라 부르시고 어둠을 밤이라 부르시니라 저녁이 되고 아침이 되니 이는 첫째 날이니라']
        self.assertEqual(partition_verses(v5_gen, kor_font_size=26), [[0, 1, 2], [3, 4]])

        # 3. 물리적 높이를 초과하여 2슬라이드 분할이 불가피할 때 마지막 1절 고아 방지
        # 앞의 4개 절이 각각 2줄씩(총 8줄)이고 마지막 5번째 절이 짧은 1줄인 경우:
        # 무작정 [[0, 1, 2, 3], [4]]로 나누면 마지막 슬라이드에 짧은 1줄만 남으므로,
        # 앞 슬라이드를 충분히 채우면서도 마지막 슬라이드에 2절이 오도록 [[0, 1, 2], [3, 4]]로 보정
        v5_multi = [
            '1 사랑은 오래 참고 사랑은 온유하며 시기하지 아니하며 사랑은 자랑하지 아니하며 교만하지 아니하며',
            '2 무례히 행하지 아니하며 자기의 유익을 구하지 아니하며 성내지 아니하며 악한 것을 생각하지 아니하며',
            '3 내가 사람의 방언과 천사의 말을 할지라도 사랑이 없으면 소리 나는 구리와 울리는 꽹과리가 되고',
            '4 내가 예언하는 능력이 있어 모든 비밀과 모든 지식을 알고 또 산을 옮길 만한 모든 믿음이 있을지라도',
            '5 사랑은 언제까지나 떨어지지 아니하되',
        ]
        chunks5 = partition_verses(v5_multi, kor_font_size=26)
        self.assertEqual(chunks5, [[0, 1, 2], [3, 4]])

        # 4. 첫 절이 짧은 1줄이고 두 번째 절이 긴 경우 (탄력적 상한으로 1슬라이드에 함께 배치)
        v_short_first = [
            '1 태초에 하나님이 천지를 창조하시니라',
            '2 땅이 혼돈하고 공허하며 흑암이 깊음 위에 있고 하나님의 영은 수면 위에 운행하시니라 하나님이 이르시되 빛이 있으라 하시니 빛이 있었고',
        ]
        self.assertEqual(partition_verses(v_short_first, kor_font_size=26), [[0, 1]])

        # 5. 단일 절
        self.assertEqual(partition_verses(['1 태초에 하나님이 천지를 창조하시니라']), [[0]])


if __name__ == '__main__':
    unittest.main()
