'use strict';

const fs   = require('fs');
const path = require('path');

// ─── 경로 ─────────────────────────────────────────────────────────────────────
const ROOT           = path.join(__dirname, '..', '..');
const KOR_BIBLE_DIR  = path.join(ROOT, 'text_DB', '개역개정-text');
const ESV_BIBLE_FILE = path.join(ROOT, 'text_DB', 'ESV-text', 'ESV_cleaned.txt');

// ─── 성경 책 목록 ──────────────────────────────────────────────────────────────
const BIBLE_BOOKS = [
  '창세기','출애굽기','레위기','민수기','신명기','여호수아','사사기','룻기','사무엘상','사무엘하',
  '열왕기상','열왕기하','역대상','역대하','에스라','느헤미야','에스더','욥기','시편','잠언',
  '전도서','아가','이사야','예레미야','예레미야애가','에스겔','다니엘','호세아','요엘','아모스',
  '오바댜','요나','미가','나훔','하박국','스바냐','학개','스가랴','말라기','마태복음','마가복음',
  '누가복음','요한복음','사도행전','로마서','고린도전서','고린도후서','갈라디아서','에베소서','빌립보서','골로새서',
  '데살로니가전서','데살로니가후서','디모데전서','디모데후서','디도서','빌레몬서','히브리서','야고보서','베드로전서','베드로후서',
  '요한일서','요한이서','요한삼서','유다서','요한계시록',
];

// ─── 약어 맵 ──────────────────────────────────────────────────────────────────
const BOOK_ABBR_MAP = {
  '창':'창세기','출':'출애굽기','레':'레위기','민':'민수기','신':'신명기',
  '수':'여호수아','삿':'사사기','룻':'룻기','삼상':'사무엘상','삼하':'사무엘하',
  '왕상':'열왕기상','왕하':'열왕기하','대상':'역대상','대하':'역대하','스':'에스라',
  '느':'느헤미야','에':'에스더','욥':'욥기','시':'시편','잠':'잠언',
  '전':'전도서','아':'아가','사':'이사야','렘':'예레미야','애':'예레미야애가',
  '겔':'에스겔','단':'다니엘','호':'호세아','욜':'요엘','암':'아모스',
  '옵':'오바댜','욘':'요나','미':'미가','나':'나훔','합':'하박국',
  '습':'스바냐','학':'학개','슥':'스가랴','말':'말라기','마':'마태복음',
  '막':'마가복음','눅':'누가복음','요':'요한복음','행':'사도행전','롬':'로마서',
  '고전':'고린도전서','고후':'고린도후서','갈':'갈라디아서','엡':'에베소서',
  '빌':'빌립보서','골':'골로새서','살전':'데살로니가전서','살후':'데살로니가후서',
  '딤전':'디모데전서','딤후':'디모데후서','딛':'디도서','몬':'빌레몬서',
  '히':'히브리서','약':'야고보서','벧전':'베드로전서','벧후':'베드로후서',
  '요일':'요한일서','요이':'요한이서','요삼':'요한삼서','유':'유다서','계':'요한계시록',
};

const BOOK_ABBR_MAP_ESV = {
  '창': 'Gen', '출': 'Exod', '레': 'Lev', '민': 'Num', '신': 'Deut',
  '수': 'Josh', '삿': 'Judg', '룻': 'Ruth', '삼상': '1 Sam', '삼하': '2 Sam',
  '왕상': '1 Kgs', '왕하': '2 Kgs', '대상': '1 Chron', '대하': '2 Chron', '스': 'Ezra',
  '느': 'Neh', '에': 'Esth', '욥': 'Job', '시': 'Ps', '잠': 'Prov',
  '전': 'Eccl', '아': 'Song', '사': 'Isa', '렘': 'Jer', '애': 'Lam',
  '겔': 'Ezek', '단': 'Dan', '호': 'Hos', '욜': 'Joel', '암': 'Amos',
  '옵': 'Obad', '욘': 'Jonah', '미': 'Mic', '나': 'Nah', '합': 'Hab',
  '습': 'Zeph', '학': 'Hag', '슥': 'Zech', '말': 'Mal', '마': 'Matt',
  '막': 'Mark', '눅': 'Luke', '요': 'John', '행': 'Acts', '롬': 'Rom',
  '고전': '1 Cor', '고후': '2 Cor', '갈': 'Gal', '엡': 'Eph', '빌': 'Phil',
  '골': 'Col', '살전': '1 Thess', '살후': '2 Thess', '딤전': '1 Tim', '딤후': '2 Tim',
  '딛': 'Titus', '몬': 'Philem', '히': 'Heb', '약': 'James', '벧전': '1 Pet',
  '벧후': '2 Pet', '요일': '1 John', '요이': '2 John', '요삼': '3 John', '유': 'Jude', '계': 'Rev',
};

