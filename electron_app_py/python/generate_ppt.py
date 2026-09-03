#!/usr/bin/env python3
"""
Electron → Python IPC 브릿지 스크립트

Electron 메인 프로세스로부터 표준 입력(stdin)으로 JSON 페이로드를 전달받아,
pptx_generator 패키지의 도메인 로직을 호출하여 PPTX를 생성하고
결과를 표준 출력(stdout)으로 반환합니다.

stdin:  JSON { rawText, style, boldFont, outputPath, rootPath, isIntegrated?, worshipType?, slots?, languages?, ... }
stdout: JSON { success: bool, error?: str, detail?: str }
"""

import sys
import os
import json
import traceback

# ─── 경로 및 인코딩 설정 ───────────────────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))


def _resolve_root(root_from_electron):
    """프로젝트 루트 경로를 결정한다."""
    if root_from_electron and os.path.isdir(root_from_electron):
        return root_from_electron
    # 개발 환경 기본 경로: electron_app_py/python/ -> ../../
    return os.path.abspath(os.path.join(HERE, '..', '..'))


# Windows stdout/stderr UTF-8 설정
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# stdin 바이너리 수신 및 UTF-8 디코딩
raw_input = sys.stdin.buffer.read().decode('utf-8').strip()

try:
    data = json.loads(raw_input)
except json.JSONDecodeError as e:
    print(json.dumps({'success': False, 'error': f'JSON 파싱 실패: {e}'}), flush=True)
    sys.exit(1)

ROOT = _resolve_root(data.get('rootPath', ''))
PG_DIR = os.path.join(ROOT, 'pptx_generator')
sys.path.insert(0, ROOT)
sys.path.insert(0, PG_DIR)

# ─── 도메인 모듈 임포트 ───────────────────────────────────────────────────────
try:
    import constants
    import parser
    import loader
    import generator
    import pptx_merger as pm
except Exception as e:
    print(json.dumps({
        'success': False,
        'error': f'모듈 로드 실패: {e}\n경로: {PG_DIR}',
        'detail': traceback.format_exc(),
    }), flush=True)
    sys.exit(1)


# ─── 템플릿 슬롯 스캔 액션 ───────────────────────────────────────────────────
if data.get('action') == 'scanTemplate':
    template_path = data.get('templatePath', '').strip()
    if not template_path or not os.path.isfile(template_path):
        print(json.dumps({'success': False, 'error': f'템플릿 파일을 찾을 수 없습니다: {template_path}'}), flush=True)
        sys.exit(1)
    try:
        raw_slots = pm.scan_template_slots(template_path)
        found_tags = []
        seen = set()
        for s in raw_slots:
            for t in s.get('tags', []):
                t_clean = t.strip()
                if t_clean not in seen:
                    seen.add(t_clean)
                    found_tags.append({
                        'tag': f'{{{{{t_clean}}}}}',
                        'name': t_clean,
                        'type': 'scripture' if pm.is_scripture_tag(t_clean) else 'file',
                    })
        print(json.dumps({'success': True, 'slots': found_tags}), flush=True)
        sys.exit(0)
    except Exception as e:
        print(json.dumps({'success': False, 'error': f'템플릿 스캔 실패: {e}', 'detail': traceback.format_exc()}), flush=True)
        sys.exit(1)


