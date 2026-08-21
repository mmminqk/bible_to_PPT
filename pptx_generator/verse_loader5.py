import os
import re
import pickle
from collections import defaultdict
import sys

"""
exe 빌드 전 반드시 먼저 실행:
    python build_pkl.py

exe 빌드:
    pyinstaller --noconfirm --onefile \
        --add-data "text_DB/개역개정-text/_cache_kor.pkl;bible_cache" \
        --add-data "text_DB/ESV-text/_cache_esv.pkl;bible_cache" \
        --add-data "pptx_template/template.pptx;pptx_template" \
        gui.py
"""

# 개역개정 성경 매핑
book_abbr_map = {
    '창': '창세기', '출': '출애굽기', '레': '레위기', '민': '민수기', '신': '신명기',
    '수': '여호수아', '삿': '사사기', '룻': '룻기', '삼상': '사무엘상', '삼하': '사무엘하',
    '왕상': '열왕기상', '왕하': '열왕기하', '대상': '역대상', '대하': '역대하', '스': '에스라',
    '느': '느헤미야', '에': '에스더', '욥': '욥기', '시': '시편', '잠': '잠언',
    '전': '전도서', '아': '아가', '사': '이사야', '렘': '예레미야', '애': '예레미야애가',
    '겔': '에스겔', '단': '다니엘', '호': '호세아', '욜': '요엘', '암': '아모스',
    '옵': '오바댜', '욘': '요나', '미': '미가', '나': '나훔', '합': '하박국',
    '습': '스바냐', '학': '학개', '슥': '스가랴', '말': '말라기', '마': '마태복음',
    '막': '마가복음', '눅': '누가복음', '요': '요한복음', '행': '사도행전', '롬': '로마서',
    '고전': '고린도전서', '고후': '고린도후서', '갈': '갈라디아서', '엡': '에베소서',
    '빌': '빌립보서', '골': '골로새서', '살전': '데살로니가전서', '살후': '데살로니가후서',
    '딤전': '디모데전서', '딤후': '디모데후서', '딛': '디도서', '몬': '빌레몬서',
    '히': '히브리서', '약': '야고보서', '벧전': '베드로전서', '벧후': '베드로후서',
    '요일': '요한일서', '요이': '요한이서', '요삼': '요한삼서', '유': '유다서', '계': '요한계시록'
}

# ESV 성경 매핑
bible_book_abbreviations = {
    '창': 'Gen', '출': 'Exo', '레': 'Lev', '민': 'Num', '신': 'Deu',
    '수': 'Jos', '삿': 'Jdg', '룻': 'Rut', '삼상': '1Sa', '삼하': '2Sa',
    '왕상': '1Ki', '왕하': '2Ki', '대상': '1Ch', '대하': '2Ch', '스': 'Ezr',
    '느': 'Neh', '에': 'Est', '욥': 'Job', '시': 'Psa', '잠': 'Pro',
    '전': 'Ecc', '아': 'Sol', '사': 'Isa', '렘': 'Jer', '애': 'Lam',
    '겔': 'Eze', '단': 'Dan', '호': 'Hos', '욜': 'Joe', '암': 'Amo',
    '옵': 'Oba', '욘': 'Jon', '미': 'Mic', '나': 'Nah', '합': 'Hab',
    '습': 'Zep', '학': 'Hag', '슥': 'Zec', '말': 'Mal', '마': 'Mat',
    '막': 'Mar', '눅': 'Luk', '요': 'Joh', '행': 'Act', '롬': 'Rom',
    '고전': '1Co', '고후': '2Co', '갈': 'Gal', '엡': 'Eph', '빌': 'Phi',
    '골': 'Col', '살전': '1Th', '살후': '2Th', '딤전': '1Ti', '딤후': '2Ti',
    '딛': 'Tit', '몬': 'Phm', '히': 'Heb', '약': 'Jam', '벧전': '1Pe',
    '벧후': '2Pe', '요일': '1Jo', '요이': '2Jo', '요삼': '3Jo', '유': 'Jud', '계': 'Rev'
}

