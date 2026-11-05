"""
pptx_generator.loader

성경 텍스트 DB(개역개정, ESV) 로드 및 캐싱,
구절 텍스트 추출, 슬라이드 글자수 기반 청킹 및 한/영 동기화 추출 모듈.
"""

import os
import sys
import re
import math
import pickle
from collections import defaultdict

try:
    from .constants import (
        EMPHASIS_PATTERN,
    )
    from .parser import (
        BOOK_ABBR_MAP_KOR,
        BOOK_ABBR_MAP_ENG,
        BOOK_DB_KEY_MAP_ENG,
        ESV_DISPLAY_TO_RAW,
        ESV_RAW_TO_DISPLAY,
        REF_PATTERN,
        REF_PATTERN_CHAP,
        CROSS_CHAP_PATTERN,
        parse_emphasis_from_ref,
        parse_passages,
        expand_ref_group,
    )
except (ImportError, ValueError):
    from constants import (
        EMPHASIS_PATTERN,
    )
    from parser import (
        BOOK_ABBR_MAP_KOR,
        BOOK_ABBR_MAP_ENG,
        BOOK_DB_KEY_MAP_ENG,
        ESV_DISPLAY_TO_RAW,
        ESV_RAW_TO_DISPLAY,
        REF_PATTERN,
        REF_PATTERN_CHAP,
        CROSS_CHAP_PATTERN,
        parse_emphasis_from_ref,
        parse_passages,
        expand_ref_group,
    )


# ─── 경로 유틸리티 ───────────────────────────────────────────────────────────
def resource_path(relative_path):
    """PyInstaller 환경과 일반 환경 모두 지원하는 리소스 경로 반환."""
    base = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    return os.path.join(base, relative_path)


def absolute_path(file_path):
    """절대경로이면 그대로, 아니면 현재 경로 기준으로 반환."""
    return file_path if os.path.isabs(file_path) else os.path.abspath(file_path)


# ─── pkl 캐시 유틸리티 ──────────────────────────────────────────────────────
def _is_cache_valid(pkl_path, *source_paths):
    """pkl 파일이 존재하고 모든 소스 파일보다 최신이면 True."""
    if not os.path.exists(pkl_path):
        return False
    pkl_mtime = os.path.getmtime(pkl_path)
    return all(os.path.getmtime(p) <= pkl_mtime for p in source_paths if os.path.exists(p))


def _load_pkl(pkl_path):
    with open(pkl_path, 'rb') as f:
        return pickle.load(f)


def _save_pkl(pkl_path, data):
    with open(pkl_path, 'wb') as f:
        pickle.dump(data, f)


# ─── 성경 데이터 로딩 ────────────────────────────────────────────────────────
def read_files_in_directory(directory):
    """디렉터리 내 .txt 파일을 순서대로 읽어 내용 리스트 반환."""
    contents = []
    for filename in sorted(os.listdir(directory)):
        if filename.endswith('.txt'):
            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as f:
                contents.append(f.read())
    return contents


def split_and_format_verses(bible_dict):
    """bible_dict(책이름→원문 텍스트)를 {책: [[절문자열, ...], ...]} 구조로 변환."""
    result = {}
    for book, raw in bible_dict.items():
        chapter_map = defaultdict(list)
        for line in raw.splitlines():
            m = re.match(r'[가-힣]+(\d+):(\d+)\s+(.*)', line)
            if m:
                chapter_map[m.group(1)].append(f"{m.group(2)} {m.group(3)}")
            elif re.match(r'^\d+:\d+\s+', line):
                m2 = re.match(r'^(\d+):(\d+)\s+(.*)', line)
                if m2:
                    chapter_map[m2.group(1)].append(f"{m2.group(2)} {m2.group(3)}")
        result[book] = [verses for _, verses in sorted(chapter_map.items(), key=lambda x: int(x[0]))]
    return result


def load_kor_bible(directory, bible_books):
    """
    개역개정 성경 로드.
    - PyInstaller 환경: sys._MEIPASS/bible_cache/_cache_kor.pkl 직접 로드
    - 일반 환경: directory/_cache_kor.pkl 캐시 사용 (txt 수정 시 재파싱)
    """
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(sys._MEIPASS, 'bible_cache', '_cache_kor.pkl')
        if os.path.exists(bundled):
            return _load_pkl(bundled)

    pkl_path = os.path.join(directory, '_cache_kor.pkl')
    txt_files = [
        os.path.join(directory, f)
        for f in sorted(os.listdir(directory))
        if f.endswith('.txt')
    ]
    if _is_cache_valid(pkl_path, *txt_files):
        return _load_pkl(pkl_path)

    texts = read_files_in_directory(directory)
    bible_dict = dict(zip(bible_books, texts))
    formatted = split_and_format_verses(bible_dict)
    try:
        _save_pkl(pkl_path, formatted)
    except Exception:
        pass
    return formatted


