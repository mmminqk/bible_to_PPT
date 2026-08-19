import os
import re
import copy
from collections import defaultdict
import sys

"""
exe 생성 빌드
pyinstaller --noconfirm --onefile --add-data "개역개정-text;개역개정-text" --add-data "ESV-text/ESV_cleaned.txt;ESV-text" gui.py
"""

# 개역개정 성경 매핑
book_abbr_map = {'창': '창세기','출': '출애굽기','레': '레위기','민': '민수기','신': '신명기','수': '여호수아','삿': '사사기','룻': '룻기','삼상': '사무엘상','삼하': '사무엘하','왕상': '열왕기상','왕하': '열왕기하','대상': '역대상','대하': '역대하','스': '에스라','느': '느헤미야','에': '에스더','욥': '욥기','시': '시편','잠': '잠언','전': '전도서','아': '아가','사': '이사야','렘': '예레미야','애': '예레미야애가','겔': '에스겔','단': '다니엘','호': '호세아','욜': '요엘','암': '아모스','옵': '오바댜','욘': '요나','미': '미가','나': '나훔','합': '하박국','습': '스바냐','학': '학개','슥': '스가랴','말': '말라기','마': '마태복음','막': '마가복음','눅': '누가복음','요': '요한복음','행': '사도행전','롬': '로마서','고전': '고린도전서','고후': '고린도후서','갈': '갈라디아서','엡': '에베소서','빌': '빌립보서','골': '골로새서','살전': '데살로니가전서','살후': '데살로니가후서','딤전': '디모데전서','딤후': '디모데후서','딛': '디도서','몬': '빌레몬서','히': '히브리서','약': '야고보서','벧전': '베드로전서','벧후': '베드로후서','요일': '요한일서','요이': '요한이서','요삼': '요한삼서','유': '유다서','계': '요한계시록'}

# ESV 성경 매핑
bible_book_abbreviations = {
    '창': 'Gen', '출': 'Exo', '레': 'Lev', '민': 'Num', '신': 'Deu', '수': 'Jos', '삿': 'Jdg', '룻': 'Rut', '삼상': '1Sa', '삼하': '2Sa', '왕상': '1Ki', '왕하': '2Ki', '대상': '1Ch', '대하': '2Ch', '스': 'Ezr', '느': 'Neh', '에': 'Est', '욥': 'Job', '시': 'Psa', '잠': 'Pro', '전': 'Ecc', '아': 'Sol', '사': 'Isa', '렘': 'Jer', '애': 'Lam', '겔': 'Eze', '단': 'Dan', '호': 'Hos', '욜': 'Joe', '암': 'Amo', '옵': 'Oba', '욘': 'Jon', '미': 'Mic', '나': 'Nah', '합': 'Hab', '습': 'Zep', '학': 'Hag', '슥': 'Zec', '말': 'Mal', '마': 'Mat', '막': 'Mar', '눅': 'Luk', '요': 'Joh', '행': 'Act', '롬': 'Rom', '고전': '1Co', '고후': '2Co', '갈': 'Gal', '엡': 'Eph', '빌': 'Phi', '골': 'Col', '살전': '1Th', '살후': '2Th', '딤전': '1Ti', '딤후': '2Ti', '딛': 'Tit', '몬': 'Phm', '히': 'Heb', '약': 'Jam', '벧전': '1Pe', '벧후': '2Pe', '요일': '1Jo', '요이': '2Jo', '요삼': '3Jo', '유': 'Jud', '계': 'Rev'
}

# 실행 경로 얻기 (PyInstaller 환경과 일반 환경 모두 지원)
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 임시폴더 경로
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def absolute_path(file_path):
    # 절대경로가 이미 주어졌으면 그대로 반환, 아니면 현재 경로 기준으로 반환
    if os.path.isabs(file_path):
        return file_path
    else:
        return os.path.abspath(file_path)


# ------------------------- 성경 데이터 처리 -------------------------

# 성경 파일 읽어오기
def read_files_in_directory(directory):
    file_contents = []
    for filename in os.listdir(directory):
        if filename.endswith('.txt'):
            with open(os.path.join(directory, filename), 'r', encoding='utf-8') as file:
                content = file.read()
                file_contents.append(content)
    return file_contents