const ESV_DISPLAY_TO_RAW = {
  'Gen':'Gen','Exod':'Exo','Lev':'Lev','Num':'Num','Deut':'Deu',
  'Josh':'Jos','Judg':'Jdg','Ruth':'Rut','1 Sam':'1Sa','2 Sam':'2Sa',
  '1 Kgs':'1Ki','2 Kgs':'2Ki','1 Chron':'1Ch','2 Chron':'2Ch','Ezra':'Ezr',
  'Neh':'Neh','Esth':'Est','Job':'Job','Ps':'Psa','Prov':'Pro',
  'Eccl':'Ecc','Song':'Sol','Isa':'Isa','Jer':'Jer','Lam':'Lam',
  'Ezek':'Eze','Dan':'Dan','Hos':'Hos','Joel':'Joe','Amos':'Amo',
  'Obad':'Oba','Jonah':'Jon','Mic':'Mic','Nah':'Nah','Hab':'Hab',
  'Zeph':'Zep','Hag':'Hag','Zech':'Zec','Mal':'Mal','Matt':'Mat',
  'Mark':'Mar','Luke':'Luk','John':'Joh','Acts':'Act','Rom':'Rom',
  '1 Cor':'1Co','2 Cor':'2Co','Gal':'Gal','Eph':'Eph','Phil':'Phi',
  'Col':'Col','1 Thess':'1Th','2 Thess':'2Th','1 Tim':'1Ti','2 Tim':'2Ti',
  'Titus':'Tit','Philem':'Phm','Heb':'Heb','James':'Jam','1 Pet':'1Pe',
  '2 Pet':'2Pe','1 John':'1Jo','2 John':'2Jo','3 John':'3Jo','Jude':'Jud','Rev':'Rev',
};

// ─── 정규식 ───────────────────────────────────────────────────────────────────
const REF_PATTERN      = /^([가-힣]+)\s*(\d+):([\d,\-\s]+)/;
const REF_PATTERN_CHAP = /^([가-힣]+)\s*(\d+)$/;
const REF_PATTERN_CROSS_CHAP = /^([가-힣]+)\s*(\d+):(\d+)-(\d+):(\d+)/;
const EMPH_PATTERN     = /'([^']+)'\s*(굵게|밑줄)/g;

// ─── 강조 파싱 ────────────────────────────────────────────────────────────────
function parseEmphasisFromRef(rawRef) {
  const emphases = [];
  let m;
  const re = new RegExp(EMPH_PATTERN.source, 'g');
  while ((m = re.exec(rawRef)) !== null) {
    emphases.push({ text: m[1], kind: m[2] === '굵게' ? 'bold' : 'underline' });
  }
  const cleanRef = rawRef.replace(new RegExp(EMPH_PATTERN.source, 'g'), '').trim();
  return { cleanRef, emphases };
}

// ─── 캐시 유틸 ───────────────────────────────────────────────────────────────
function isCacheValid(cacheFile, ...sourceFiles) {
  if (!fs.existsSync(cacheFile)) return false;
  const cacheMtime = fs.statSync(cacheFile).mtimeMs;
  return sourceFiles.every(f => !fs.existsSync(f) || fs.statSync(f).mtimeMs <= cacheMtime);
}

// ─── 성경 로딩 ────────────────────────────────────────────────────────────────
function readFilesInDirectory(dir) {
  return fs.readdirSync(dir)
    .filter(f => f.endsWith('.txt'))
    .sort()
    .map(f => fs.readFileSync(path.join(dir, f), 'utf-8'));
}