def _ensure_esv_aliases(data):
    """ESV 데이터 딕셔너리에 표시용 약어 키(예: '1 Cor', 'John', 'Ruth')가 없으면 raw 키로부터 채워넣는다."""
    if not isinstance(data, dict):
        return
    for raw_key, disp_key in ESV_RAW_TO_DISPLAY.items():
        if raw_key in data and disp_key not in data:
            data[disp_key] = data[raw_key]


def _get_chapter_data(data, book_name):
    """
    data 딕셔너리에서 book_name에 해당하는 장 데이터 리스트를 반환.
    표시용 약어('1 Cor', 'John') 및 raw 식별자('1Co', 'Joh') 모두 안전하게 조회.
    """
    if not data or not book_name:
        return []
    res = data.get(book_name)
    if res is not None:
        return res
    raw_key = ESV_DISPLAY_TO_RAW.get(book_name)
    if raw_key and raw_key in data:
        return data[raw_key]
    return []


def parse_scripture_file(file_path):
    """
    ESV 성경 텍스트 파일 로드.
    - PyInstaller 환경: sys._MEIPASS/bible_cache/_cache_esv.pkl 로드
    - 일반 환경: 같은 폴더의 _cache_esv.pkl 캐시 사용
    """
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(sys._MEIPASS, 'bible_cache', '_cache_esv.pkl')
        if os.path.exists(bundled):
            cached = _load_pkl(bundled)
            _ensure_esv_aliases(cached)
            return cached

    pkl_path = os.path.join(os.path.dirname(file_path), '_cache_esv.pkl')
    if _is_cache_valid(pkl_path, file_path):
        cached = _load_pkl(pkl_path)
        _ensure_esv_aliases(cached)
        return cached

    pattern = re.compile(r'^([A-Za-z0-9]+\.?)\s+(\d+):(\d+)\s+(.*)')
    raw = defaultdict(lambda: defaultdict(list))
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                book, chap, verse, text = m.groups()
                raw[book][int(chap)].append(f"{verse} {text.strip()}")

    result = {
        book: [chapters.get(i, []) for i in range(1, max(chapters) + 1)]
        for book, chapters in raw.items()
    }
    _ensure_esv_aliases(result)
    try:
        _save_pkl(pkl_path, result)
    except Exception:
        pass
    return result


# ─── 구절 조회 내부 헬퍼 ───────────────────────────────────────────────────
def _resolve_verse_nums(verses_str):
    """'1-3' 또는 '1,3' 또는 '1' 형태의 절 범위를 숫자 리스트와 라벨 접미사로 변환."""
    verses_str = verses_str.strip()
    try:
        if '-' in verses_str:
            start, end = map(int, verses_str.split('-', 1))
            return list(range(start, end + 1)), f"{start}-{end}"
        elif ',' in verses_str:
            nums = [int(v.strip()) for v in verses_str.split(',')]
            return nums, ','.join(map(str, nums))
        else:
            v = int(verses_str)
            return [v], str(v)
    except ValueError:
        raise ValueError(f"절 번호를 파싱할 수 없습니다: '{verses_str}'")


def lookup_cross_chapter_verses(bible_data, book_name, ch1, v1, ch2, v2):
    """
    장을 넘어가는 범위(예: 창 1:31-2:3)의 구절을 장별로 분리하여
    [(label1, texts1), (label2, texts2), ...] 형식으로 반환.
    """
    results = []
    for ch in range(int(ch1), int(ch2) + 1):
        chap_idx = ch - 1
        chap_data = _get_chapter_data(bible_data, book_name)
        if chap_idx >= len(chap_data) or not chap_data[chap_idx]:
            continue
        verses_in_chap = chap_data[chap_idx]

        if ch == int(ch1) and ch == int(ch2):
            start_v, end_v = int(v1), int(v2)
        elif ch == int(ch1):
            start_v, end_v = int(v1), len(verses_in_chap)
        elif ch == int(ch2):
            start_v, end_v = 1, int(v2)
        else:
            start_v, end_v = 1, len(verses_in_chap)

        texts = []
        for v in range(start_v, min(end_v, len(verses_in_chap)) + 1):
            texts.append(verses_in_chap[v - 1])
        if texts:
            label_verses = str(start_v) if start_v == end_v else f"{start_v}-{end_v}"
            label = f"{book_name} {ch}:{label_verses}\n"
            results.append((label, texts))
    return results


