#!/usr/bin/env python3
"""
Electron → Python IPC 브릿지
pptx_generator5.py / verse_loader5.py 를 GUI 없이 호출한다.

stdin:  JSON { rawText, style, boldFont, outputPath, rootPath }
stdout: JSON { success, error? }
"""
import sys
import os
import json
import traceback
from unittest.mock import MagicMock

# ── tkinter 모킹: GUI 없이 pptx_generator5 임포트 ────────────────────────────
for _m in [
    'tkinter', 'tkinter.messagebox', 'tkinter.filedialog',
    'tkinter.ttk', 'tkinter.font', 'tkinter.colorchooser',
    'tkinter.simpledialog',
]:
    sys.modules[_m] = MagicMock()

# ── 경로 설정 ─────────────────────────────────────────────────────────────────
HERE   = os.path.dirname(os.path.abspath(__file__))

def _resolve_root(root_from_electron):
    """참고구절_최종(3.16) 루트 경로를 결정한다."""
    # Electron이 rootPath를 전달해 주면 그것을 우선 사용
    if root_from_electron and os.path.isdir(root_from_electron):
        return root_from_electron
    # 개발 환경: .../electron_app_py/python/ → ../../ = 프로젝트 루트
    candidate = os.path.abspath(os.path.join(HERE, '..', '..'))
    return candidate

# Windows stdout/stderr도 UTF-8로 강제 설정
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# stdin을 바이너리로 읽어 UTF-8 디코딩 (Windows CP949 오염 방지)
raw_input = sys.stdin.buffer.read().decode('utf-8').strip()

try:
    data = json.loads(raw_input)
except json.JSONDecodeError as e:
    print(json.dumps({'success': False, 'error': f'JSON 파싱 실패: {e}'}), flush=True)
    sys.exit(1)

ROOT       = _resolve_root(data.get('rootPath', ''))
PG_DIR     = os.path.join(ROOT, 'pptx_generator')
sys.path.insert(0, ROOT)
sys.path.insert(0, PG_DIR)

# ── 모듈 임포트 ───────────────────────────────────────────────────────────────
try:
    import verse_loader5 as vl
    import pptx_generator5 as pg
except Exception as e:
    print(json.dumps({
        'success': False,
        'error': f'모듈 로드 실패: {e}\n경로: {PG_DIR}',
    }), flush=True)
    sys.exit(1)

# ── 66권 목록 (verse_loader5 상수 우선, 없으면 여기 정의) ────────────────────
_FALLBACK_BOOKS = [
    '창세기','출애굽기','레위기','민수기','신명기','여호수아','사사기','룻기',
    '사무엘상','사무엘하','열왕기상','열왕기하','역대상','역대하','에스라','느헤미야',
    '에스더','욥기','시편','잠언','전도서','아가','이사야','예레미야','예레미야애가',
    '에스겔','다니엘','호세아','요엘','아모스','오바댜','요나','미가','나훔','하박국',
    '스바냐','학개','스가랴','말라기','마태복음','마가복음','누가복음','요한복음',
    '사도행전','로마서','고린도전서','고린도후서','갈라디아서','에베소서','빌립보서',
    '골로새서','데살로니가전서','데살로니가후서','디모데전서','디모데후서','디도서',
    '빌레몬서','히브리서','야고보서','베드로전서','베드로후서','요한일서','요한이서',
    '요한삼서','유다서','요한계시록',
]

def _get_bible_books():
    for attr in ('BIBLE_BOOKS', 'bible_books', '_BIBLE_BOOKS'):
        val = getattr(vl, attr, None)
        if val:
            return val
    return _FALLBACK_BOOKS

# ── 색상 정규화: "#213337" 또는 "213337" → "213337" ──────────────────────────
def _norm_color(c):
    if isinstance(c, str) and c.startswith('#'):
        return c[1:]
    return c

def _norm_style(style):
    """style 딕셔너리 안의 color 값을 # 없는 hex 문자열로 통일한다."""
    result = {}
    for key, sub in style.items():
        result[key] = {k: (_norm_color(v) if k == 'color' else v) for k, v in sub.items()}
    return result

# ── 청킹 구절 주소 통합 헬퍼 ─────────────────────────────────────────────────
import re as _re

def _should_unify(ref_group, n):
    """단일 ref + 세미콜론 없음 + 2개 이상 슬라이드 → 청킹된 것으로 판단"""
    if n <= 1 or len(ref_group) != 1:
        return False
    # 강조 마커(굵게/밑줄) 제거 후 판단
    clean = _re.sub(r"'[^']+'\s*(굵게|밑줄)", '', ref_group[0]).strip()
    return ';' not in clean and '\t' not in clean