REF_PATTERN      = re.compile(r'([가-힣]+)\s*(\d+):([\d,\-\s]+)')
REF_PATTERN_CHAP = re.compile(r'^([가-힣]+)\s*(\d+)$')   # 장 번호만 (예: 창 1)
CROSS_CHAP_PATTERN = re.compile(r'^([가-힣]+)\s*(\d+):(\d+)-(\d+):(\d+)')

from constants import (
    EMPHASIS_BOLD,
    EMPHASIS_UNDERLINE,
    EMPHASIS_PATTERN as _EMPHASIS_PATTERN_FROM_CONSTANTS,
)


# ─── 경로 유틸리티 ───────────────────────────────────────────────────────────

def resource_path(relative_path):
    """PyInstaller 환경과 일반 환경 모두 지원하는 경로 반환."""
    base = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    return os.path.join(base, relative_path)

def absolute_path(file_path):
    """절대경로이면 그대로, 아니면 현재 경로 기준으로 반환."""
    return file_path if os.path.isabs(file_path) else os.path.abspath(file_path)


# ─── 성경 데이터 로딩 ────────────────────────────────────────────────────────

# ─── pkl 캐시 유틸리티 ──────────────────────────────────────────────────────

def _is_cache_valid(pkl_path, *source_paths):
    """pkl이 존재하고 모든 소스 파일보다 최신이면 True."""
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


# ─── 성경 데이터 로딩 (pkl 캐시) ─────────────────────────────────────────────

def read_files_in_directory(directory):
    """디렉터리 내 .txt 파일을 순서대로 읽어 리스트로 반환."""
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
        result[book] = [verses for _, verses in sorted(chapter_map.items(), key=lambda x: int(x[0]))]
    return result

def load_kor_bible(directory, bible_books):
    """
    개역개정 성경 로드.

    - exe 환경 (PyInstaller): sys._MEIPASS/bible_cache/_cache_kor.pkl 을 읽기만 함.
      쓰기 불필요 → 캐시 갱신 로직 없음.
    - 일반 환경: directory/_cache_kor.pkl 캐시 사용.
      txt가 pkl보다 새로 갱신된 경우에만 재파싱 후 저장.
    """
    # ── exe 환경: 번들된 pkl 직접 로드 ──────────────────────────────────────
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(sys._MEIPASS, 'bible_cache', '_cache_kor.pkl')
        return _load_pkl(bundled)

    # ── 일반 환경: 캐시 유효하면 바로 반환, 아니면 파싱 후 저장 ──────────────
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
    _save_pkl(pkl_path, formatted)
    return formatted

def parse_scripture_file(file_path):
    """
    ESV 성경 로드.

    - exe 환경 (PyInstaller): sys._MEIPASS/bible_cache/_cache_esv.pkl 을 읽기만 함.
    - 일반 환경: 같은 폴더의 _cache_esv.pkl 캐시 사용.
    """
    # ── exe 환경: 번들된 pkl 직접 로드 ──────────────────────────────────────
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(sys._MEIPASS, 'bible_cache', '_cache_esv.pkl')
        return _load_pkl(bundled)

    # ── 일반 환경: 캐시 유효하면 바로 반환, 아니면 파싱 후 저장 ──────────────
    pkl_path = os.path.join(os.path.dirname(file_path), '_cache_esv.pkl')
    if _is_cache_valid(pkl_path, file_path):
        return _load_pkl(pkl_path)

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
    _save_pkl(pkl_path, result)
    return result


# ─── 강조(Emphasis) 파싱 ─────────────────────────────────────────────────────

# EmphasisInfo 구조: {'text': str, 'kind': EMPHASIS_BOLD | EMPHASIS_UNDERLINE}
# 한 구절 줄에 여러 강조 구간이 올 수 있음.
#
# 입력 예시:
#   창 1:1 '태초에 하나님이' 굵게
#   창 1:1 '빛이 있으라' 밑줄
#   창 1:1 '태초에' 굵게 '빛이' 밑줄

