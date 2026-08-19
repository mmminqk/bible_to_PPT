import os
import re
import pickle
import sys

# --- 경로 설정 (PyInstaller 환경 대응) ---
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def absolute_path(file_path):
    if os.path.isabs(file_path):
        return file_path
    return os.path.abspath(file_path)

# --- 성경 매핑 정보 (기존 유지) ---
book_abbr_map = {'창': '창세기','출': '출애굽기','레': '레위기','민': '민수기','신': '신명기','수': '여호수아','삿': '사사기','룻': '룻기','삼상': '사무엘상','삼하': '사무엘하','왕상': '열왕기상','왕하': '열왕기하','대상': '역대상','대하': '역대하','스': '에스라','느': '느헤미야','에': '에스더','욥': '욥기','시': '시편','잠': '잠언','전': '전도서','아': '아가','사': '이사야','렘': '예레미야','애': '예레미야애가','겔': '에스겔','단': '다니엘','호': '호세아','욜': '요엘','암': '아모스','옵': '오바댜','욘': '요나','미': '미가','나': '나훔','합': '하박국','습': '스바냐','학': '학개','슥': '스가랴','말': '말라기','마': '마태복음','막': '마가복음','눅': '누가복음','요': '요한복음','행': '사도행전','롬': '로마서','고전': '고린도전서','고후': '고린도후서','갈': '갈라디아서','엡': '에베소서','빌': '빌립보서','골': '골로새서','살전': '데살로니가전서','살후': '데살로니가후서','딤전': '디모데전서','딤후': '디모데후서','딛': '디도서','몬': '빌레몬서','히': '히브리서','약': '야고보서','벧전': '베드로전서','벧후': '베드로후서','요일': '요한일서','요이': '요한이서','요삼': '요한삼서','유': '유다서','계': '요한계시록'}

bible_book_abbreviations = {
    '창': 'Gen', '출': 'Exo', '레': 'Lev', '민': 'Num', '신': 'Deu', '수': 'Jos', '삿': 'Jdg', '룻': 'Rut', '삼상': '1Sa', '삼하': '2Sa', '왕상': '1Ki', '왕하': '2Ki', '대상': '1Ch', '대하': '2Ch', '스': 'Ezr', '느': 'Neh', '에': 'Est', '욥': 'Job', '시': 'Psa', '잠': 'Pro', '전': 'Ecc', '아': 'Sol', '사': 'Isa', '렘': 'Jer', '애': 'Lam', '겔': 'Eze', '단': 'Dan', '호': 'Hos', '욜': 'Joe', '암': 'Amo', '옵': 'Oba', '욘': 'Jon', '미': 'Mic', '나': 'Nah', '합': 'Hab', '습': 'Zep', '학': 'Hag', '슥': 'Zec', '말': 'Mal', '마': 'Mat', '막': 'Mar', '눅': 'Luk', '요': 'Joh', '행': 'Act', '롬': 'Rom', '고전': '1Co', '고후': '2Co', '갈': 'Gal', '엡': 'Eph', '빌': 'Phi', '골': 'Col', '살전': '1Th', '살후': '2Th', '딤전': '1Ti', '딤후': '2Ti', '딛': 'Tit', '몬': 'Phm', '히': 'Heb', '약': 'Jam', '벧전': '1Pe', '벧후': '2Pe', '요일': '1Jo', '요이': '2Jo', '요삼': '3Jo', '유': 'Jud', '계': 'Rev'
}

# ------------------------- PKL 로더 -------------------------

def load_bible_data(pkl_path):
    """PKL 파일을 로드하여 딕셔너리 반환"""
    path = resource_path(pkl_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"PKL 파일을 찾을 수 없습니다: {path}")
    with open(path, 'rb') as f:
        return pickle.load(f)

# ------------------------- 텍스트 파싱 로직 (유지) -------------------------

def process_text(input_text):
    pattern = r"^(.*?)\s+'.*"
    match = re.search(pattern, input_text)
    return match.group(1).strip() if match else input_text.strip()

def parse_multi_refs_line(text):
    lines = text.strip().split('\n')
    grouped_refs = []
    for line in lines:
        parts = line.strip().split(' ', 1)
        if len(parts) < 2: continue
        ref_text = parts[1]
        ref_items = [r.strip() for r in ref_text.split('    ')]
        grouped_refs.append(ref_items)
    return grouped_refs

def parse_passages(ref_string):
    parts = [part.strip() for part in ref_string.split(';') if part.strip()]
    result = []
    current_book = None
    for part in parts:
        match = re.match(r'^([가-힣]+)\s*(\d+:\d[\d,\-\s]*)$', part)
        if match:
            current_book = match.group(1)
            passage = match.group(2).strip()
            result.append(f"{current_book} {passage}")
        elif current_book:
            result.append(f"{current_book} {part}")
    return result

# ------------------------- 데이터 추출 (PKL 데이터 기반) -------------------------

