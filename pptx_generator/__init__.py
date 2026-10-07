"""
pptx_generator 패키지

성경 구절 주소 파싱, 텍스트 로드, PPT 슬라이드 생성 및 예배 통합 모듈을 제공합니다.
"""

from .constants import (
    BIBLE_BOOKS,
    EMPHASIS_BOLD,
    EMPHASIS_UNDERLINE,
    EMPHASIS_PATTERN,
    DEFAULT_STYLE,
    DEFAULT_BOLD_FONT,
    get_full_style,
    normalize_color,
)

from .parser import (
    BOOK_ABBR_MAP_KOR,
    BOOK_ABBR_MAP_ENG,
    BOOK_DB_KEY_MAP_ENG,
    ESV_DISPLAY_TO_RAW,
    ESV_RAW_TO_DISPLAY,
    book_abbr_map,
    bible_book_abbreviations,
    parse_emphasis_from_ref,
    process_text,
    split_semicolon_refs,
    parse_passages,
    parse_multi_refs_line,
    expand_ref_group,
    is_multi_verse_ref,
    is_quote_body,
    strip_quote_tag,
    parse_quote_content,
    is_responsive_body,
    normalize_responsive_line,
    parse_responsive_item,
    split_items,
)

from .loader import (
    resource_path,
    absolute_path,
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

from .generator import (
    hex_to_rgb,
    duplicate_slide_with_blank_layout,
    move_slide,
    insert_black_slides,
    detect_shape_mapping,
    add_scripture_to_ppt,
)

from .pptx_merger import (
    get_slide_tags,
    scan_template_slots,
    is_scripture_tag,
    merge_worship_ppt,
)

__all__ = [
    # constants
    'BIBLE_BOOKS', 'EMPHASIS_BOLD', 'EMPHASIS_UNDERLINE', 'EMPHASIS_PATTERN',
    'DEFAULT_STYLE', 'DEFAULT_BOLD_FONT', 'get_full_style', 'normalize_color',
    # parser
    'BOOK_ABBR_MAP_KOR', 'BOOK_ABBR_MAP_ENG', 'BOOK_DB_KEY_MAP_ENG',
    'ESV_DISPLAY_TO_RAW', 'ESV_RAW_TO_DISPLAY', 'book_abbr_map', 'bible_book_abbreviations',
    'parse_emphasis_from_ref', 'process_text', 'split_semicolon_refs', 'parse_passages',
    'parse_multi_refs_line', 'expand_ref_group', 'is_multi_verse_ref',
    'is_quote_body', 'strip_quote_tag', 'parse_quote_content',
    'is_responsive_body', 'normalize_responsive_line', 'parse_responsive_item', 'split_items',
    # loader
    'resource_path', 'absolute_path', 'load_kor_bible', 'parse_scripture_file',
    'lookup_cross_chapter_verses', 'estimate_slide_capacity',
    'extract_passages_grouped', 'extract_passages_grouped_eng', 'extract_passages_synchronized',
    'should_unify_chunk', 'merge_labels', 'extract_with_canonical_labels',
    # generator
    'hex_to_rgb', 'duplicate_slide_with_blank_layout', 'move_slide',
    'insert_black_slides', 'detect_shape_mapping', 'add_scripture_to_ppt',
    # merger
    'get_slide_tags', 'scan_template_slots', 'is_scripture_tag', 'merge_worship_ppt',
]
