"""
pptx_generator.parser

성경 구절 주소, 강조 서식, 교독문, 인용구 등
사용자 입력 텍스트를 파싱하고 정규화하는 도메인 모듈.
"""

import re
import unicodedata
try:
    from .constants import (
        EMPHASIS_BOLD,
        EMPHASIS_UNDERLINE,
        EMPHASIS_PATTERN,
    )
except (ImportError, ValueError):
    from constants import (
        EMPHASIS_BOLD,
        EMPHASIS_UNDERLINE,
        EMPHASIS_PATTERN,
    )

# ─── 개역개정 성경 약어 매핑 ──────────────────────────────────────────────────
BOOK_ABBR_MAP_KOR = {
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
    '요일': '요한일서', '요이': '요한이서', '요삼': '요한삼서', '유': '유다서', '계': '요한계시록',
}

# ─── ESV 성경 약어 매핑 ───────────────────────────────────────────────────────
BOOK_ABBR_MAP_ENG = {
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
    '벧후': '2Pe', '요일': '1Jo', '요이': '2Jo', '요삼': '3Jo', '유': 'Jud', '계': 'Rev',
}

# 하위호환 alias
book_abbr_map = BOOK_ABBR_MAP_KOR
bible_book_abbreviations = BOOK_ABBR_MAP_ENG

# ─── 정규식 패턴 ─────────────────────────────────────────────────────────────
REF_PATTERN        = re.compile(r'([가-힣]+)\s*(\d+):([\d,\-\s]+)')
REF_PATTERN_CHAP   = re.compile(r'^([가-힣]+)\s*(\d+)$')   # 장 번호만 (예: 창 1)
CROSS_CHAP_PATTERN = re.compile(r'^([가-힣]+)\s*(\d+):(\d+)-(\d+):(\d+)')

QUOTE_TAG          = unicodedata.normalize('NFC', '<인용>')
QUOTE_PATTERN      = re.compile(r'^<\s*(?:인용|인용구)\s*>', re.UNICODE)
RESPONSIVE_PATTERN = re.compile(r'^<\s*교독문(?:\s+(.*?))?\s*>', re.UNICODE)

ROLE_LEADER_PAT = re.compile(r'^(?:\[(?:인도|인도자)\]|\((?:인도|인도자)\)|<(?:인도|인도자)>|(?:인도|인도자)\s*:)\s*(.*)$', re.UNICODE)
ROLE_CONG_PAT   = re.compile(r'^(?:\[(?:회중|성도|교인)\]|\((?:회중|성도|교인)\)|<(?:회중|성도|교인)>|(?:회중|성도|교인)\s*:)\s*(.*)$', re.UNICODE)
ROLE_ALL_PAT    = re.compile(r'^(?:\[(?:다함께|다같이|함께)\]|\((?:다함께|다같이|함께)\)|<(?:다함께|다같이|함께)>|(?:다함께|다같이|함께)\s*:)\s*(.*)$', re.UNICODE)


# ─── 강조(Emphasis) 파싱 ─────────────────────────────────────────────────────
def parse_emphasis_from_ref(raw_ref):
    """
    구절 문자열에서 강조 서식('단어' 굵게/밑줄)을 추출하고 순수 구절과 분리한다.
    반환: (clean_ref: str, emphases: list[dict])
      - clean_ref: 강조 표기가 제거된 문자열
      - emphases: [{'text': str, 'kind': 'bold'|'underline'}, ...]
    """
    emphases = [
        {'text': m.group(1), 'kind': EMPHASIS_BOLD if m.group(2) == '굵게' else EMPHASIS_UNDERLINE}
        for m in EMPHASIS_PATTERN.finditer(raw_ref)
    ]
    clean_ref = EMPHASIS_PATTERN.sub('', raw_ref).strip()
    return clean_ref, emphases


def process_text(input_text):
    """강조 표기를 제거하고 구절 주소만 반환 (하위 호환용)."""
    clean, _ = parse_emphasis_from_ref(input_text)
    return clean


# ─── 세미콜론 및 다중 구절 파싱 ──────────────────────────────────────────────
def split_semicolon_refs(ref_string, initial_book=None):
    """
    세미콜론(;)으로 구분된 구절 문자열을 개별 구절 리스트로 분리.
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
    """세미콜론으로 연결된 구절 문자열에서 강조를 뗀 개별 구절 리스트 반환."""
    return [parse_emphasis_from_ref(r)[0] for r in split_semicolon_refs(ref_string)]


def parse_multi_refs_line(text):
    """
    입력 텍스트를 줄 단위로 분리한 뒤
    '번호. 구절주소' 형식에서 구절 주소 부분만 추출해 그룹 리스트로 반환.
    탭(\\t)이나 연속 공백으로 분리된 구절들도 추출.
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


def is_multi_verse_ref(clean_part):
    """한 참조가 복수 절인지 확인 (범위·쉼표·장 전체)."""
    m = REF_PATTERN.match(clean_part.strip())
    if m:
        verses_part = m.group(3).strip()
        return '-' in verses_part or ',' in verses_part
    return bool(REF_PATTERN_CHAP.match(clean_part.strip()))