function splitAndFormatVerses(bibleDict) {
  const result = {};
  for (const [book, raw] of Object.entries(bibleDict)) {
    const chapMap = {};
    for (const line of raw.split('\n')) {
      const m = line.match(/[가-힣]+(\d+):(\d+)\s+(.*)/);
      if (m) {
        const chap = parseInt(m[1]);
        if (!chapMap[chap]) chapMap[chap] = [];
        chapMap[chap].push(`${m[2]} ${m[3]}`);
      }
    }
    result[book] = Object.keys(chapMap)
      .sort((a, b) => parseInt(a) - parseInt(b))
      .map(k => chapMap[k]);
  }
  return result;
}

function loadKorBible() {
  const cacheFile = path.join(KOR_BIBLE_DIR, '_cache_kor.json');
  const txtFiles  = fs.readdirSync(KOR_BIBLE_DIR)
    .filter(f => f.endsWith('.txt'))
    .map(f => path.join(KOR_BIBLE_DIR, f));

  if (isCacheValid(cacheFile, ...txtFiles)) {
    return JSON.parse(fs.readFileSync(cacheFile, 'utf-8'));
  }

  const texts     = readFilesInDirectory(KOR_BIBLE_DIR);
  const bibleDict = Object.fromEntries(BIBLE_BOOKS.map((book, i) => [book, texts[i]]));
  const formatted = splitAndFormatVerses(bibleDict);
  fs.writeFileSync(cacheFile, JSON.stringify(formatted));
  return formatted;
}

function loadEsvBible() {
  const cacheFile = path.join(path.dirname(ESV_BIBLE_FILE), '_cache_esv.json');

  const ensureEsvAliases = (dict) => {
    for (const [disp, raw] of Object.entries(ESV_DISPLAY_TO_RAW)) {
      if (dict[raw] && !dict[disp]) {
        dict[disp] = dict[raw];
      }
    }
  };

  if (isCacheValid(cacheFile, ESV_BIBLE_FILE)) {
    const cached = JSON.parse(fs.readFileSync(cacheFile, 'utf-8'));
    ensureEsvAliases(cached);
    return cached;
  }

  const raw = {};
  for (const line of fs.readFileSync(ESV_BIBLE_FILE, 'utf-8').split('\n')) {
    const m = line.trim().match(/^([A-Za-z0-9]+\.?)\s+(\d+):(\d+)\s+(.*)/);
    if (m) {
      const [, book, chap, verse, text] = m;
      if (!raw[book]) raw[book] = {};
      const c = parseInt(chap);
      if (!raw[book][c]) raw[book][c] = [];
      raw[book][c].push(`${verse} ${text.trim()}`);
    }
  }

  const result = {};
  for (const [book, chapters] of Object.entries(raw)) {
    const maxChap = Math.max(...Object.keys(chapters).map(Number));
    result[book] = Array.from({ length: maxChap }, (_, i) => chapters[i + 1] || []);
  }
  ensureEsvAliases(result);
  fs.writeFileSync(cacheFile, JSON.stringify(result));
  return result;
}

// ─── 입력 파싱 ────────────────────────────────────────────────────────────────
function parseMultiRefsLine(text) {
  const grouped = [];
  for (const line of text.replace(/–/g, '-').trim().split('\n')) {
    const trimmed = line.trim();
    const idx = trimmed.indexOf(' ');
    if (idx === -1) continue;
    const refPart = trimmed.slice(idx + 1).trim();
    const refs = refPart.split('    ').map(r => r.trim()).filter(Boolean);
    if (refs.length) grouped.push(refs);
  }
  return grouped;
}