_EMPHASIS_PATTERN = _EMPHASIS_PATTERN_FROM_CONSTANTS

def parse_emphasis_from_ref(raw_ref):
    """
    원본 입력 줄에서 강조 정보를 추출.
    반환: (clean_ref: str, emphases: list[dict])
      - clean_ref : 강조 표기를 제거한 순수 구절 주소
      - emphases  : [{'text': ..., 'kind': ...}, ...]  (없으면 빈 리스트)
    """
    emphases = [
        {'text': m.group(1), 'kind': EMPHASIS_BOLD if m.group(2) == '굵게' else EMPHASIS_UNDERLINE}
        for m in _EMPHASIS_PATTERN.finditer(raw_ref)
    ]
    clean_ref = _EMPHASIS_PATTERN.sub('', raw_ref).strip()
    return clean_ref, emphases


# ─── 입력 파싱 ───────────────────────────────────────────────────────────────

def process_text(input_text):
    """강조 표기를 제거하고 구절 주소만 반환."""
    clean, _ = parse_emphasis_from_ref(input_text)
    return clean

def parse_multi_refs_line(text):
    """
    입력 텍스트를 줄 단위로 분리한 뒤
    '번호. 구절주소' 형식에서 구절 주소 부분만 추출해 그룹 리스트로 반환.
    탭(\t)이나 연속 공백으로 분리된 구절들도 추출.
    강조 표기('...' 굵게/밑줄)는 각 항목에 그대로 보존됨.
    """
    grouped = []
    for line in text.strip().splitlines():
        parts = line.strip().split(' ', 1)
        if len(parts) < 2:
            continue
        items = re.split(r'\t| {4,}', parts[1])
        refs = [r.strip() for r in items if r.strip()]
        if refs:
            grouped.append(refs)
    return grouped

def split_semicolon_refs(ref_string, initial_book=None):
    """
    세미콜론(;)으로 연결된 구절 문자열을 개별 구절 리스트로 분리.
    - 앞선 구절의 책 이름을 상속 (예: "창 1:1; 1:2" -> ["창 1:1", "창 1:2"])
    - 각 구절에 지정된 강조 표기('...' 굵게/밑줄) 보존
    """
    result = []
    current_book = initial_book
    for part in (p.strip() for p in ref_string.split(';') if p.strip()):
        clean_part, emphases = parse_emphasis_from_ref(part)
        clean_part = clean_part.strip()

        # 0. 책 + 장:절-장:절 (예: 창 1:31-2:3)
        m_cross = CROSS_CHAP_PATTERN.match(clean_part)
        if m_cross:
            current_book = m_cross.group(1)
            base_ref = f"{current_book} {m_cross.group(2)}:{m_cross.group(3)}-{m_cross.group(4)}:{m_cross.group(5)}"
        else:
            # 0.5. 책 이름 없는 장:절-장:절 (예: 1:31-2:3)
            m_cross_no_book = re.match(r'^(\d+):(\d+)-(\d+):(\d+)$', clean_part)
            if m_cross_no_book:
                if not current_book:
                    raise ValueError(f"책 이름이 없는 구절인데 앞선 책 정보가 없습니다: '{part}'")
                base_ref = f"{current_book} {clean_part}"
            else:
                # 1. 책 + 장:절 형식 (예: 창 1:1-3)
                m = re.match(r'^([가-힣]+)\s*(\d+:\d[\d,\-\s]*)$', clean_part)
        if m:
            current_book = m.group(1)
            base_ref = f"{current_book} {m.group(2).strip()}"
        else:
            # 2. 책 + 장 형식 (예: 창 1)
            m_chap = re.match(r'^([가-힣]+)\s*(\d+)$', clean_part)
            if m_chap:
                current_book = m_chap.group(1)
                base_ref = f"{current_book} {m_chap.group(2)}"
            else:
                # 3. 책 이름 없는 장:절 (예: 1:2)
                m_verse = re.match(r'^(\d+:\d[\d,\-\s]*)$', clean_part)
                if m_verse:
                    if not current_book:
                        raise ValueError(f"책 이름이 없는 구절인데 앞선 책 정보가 없습니다: '{part}'")
                    base_ref = f"{current_book} {m_verse.group(1).strip()}"
                else:
                    # 4. 책 이름 없는 장 (예: 2)
                    m_chap_only = re.match(r'^(\d+)$', clean_part)
                    if m_chap_only:
                        if not current_book:
                            raise ValueError(f"책 이름이 없는 구절인데 앞선 책 정보가 없습니다: '{part}'")
                        base_ref = f"{current_book} {m_chap_only.group(1)}"
                    else:
                                base_ref = clean_part

        # 강조 구문 복원
        emph_str = ""
        for emp in emphases:
            k = "굵게" if emp['kind'] == EMPHASIS_BOLD else "밑줄"
            emph_str += f" '{emp['text']}' {k}"

        result.append(f"{base_ref}{emph_str}")
    return result