def _lookup_verses(data, abbr, chapter, verses_str, book_map):
    book = book_map.get(abbr, abbr)
    chapter_idx = int(chapter) - 1
    chapter_data = _get_chapter_data(data, book)
    if chapter_idx >= len(chapter_data):
        return None

    chapter_content = chapter_data[chapter_idx]
    verse_nums, label_suffix = _resolve_verse_nums(verses_str)
    texts = [chapter_content[v - 1] for v in verse_nums if v <= len(chapter_content)]
    if not texts:
        return None

    return f"{book} {chapter}:{label_suffix}\n", texts


def _lookup_whole_chapter(data, abbr, chapter, book_map):
    """장 전체 구절을 (label, [절텍스트]) 형식으로 반환."""
    book = book_map.get(abbr, abbr)
    chapter_idx = int(chapter) - 1
    chapter_data = _get_chapter_data(data, book)
    if chapter_idx >= len(chapter_data):
        return []
    verses = chapter_data[chapter_idx]
    if not verses:
        return []
    label = f"{book} {chapter}:1-{len(verses)}\n"
    return [(label, verses)]


def _extract_ref(data, ref, book_map):
    """
    단일 구절 참조(ref)에서 [(label, [절텍스트]), ...] 목록을 반환.
    '책 장:절', '책 장:절범위', '책 장' (장 전체), 장 넘김 범위 모두 지원.
    """
    clean_ref, _ = parse_emphasis_from_ref(ref)

    if ';' in clean_ref:
        results = []
        for p in parse_passages(clean_ref):
            m_cross = CROSS_CHAP_PATTERN.match(p.strip())
            if m_cross:
                book, ch1, v1, ch2, v2 = m_cross.groups()
                real_book = book_map.get(book, book)
                results.extend(lookup_cross_chapter_verses(data, real_book, ch1, v1, ch2, v2))
                continue
            m = REF_PATTERN.match(p)
            if m:
                item = _lookup_verses(data, *m.groups(), book_map)
                if item:
                    results.append(item)
                continue
            m_chap = REF_PATTERN_CHAP.match(p.strip())
            if m_chap:
                results.extend(_lookup_whole_chapter(data, m_chap.group(1), m_chap.group(2), book_map))
        return results

    # 장 넘김 형식
    m_cross = CROSS_CHAP_PATTERN.match(clean_ref.strip())
    if m_cross:
        book, ch1, v1, ch2, v2 = m_cross.groups()
        real_book = book_map.get(book, book)
        return lookup_cross_chapter_verses(data, real_book, ch1, v1, ch2, v2)

    # 책+장+절 형식
    m = REF_PATTERN.match(clean_ref.strip())
    if m:
        item = _lookup_verses(data, *m.groups(), book_map)
        return [item] if item else []

    # 책+장 형식 (장 전체)
    m_chap = REF_PATTERN_CHAP.match(clean_ref.strip())
    if m_chap:
        return _lookup_whole_chapter(data, m_chap.group(1), m_chap.group(2), book_map)

    return []


# ─── 슬라이드 텍스트박스 물리 치수 및 줄바꿈/높이 기반 청킹 ─────────────────────
# template.pptx (13.333" x 7.500") 기준:
# - kor_body: top=0.45" (32.4pt), width=7.93" (571.0pt, 좌우 여백 제외 유효 폭 567.0pt)
# - eng_body: top=4.37" (314.6pt), width=7.93" (영문 단어 줄바꿈 여유 폭 550.0pt)
# - kor_body ~ eng_body 간 수직 가용 거리: 3.92" (282.2pt)
# - eng_body ~ 슬라이드 하단(7.50") 간 수직 가용 거리: 3.13" (225.4pt)
KOR_BASE_CAPACITY = 200  # 한글 26pt 기준 약 180~200자 (최대 7줄)
ENG_BASE_CAPACITY = 400  # 영어 18pt 기준 약 360~400자 (최대 8줄)

# PowerPoint 실제 렌더링 줄바꿈 유효 폭 (창세기 1장 실측 캘리브레이션:
# 한글 26pt 기준 위첨자 포함 한 줄 약 20~21음절 + 공백 5~6개 = 548pt에서 줄바꿈 발생)
KOR_LINE_WIDTH_PT = 548.0
ENG_LINE_WIDTH_PT = 545.0