def _merge_labels(first_label, last_label):
    """
    '요한계시록 21:1-3' + '요한계시록 21:4' → '요한계시록 21:1-4'
    같은 책·장이면 절 범위를 합친다. 다르면 first_label 그대로 반환.
    """
    m1 = _re.match(r'^(.*?)\s+(\d+):(\d+)(?:-(\d+))?$', first_label.strip())
    m2 = _re.match(r'^(.*?)\s+(\d+):(\d+)(?:-(\d+))?$', last_label.strip())
    if m1 and m2 and m1.group(1) == m2.group(1) and m1.group(2) == m2.group(2):
        start_v = m1.group(3)
        end_v   = m2.group(4) or m2.group(3)
        return f"{m1.group(1)} {m1.group(2)}:{start_v}-{end_v}"
    return first_label

def _extract_with_canonical_labels(vl, kor_data, eng_data, grouped_refs, book_abbr_map):
    """
    grouped_refs를 순회하며 구절을 추출한다.
    구절 수에 상관없이 각 구절별로 분리하여 추출하며,
    단일 구절의 범위가 3절 이상이라 청킹된 경우(예: '창 1:1-5') 해당 청크 슬라이드들의
    주소 라벨을 원래 전체 범위로 통일한다.
    """
    kor_entries, eng_entries = [], []

    for ref_group in grouped_refs:
        # ref_group 내의 세미콜론 및 다중 구절을 개별 항목으로 전개
        expanded_groups = vl._expand_ref_group(ref_group) if hasattr(vl, '_expand_ref_group') else [[r] for r in ref_group]

        for single_group in expanded_groups:
            grp_kor = vl.extract_passages_grouped(kor_data, [single_group]) if kor_data is not None else []
            grp_eng = vl.extract_passages_grouped_eng(eng_data, [single_group]) if (eng_data is not None and hasattr(vl, 'extract_passages_grouped_eng')) else []

            n = len(grp_kor) if grp_kor else len(grp_eng)

            if _should_unify(single_group, n):
                # 청킹된 케이스: 첫·마지막 레이블로 전체 범위 계산
                if grp_kor:
                    canonical_kor = _merge_labels(grp_kor[0][0], grp_kor[-1][0])
                    grp_kor = [(canonical_kor, v, e) for _, v, e in grp_kor]
                if grp_eng:
                    canonical_eng = _merge_labels(grp_eng[0][0], grp_eng[-1][0])
                    grp_eng = [(canonical_eng, v, e) for _, v, e in grp_eng]

            kor_entries.extend(grp_kor)
            eng_entries.extend(grp_eng)

    return kor_entries, eng_entries


# ── <인용> 항목 분리 헬퍼 ────────────────────────────────────────────────────
import unicodedata as _ud

# NFC 정규화된 태그 (Windows/macOS 모두 대응)
_QUOTE_TAG     = _ud.normalize('NFC', '<인용>')
# 대소문자·전각 등 다양한 입력도 허용하기 위한 패턴
_QUOTE_PATTERN = _re.compile(r'^<\s*인용\s*>', _re.UNICODE)

def _is_quote_body(body):
    """body가 <인용> 태그로 시작하는지 정규화 후 판단한다."""
    normalized = _ud.normalize('NFC', body)
    return bool(_QUOTE_PATTERN.match(normalized))

def _strip_quote_tag(body):
    """<인용> 태그를 제거하고 뒤 내용만 반환한다."""
    normalized = _ud.normalize('NFC', body)
    return _QUOTE_PATTERN.sub('', normalized).strip()

def _move_slide(prs, old_index, new_index):
    """python-pptx: 슬라이드를 old_index에서 new_index로 이동."""
    xml_slides = prs.slides._sldIdLst
    slides = list(xml_slides)
    elem = slides[old_index]
    xml_slides.remove(elem)
    if new_index >= len(xml_slides):
        xml_slides.append(elem)
    else:
        xml_slides.insert(new_index, elem)


def _insert_black_slides(output_path, group_sizes):
    """
    output_path의 PPT를 열어, group_sizes에 따라
    각 번호 항목의 마지막 슬라이드 뒤에 검은 슬라이드를 삽입한다.
    group_sizes = [n1, n2, ...] (각 번호 항목이 차지하는 슬라이드 수)
    """
    from pptx import Presentation as _Prs
    from pptx.dml.color import RGBColor as _RGB

    prs = _Prs(output_path)

    # 삽입 위치(0-based): 각 그룹 끝 뒤
    # 뒤에서부터 처리해 인덱스 밀림을 방지
    insert_positions = []
    cumulative = 0
    for size in group_sizes:
        cumulative += size
        insert_positions.append(cumulative)

    for pos in reversed(insert_positions):
        # 빈 레이아웃으로 슬라이드 추가
        blank_layout = prs.slide_layouts[6]
        new_slide = prs.slides.add_slide(blank_layout)
        # 슬라이드 배경을 검정으로 설정
        bg = new_slide.background.fill
        bg.solid()
        bg.fore_color.rgb = _RGB(0, 0, 0)
        # 맨 끝에 추가된 슬라이드를 원하는 위치로 이동
        last_idx = len(prs.slides) - 1
        _move_slide(prs, last_idx, pos)

    prs.save(output_path)