# 성경 구절을 책, 장, 절로 분리하고 정렬
def split_and_format_verses(bible_dict):
    result = {}
    for book, verses in bible_dict.items():
        chapter_map = defaultdict(list)
        for verse in verses.splitlines():
            match = re.match(r'([가-힣]+)(\d+):(\d+)\s+(.*)', verse)
            if match:
                chapter = match.group(2)
                verse_num = match.group(3)
                content = match.group(4)
                chapter_map[chapter].append(f"{verse_num} {content}")
        sorted_chapters = sorted(chapter_map.items(), key=lambda x: int(x[0]))
        chapter_list = [verses for _, verses in sorted_chapters]
        result[book] = chapter_list
    return result

# 여러 구절을 한 줄로 묶어서 처리 예) '창세기 1:1; 창세기 1:2' -> [['창세기 1:1', '창세기 1:2']]
def parse_multi_refs_line(text):
    lines = text.strip().split('\n')
    grouped_refs = []
    for line in lines:
        parts = line.strip().split(' ', 1)
        if len(parts) < 2:
            continue
        ref_text = parts[1]
        # ref_items = [r.strip() for r in ref_text.split(';')]
        # grouped_refs.append(ref_items)
        if ';' in line and '-' not in line:
            ref_items = [r.strip() for r in ref_text.split(';')]
            grouped_refs.append(ref_items)
        elif ';' in line and '-' in line:
            ref_items = [r.strip() for r in ref_text.split(';')]
            for l in ref_items:
                grouped_refs.append([l])
    return grouped_refs

# 성경 구절을 그룹화하여 추출
# 예) [['창세기 1:1', '창세기 1:2'], ['출애굽기 3:1', '출애굽기 3:2']]
def extract_passages_grouped(data, grouped_refs):
    result = []

    for ref_group in grouped_refs:
        merged_verses = []
        merged_label = []

        for ref in ref_group:
            match = re.match(r'([가-힣]+)\s*(\d+):([\d,\-\s]+)', ref)
            if not match:
                continue
            abbr, chapter, verses = match.groups()
            book = book_abbr_map.get(abbr, abbr)
            chapter_idx = int(chapter) - 1
            chapter_data = data.get(book, [])

            if chapter_idx >= len(chapter_data):
                continue

            chapter_content = chapter_data[chapter_idx]

            if '-' in verses:
                start, end = map(int, verses.split('-'))
                if end > len(chapter_content):
                    continue
                verse_texts = [chapter_content[v - 1] for v in range(start, end + 1)]
                merged_label.append(f"{book} {chapter}:{start}-{end}\n")
                merged_verses.extend(verse_texts)
            elif ',' in verses:
                verse_numbers = [int(v.strip()) for v in verses.split(',')]
                verse_texts = [chapter_content[v - 1] for v in verse_numbers if v <= len(chapter_content)]
                merged_label.append(f"{book} {chapter}:{','.join(map(str, verse_numbers))}\n")
                merged_verses.extend(verse_texts)
            else:
                v = int(verses)
                if v > len(chapter_content):
                    continue
                verse_text = chapter_content[v - 1]
                merged_label.append(f"{book} {chapter}:{v}\n")
                merged_verses.append(verse_text)

        label = ''.join(merged_label)
        # 분할 조건: label에 '-'가 있고, 구절 개수가 3 이상일 때
        dash_match = re.search(r':(\d+)-(\d+)', label)
        if dash_match:
            start, end = map(int, dash_match.groups())
            count = end - start + 1
            if count >= 3:
                for i in range(0, len(merged_verses), 3):
                    chunk = merged_verses[i:i+3]
                    content = '\n'.join(chunk)
                    result.append([label, content])
                continue

        content = '\n'.join(merged_verses)
        result.append([label, content])

    return result


# 성경 파일을 파싱하여 책, 장, 절로 정리
# 예) {'창세기': {1: ['1 태초에 하나님이 천지를 창조하시니라'], 2: ['1 천지가 창조되었을 때에 하나님이 천지를 창조하시니라']}, ...}
def parse_scripture_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    result = defaultdict(lambda: defaultdict(list))
    
    # 책 이름 뒤에 공백이 있는 경우를 반영한 정규표현식
    pattern = re.compile(r'^([A-Za-z0-9]+\.?)\s+(\d+):(\d+)\s+(.*)')

    for line in lines:
        match = pattern.match(line.strip())
        if match:
            book, chapter, verse, content = match.groups()
            chapter = int(chapter)
            result[book][chapter].append(f"{verse} {content.strip()}")

    final_result = {}
    for book, chapters in result.items():
        max_chapter = max(chapters)
        chapter_list = [chapters[i] if i in chapters else [] for i in range(1, max_chapter + 1)]
        final_result[book] = chapter_list

    return final_result