# PowerPoint 실제 수직 줄간격(line_spacing=1.15 -> 글리프 기본 높이 1.22*fs * 1.15 = 1.40*fs/줄) 기준:
# - 한글 26pt: 7줄 = 257~266pt (영어 박스와 겹치지 않는 최대 줄 수), 8줄 = 293.5pt+ (영어 박스와 침범/오버랩 발생)
# - 영어 18pt: 8줄 = 205~211pt (하단 여백 내 최대 줄 수), 9줄 = 233.6pt+ (슬라이드 하단 밖으로 넘침)
KOR_TARGET_HEIGHT_PT  = 264.0  # 평상시 목표 채움 높이 (한글 26pt 기준 최대 7줄)
KOR_CEILING_HEIGHT_PT = 268.0  # 탄력적 물리 상한 (7줄 5단락까지 허용, 8줄 이상은 원천 차단)

ENG_TARGET_HEIGHT_PT  = 209.0  # 평상시 영문 목표 채움 높이 (영어 18pt 기준 최대 8줄)
ENG_CEILING_HEIGHT_PT = 214.0  # 탄력적 물리 상한 (8줄 4단락까지 허용, 9줄 이상은 원천 차단)


def estimate_slide_capacity(font_size, is_english=False):
    """폰트 크기에 따른 슬라이드 본문 용량(글자 수) 추정."""
    base_cap = ENG_BASE_CAPACITY if is_english else KOR_BASE_CAPACITY
    base_size = 18 if is_english else 26
    if not font_size or font_size <= 0:
        font_size = base_size
    return round(base_cap * (base_size / font_size) ** 2)


def _char_em_width(ch):
    """나눔스퀘어 네오(Bold/Regular) 실측 글리프 폭(em 비율) 반환."""
    o = ord(ch)
    if ch == ' ':
        return 0.246
    if ch in '.,!?;:\'"()[]{}<>-·':
        return 0.258
    if 0xAC00 <= o <= 0xD7A3 or 0x3130 <= o <= 0x318F or 0x4E00 <= o <= 0x9FFF:
        return 0.935
    if 'A' <= ch <= 'Z':
        return 0.640
    if 'a' <= ch <= 'z':
        return 0.520
    if '0' <= ch <= '9':
        return 0.477
    return 0.520


def estimate_verse_lines(verse_text, font_size=26, is_english=False):
    """
    단일 절(단락)이 PowerPoint 텍스트박스에서 실제로 차지하는 줄(line) 수를 계산.
    - 절 번호("4 ")는 generator._fill_slide에서 위첨자("⁴ ")로 변환되므로 위첨자 폭 적용
    - 한글은 글자 단위 줄바꿈(eaLnBrk=1), 영어는 단어(공백) 단위 줄바꿈 시뮬레이션
    """
    if not verse_text or not verse_text.strip():
        return 0
    if not font_size or font_size <= 0:
        font_size = 18 if is_english else 26

    s = verse_text.strip()
    parts = s.split(' ', 1)
    if len(parts) == 2 and parts[0].isdigit():
        num_str, body = parts[0], parts[1]
        prefix_w = (len(num_str) * 0.423 + 0.246) * font_size
    else:
        body = s
        prefix_w = 0.0

    if not is_english:
        total_w = prefix_w + sum(_char_em_width(c) for c in body) * font_size
        return max(1, math.ceil(total_w / KOR_LINE_WIDTH_PT))
    else:
        total_w = prefix_w + sum(_char_em_width(c) for c in body) * font_size
        char_lines = max(1, math.ceil(total_w / ENG_LINE_WIDTH_PT))
        words = body.split(' ')
        word_lines = 1
        cur_w = prefix_w
        space_w = 0.246 * font_size
        for w in words:
            ww = sum(_char_em_width(c) for c in w) * font_size
            if cur_w <= prefix_w and word_lines == 1:
                cur_w += ww
            elif cur_w + space_w + ww <= ENG_LINE_WIDTH_PT + 10.0:
                cur_w += space_w + ww
            else:
                word_lines += 1
                cur_w = ww
        return max(char_lines, word_lines)