# ─── 성경 및 슬라이드 생성 파이프라인 ──────────────────────────────────────────
def build_scripture_presentation(raw_text, kor_data, eng_data, inc_kor, inc_eng, style, bold_font, bible_tmpl, is_integrated):
    """사용자 입력 raw_text를 바탕으로 Presentation 객체를 생성한다."""
    item_list = parser.split_items(raw_text)
    if not item_list:
        return None

    main_entries = []
    sub_entries = []
    group_sizes = []

    for kind, content in item_list:
        prev_len = len(main_entries)

        if kind == 'responsive':
            resp_title, resp_slides = parser.parse_responsive_item(content)
            for st in resp_slides:
                main_entries.append((resp_title, st, []))
                sub_entries.append(('', '', []))

        elif kind == 'quote':
            q_title, clean_body, q_emphases = parser.parse_quote_content(content)
            main_entries.append((q_title, clean_body, q_emphases))
            sub_entries.append(('', '', []))

        else:  # 'verse'
            grouped_refs = parser.parse_multi_refs_line(content)
            if not grouped_refs:
                continue

            kor_body_size = style.get('kor_body', {}).get('size', 28)
            eng_body_size = style.get('eng_body', {}).get('size', 18)

            k, e = loader.extract_with_canonical_labels(
                kor_data, eng_data, grouped_refs,
                kor_font_size=kor_body_size,
                eng_font_size=eng_body_size
            )

            if inc_kor and inc_eng:
                main_entries.extend(k)
                sub_entries.extend(e)
            elif inc_kor:
                main_entries.extend(k)
                sub_entries.extend([('', '', []) for _ in k])
            else:
                main_entries.extend(e)
                sub_entries.extend([('', '', []) for _ in e])

        added = len(main_entries) - prev_len
        if added > 0:
            group_sizes.append(added)

    if not main_entries:
        return None

    scripture_prs = generator.add_scripture_to_ppt(
        template_path=bible_tmpl,
        verse_texts=main_entries,
        verse_texts_eng=sub_entries,
        style=style,
        bold_font=bold_font,
        return_prs=True,
    )

    if group_sizes and not is_integrated:
        generator.insert_black_slides(scripture_prs, group_sizes)

    return scripture_prs


# ─── 메인 실행 루틴 ───────────────────────────────────────────────────────────
def main():
    raw_text      = data.get('rawText', '').strip()
    style         = constants.get_full_style(data.get('style'))
    bold_font     = data.get('boldFont', constants.DEFAULT_BOLD_FONT)
    output_path   = data['outputPath']
    languages     = data.get('languages', {'kor': True, 'eng': True})
    inc_kor       = bool(languages.get('kor', True))
    inc_eng       = bool(languages.get('eng', True))
    is_integrated = bool(data.get('isIntegrated', False))
    worship_type  = data.get('worshipType', 'sunday')

    if not inc_kor and not inc_eng:
        raise ValueError('최소 하나의 언어를 선택해야 합니다.')

    kor_dir    = os.path.join(ROOT, 'text_DB', '개역개정-text')
    esv_file   = os.path.join(ROOT, 'text_DB', 'ESV-text', 'ESV_cleaned.txt')
    bible_tmpl = os.path.join(ROOT, 'pptx_template', 'template.pptx')

    if inc_kor and not os.path.isdir(kor_dir):
        raise FileNotFoundError(f'한글 성경 폴더 없음: {kor_dir}')
    if inc_eng and not os.path.isfile(esv_file):
        raise FileNotFoundError(f'ESV 파일 없음: {esv_file}')
    if not os.path.isfile(bible_tmpl):
        raise FileNotFoundError(f'성경 기본 템플릿 없음: {bible_tmpl}')

    # 성경 텍스트 데이터 로드
    kor_data = loader.load_kor_bible(kor_dir, constants.BIBLE_BOOKS) if inc_kor else None
    eng_data = loader.parse_scripture_file(esv_file) if inc_eng else None

    # 슬라이드 Presentation 생성
    scripture_prs = None
    if raw_text:
        scripture_prs = build_scripture_presentation(
            raw_text=raw_text,
            kor_data=kor_data,
            eng_data=eng_data,
            inc_kor=inc_kor,
            inc_eng=inc_eng,
            style=style,
            bold_font=bold_font,
            bible_tmpl=bible_tmpl,
            is_integrated=is_integrated,
        )

    # 모드 분기: 통합 예배 템플릿 생성 vs 단일 성경 구절 생성
    if is_integrated:
        if worship_type == 'wednesday':
            worship_tmpl_path = os.path.join(ROOT, 'pptx_template', 'wednesday_template.pptx')
        elif worship_type == 'custom':
            worship_tmpl_path = data.get('customTemplatePath', '')
        else:
            worship_tmpl_path = os.path.join(ROOT, 'pptx_template', 'sunday_template.pptx')

        if not os.path.isfile(worship_tmpl_path):
            raise FileNotFoundError(f'예배 템플릿 파일 없음: {worship_tmpl_path}')

        slots = data.get('slots', {})
        pm.merge_worship_ppt(
            template_path=worship_tmpl_path,
            scripture_prs=scripture_prs,
            external_slots=slots,
            output_path=output_path,
        )
    else:
        if not scripture_prs:
            raise ValueError(
                '슬라이드를 생성할 수 없습니다. '
                '유효한 성경 구절 또는 <교독문> / <인용> 항목을 입력하세요.'
            )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        scripture_prs.save(output_path)

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