def _split_items(raw_text):
    """
    번호. 로 시작하는 항목들을 순서대로 분리한다.
    반환값: [('quote', 텍스트) | ('verse', '1. 원문내용'), ...]
    """
    items = []
    lines = raw_text.strip().splitlines()
    current_lines = []

    def _flush(buf):
        if not buf:
            return
        joined = '\n'.join(buf).strip()
        body = _re.sub(r'^\d+\.\s*', '', joined, count=1).strip()
        if _is_quote_body(body):
            items.append(('quote', _strip_quote_tag(body)))
        else:
            items.append(('verse', f'1. {body}'))

    for line in lines:
        if _re.match(r'^\d+\.', line.strip()):
            _flush(current_lines)
            current_lines = [line]
        else:
            current_lines.append(line)
    _flush(current_lines)
    return items


# ── 메인 로직 ─────────────────────────────────────────────────────────────────
def main():
    raw_text    = data['rawText']
    style       = _norm_style(data['style'])
    bold_font   = data.get('boldFont', '나눔스퀘어 네오 ExtraBold')
    output_path = data['outputPath']
    languages   = data.get('languages', {'kor': True, 'eng': True})
    inc_kor     = bool(languages.get('kor', True))
    inc_eng     = bool(languages.get('eng', True))

    if not inc_kor and not inc_eng:
        raise ValueError('최소 하나의 언어를 선택해야 합니다.')

    # 경로
    kor_dir       = os.path.join(ROOT, 'text_DB', '개역개정-text')
    esv_file      = os.path.join(ROOT, 'text_DB', 'ESV-text', 'ESV_cleaned.txt')
    custom_tmpl   = data.get('templatePath')
    template_path = custom_tmpl if (custom_tmpl and os.path.isfile(custom_tmpl)) else os.path.join(ROOT, 'pptx_template', 'template.pptx')

    if inc_kor and not os.path.isdir(kor_dir):
        raise FileNotFoundError(f'한글 성경 폴더 없음: {kor_dir}')
    if inc_eng and not os.path.isfile(esv_file):
        raise FileNotFoundError(f'ESV 파일 없음: {esv_file}')
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f'템플릿 없음: {template_path}')

    # ── 성경 데이터 로드 ──────────────────────────────────────────────────────
    bible_books = _get_bible_books()
    kor_data    = vl.load_kor_bible(kor_dir, bible_books) if inc_kor else None
    eng_data    = vl.parse_scripture_file(esv_file) if inc_eng else None

    # ── 항목 분리: <인용> vs 성경 구절 ───────────────────────────────────────
    item_list = _split_items(raw_text)
    if not item_list:
        raise ValueError(
            '입력된 항목이 없습니다. '
            '"1. 창 1:1-3" 또는 "1. <인용> 텍스트" 형식으로 입력하세요.'
        )

    book_abbr_map = getattr(vl, 'book_abbr_map', {})
    main_entries, sub_entries = [], []
    group_sizes = []  # 번호 항목별 슬라이드 수 추적

    for kind, content in item_list:
        prev_len = len(main_entries)
        if kind == 'quote':
            # <인용> 항목: 메인 본문에 그대로 삽입, 주소란·영문란 비움
            main_entries.append(('', content, []))
            sub_entries.append(('', '', []))
        else:
            # 일반 성경 구절 처리
            grouped_refs = vl.parse_multi_refs_line(content)
            if not grouped_refs:
                continue  # 파싱 실패 항목은 건너뜀
            k, e = _extract_with_canonical_labels(
                vl, kor_data, eng_data, grouped_refs, book_abbr_map
            )
            # 언어 설정에 따른 엔트리 분기:
            # 1) 둘 다 선택: 메인=한글, 서브=영어
            # 2) 한국어만 선택: 메인=한글, 서브=빈값(영어 박스 비움)
            # 3) 영어만 선택: 메인=영어(원래 한글 박스에 출력), 서브=빈값(영어 박스 비움)
            if inc_kor and inc_eng:
                main_entries.extend(k)
                sub_entries.extend(e)
            elif inc_kor:
                main_entries.extend(k)
                sub_entries.extend([('', '', []) for _ in k])
            else:  # inc_eng only
                main_entries.extend(e)
                sub_entries.extend([('', '', []) for _ in e])

        added = len(main_entries) - prev_len
        if added > 0:
            group_sizes.append(added)

    if not main_entries:
        raise ValueError(
            '슬라이드를 생성할 수 없습니다. '
            '유효한 성경 구절 또는 <인용> 항목을 입력하세요.'
        )

    # output 폴더 생성
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # PPT 생성
    pg.add_scripture_to_ppt(
        template_path,
        main_entries,
        sub_entries,
        style,
        bold_font,
        output_path,
    )

    # 번호 항목별 검은 슬라이드 삽입
    if len(group_sizes) > 0:
        _insert_black_slides(output_path, group_sizes)

    print(json.dumps({'success': True}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(json.dumps({
            'success': False,
            'error': str(e),
            'detail': traceback.format_exc(),
        }), flush=True)
        sys.exit(1)