def estimate_chunk_height_pt(line_counts, font_size=26):
    """
    슬라이드에 배치될 절들의 줄 수 리스트(line_counts)로부터
    PowerPoint 텍스트박스에서 차지하는 실제 수직 높이(pt)를 계산.
    - 상하 내부 여백(margin_top=2pt, margin_bottom=2pt): 4.0pt
    - PowerPoint의 단일 줄 기본 높이(WinAscent+WinDescent ≈ 1.22*fs)에
      줄간격(line_spacing=1.15) 적용 시 줄당 수직 증가폭 = 1.40*fs
    - 단락 간격(space_after=3pt): (단락 수 - 1) * 3.0pt
    """
    if not line_counts:
        return 0.0
    total_lines = sum(line_counts)
    if total_lines == 0:
        return 0.0
    if not font_size or font_size <= 0:
        font_size = 26
    n_paras = len(line_counts)
    lines_h = font_size * (1.22 + 1.40 * (total_lines - 1))
    return 4.0 + lines_h + max(0, n_paras - 1) * 3.0


def partition_verses(k_texts, e_texts=None, kor_cap=None, eng_cap=None, kor_font_size=26, eng_font_size=18):
    """
    구절 리스트(한글 및/또는 영어)를 실제 텍스트박스 줄바꿈 및 수직 높이(pt) 기반으로 분할.

    핵심 설계 원칙:
    1) 공백 최소화 및 슬라이드 수 절감 (Dense Height Packing):
       글자 수를 인위적으로 균등 배분하느라 앞 슬라이드를 비우지 않고,
       한글 텍스트박스와 영어 텍스트박스 사이의 가용 수직 높이(KOR_TARGET_HEIGHT_PT / ENG_TARGET_HEIGHT_PT)까지
       각 슬라이드를 밀도 있게 채워 전체 슬라이드 수를 최소화합니다.
    2) 탄력적 상한 흡수 (Elastic Ceiling Absorption):
       마지막에 짧은 1절이 남거나(is_last_verse), 첫 절이 짧은데 다음 절이 들어올 때(cur_is_single_short)
       일반 목표 높이를 살짝 넘더라도 텍스트박스가 겹치지 않는 물리적 상한(KOR_CEILING_HEIGHT_PT / ENG_CEILING_HEIGHT_PT)
       이내라면 현재 슬라이드에 그대로 흡수하여 불필요한 추가 슬라이드 생성을 원천 차단합니다.
    3) 불가피한 분할 시 마지막 고아 절 보정 (Last-Slide Orphan Guard):
       물리적 상한을 초과하여 새 슬라이드가 불가피할 때에만, 마지막 슬라이드에 짧은 1절(<=2줄)만 남고
       직전 슬라이드에 3절 이상이 있다면 직전 슬라이드의 마지막 1절을 넘겨 고아 슬라이드를 방지합니다.

    반환값: [[0, 1, 2], [3, 4], ...] (각 슬라이드에 포함될 절 인덱스 목록)
    """
    n = max(len(k_texts) if k_texts else 0, len(e_texts) if e_texts else 0)
    if n == 0:
        return []
    if n == 1:
        return [[0]]

    has_k = bool(k_texts)
    has_e = bool(e_texts)

    k_fs = float(kor_font_size) if (kor_font_size and kor_font_size > 0) else 26.0
    e_fs = float(eng_font_size) if (eng_font_size and eng_font_size > 0) else 18.0

    # kor_cap / eng_cap이 명시적으로 전달된 경우(테스트 또는 커스텀 용량 제어), 비례 스케일 반영
    k_scale = (kor_cap / KOR_BASE_CAPACITY) if (kor_cap is not None and kor_font_size == 26) else 1.0
    e_scale = (eng_cap / ENG_BASE_CAPACITY) if (eng_cap is not None and eng_font_size == 18) else 1.0

    k_lines = [estimate_verse_lines(k_texts[i], k_fs, False) if (has_k and i < len(k_texts)) else 0 for i in range(n)]
    e_lines = [estimate_verse_lines(e_texts[i], e_fs, True) if (has_e and i < len(e_texts)) else 0 for i in range(n)]

    def fits(indices, use_ceiling=False):
        k_lim = (KOR_CEILING_HEIGHT_PT if use_ceiling else KOR_TARGET_HEIGHT_PT) * k_scale
        e_lim = (ENG_CEILING_HEIGHT_PT if use_ceiling else ENG_TARGET_HEIGHT_PT) * e_scale
        if has_k:
            kh = estimate_chunk_height_pt([k_lines[i] for i in indices], k_fs)
            if kh > k_lim:
                return False
        if has_e:
            eh = estimate_chunk_height_pt([e_lines[i] for i in indices], e_fs)
            if eh > e_lim:
                return False
        return True

    chunks = []
    cur = []
    i = 0
    while i < n:
        candidate = cur + [i]
        if not cur or fits(candidate, use_ceiling=False):
            cur.append(i)
            i += 1
        else:
            cur_is_single_short = (
                len(cur) == 1
                and (not has_k or k_lines[cur[0]] <= 2)
                and (not has_e or e_lines[cur[0]] <= 2)
            )
            is_last_verse = (n - i == 1)
            if (is_last_verse or cur_is_single_short) and fits(candidate, use_ceiling=True):
                cur.append(i)
                i += 1
            else:
                chunks.append(cur)
                cur = [i]
                i += 1
    if cur:
        chunks.append(cur)

    # 사후 보정: 마지막 슬라이드에 1절만 남았을 때
    if len(chunks) >= 2 and len(chunks[-1]) == 1:
        last_idx = chunks[-1][0]
        # 1순위: 직전 슬라이드의 물리 상한(ceiling) 내에 흡수 가능하면 병합하여 슬라이드 수 감소
        if fits(chunks[-2] + [last_idx], use_ceiling=True):
            chunks[-2].append(last_idx)
            chunks.pop()
        # 2순위: 물리 상한을 넘어 병합이 불가능하고, 마지막 절이 단독(<=3줄)이며
        # 직전 슬라이드에 3절 이상이 있어 앞 슬라이드를 비우지 않고도 1절을 나눌 수 있는 경우
        elif len(chunks[-2]) >= 3:
            is_short_orphan = (
                (not has_k or k_lines[last_idx] <= 3)
                and (not has_e or e_lines[last_idx] <= 3)
            )
            if is_short_orphan:
                moved = chunks[-2][-1]
                if fits([moved, last_idx], use_ceiling=False):
                    chunks[-2].pop()
                    chunks[-1].insert(0, moved)

    return chunks