def extract_passages_grouped(data, grouped_refs):
    """한글 PK리 데이터를 바탕으로 구절 추출"""
    result = []
    for ref_group in grouped_refs:
        merged_verses, merged_label = [], []
        
        # 인용구 처리
        for ref in ref_group:
            if ref.startswith('<인용구>'):
                merged_label.append(f"{ref[:5]}\n")
                merged_verses.append(ref[5:])

        for ref in ref_group:
            # 세미콜론 포함 다중 구절 처리
            if ';' in ref:
                for p in parse_passages(ref):
                    match = re.match(r'([가-힣]+)\s*(\d+):([\d,\-\s]+)', p)
                    if not match: continue
                    abbr, chapter, verses = match.groups()
                    book = book_abbr_map.get(abbr, abbr)
                    chapter_idx, v_idx = int(chapter) - 1, int(verses) - 1
                    
                    if book in data and chapter_idx < len(data[book]) and v_idx < len(data[book][chapter_idx]):
                        merged_label.append(f"{book} {chapter}:{verses}\n")
                        merged_verses.append(data[book][chapter_idx][v_idx])
                continue

            # 일반 구절 처리
            match = re.match(r'([가-힣]+)\s*(\d+):([\d,\-\s]+)', ref)
            if not match: continue
            abbr, chapter, verses = match.groups()
            book = book_abbr_map.get(abbr, abbr)
            chapter_idx = int(chapter) - 1
            
            if book not in data or chapter_idx >= len(data[book]): continue
            chapter_content = data[book][chapter_idx]

            if '-' in verses:
                start, end = map(int, verses.split('-'))
                verse_text = [chapter_content[v - 1] for v in range(start, end + 1) if v <= len(chapter_content)]
                merged_label.append(f"{book} {chapter}:{start}-{end}\n")
                merged_verses.extend(verse_text)
            elif ',' in verses:
                v_nums = [int(v.strip()) for v in verses.split(',')]
                verse_text = [chapter_content[v - 1] for v in v_nums if v <= len(chapter_content)]
                merged_label.append(f"{book} {chapter}:{','.join(map(str, v_nums))}\n")
                merged_verses.extend(verse_text)
            else:
                v = int(verses)
                if v <= len(chapter_content):
                    merged_label.append(f"{book} {chapter}:{v}\n")
                    merged_verses.append(chapter_content[v - 1])

        # 슬라이드 분할 로직 (3절 단위)
        label = ''.join(merged_label)
        if '-' in label and len(merged_verses) >= 3:
            for i in range(0, len(merged_verses), 3):
                result.append([label, '\n'.join(merged_verses[i:i+3])])
        else:
            result.append([label, '\n'.join(merged_verses)])
    return result

# 영어용 추출 함수 (extract_passages_grouped_eng) 도 위와 동일한 방식으로 data를 활용하도록 유지
def extract_passages_grouped_eng(data, grouped_refs):
    """영어 PKL 데이터를 바탕으로 구절 추출"""
    result = []
    for ref_group in grouped_refs:
        merged_verses, merged_label = [], []
        for ref in ref_group:
            if ';' in ref:
                for p in parse_passages(ref):
                    match = re.match(r'([가-힣]+)\s*(\d+):([\d,\-\s]+)', p)
                    if not match: continue
                    abbr, chapter, verses = match.groups()
                    book = bible_book_abbreviations.get(abbr, abbr)
                    ch_idx, v_idx = int(chapter) - 1, int(verses) - 1
                    if book in data and ch_idx < len(data[book]) and v_idx < len(data[book][ch_idx]):
                        merged_label.append(f"{book} {chapter}:{verses}\n")
                        merged_verses.append(data[book][ch_idx][v_idx])
                continue

            match = re.match(r'([가-힣]+)\s*(\d+):([\d,\-\s]+)', ref)
            if not match: continue
            abbr, chapter, verses = match.groups()
            book = bible_book_abbreviations.get(abbr, abbr)
            ch_idx = int(chapter) - 1
            if book not in data or ch_idx >= len(data[book]): continue
            ch_content = data[book][ch_idx]

            if '-' in verses:
                start, end = map(int, verses.split('-'))
                verse_text = [ch_content[v - 1] for v in range(start, end + 1) if v <= len(ch_content)]
                merged_label.append(f"{book} {chapter}:{start}-{end}\n")
                merged_verses.extend(verse_text)
            elif ',' in verses:
                v_nums = [int(v.strip()) for v in verses.split(',')]
                verse_text = [ch_content[v - 1] for v in v_nums if v <= len(ch_content)]
                merged_label.append(f"{book} {chapter}:{','.join(map(str, v_nums))}\n")
                merged_verses.extend(verse_text)
            else:
                v = int(verses)
                if v <= len(ch_content):
                    merged_label.append(f"{book} {chapter}:{v}\n")
                    merged_verses.append(ch_content[v - 1])

        label = ''.join(merged_label)
        if '-' in label and len(merged_verses) >= 3:
            for i in range(0, len(merged_verses), 3):
                result.append([label, '\n'.join(merged_verses[i:i+3])])
        else:
            result.append([label, '\n'.join(merged_verses)])
    return result