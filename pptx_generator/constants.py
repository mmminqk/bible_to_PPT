"""
pptx_generator 패키지 공통 상수 모듈.

성경 66권 목록, 강조 서식 상수, 정규식, 상첨자 변환 맵,
기본 스타일 설정 등 여러 모듈에서 공유하는 상수를 한 곳에서 관리한다.
"""
import re

# ─── 성경 66권 정식 명칭 ─────────────────────────────────────────────────────
BIBLE_BOOKS = [
    "창세기", "출애굽기", "레위기", "민수기", "신명기", "여호수아", "사사기", "룻기", "사무엘상", "사무엘하",
    "열왕기상", "열왕기하", "역대상", "역대하", "에스라", "느헤미야", "에스더", "욥기", "시편", "잠언",
    "전도서", "아가", "이사야", "예레미야", "예레미야애가", "에스겔", "다니엘", "호세아", "요엘", "아모스",
    "오바댜", "요나", "미가", "나훔", "하박국", "스바냐", "학개", "스가랴", "말라기", "마태복음", "마가복음",
    "누가복음", "요한복음", "사도행전", "로마서", "고린도전서", "고린도후서", "갈라디아서", "에베소서", "빌립보서", "골로새서",
    "데살로니가전서", "데살로니가후서", "디모데전서", "디모데후서", "디도서", "빌레몬서", "히브리서", "야고보서", "베드로전서", "베드로후서",
    "요한일서", "요한이서", "요한삼서", "유다서", "요한계시록",
]

# ─── 강조 서식 종류 상수 ─────────────────────────────────────────────────────
EMPHASIS_BOLD      = 'bold'       # 굵게 → 폰트 변경
EMPHASIS_UNDERLINE = 'underline'  # 밑줄

# ─── 강조 파싱 정규식 ────────────────────────────────────────────────────────
EMPHASIS_PATTERN = re.compile(r"'([^']+)'\s*(굵게|밑줄)")

# ─── 상첨자 변환 맵 ──────────────────────────────────────────────────────────
SUPERSCRIPT_MAP = str.maketrans("0123456789:", "⁰¹²³⁴⁵⁶⁷⁸⁹˸")

# ─── 기본 스타일 ─────────────────────────────────────────────────────────────
DEFAULT_STYLE = {
    "kor_title": {"font": "나눔스퀘어 네오 ExtraBold", "size": 37.3, "color": "#1F3337"},
    "kor_body":  {"font": "나눔스퀘어 네오 Bold",      "size": 28,   "color": "#1F3337"},
    "eng_title": {"font": "나눔스퀘어 네오 ExtraBold", "size": 28,   "color": "#8FA79F"},
    "eng_body":  {"font": "Pretendard Variable",       "size": 20,   "color": "#4F655E"},
}

DEFAULT_BOLD_FONT = "나눔스퀘어 네오 ExtraBold"  # '굵게' 서식에 사용할 기본 폰트


def normalize_color(color_str):
    """'#1F3337' 또는 '1F3337' 형태의 색상 문자열에서 '#'을 제거하고 반환."""
    if isinstance(color_str, str) and color_str.startswith('#'):
        return color_str[1:]
    return color_str


def get_full_style(custom_style=None):
    """
    custom_style 딕셔너리를 DEFAULT_STYLE과 깊은 병합(Deep Merge)하여
    누락된 키나 항목이 있어도 안전하게 완전한 스타일 딕셔너리를 반환한다.
    색상 값은 '#'이 제거된 6자리 16진수 문자열로 통일된다.
    """
    merged = {}
    custom = custom_style or {}
    for section, defaults in DEFAULT_STYLE.items():
        user_sec = custom.get(section, {})
        merged[section] = {
            'font': user_sec.get('font', defaults['font']),
            'size': float(user_sec.get('size', defaults['size'])),
            'color': normalize_color(user_sec.get('color', defaults['color'])),
        }
    return merged