def _split_single_verse_sentences(label, verse, emphases, capacity):
    """단일 긴 절이 슬라이드 용량을 초과할 때 문장 단위로 분할하여 결과 리스트 반환."""
    tokens = verse.split(' ', 1)
    if len(tokens) == 2 and tokens[0].isdigit():
        verse_num, body = tokens[0], tokens[1]
    else:
        verse_num, body = '', verse

    sentences = re.split(r'(?<=[.!?。])\s+', body)
    if len(sentences) >= 2:
        chunks = []
        current_chunk = []
        char_count = 0
        for sent in sentences:
            sent_len = len(sent)
            if current_chunk and char_count + sent_len > capacity:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sent]
                char_count = sent_len
            else:
                current_chunk.append(sent)
                char_count += sent_len
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        if len(chunks) > 1:
            res = []
            for chunk_text in chunks:
                full = f"{verse_num} {chunk_text}" if verse_num else chunk_text
                res.append((label, full, emphases))
            return res
    return [(label, verse, emphases)]


def _chunk_and_append(result, label, merged_verses, emphases, font_size=None, is_english=False):
    """실제 줄바꿈 및 텍스트박스 수직 높이 기반으로 슬라이드를 분할하여 result에 추가."""
    default_fs = 18 if is_english else 26
    eff_fs = font_size if (font_size and font_size > 0) else default_fs
    capacity = estimate_slide_capacity(eff_fs, is_english=is_english)

    if not merged_verses:
        return

    # 절이 2개 이상일 때 높이 기반 절 분할 시도
    if len(merged_verses) >= 2:
        if is_english:
            chunk_indices = partition_verses(None, merged_verses, eng_font_size=eff_fs)
        else:
            chunk_indices = partition_verses(merged_verses, None, kor_font_size=eff_fs)
        if len(chunk_indices) > 1:
            m_single_chap = re.match(r'^([^\n:]+\s+\d+):(\d+)-(\d+)', label)
            for chunk_idx in chunk_indices:
                chunk = [merged_verses[i] for i in chunk_idx]
                if m_single_chap:
                    v_start = chunk[0].split()[0]
                    v_end   = chunk[-1].split()[0]
                    chunk_label = f"{m_single_chap.group(1)}:{v_start}\n" if v_start == v_end else f"{m_single_chap.group(1)}:{v_start}-{v_end}\n"
                else:
                    chunk_label = label

                # 청크 내에 단일 절인데 capacity를 초과하는 경우 문장 단위 분할 적용
                if len(chunk) == 1 and len(chunk[0]) > capacity:
                    result.extend(_split_single_verse_sentences(chunk_label, chunk[0], emphases, capacity))
                else:
                    result.append((chunk_label, '\n'.join(chunk), emphases))
            return

    # 단일 절이거나 1개 슬라이드에 다 들어가는 경우
    joined = '\n'.join(merged_verses)
    if len(merged_verses) == 1 and len(joined) > capacity:
        result.extend(_split_single_verse_sentences(label, joined, emphases, capacity))
    else:
        result.append((label, joined, emphases))