function splitSemicolonRefs(refString, initialBook = null) {
  const result = [];
  let currentBook = initialBook;
  for (const part of refString.split(';').map(p => p.trim()).filter(Boolean)) {
    const { cleanRef, emphases } = parseEmphasisFromRef(part);
    let baseRef = cleanRef;

    // 0. 책 + 장:절-장:절 (장 넘김 범위)
    let mCross = cleanRef.match(/^([가-힣]+)\s*(\d+:\d+-\d+:\d+)$/);
    if (mCross) {
      currentBook = mCross[1];
      baseRef = `${mCross[1]} ${mCross[2]}`;
    } else {
      // 1. 책 + 장:절
      let m = cleanRef.match(/^([가-힣]+)\s*(\d+:\d[\d,\-\s]*)$/);
      if (m) {
        currentBook = m[1];
        baseRef = `${m[1]} ${m[2].trim()}`;
      } else {
        // 2. 책 + 장 (장 전체)
        let mChap = cleanRef.match(/^([가-힣]+)\s*(\d+)$/);
        if (mChap) {
          currentBook = mChap[1];
          baseRef = `${mChap[1]} ${mChap[2]}`;
        } else {
          // 3. 책 없는 장:절
          let mVerse = cleanRef.match(/^(\d+:\d[\d,\-\s]*)$/);
          if (mVerse) {
            if (!currentBook) throw new Error(`책 이름 없이 구절 파싱 불가: '${part}'`);
            baseRef = `${currentBook} ${mVerse[1].trim()}`;
          } else {
            // 4. 책 없는 장
            let mChapOnly = cleanRef.match(/^(\d+)$/);
            if (mChapOnly) {
              if (!currentBook) throw new Error(`책 이름 없이 구절 파싱 불가: '${part}'`);
              baseRef = `${currentBook} ${mChapOnly[1]}`;
            }
          }
        }
      }
    }

    let emphStr = '';
    for (const emp of emphases) {
      emphStr += ` '${emp.text}' ${emp.kind === 'bold' ? '굵게' : '밑줄'}`;
    }
    result.push(`${baseRef}${emphStr}`);
  }
  return result;
}

function parsePassages(refString) {
  return splitSemicolonRefs(refString).map(r => parseEmphasisFromRef(r).cleanRef);
}

// ─── 구절 조회 ────────────────────────────────────────────────────────────────
function resolveVerseNums(versesStr) {
  const s = versesStr.trim();
  if (s.includes('-')) {
    const [start, end] = s.split('-').map(Number);
    return { nums: Array.from({ length: end - start + 1 }, (_, i) => start + i), label: `${start}-${end}` };
  }
  if (s.includes(',')) {
    const nums = s.split(',').map(v => parseInt(v.trim()));
    return { nums, label: nums.join(',') };
  }
  const v = parseInt(s);
  return { nums: [v], label: String(v) };
}

function getChapterData(data, book) {
  if (!data || !book) return [];
  if (data[book]) return data[book];
  const raw = ESV_DISPLAY_TO_RAW[book];
  if (raw && data[raw]) return data[raw];
  return [];
}

function lookupVerses(data, abbr, chapter, versesStr, bookMap) {
  const book       = bookMap[abbr] ?? abbr;
  const chapIdx    = parseInt(chapter) - 1;
  const chapData   = getChapterData(data, book)[chapIdx] || [];
  if (!chapData.length) return null;

  const { nums, label } = resolveVerseNums(versesStr);
  const texts = nums.filter(v => v <= chapData.length).map(v => chapData[v - 1]);
  if (!texts.length) return null;
  return { label: `${book} ${chapter}:${label}\n`, texts };
}

function lookupWholeChapter(data, abbr, chapter, bookMap) {
  const book    = bookMap[abbr] ?? abbr;
  const chapIdx = parseInt(chapter) - 1;
  const verses  = getChapterData(data, book)[chapIdx] || [];
  if (!verses.length) return [];
  return [{ label: `${book} ${chapter}:1-${verses.length}\n`, texts: verses }];
}

function lookupCrossChapterVerses(data, abbr, ch1, v1, ch2, v2, bookMap) {
  const book = bookMap[abbr] ?? abbr;
  const results = [];

  for (let ch = parseInt(ch1); ch <= parseInt(ch2); ch++) {
    const chapIdx = ch - 1;
    const chapData = getChapterData(data, book)[chapIdx] || [];
    if (!chapData.length) continue;

    let startV, endV;
    if (ch === parseInt(ch1) && ch === parseInt(ch2)) {
      startV = parseInt(v1);
      endV = parseInt(v2);
    } else if (ch === parseInt(ch1)) {
      startV = parseInt(v1);
      endV = chapData.length;
    } else if (ch === parseInt(ch2)) {
      startV = 1;
      endV = parseInt(v2);
    } else {
      startV = 1;
      endV = chapData.length;
    }

    const texts = [];
    for (let v = startV; v <= Math.min(endV, chapData.length); v++) {
      texts.push(chapData[v - 1]);
    }
    if (texts.length) {
      const labelVerses = startV === endV ? String(startV) : `${startV}-${endV}`;
      const label = `${book} ${ch}:${labelVerses}\n`;
      results.push({ label, texts });
    }
  }
  return results;
}

