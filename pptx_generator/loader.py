"""
pptx_generator.loader

성경 텍스트 DB(개역개정, ESV) 로드 및 캐싱,
구절 텍스트 추출, 슬라이드 글자수 기반 청킹 및 한/영 동기화 추출 모듈.
"""

import os
import sys
import re
import pickle
from collections import defaultdict

from constants import (
    EMPHASIS_PATTERN,
)
from parser import (
    BOOK_ABBR_MAP_KOR,
    BOOK_ABBR_MAP_ENG,
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


def parse_scripture_file(file_path):
    """
    ESV 성경 텍스트 파일 로드.
    - PyInstaller 환경: sys._MEIPASS/bible_cache/_cache_esv.pkl 로드
    - 일반 환경: 같은 폴더의 _cache_esv.pkl 캐시 사용
    """
    if getattr(sys, 'frozen', False):
        bundled = os.path.join(sys._MEIPASS, 'bible_cache', '_cache_esv.pkl')
        if os.path.exists(bundled):
            return _load_pkl(bundled)

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


# ─── 슬라이드 용량 추정 및 청킹 ──────────────────────────────────────────────
KOR_BASE_CAPACITY = 140  # 한글 26pt 기준 약 140자
ENG_BASE_CAPACITY = 280  # 영어 18pt 기준 약 280자


def estimate_slide_capacity(font_size, is_english=False):
    """폰트 크기에 따른 슬라이드 본문 용량(글자 수) 추정."""
    base_cap = ENG_BASE_CAPACITY if is_english else KOR_BASE_CAPACITY
    base_size = 18 if is_english else 26
    if not font_size or font_size <= 0:
        font_size = base_size
    return round(base_cap * (base_size / font_size) ** 2)


def _chunk_and_append(result, label, merged_verses, emphases, font_size=None):
    """글자 수 기반으로 슬라이드를 동적 분할하여 result에 추가."""
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
        tokens = merged_verses[0].split(' ', 1)
        if len(tokens) == 2 and tokens[0].isdigit():
            verse_num, body = tokens[0], tokens[1]
        else:
            verse_num, body = '', merged_verses[0]

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


def _extract_passages_grouped_impl(data, grouped_refs, book_map, *, allow_quote=False, font_size=None):
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
                    _chunk_and_append(result, label, texts, emphases, font_size=font_size)
    return result


def extract_passages_grouped(data, grouped_refs, font_size=None):
    """개역개정 구절 그룹 추출."""
    return _extract_passages_grouped_impl(data, grouped_refs, BOOK_ABBR_MAP_KOR, allow_quote=True, font_size=font_size)


def extract_passages_grouped_eng(data, grouped_refs, font_size=None):
    """ESV 구절 그룹 추출."""
    return _extract_passages_grouped_impl(data, grouped_refs, BOOK_ABBR_MAP_ENG, font_size=font_size)


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

            kor_entries.extend(grp_kor)
            eng_entries.extend(grp_eng)

    return kor_entries, eng_entries