def _extract_passages_grouped_impl(data, grouped_refs, book_map, *, allow_quote=False, font_size=None, is_english=False):
    """구절 그룹 추출 공통 구현."""
    result = []
    for ref_group in grouped_refs:
        for group in expand_ref_group(ref_group):
            for ref in group:
                if allow_quote and ref.startswith('<인용구>'):
                    result.append(('<인용구>\n', ref[5:], []))
                    continue
                _, emphases = parse_emphasis_from_ref(ref)
                for label, texts in _extract_ref(data, ref, book_map):
                    _chunk_and_append(result, label, texts, emphases, font_size=font_size, is_english=is_english)
    return result


def extract_passages_grouped(data, grouped_refs, font_size=None):
    """개역개정 구절 그룹 추출."""
    return _extract_passages_grouped_impl(data, grouped_refs, BOOK_ABBR_MAP_KOR, allow_quote=True, font_size=font_size, is_english=False)


def extract_passages_grouped_eng(data, grouped_refs, font_size=None):
    """ESV 구절 그룹 추출."""
    return _extract_passages_grouped_impl(data, grouped_refs, BOOK_ABBR_MAP_ENG, font_size=font_size, is_english=True)


def extract_passages_synchronized(kor_data, eng_data, grouped_refs, kor_font_size=26, eng_font_size=18):
    """
    한/영 구절을 동일한 절 경계로 동기화하여 추출.
    어느 한 쪽 언어라도 슬라이드 텍스트박스 높이를 초과하면 동일한 절에서 슬라이드를 분할한다.
    반환: (kor_entries, eng_entries)
    """
    if not kor_data and not eng_data:
        return [], []
    if not kor_data:
        return [], extract_passages_grouped_eng(eng_data, grouped_refs, font_size=eng_font_size)
    if not eng_data:
        return extract_passages_grouped(kor_data, grouped_refs, font_size=kor_font_size), []

    k_fs = kor_font_size if (kor_font_size and kor_font_size > 0) else 26
    e_fs = eng_font_size if (eng_font_size and eng_font_size > 0) else 18

    kor_result, eng_result = [], []

    for ref_group in grouped_refs:
        for group in expand_ref_group(ref_group):
            for ref in group:
                if ref.startswith('<인용구>'):
                    kor_result.append(('<인용구>\n', ref[5:], []))
                    eng_result.append(('', '', []))
                    continue

                _, emphases = parse_emphasis_from_ref(ref)
                k_items = _extract_ref(kor_data, ref, BOOK_ABBR_MAP_KOR)
                e_items = _extract_ref(eng_data, ref, BOOK_ABBR_MAP_ENG)

                num_items = max(len(k_items), len(e_items))
                for idx in range(num_items):
                    k_label, k_texts = k_items[idx] if idx < len(k_items) and k_items[idx] else ('', [])
                    e_label, e_texts = e_items[idx] if idx < len(e_items) and e_items[idx] else ('', [])

                    n_verses = max(len(k_texts), len(e_texts))
                    if n_verses == 0:
                        continue

                    # 실제 줄바꿈/수직 높이 기반 절 인덱스 분할 (공백 최소화 및 탄력적 고아 절 흡수)
                    k_list = [k_texts[i] if i < len(k_texts) else '' for i in range(n_verses)]
                    e_list = [e_texts[i] if i < len(e_texts) else '' for i in range(n_verses)]
                    chunks = partition_verses(k_list, e_list, kor_font_size=k_fs, eng_font_size=e_fs)

                    for chunk_indices in chunks:
                        k_chunk = [k_texts[i] for i in chunk_indices if i < len(k_texts)]
                        e_chunk = [e_texts[i] for i in chunk_indices if i < len(e_texts)]

                        if len(chunks) > 1:
                            m_k = re.match(r'^([^\n:]+\s+\d+):(\d+)-(\d+)', k_label)
                            if m_k and k_chunk:
                                vs_k = k_chunk[0].split()[0]
                                ve_k = k_chunk[-1].split()[0]
                                actual_k_label = f"{m_k.group(1)}:{vs_k}\n" if vs_k == ve_k else f"{m_k.group(1)}:{vs_k}-{ve_k}\n"
                            else:
                                actual_k_label = k_label

                            m_e = re.match(r'^([^\n:]+\s+\d+):(\d+)-(\d+)', e_label)
                            if m_e and e_chunk:
                                vs_e = e_chunk[0].split()[0]
                                ve_e = e_chunk[-1].split()[0]
                                actual_e_label = f"{m_e.group(1)}:{vs_e}\n" if vs_e == ve_e else f"{m_e.group(1)}:{vs_e}-{ve_e}\n"
                            else:
                                actual_e_label = e_label
                        else:
                            actual_k_label = k_label
                            actual_e_label = e_label

                        kor_result.append((actual_k_label, '\n'.join(k_chunk), emphases))
                        eng_result.append((actual_e_label, '\n'.join(e_chunk), emphases))

    return kor_result, eng_result