# 영어 성경 구절을 그룹화하여 추출
# 예) [['Gen 1:1', 'Gen 1:2'], ['Exo 3:1', 'Exo 3:2']]
def extract_passages_grouped_eng(data, grouped_refs):
    result = []

    for ref_group in grouped_refs:
        merged_verses = []
        merged_label = []

        for ref in ref_group:
            match = re.match(r'([가-힣]+)\s*(\d+):([\d,\-\s]+)', ref)
            if not match:
                continue
            abbr, chapter, verses = match.groups()
            book = bible_book_abbreviations.get(abbr, abbr)
            chapter_idx = int(chapter) - 1
            chapter_data = data.get(book, [])

            if chapter_idx >= len(chapter_data):
                continue

            chapter_content = chapter_data[chapter_idx]

            if '-' in verses:
                start, end = map(int, verses.split('-'))
                count = end - start + 1
                if end > len(chapter_content):
                    continue
                if count >= 3:
                    for i in range(start, end + 1, 3):
                        chunk_start = i
                        chunk_end = min(i + 2, end)
                        verse_texts = [chapter_content[v - 1] for v in range(chunk_start, chunk_end + 1)]
                        label = f"{book} {chapter}:{chunk_start}-{chunk_end}\n" if chunk_start != chunk_end else f"{book} {chapter}:{chunk_start}\n"
                        content = '\n'.join(verse_texts)
                        result.append([label, content])
                    break  # 한 ref_group에서 분할이 일어나면 나머지는 무시
                else:
                    verse_text = '\n'.join(chapter_content[v - 1] for v in range(start, end + 1))
                    merged_label.append(f"{book} {chapter}:{start}-{end}\n")
                    merged_verses.append(verse_text)
            elif ',' in verses:
                verse_numbers = [int(v.strip()) for v in verses.split(',')]
                verse_text = '\n'.join(chapter_content[v - 1] for v in verse_numbers if v <= len(chapter_content))
                merged_label.append(f"{book} {chapter}:{','.join(map(str, verse_numbers))}\n")
                merged_verses.append(verse_text)
            else:
                v = int(verses)
                if v > len(chapter_content):
                    continue
                verse_text = chapter_content[v - 1]
                merged_label.append(f"{book} {chapter}:{v}\n")
                merged_verses.append(verse_text)
        else:
            # 분할이 없었을 때만 병합
            label = ''.join(merged_label)
            content = '\n'.join(merged_verses)
            if label and content:
                result.append([label, content])

    return result

# '-'로 이어진 구절이 3개 이상이면 3개씩 묶어서 별개의 리스트로 나누는 함수
def split_long_range_refs(grouped_refs, threshold=3):
    new_grouped_refs = []
    for ref_group in grouped_refs:
        split_groups = []
        for ref in ref_group:
            match = re.match(r'([가-힣]+)\s*(\d+):([\d,\-\s]+)', ref)
            if match:
                abbr, chapter, verses = match.groups()
                if '-' in verses:
                    parts = verses.split('-')
                    if len(parts) == 2:
                        start, end = map(int, parts)
                        count = end - start + 1
                        if count >= threshold:
                            # 분할된 각 덩어리를 새로운 그룹으로 추가
                            for i in range(start, end + 1, threshold):
                                chunk_start = i
                                chunk_end = min(i + threshold - 1, end)
                                if chunk_start == chunk_end:
                                    split_groups.append([f"{abbr} {chapter}:{chunk_start}"])
                                else:
                                    split_groups.append([f"{abbr} {chapter}:{chunk_start}-{chunk_end}"])
                            break  # 한 ref_group에서 분할이 일어나면 나머지는 무시
        else:
            # 분할이 없으면 원래 그룹을 그대로 추가
            split_groups.append(ref_group)
        new_grouped_refs.extend(split_groups)
    return new_grouped_refs