function extractRef(data, ref, bookMap) {
  const { cleanRef } = parseEmphasisFromRef(ref);

  if (cleanRef.includes(';')) {
    const results = [];
    for (const p of parsePassages(cleanRef)) {
      // 장 넘김 범위 먼저 시도
      let m = p.match(REF_PATTERN_CROSS_CHAP);
      if (m) {
        results.push(...lookupCrossChapterVerses(data, m[1], m[2], m[3], m[4], m[5], bookMap));
        continue;
      }
      m = p.match(REF_PATTERN);
      if (m) {
        const item = lookupVerses(data, m[1], m[2], m[3], bookMap);
        if (item) results.push(item);
        continue;
      }
      m = p.trim().match(REF_PATTERN_CHAP);
      if (m) results.push(...lookupWholeChapter(data, m[1], m[2], bookMap));
    }
    return results;
  }

  // 장 넘김 범위 먼저 시도
  let m = cleanRef.trim().match(REF_PATTERN_CROSS_CHAP);
  if (m) return lookupCrossChapterVerses(data, m[1], m[2], m[3], m[4], m[5], bookMap);

  m = cleanRef.trim().match(REF_PATTERN);
  if (m) {
    const item = lookupVerses(data, m[1], m[2], m[3], bookMap);
    return item ? [item] : [];
  }
  m = cleanRef.trim().match(REF_PATTERN_CHAP);
  if (m) return lookupWholeChapter(data, m[1], m[2], bookMap);
  return [];
}

// ─── 세미콜론 분리 로직 ───────────────────────────────────────────────────────
function expandRefGroup(refGroup) {
  const expanded = [];
  let currentBook = null;
  for (const ref of refGroup) {
    if (!ref.trim()) continue;
    if (ref.includes(';')) {
      const subRefs = splitSemicolonRefs(ref, currentBook);
      for (const subRef of subRefs) {
        const { cleanRef } = parseEmphasisFromRef(subRef);
        const m = cleanRef.trim().match(/^([가-힣]+)/);
        if (m) currentBook = m[1];
        expanded.push([subRef]);
      }
    } else {
      const { cleanRef } = parseEmphasisFromRef(ref);
      const m = cleanRef.trim().match(/^([가-힣]+)/);
      if (m) currentBook = m[1];
      expanded.push([ref]);
    }
  }
  return expanded;
}

// ─── 슬라이드 텍스트박스 물리 치수 및 줄바꿈/높이 기반 청킹 ───────────────────────
// 템플릿(template.pptx) 우측 패널 기준: 너비 7.93", 한글~영어 간격 3.92" (282.2pt), 영어~하단 간격 3.13" (225.4pt)
const KOR_BASE_CAPACITY = 200;  // 한글 26pt 기준 약 200자 (약 7~7.5줄)
const ENG_BASE_CAPACITY = 400;  // 영어 18pt 기준 약 400자 (약 7.5~8.5줄)

const KOR_LINE_WIDTH_PT = 548.0;
const ENG_LINE_WIDTH_PT = 545.0;

const KOR_TARGET_HEIGHT_PT  = 264.0;
const KOR_CEILING_HEIGHT_PT = 268.0;

const ENG_TARGET_HEIGHT_PT  = 209.0;
const ENG_CEILING_HEIGHT_PT = 214.0;

function estimateSlideCapacity(fontSize, isEnglish = false) {
  const baseCap = isEnglish ? ENG_BASE_CAPACITY : KOR_BASE_CAPACITY;
  const baseSize = isEnglish ? 18 : 26;
  if (!fontSize || fontSize <= 0) fontSize = baseSize;
  return Math.round(baseCap * (baseSize / fontSize) ** 2);
}