# ─── 청킹 구절 주소 통합 헬퍼 ─────────────────────────────────────────────────
def should_unify_chunk(ref_group, n):
    """단일 ref + 세미콜론 없음 + 2개 이상 슬라이드로 분할된 경우 청킹으로 판단."""
    if n <= 1 or len(ref_group) != 1:
        return False
    clean = EMPHASIS_PATTERN.sub('', ref_group[0]).strip()
    return ';' not in clean and '\t' not in clean


def merge_labels(first_label, last_label):
    """
    '요한계시록 21:1-3' + '요한계시록 21:4' → '요한계시록 21:1-4'
    '창세기 1:1-31' + '창세기 2:1-3' → '창세기 1:1-2:3'
    """
    fl = first_label.strip()
    ll = last_label.strip()
    if fl == ll:
        return fl

    m1 = re.match(r'^(.*?)\s+(\d+):(\d+)(?:-(\d+)(?::(\d+))?)?$', fl)
    m2 = re.match(r'^(.*?)\s+(\d+):(\d+)(?:-(\d+)(?::(\d+))?)?$', ll)

    if m1 and m2 and m1.group(1) == m2.group(1):
        book = m1.group(1)
        ch1  = m1.group(2)
        v1   = m1.group(3)

        if m2.group(5):
            ch2 = m2.group(4)
            v2  = m2.group(5)
        elif m2.group(4):
            ch2 = m2.group(2)
            v2  = m2.group(4)
        else:
            ch2 = m2.group(2)
            v2  = m2.group(3)

        if ch1 == ch2:
            return f"{book} {ch1}:{v1}-{v2}"
        else:
            return f"{book} {ch1}:{v1}-{ch2}:{v2}"
    return fl


def extract_with_canonical_labels(kor_data, eng_data, grouped_refs, kor_font_size=None, eng_font_size=None):
    """
    grouped_refs를 순회하며 구절을 추출한다.
    단일 구절의 범위가 슬라이드 용량을 초과해 여러 장으로 청킹된 경우
    청크 슬라이드들의 주소 라벨을 원래의 전체 범위로 통일한다.
    """
    kor_entries, eng_entries = [], []

    for ref_group in grouped_refs:
        expanded_groups = expand_ref_group(ref_group)

        for single_group in expanded_groups:
            grp_kor, grp_eng = extract_passages_synchronized(
                kor_data, eng_data, [single_group],
                kor_font_size=kor_font_size or 26,
                eng_font_size=eng_font_size or 18
            )

            n = len(grp_kor) if grp_kor else len(grp_eng)

            if should_unify_chunk(single_group, n):
                if grp_kor:
                    canonical_kor = merge_labels(grp_kor[0][0], grp_kor[-1][0])
                    grp_kor = [(canonical_kor, v, e) for _, v, e in grp_kor]
                if grp_eng:
                    canonical_eng = merge_labels(grp_eng[0][0], grp_eng[-1][0])
                    grp_eng = [(canonical_eng, v, e) for _, v, e in grp_eng]
            elif len(single_group) == 1 and n == 1:
                if grp_kor:
                    grp_kor = [(lbl.strip(), v, e) for lbl, v, e in grp_kor]
                if grp_eng:
                    grp_eng = [(lbl.strip(), v, e) for lbl, v, e in grp_eng]

            kor_entries.extend(grp_kor)
            eng_entries.extend(grp_eng)

    return kor_entries, eng_entries
