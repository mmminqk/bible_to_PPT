"""
tests/test_parser.py

pptx_generator.parser 모듈 단위 테스트:
- 성경 구절 파싱
- 세미콜론 다중 구절 및 책 상속
- 크로스 챕터
- 강조 구문 ('단어' 굵게/밑줄)
- 교독문 파싱 및 페어링
- 인용문 파싱
- split_items 분할
"""

import unittest
import os
import sys

# 프로젝트 루트 및 pptx_generator 경로 추가
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PG_DIR = os.path.join(ROOT_DIR, 'pptx_generator')
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
if PG_DIR not in sys.path:
    sys.path.insert(0, PG_DIR)

from pptx_generator.parser import (
    parse_emphasis_from_ref,
    parse_multi_refs_line,
    split_semicolon_refs,
    parse_passages,
    is_quote_body,
    strip_quote_tag,
    parse_quote_content,
    is_responsive_body,
    parse_responsive_item,
    split_items,
    BOOK_ABBR_MAP_KOR,
    BOOK_ABBR_MAP_ENG,
    BOOK_DB_KEY_MAP_ENG,
    ESV_DISPLAY_TO_RAW,
    ESV_RAW_TO_DISPLAY,
)


class TestParser(unittest.TestCase):

    def test_parse_emphasis_from_ref(self):
        # 굵게 서식
        clean, emphases = parse_emphasis_from_ref("창 1:1 '태초에' 굵게")
        self.assertEqual(clean, "창 1:1")
        self.assertEqual(len(emphases), 1)
        self.assertEqual(emphases[0]['text'], "태초에")
        self.assertEqual(emphases[0]['kind'], "bold")

        # 밑줄 서식
        clean, emphases = parse_emphasis_from_ref("요 3:16 '하나님이' 밑줄")
        self.assertEqual(clean, "요 3:16")
        self.assertEqual(len(emphases), 1)
        self.assertEqual(emphases[0]['text'], "하나님이")
        self.assertEqual(emphases[0]['kind'], "underline")

        # 복합 강조
        clean, emphases = parse_emphasis_from_ref("고전 13:4 '사랑은' 굵게 '온유하며' 밑줄")
        self.assertEqual(clean, "고전 13:4")
        self.assertEqual(len(emphases), 2)
        self.assertEqual(emphases[0]['text'], "사랑은")
        self.assertEqual(emphases[0]['kind'], "bold")
        self.assertEqual(emphases[1]['text'], "온유하며")
        self.assertEqual(emphases[1]['kind'], "underline")

    def test_split_semicolon_refs(self):
        # 앞선 책 이름 상속
        result = split_semicolon_refs("창 1:1; 1:3; 롬 8:28")
        self.assertEqual(result, ["창 1:1", "창 1:3", "롬 8:28"])

        # 장만 있는 경우
        result2 = split_semicolon_refs("시 23; 24")
        self.assertEqual(result2, ["시 23", "시 24"])

        # 세미콜론 내 강조 표기 보존
        result3 = split_semicolon_refs("창 1:1 '태초에' 굵게; 1:3 '빛이' 밑줄")
        self.assertEqual(result3, ["창 1:1 '태초에' 굵게", "창 1:3 '빛이' 밑줄"])

    def test_parse_multi_refs_line(self):
        input_text = """1. 창 1:1-3
2. 요 3:16
3. 시 23:1; 23:4
"""
        grouped = parse_multi_refs_line(input_text)
        self.assertEqual(len(grouped), 3)
        self.assertEqual(grouped[0], ["창 1:1-3"])
        self.assertEqual(grouped[1], ["요 3:16"])
        self.assertEqual(grouped[2], ["시 23:1; 23:4"])

    def test_quote_parsing(self):
        # 인용구 판별
        self.assertTrue(is_quote_body("<인용> C.S. 루이스 / 순전한 기독교"))
        self.assertTrue(is_quote_body("<인용구> 명언"))
        self.assertFalse(is_quote_body("창 1:1"))

        # 제목 및 본문 분리
        title, body, emph = parse_quote_content("C.S. 루이스 / 순전한 기독교 '믿음' 굵게")
        self.assertEqual(title, "C.S. 루이스")
        self.assertEqual(body, "순전한 기독교 믿음")
        self.assertEqual(len(emph), 1)
        self.assertEqual(emph[0]['text'], "믿음")
        self.assertEqual(emph[0]['kind'], "bold")

        # 슬래시 없는 인용문
        title_no_slash, body_no_slash, _ = parse_quote_content("항상 기뻐하라")
        self.assertEqual(title_no_slash, "")
        self.assertEqual(body_no_slash, "항상 기뻐하라")

    def test_responsive_parsing(self):
        # 교독문 판별
        self.assertTrue(is_responsive_body("<교독문> 시편 23편"))
        self.assertFalse(is_responsive_body("창 1:1"))

        text = """<교독문> 시편 23편
[인도] 여호와는 나의 목자시니 내게 부족함이 없으리로다
[회중] 그가 나를 푸른 풀밭에 누이시며 쉴 만한 물 가로 인도하시는도다
[인도] 내 영혼을 소생시키시고 자기 이름을 위하여 의의 길로 인도하시는도다
[회중] 내가 사망의 음침한 골짜기로 다닐지라도
[다함께] 내 평생에 선하심과 인자하심이 반드시 나를 따르리니
"""
        title, slides = parse_responsive_item(text)
        self.assertIn("시편 23편", title)
        # 인도+회중(1) + 인도+회중(2) + 다함께(3) = 총 3개 슬라이드
        self.assertEqual(len(slides), 3)
        self.assertIn("(인도)", slides[0])
        self.assertIn("(회중)", slides[0])
        self.assertIn("(다함께)", slides[2])

    def test_split_items(self):
        raw_text = """1. 창 1:1
2. <인용> 파스칼 / 팡세
3. <교독문> 시편 1편
[인도] 복 있는 사람은
[회중] 악인들의 꾀를 따르지 아니하며
"""
        items = split_items(raw_text)
        self.assertEqual(len(items), 3)
        self.assertEqual(items[0][0], 'verse')
        self.assertEqual(items[1][0], 'quote')
        self.assertEqual(items[2][0], 'responsive')

    def test_book_abbr_map_eng_natural_abbreviations(self):
        # 66권 전체 매핑 존재 확인
        self.assertEqual(len(BOOK_ABBR_MAP_ENG), 66)
        self.assertEqual(len(BOOK_DB_KEY_MAP_ENG), 66)

        # 주요 변경된 자연스러운 약어 검증
        self.assertEqual(BOOK_ABBR_MAP_ENG['출'], 'Exod')
        self.assertEqual(BOOK_ABBR_MAP_ENG['신'], 'Deut')
        self.assertEqual(BOOK_ABBR_MAP_ENG['수'], 'Josh')
        self.assertEqual(BOOK_ABBR_MAP_ENG['삿'], 'Judg')
        self.assertEqual(BOOK_ABBR_MAP_ENG['룻'], 'Ruth')
        self.assertEqual(BOOK_ABBR_MAP_ENG['삼상'], '1 Sam')
        self.assertEqual(BOOK_ABBR_MAP_ENG['삼하'], '2 Sam')
        self.assertEqual(BOOK_ABBR_MAP_ENG['왕상'], '1 Kgs')
        self.assertEqual(BOOK_ABBR_MAP_ENG['왕하'], '2 Kgs')
        self.assertEqual(BOOK_ABBR_MAP_ENG['대상'], '1 Chron')
        self.assertEqual(BOOK_ABBR_MAP_ENG['대하'], '2 Chron')
        self.assertEqual(BOOK_ABBR_MAP_ENG['스'], 'Ezra')
        self.assertEqual(BOOK_ABBR_MAP_ENG['에'], 'Esth')
        self.assertEqual(BOOK_ABBR_MAP_ENG['시'], 'Ps')
        self.assertEqual(BOOK_ABBR_MAP_ENG['잠'], 'Prov')
        self.assertEqual(BOOK_ABBR_MAP_ENG['전'], 'Eccl')
        self.assertEqual(BOOK_ABBR_MAP_ENG['아'], 'Song')
        self.assertEqual(BOOK_ABBR_MAP_ENG['겔'], 'Ezek')
        self.assertEqual(BOOK_ABBR_MAP_ENG['욜'], 'Joel')
        self.assertEqual(BOOK_ABBR_MAP_ENG['암'], 'Amos')
        self.assertEqual(BOOK_ABBR_MAP_ENG['욘'], 'Jonah')
        self.assertEqual(BOOK_ABBR_MAP_ENG['습'], 'Zeph')
        self.assertEqual(BOOK_ABBR_MAP_ENG['슥'], 'Zech')
        self.assertEqual(BOOK_ABBR_MAP_ENG['마'], 'Matt')
        self.assertEqual(BOOK_ABBR_MAP_ENG['막'], 'Mark')
        self.assertEqual(BOOK_ABBR_MAP_ENG['눅'], 'Luke')
        self.assertEqual(BOOK_ABBR_MAP_ENG['요'], 'John')
        self.assertEqual(BOOK_ABBR_MAP_ENG['행'], 'Acts')
        self.assertEqual(BOOK_ABBR_MAP_ENG['고전'], '1 Cor')
        self.assertEqual(BOOK_ABBR_MAP_ENG['고후'], '2 Cor')
        self.assertEqual(BOOK_ABBR_MAP_ENG['빌'], 'Phil')
        self.assertEqual(BOOK_ABBR_MAP_ENG['살전'], '1 Thess')
        self.assertEqual(BOOK_ABBR_MAP_ENG['살후'], '2 Thess')
        self.assertEqual(BOOK_ABBR_MAP_ENG['딤전'], '1 Tim')
        self.assertEqual(BOOK_ABBR_MAP_ENG['딤후'], '2 Tim')
        self.assertEqual(BOOK_ABBR_MAP_ENG['딛'], 'Titus')
        self.assertEqual(BOOK_ABBR_MAP_ENG['몬'], 'Philem')
        self.assertEqual(BOOK_ABBR_MAP_ENG['약'], 'James')
        self.assertEqual(BOOK_ABBR_MAP_ENG['벧전'], '1 Pet')
        self.assertEqual(BOOK_ABBR_MAP_ENG['벧후'], '2 Pet')
        self.assertEqual(BOOK_ABBR_MAP_ENG['요일'], '1 John')
        self.assertEqual(BOOK_ABBR_MAP_ENG['유'], 'Jude')

    def test_esv_display_and_raw_mappings(self):
        # Display -> Raw 변환
        self.assertEqual(ESV_DISPLAY_TO_RAW['1 Cor'], '1Co')
        self.assertEqual(ESV_DISPLAY_TO_RAW['John'], 'Joh')
        self.assertEqual(ESV_DISPLAY_TO_RAW['Ruth'], 'Rut')
        self.assertEqual(ESV_DISPLAY_TO_RAW['Joel'], 'Joe')
        self.assertEqual(ESV_DISPLAY_TO_RAW['Exod'], 'Exo')

        # Raw -> Display 변환
        self.assertEqual(ESV_RAW_TO_DISPLAY['1Co'], '1 Cor')
        self.assertEqual(ESV_RAW_TO_DISPLAY['Joh'], 'John')
        self.assertEqual(ESV_RAW_TO_DISPLAY['Rut'], 'Ruth')
        self.assertEqual(ESV_RAW_TO_DISPLAY['Joe'], 'Joel')
        self.assertEqual(ESV_RAW_TO_DISPLAY['Exo'], 'Exod')


if __name__ == '__main__':
    unittest.main()