def parse_passages(ref_string):
    """
    세미콜론으로 연결된 구절 문자열을 개별 항목 리스트로 분리.
    '책 장:절' 형식과 '책 장' (장 전체) 형식 모두 지원.
    """
    return [parse_emphasis_from_ref(r)[0] for r in split_semicolon_refs(ref_string)]


# ─── 공통 구절 추출 로직 ─────────────────────────────────────────────────────

def _resolve_verse_nums(verses_str):
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
        chap_data = bible_data.get(book_name, [])
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
    chapter_data = data.get(book, [])
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
    chapter_data = data.get(book, [])
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
    강조 표기는 미리 제거한 clean_ref로 조회.
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

# ─── 슬라이드 용량 추정 ──────────────────────────────────────────────────────
# 템플릿(template.pptx) 우측 패널 기준: 너비 7.93", 한글 높이 3.92", 영어 높이 2.83"
# 폰트 크기에 비례하여 글자 수가 넘치거나 겹치지 않도록 용량을 추정
KOR_BASE_CAPACITY = 140  # 한글 26pt 기준 약 140자 (2~3절)
ENG_BASE_CAPACITY = 280  # 영어 18pt 기준 약 280자 (2~3절)

def estimate_slide_capacity(font_size, is_english=False):
    """폰트 크기에 따른 슬라이드 본문 용량(글자 수) 추정."""
    base_cap = ENG_BASE_CAPACITY if is_english else KOR_BASE_CAPACITY
    base_size = 18 if is_english else 26
    if not font_size or font_size <= 0:
        font_size = base_size
    return round(base_cap * (base_size / font_size) ** 2)

def _chunk_and_append(result, label, merged_verses, emphases, font_size=None):
    """
    글자 수 기반으로 슬라이드를 동적 분할.
    각 청크의 라벨은 실제 절 범위를 반영해 갱신.
    각 항목: (label, verse_text, emphases)
    """
    capacity = estimate_slide_capacity(font_size)

    # 절이 2개 이상일 때 절 단위 분할 시도
    if len(merged_verses) >= 2:
        chunks = []
        current_chunk = []
        char_count = 0

        for verse in merged_verses:
            verse_len = len(verse)
            if current_chunk and char_count + verse_len > capacity:
                chunks.append(current_chunk)
                current_chunk = [verse]
                char_count = verse_len
            else:
                current_chunk.append(verse)
                char_count += verse_len
        if current_chunk:
            chunks.append(current_chunk)

        if len(chunks) > 1:
            m_single_chap = re.match(r'^([^\n:]+\s+\d+):(\d+)-(\d+)', label)
            for chunk in chunks:
                if m_single_chap:
                    v_start = int(chunk[0].split()[0])
                    v_end   = int(chunk[-1].split()[0])
                    chunk_label = f"{m_single_chap.group(1)}:{v_start}-{v_end}\n"
                else:
                    chunk_label = label
                result.append((chunk_label, '\n'.join(chunk), emphases))
            return

    # 단일 절(또는 분할 불필요한 경우) — 용량 초과 시 문장 단위 분할
    joined = '\n'.join(merged_verses)
    if len(joined) > capacity and len(merged_verses) == 1:
        # 절 번호 토큰 분리 (예: "9 본문...")
        tokens = merged_verses[0].split(' ', 1)
        if len(tokens) == 2 and tokens[0].isdigit():
            verse_num, body = tokens[0], tokens[1]
        else:
            verse_num, body = '', merged_verses[0]

        # 문장 단위 분할 (마침표/느낌표/물음표 + 공백 기준)
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
                for chunk_text in chunks:
                    full = f"{verse_num} {chunk_text}" if verse_num else chunk_text
                    result.append((label, full, emphases))
                return

    result.append((label, joined, emphases))


