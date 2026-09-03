"""
pptx_generator5.py (하위 호환성 브릿지 모듈)

새로 분리된 `generator` 모듈의 함수 및 상수를 기존 이름 그대로 재노출합니다.
신규 코드는 `from pptx_generator import generator`를 사용하는 것을 권장합니다.
"""

import os
from constants import (
    BIBLE_BOOKS,
    SUPERSCRIPT_MAP,
    DEFAULT_STYLE,
    DEFAULT_BOLD_FONT,
    EMPHASIS_BOLD,
    EMPHASIS_UNDERLINE,
)
from generator import (
    hex_to_rgb,
    duplicate_slide_with_blank_layout,
    move_slide as _move_slide,
    insert_black_slides as _insert_black_slides,
    detect_shape_mapping,
    add_scripture_to_ppt,
)

# ─── 하위 호환 경로 및 alias ──────────────────────────────────────────────────
bible_books = BIBLE_BOOKS

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOR_BIBLE_PATH = os.path.join(_BASE, 'text_DB', '개역개정-text')
ESV_BIBLE_PATH = os.path.join(_BASE, 'text_DB', 'ESV-text', 'ESV_cleaned.txt')
TEMPLATE_PATH  = os.path.join(_BASE, 'pptx_template', 'template.pptx')
OUTPUT_PATH    = os.path.join(_BASE, 'pptx_template', 'output.pptx')