function charEmWidth(ch) {
  const o = ch.codePointAt(0);
  if (ch === ' ') return 0.246;
  if ('.,!?;:\'"()[]{}<>-·'.includes(ch)) return 0.258;
  if ((o >= 0xAC00 && o <= 0xD7A3) || (o >= 0x3130 && o <= 0x318F) || (o >= 0x4E00 && o <= 0x9FFF)) {
    return 0.935;
  }
  if (ch >= 'A' && ch <= 'Z') return 0.640;
  if (ch >= 'a' && ch <= 'z') return 0.520;
  if (ch >= '0' && ch <= '9') return 0.477;
  return 0.520;
}

function estimateVerseLines(verseText, fontSize = 26, isEnglish = false) {
  if (!verseText || !verseText.trim()) return 0;
  if (!fontSize || fontSize <= 0) fontSize = isEnglish ? 18 : 26;

  const s = verseText.trim();
  const spaceIdx = s.indexOf(' ');
  let body = s;
  let prefixW = 0.0;
  if (spaceIdx > 0) {
    const numStr = s.slice(0, spaceIdx);
    if (/^\d+$/.test(numStr)) {
      body = s.slice(spaceIdx + 1);
      prefixW = (numStr.length * 0.423 + 0.246) * fontSize;
    }
  }

  if (!isEnglish) {
    let sumEm = 0;
    for (const c of body) sumEm += charEmWidth(c);
    const totalW = prefixW + sumEm * fontSize;
    return Math.max(1, Math.ceil(totalW / KOR_LINE_WIDTH_PT));
  } else {
    let sumEm = 0;
    for (const c of body) sumEm += charEmWidth(c);
    const totalW = prefixW + sumEm * fontSize;
    const charLines = Math.max(1, Math.ceil(totalW / ENG_LINE_WIDTH_PT));

    const words = body.split(' ');
    let wordLines = 1;
    let curW = prefixW;
    const spaceW = 0.246 * fontSize;
    for (const w of words) {
      let wEm = 0;
      for (const c of w) wEm += charEmWidth(c);
      const ww = wEm * fontSize;
      if (curW <= prefixW && wordLines === 1) {
        curW += ww;
      } else if (curW + spaceW + ww <= ENG_LINE_WIDTH_PT + 10.0) {
        curW += spaceW + ww;
      } else {
        wordLines += 1;
        curW = ww;
      }
    }
    return Math.max(charLines, wordLines);
  }
}

function estimateChunkHeightPt(lineCounts, fontSize = 26) {
  if (!lineCounts || !lineCounts.length) return 0.0;
  const totalLines = lineCounts.reduce((a, b) => a + b, 0);
  if (totalLines === 0) return 0.0;
  if (!fontSize || fontSize <= 0) fontSize = 26;
  const nParas = lineCounts.length;
  const linesH = fontSize * (1.22 + 1.40 * (totalLines - 1));
  return 4.0 + linesH + Math.max(0, nParas - 1) * 3.0;
}