# ─── 공개 추출 함수 ──────────────────────────────────────────────────────────

def _is_multi_verse_ref(clean_part):
    """한 참조가 복수 절인지 확인 (범위·쉼표·장 전체)."""
    m = REF_PATTERN.match(clean_part.strip())
    if m:
        verses_part = m.group(3).strip()
        return '-' in verses_part or ',' in verses_part
    # 장 전체 참조는 항상 복수
    return bool(REF_PATTERN_CHAP.match(clean_part.strip()))


def _expand_ref_group(ref_group):
    """
    한 줄에 입력된 모든 구절(세미콜론 및 탭/공백 구분 포함)을 개별 구절로 분리하여
    각각 별도의 단일 구절 리스트 [[ref1], [ref2], [ref3], ...] 로 반환.
    구절 수(단일 절, 복수 절 등)에 상관없이 항상 각각 별도의 슬라이드로 나뉜다.
    """
    expanded = []
    current_book = None
    for ref in ref_group:
        if not ref.strip():
            continue
        if ';' in ref:
            sub_refs = split_semicolon_refs(ref, current_book)
            for sub_ref in sub_refs:
                clean, _ = parse_emphasis_from_ref(sub_ref)
                m = re.match(r'^([가-힣]+)', clean.strip())
                if m:
                    current_book = m.group(1)
                expanded.append([sub_ref])
        else:
            clean, _ = parse_emphasis_from_ref(ref)
            m = re.match(r'^([가-힣]+)', clean.strip())
            if m:
                current_book = m.group(1)
            expanded.append([ref])
    return expanded


def _extract_passages_grouped_impl(data, grouped_refs, book_map, *, allow_quote=False, font_size=None):
    """
    구절 그룹 추출 공통 로직.
    allow_quote=True 이면 '<인용구>' 접두사 항목을 그대로 슬라이드에 삽입.
    반환: [(label, verse_text, emphases), ...]
    """
    result = []
    for ref_group in grouped_refs:
        for group in _expand_ref_group(ref_group):
            for ref in group:
                if allow_quote and ref.startswith('<인용구>'):
                    result.append(('<인용구>\n', ref[5:], []))
                    continue
                _, emphases = parse_emphasis_from_ref(ref)
                for label, texts in _extract_ref(data, ref, book_map):
                    _chunk_and_append(result, label, texts, emphases, font_size=font_size)

    return result


def extract_passages_grouped(data, grouped_refs, font_size=None):
    """
    개역개정 구절 그룹 추출.
    반환: [(label, verse_text, emphases), ...]
      emphases = [{'text': str, 'kind': 'bold'|'underline'}, ...]
    """
    return _extract_passages_grouped_impl(data, grouped_refs, book_abbr_map, allow_quote=True, font_size=font_size)


def extract_passages_grouped_eng(data, grouped_refs, font_size=None):
    """
    ESV 구절 그룹 추출.
    반환: [(label, verse_text, emphases), ...]
    """
    return _extract_passages_grouped_impl(data, grouped_refs, bible_book_abbreviations, font_size=font_size)


