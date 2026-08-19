import os
import re
import pickle
import sys

# --- 경로 설정 및 PKL 로더 ---
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def load_bible_data(pkl_path):
    path = resource_path(pkl_path)
    if not os.path.exists(path):
        raise FileNotFoundError(f"PKL 파일을 찾을 수 없습니다: {path}")
    with open(path, 'rb') as f:
        return pickle.load(f)

# --- 매핑 데이터 ---
book_abbr_map = {'창': '창세기','출': '출애굽기','레': '레위기','민': '민수기','신': '신명기','수': '여호수아','삿': '사사기','룻': '룻기','삼상': '사무엘상','삼하': '사무엘하','왕상': '열왕기상','왕하': '열왕기하','대상': '역대상','대하': '역대하','스': '에스라','느': '느헤미야','에': '에스더','욥': '욥기','시': '시편','잠': '잠언','전': '전도서','아': '아가','사': '이사야','렘': '예레미야','애': '예레미야애가','겔': '에스겔','단': '다니엘','호': '호세아','욜': '요엘','암': '아모스','옵': '오바댜','욘': '요나','미': '미가','나': '나훔','합': '하박국','습': '스바냐','학': '학개','슥': '스가랴','말': '말라기','마': '마태복음','막': '마가복음','눅': '누가복음','요': '요한복음','행': '사도행전','롬': '로마서','고전': '고린도전서','고후': '고린도후서','갈': '갈라디아서','엡': '에베소서','빌': '빌립보서','골': '골로새서','살전': '데살로니가전서','살후': '데살로니가후서','딤전': '디모데전서','딤후': '디모데후서','딛': '디도서','몬': '빌레몬서','히': '히브리서','약': '야고보서','벧전': '베드로전서','벧후': '베드로후서','요일': '요한일서','요이': '요한이서','요삼': '요한삼서','유': '유다서','계': '요한계시록'}
bible_book_abbreviations = {k: v for k, v in zip(book_abbr_map.keys(), ['Gen', 'Exo', 'Lev', 'Num', 'Deu', 'Jos', 'Jdg', 'Rut', '1Sa', '2Sa', '1Ki', '2Ki', '1Ch', '2Ch', 'Ezr', 'Neh', 'Est', 'Job', 'Psa', 'Pro', 'Ecc', 'Sol', 'Isa', 'Jer', 'Lam', 'Eze', 'Dan', 'Hos', 'Joe', 'Amo', 'Oba', 'Jon', 'Mic', 'Nah', 'Hab', 'Zep', 'Hag', 'Zec', 'Mal', 'Mat', 'Mar', 'Luk', 'Joh', 'Act', 'Rom', '1Co', '2Co', 'Gal', 'Eph', 'Phi', 'Col', '1Th', '2Th', '1Ti', '2Ti', 'Tit', 'Phm', 'Heb', 'Jam', '1Pe', '2Pe', '1Jo', '2Jo', '3Jo', 'Jud', 'Rev'])}

# ------------------------- 텍스트 파싱 -------------------------

import re

def process_text_with_format(input_text):
    """
    입력 예시:
    1. 창 1:1 '태초에' 굵게
    2. 창 1:1 "태초에 하나님이" 굵게
    3. 창 1:1 “하나님이 세상을” 밑줄
    
    반환: {"address": 주소, "keyword": 키워드, "action": "밑줄"/"굵게", "font_override": 폰트명}
    """
    # 1. 스마트 따옴표(대칭형 따옴표)를 일반 따옴표로 통일
    text = input_text.strip()
    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")

    # 2. 정규표현식 수정
    # [^'\"]+? : 따옴표가 나오기 전까지의 주소 부분
    # ['\"](.*?)['\"] : 따옴표(' 또는 ") 내부의 키워드 (문장 포함)
    # \s+([^\s]+) : 키워드 뒤 공백 이후의 옵션(서식 또는 폰트명)
    pattern = r"^([^'\"]+?)(?:\s+['\"](.*?)['\"]\s+([^\s]+))?$"
    
    match = re.search(pattern, text)
    
    if match:
        addr = match.group(1).strip()
        kw = match.group(2)
        opt = match.group(3)
        
        action = opt if opt in ["밑줄", "굵게"] else None
        font_override = opt if opt and opt not in ["밑줄", "굵게"] else None
        
        return {
            "address": addr, 
            "keyword": kw, 
            "action": action, 
            "font_override": font_override
        }
    
    return {"address": text, "keyword": None, "action": None, "font_override": None}

def parse_multi_refs_line(text):
    lines = text.strip().split('\n')
    grouped_refs = []
    for line in lines:
        parts = line.strip().split(' ', 1)
        if len(parts) < 2: continue
        ref_items_raw = [r.strip() for r in parts[1].split('    ')]
        ref_items = [process_text_with_format(r) for r in ref_items_raw]
        grouped_refs.append(ref_items)
    return grouped_refs

# ------------------------- 데이터 추출 -------------------------

def extract_passages_grouped_core(data, grouped_refs, is_eng=False):
    result = []
    map_dict = bible_book_abbreviations if is_eng else book_abbr_map

    for ref_group in grouped_refs:
        merged_verses, merged_label = [], []
        fmt_info = {"keyword": None, "action": None, "font_override": None}

        for item in ref_group:
            ref = item["address"]
            if item["keyword"]:
                fmt_info = {"keyword": item["keyword"], "action": item["action"], "font_override": item["font_override"]}

            match = re.match(r'([가-힣]+)\s*(\d+):([\d,\-\s]+)', ref)
            if not match: continue
            abbr, chapter, verses = match.groups()
            book = map_dict.get(abbr, abbr)
            ch_idx = int(chapter) - 1
            if book not in data or ch_idx >= len(data[book]): continue
            ch_content = data[book][ch_idx]

            if '-' in verses:
                start, end = map(int, verses.split('-'))
                v_text = [ch_content[v-1] for v in range(start, end+1) if v <= len(ch_content)]
                merged_label.append(f"{book} {chapter}:{start}-{end}\n")
                merged_verses.extend(v_text)
            elif ',' in verses:
                v_nums = [int(v.strip()) for v in verses.split(',')]
                v_text = [ch_content[v-1] for v in v_nums if v <= len(ch_content)]
                merged_label.append(f"{book} {chapter}:{','.join(map(str, v_nums))}\n")
                merged_verses.extend(v_text)
            else:
                v = int(verses)
                if v <= len(ch_content):
                    merged_label.append(f"{book} {chapter}:{v}\n")
                    merged_verses.append(ch_content[v-1])

        label = ''.join(merged_label)
        if '-' in label and len(merged_verses) >= 3:
            for i in range(0, len(merged_verses), 3):
                result.append((label, '\n'.join(merged_verses[i:i+3]), fmt_info))
        else:
            result.append((label, '\n'.join(merged_verses), fmt_info))
    return result

def extract_passages_grouped(data, grouped_refs):
    return extract_passages_grouped_core(data, grouped_refs, is_eng=False)

def extract_passages_grouped_eng(data, grouped_refs):
    return extract_passages_grouped_core(data, grouped_refs, is_eng=True)