def expand_ref_group(ref_group):
    """
    한 줄에 입력된 모든 구절(세미콜론 및 탭/공백 구분 포함)을 개별 구절로 분리하여
    각각 별도의 단일 구절 리스트 [[ref1], [ref2], [ref3], ...] 로 반환.
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


# ─── <인용> & <교독문> 파싱 ──────────────────────────────────────────────────
def is_quote_body(body):
    """body가 <인용> 또는 <인용구> 태그로 시작하는지 정규화 후 판단한다."""
    normalized = unicodedata.normalize('NFC', body.strip())
    return bool(QUOTE_PATTERN.match(normalized))


def strip_quote_tag(body):
    """<인용> 태그를 제거하고 뒤 내용만 반환한다."""
    normalized = unicodedata.normalize('NFC', body.strip())
    return QUOTE_PATTERN.sub('', normalized).strip()


def parse_quote_content(content):
    """
    <인용> 본문에서 제목/본문 분리 및 강조 서식을 파싱한다.
    '/' 기준으로 앞은 제목(title), 뒤는 본문(body).
    본문 내 강조 표기는 인라인('단어' 굵게) 및 후미('단어' 굵게) 모두 완벽 지원.
    반환: (title, clean_body, emphases)
    """
    if '/' in content:
        parts = content.split('/', 1)
        q_title = parts[0].strip()
        raw_body = parts[1].strip()
    else:
        q_title = ''
        raw_body = content.strip()

    emphases = [
        {'text': m.group(1), 'kind': 'bold' if m.group(2) == '굵게' else 'underline'}
        for m in EMPHASIS_PATTERN.finditer(raw_body)
    ]

    if not emphases:
        return q_title, raw_body, []

    text_without_emp = EMPHASIS_PATTERN.sub('', raw_body).strip()
    if all(emp['text'] in text_without_emp for emp in emphases):
        clean_body = text_without_emp
    else:
        clean_body = EMPHASIS_PATTERN.sub(r'\1', raw_body).strip()

    return q_title, clean_body, emphases


def is_responsive_body(body):
    """body가 <교독문> 태그로 시작하는지 정규화 후 판단한다."""
    normalized = unicodedata.normalize('NFC', body.strip())
    return bool(RESPONSIVE_PATTERN.match(normalized))


def normalize_responsive_line(line):
    """교독문 한 줄의 발화자 역할(leader/congregation/all/plain)을 인식하고 표준 서식 문자열로 변환."""
    line = line.strip()
    if not line:
        return None
    m_lead = ROLE_LEADER_PAT.match(line)
    if m_lead:
        return ('leader', f"(인도) {m_lead.group(1).strip()}")
    m_cong = ROLE_CONG_PAT.match(line)
    if m_cong:
        return ('congregation', f"(회중) {m_cong.group(1).strip()}")
    m_all = ROLE_ALL_PAT.match(line)
    if m_all:
        return ('all', f"(다함께) {m_all.group(1).strip()}")
    return ('plain', line)


def parse_responsive_item(body):
    """
    <교독문> 본문을 파싱하여 (title, list_of_slide_texts) 반환.
    인도자 1절 + 회중 1절을 자동으로 1개 슬라이드로 페어링하며,
    다함께 파트는 독립 슬라이드로 배치한다.
    """
    normalized = unicodedata.normalize('NFC', body.strip())
    lines = normalized.splitlines()
    if not lines:
        return '교독문', []

    first_line = lines[0].strip()
    m = RESPONSIVE_PATTERN.match(first_line)
    title_extra = ''
    content_lines = lines

    if m:
        inside = (m.group(1) or '').strip()
        outside = RESPONSIVE_PATTERN.sub('', first_line).strip()
        title_extra = inside or outside
        content_lines = lines[1:]

    if title_extra:
        sub = re.sub(r'^교독문\s*', '', title_extra).strip()
        title = f"교독문\n{sub}" if sub else "교독문"
    else:
        title = "교독문"

    parsed_lines = []
    for cl in content_lines:
        item = normalize_responsive_line(cl)
        if item:
            parsed_lines.append(item)

    if not parsed_lines:
        return title, []

    slides = []
    current_group = []
    has_cong = False

    for role, text in parsed_lines:
        if role == 'all':
            if current_group:
                slides.append('\n'.join([t for _, t in current_group]))
                current_group = []
                has_cong = False
            slides.append(text)
        elif role == 'leader':
            if has_cong:
                slides.append('\n'.join([t for _, t in current_group]))
                current_group = [(role, text)]
                has_cong = False
            else:
                current_group.append((role, text))
        elif role == 'congregation':
            current_group.append((role, text))
            has_cong = True
        else:  # plain line
            if not current_group:
                current_group.append(('leader', f"(인도) {text}"))
            else:
                current_group.append((role, text))

    if current_group:
        slides.append('\n'.join([t for _, t in current_group]))

    return title, slides


def split_items(raw_text):
    """
    입력 전체 텍스트에서 '번호.' 단위로 각 항목을 분리한다.
    반환: [('quote', 내용) | ('responsive', 내용) | ('verse', '1. 구절내용'), ...]
    """
    items = []
    lines = raw_text.strip().splitlines()
    current_lines = []

    def _flush(buf):
        if not buf:
            return
        joined = '\n'.join(buf).strip()
        body = re.sub(r'^\d+\.\s*', '', joined, count=1).strip()
        if is_responsive_body(body):
            items.append(('responsive', body))
        elif is_quote_body(body):
            items.append(('quote', strip_quote_tag(body)))
        else:
            items.append(('verse', f'1. {body}'))

    for line in lines:
        line_stripped = line.strip()
        if re.match(r'^\d+\.', line_stripped):
            _flush(current_lines)
            current_lines = [line]
        elif not current_lines and (is_responsive_body(line_stripped) or is_quote_body(line_stripped)):
            _flush(current_lines)
            current_lines = [line]
        else:
            current_lines.append(line)
    _flush(current_lines)
    return items