// ─── 청크 분할 ────────────────────────────────────────────────────────────────
function partitionVerses(kTexts, eTexts = null, korCap = null, engCap = null, korFontSize = 26, engFontSize = 18) {
  const n = Math.max(kTexts ? kTexts.length : 0, eTexts ? eTexts.length : 0);
  if (n === 0) return [];
  if (n === 1) return [[0]];

  const hasK = Boolean(kTexts && kTexts.length);
  const hasE = Boolean(eTexts && eTexts.length);

  const kFs = (korFontSize && korFontSize > 0) ? korFontSize : 26;
  const eFs = (engFontSize && engFontSize > 0) ? engFontSize : 18;

  const kScale = (korCap !== null && korFontSize === 26) ? (korCap / KOR_BASE_CAPACITY) : 1.0;
  const eScale = (engCap !== null && engFontSize === 18) ? (engCap / ENG_BASE_CAPACITY) : 1.0;

  const kLines = Array.from({ length: n }, (_, i) => (hasK && i < kTexts.length ? estimateVerseLines(kTexts[i], kFs, false) : 0));
  const eLines = Array.from({ length: n }, (_, i) => (hasE && i < eTexts.length ? estimateVerseLines(eTexts[i], eFs, true) : 0));

  function fits(indices, useCeiling = false) {
    const kLim = (useCeiling ? KOR_CEILING_HEIGHT_PT : KOR_TARGET_HEIGHT_PT) * kScale;
    const eLim = (useCeiling ? ENG_CEILING_HEIGHT_PT : ENG_TARGET_HEIGHT_PT) * eScale;
    if (hasK) {
      const kh = estimateChunkHeightPt(indices.map(i => kLines[i]), kFs);
      if (kh > kLim) return false;
    }
    if (hasE) {
      const eh = estimateChunkHeightPt(indices.map(i => eLines[i]), eFs);
      if (eh > eLim) return false;
    }
    return true;
  }

  const chunks = [];
  let cur = [];
  let i = 0;
  while (i < n) {
    const candidate = [...cur, i];
    if (cur.length === 0 || fits(candidate, false)) {
      cur.push(i);
      i += 1;
    } else {
      const curIsSingleShort = (
        cur.length === 1 &&
        (!hasK || kLines[cur[0]] <= 2) &&
        (!hasE || eLines[cur[0]] <= 2)
      );
      const isLastVerse = (n - i === 1);
      if ((isLastVerse || curIsSingleShort) && fits(candidate, true)) {
        cur.push(i);
        i += 1;
      } else {
        chunks.push(cur);
        cur = [i];
        i += 1;
      }
    }
  }
  if (cur.length) chunks.push(cur);

  if (chunks.length >= 2 && chunks[chunks.length - 1].length === 1) {
    const lastIdx = chunks[chunks.length - 1][0];
    const prevChunk = chunks[chunks.length - 2];
    if (fits([...prevChunk, lastIdx], true)) {
      prevChunk.push(lastIdx);
      chunks.pop();
    } else if (prevChunk.length >= 3) {
      const isShortOrphan = (!hasK || kLines[lastIdx] <= 3) && (!hasE || eLines[lastIdx] <= 3);
      if (isShortOrphan) {
        const moved = prevChunk[prevChunk.length - 1];
        if (fits([moved, lastIdx], false)) {
          prevChunk.pop();
          chunks[chunks.length - 1].unshift(moved);
        }
      }
    }
  }

  return chunks;
}

function chunkAndAppend(result, label, mergedVerses, emphases, fontSize, isEnglish = false) {
  const defaultFs = isEnglish ? 18 : 26;
  const effFs = (fontSize && fontSize > 0) ? fontSize : defaultFs;

  if (!mergedVerses || !mergedVerses.length) return;

  // 절이 2개 이상일 때 실제 높이 기반 절 분할 시도
  if (mergedVerses.length >= 2) {
    const chunkIndices = isEnglish
      ? partitionVerses(null, mergedVerses, null, null, 26, effFs)
      : partitionVerses(mergedVerses, null, null, null, effFs, 18);
    if (chunkIndices.length > 1) {
      const mSingleChap = label.match(/^([^\n:]+\s+\d+):(\d+)-(\d+)/);
      for (const chunkIdx of chunkIndices) {
        const chunk = chunkIdx.map(i => mergedVerses[i]);
        let chunkLabel = label;
        if (mSingleChap) {
          const vStart = chunk[0].split(' ')[0];
          const vEnd   = chunk[chunk.length - 1].split(' ')[0];
          chunkLabel = vStart === vEnd
            ? `${mSingleChap[1]}:${vStart}\n`
            : `${mSingleChap[1]}:${vStart}-${vEnd}\n`;
        }
        result.push({ label: chunkLabel, verses: chunk.join('\n'), emphases });
      }
      return;
    }
  }
  result.push({ label, verses: mergedVerses.join('\n'), emphases });
}

// ─── 공개 추출 함수 ───────────────────────────────────────────────────────────
function _extractImpl(data, groupedRefs, bookMap, allowQuote = false, fontSize = null, isEnglish = false) {
  const result = [];
  for (const refGroup of groupedRefs) {
    for (const group of expandRefGroup(refGroup)) {
      for (const ref of group) {
        if (allowQuote && ref.startsWith('<인용구>')) {
          result.push({ label: '<인용구>\n', verses: ref.slice(5), emphases: [] });
          continue;
        }
        const { emphases } = parseEmphasisFromRef(ref);
        for (const { label, texts } of extractRef(data, ref, bookMap)) {
          chunkAndAppend(result, label, texts, emphases, fontSize, isEnglish);
        }
      }
    }
  }
  return result;
}

