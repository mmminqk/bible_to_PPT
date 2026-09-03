"""
verse_loader5.py (하위 호환성 브릿지 모듈)

새로 분리된 `parser` 및 `loader` 모듈의 함수들을 기존 이름 그대로 재노출합니다.
신규 코드는 `from pptx_generator import loader, parser`를 사용하는 것을 권장합니다.
"""

from parser import (
    BOOK_ABBR_MAP_KOR as book_abbr_map,
    BOOK_ABBR_MAP_ENG as bible_book_abbreviations,
    REF_PATTERN,
    REF_PATTERN_CHAP,
    CROSS_CHAP_PATTERN,
    parse_emphasis_from_ref,
    process_text,
    parse_multi_refs_line,
    split_semicolon_refs,
    parse_passages,
    expand_ref_group as _expand_ref_group,
    is_multi_verse_ref as _is_multi_verse_ref,
    is_quote_body,
    strip_quote_tag,
    parse_quote_content,
    is_responsive_body,
    normalize_responsive_line,
    parse_responsive_item,
    split_items,
)

from loader import (
    resource_path,
    absolute_path,
    read_files_in_directory,
    split_and_format_verses,
    load_kor_bible,
    parse_scripture_file,
    lookup_cross_chapter_verses,
    estimate_slide_capacity,
    extract_passages_grouped,
    extract_passages_grouped_eng,
    extract_passages_synchronized,
    should_unify_chunk,
    merge_labels,
    extract_with_canonical_labels,
)