def extract_passages_synchronized(kor_data, eng_data, grouped_refs, kor_font_size=26, eng_font_size=18):
    """
    한/영 구절을 동일한 절 경계로 동기화하여 추출.
    어느 한 쪽 언어라도 슬라이드 용량을 초과하면 동일한 절에서 슬라이드를 분할한다.
    반환: (kor_entries, eng_entries)
    """
    if not kor_data and not eng_data:
        return [], []
    if not kor_data:
        return [], extract_passages_grouped_eng(eng_data, grouped_refs, font_size=eng_font_size)
    if not eng_data:
        return extract_passages_grouped(kor_data, grouped_refs, font_size=kor_font_size), []

    kor_cap = estimate_slide_capacity(kor_font_size, is_english=False)
    eng_cap = estimate_slide_capacity(eng_font_size, is_english=True)

    kor_result, eng_result = [], []

    for ref_group in grouped_refs:
        for group in _expand_ref_group(ref_group):
            for ref in group:
                if ref.startswith('<인용구>'):
                    kor_result.append(('<인용구>\n', ref[5:], []))
                    eng_result.append(('', '', []))
                    continue

                _, emphases = parse_emphasis_from_ref(ref)
                k_items = _extract_ref(kor_data, ref, book_abbr_map)
                e_items = _extract_ref(eng_data, ref, bible_book_abbreviations)

                num_items = max(len(k_items), len(e_items))
                for idx in range(num_items):
                    k_label, k_texts = k_items[idx] if idx < len(k_items) and k_items[idx] else ('', [])
                    e_label, e_texts = e_items[idx] if idx < len(e_items) and e_items[idx] else ('', [])

                    n_verses = max(len(k_texts), len(e_texts))
                    if n_verses == 0:
                        continue

                    # 두 언어의 용량을 동시에 고려하여 절 인덱스 분할
                    chunks = []
                    cur_chunk = []
                    k_chars, e_chars = 0, 0

                    for vi in range(n_verses):
                        kv = k_texts[vi] if vi < len(k_texts) else ''
                        ev = e_texts[vi] if vi < len(e_texts) else ''
                        kl, el = len(kv), len(ev)

                        if cur_chunk and ((k_chars + kl > kor_cap) or (e_chars + el > eng_cap)):
                            chunks.append(cur_chunk)
                            cur_chunk = [vi]
                            k_chars, e_chars = kl, el
                        else:
                            cur_chunk.append(vi)
                            k_chars += kl
                            e_chars += el
                    if cur_chunk:
                        chunks.append(cur_chunk)

                    for chunk_indices in chunks:
                        k_chunk = [k_texts[i] for i in chunk_indices if i < len(k_texts)]
                        e_chunk = [e_texts[i] for i in chunk_indices if i < len(e_texts)]

                        if len(chunks) > 1:
                            m_k = re.match(r'^([^\n:]+\s+\d+):(\d+)-(\d+)', k_label)
                            if m_k and k_chunk:
                                vs_k = k_chunk[0].split()[0]
                                ve_k = k_chunk[-1].split()[0]
                                actual_k_label = f"{m_k.group(1)}:{vs_k}-{ve_k}\n"
                            else:
                                actual_k_label = k_label

                            m_e = re.match(r'^([^\n:]+\s+\d+):(\d+)-(\d+)', e_label)
                            if m_e and e_chunk:
                                vs_e = e_chunk[0].split()[0]
                                ve_e = e_chunk[-1].split()[0]
                                actual_e_label = f"{m_e.group(1)}:{vs_e}-{ve_e}\n"
                            else:
                                actual_e_label = e_label
                        else:
                            actual_k_label = k_label
                            actual_e_label = e_label

                        kor_result.append((actual_k_label, '\n'.join(k_chunk), emphases))
                        eng_result.append((actual_e_label, '\n'.join(e_chunk), emphases))

    return kor_result, eng_result