function extractPassagesGrouped(data, groupedRefs, fontSize) {
  return _extractImpl(data, groupedRefs, BOOK_ABBR_MAP, true, fontSize, false);
}

function extractPassagesGroupedEng(data, groupedRefs, fontSize) {
  return _extractImpl(data, groupedRefs, BOOK_ABBR_MAP_ESV, false, fontSize, true);
}

function extractPassagesSynchronized(korData, engData, groupedRefs, korFontSize = 26, engFontSize = 18) {
  if (!korData && !engData) return { korEntries: [], engEntries: [] };
  if (!korData) return { korEntries: [], engEntries: extractPassagesGroupedEng(engData, groupedRefs, engFontSize) };
  if (!engData) return { korEntries: extractPassagesGrouped(korData, groupedRefs, korFontSize), engEntries: [] };

  const kFs = (korFontSize && korFontSize > 0) ? korFontSize : 26;
  const eFs = (engFontSize && engFontSize > 0) ? engFontSize : 18;

  const korEntries = [];
  const engEntries = [];

  for (const refGroup of groupedRefs) {
    for (const group of expandRefGroup(refGroup)) {
      for (const ref of group) {
        if (ref.startsWith('<인용구>')) {
          korEntries.push({ label: '<인용구>\n', verses: ref.slice(5), emphases: [] });
          engEntries.push({ label: '', verses: '', emphases: [] });
          continue;
        }

        const { emphases } = parseEmphasisFromRef(ref);
        const kItems = extractRef(korData, ref, BOOK_ABBR_MAP);
        const eItems = extractRef(engData, ref, BOOK_ABBR_MAP_ESV);

        const numItems = Math.max(kItems.length, eItems.length);
        for (let idx = 0; idx < numItems; idx++) {
          const kItem = kItems[idx] || { label: '', texts: [] };
          const eItem = eItems[idx] || { label: '', texts: [] };

          const nVerses = Math.max(kItem.texts.length, eItem.texts.length);
          if (nVerses === 0) continue;

          const kList = Array.from({ length: nVerses }, (_, i) => kItem.texts[i] || '');
          const eList = Array.from({ length: nVerses }, (_, i) => eItem.texts[i] || '');
          const chunks = partitionVerses(kList, eList, null, null, kFs, eFs);

          for (const chunkIndices of chunks) {
            const kChunk = chunkIndices.filter(i => i < kItem.texts.length).map(i => kItem.texts[i]);
            const eChunk = chunkIndices.filter(i => i < eItem.texts.length).map(i => eItem.texts[i]);

            let actualKLabel = kItem.label;
            let actualELabel = eItem.label;

            if (chunks.length > 1) {
              const mK = kItem.label.match(/^([^\n:]+\s+\d+):(\d+)-(\d+)/);
              if (mK && kChunk.length) {
                const vsK = kChunk[0].split(' ')[0];
                const veK = kChunk[kChunk.length - 1].split(' ')[0];
                actualKLabel = vsK === veK ? `${mK[1]}:${vsK}\n` : `${mK[1]}:${vsK}-${veK}\n`;
              }

              const mE = eItem.label.match(/^([^\n:]+\s+\d+):(\d+)-(\d+)/);
              if (mE && eChunk.length) {
                const vsE = eChunk[0].split(' ')[0];
                const veE = eChunk[eChunk.length - 1].split(' ')[0];
                actualELabel = vsE === veE ? `${mE[1]}:${vsE}\n` : `${mE[1]}:${vsE}-${veE}\n`;
              }
            }

            korEntries.push({ label: actualKLabel, verses: kChunk.join('\n'), emphases });
            engEntries.push({ label: actualELabel, verses: eChunk.join('\n'), emphases });
          }
        }
      }
    }
  }

  return { korEntries, engEntries };
}

module.exports = {
  loadKorBible,
  loadEsvBible,
  parseMultiRefsLine,
  parseEmphasisFromRef,
  extractPassagesGrouped,
  extractPassagesGroupedEng,
  extractPassagesSynchronized,
};
