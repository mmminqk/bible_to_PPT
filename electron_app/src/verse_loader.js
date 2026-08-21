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
  '창':'Gen','출':'Exo','레':'Lev','민':'Num','신':'Deu',
  '수':'Jos','삿':'Jdg','룻':'Rut','삼상':'1Sa','삼하':'2Sa',
  '왕상':'1Ki','왕하':'2Ki','대상':'1Ch','대하':'2Ch','스':'Ezr',
  '느':'Neh','에':'Est','욥':'Job','시':'Psa','잠':'Pro',
  '전':'Ecc','아':'Sol','사':'Isa','렘':'Jer','애':'Lam',
  '겔':'Eze','단':'Dan','호':'Hos','욜':'Joe','암':'Amo',
  '옵':'Oba','욘':'Jon','미':'Mic','나':'Nah','합':'Hab',
  '습':'Zep','학':'Hag','슥':'Zec','말':'Mal','마':'Mat',
  '막':'Mar','눅':'Luk','요':'Joh','행':'Act','롬':'Rom',
  '고전':'1Co','고후':'2Co','갈':'Gal','엡':'Eph','빌':'Phi',
  '골':'Col','살전':'1Th','살후':'2Th','딤전':'1Ti','딤후':'2Ti',
  '딛':'Tit','몬':'Phm','히':'Heb','약':'Jam','벧전':'1Pe',
  '벧후':'2Pe','요일':'1Jo','요이':'2Jo','요삼':'3Jo','유':'Jud','계':'Rev',
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

  if (isCacheValid(cacheFile, ESV_BIBLE_FILE)) {
    return JSON.parse(fs.readFileSync(cacheFile, 'utf-8'));
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

function lookupVerses(data, abbr, chapter, versesStr, bookMap) {
  const book       = bookMap[abbr] ?? abbr;
  const chapIdx    = parseInt(chapter) - 1;
  const chapData   = (data[book] || [])[chapIdx] || [];
  if (!chapData.length) return null;

  const { nums, label } = resolveVerseNums(versesStr);
  const texts = nums.filter(v => v <= chapData.length).map(v => chapData[v - 1]);
  if (!texts.length) return null;
  return { label: `${book} ${chapter}:${label}\n`, texts };
}

function lookupWholeChapter(data, abbr, chapter, bookMap) {
  const book    = bookMap[abbr] ?? abbr;
  const chapIdx = parseInt(chapter) - 1;
  const verses  = (data[book] || [])[chapIdx] || [];
  if (!verses.length) return [];
  return [{ label: `${book} ${chapter}:1-${verses.length}\n`, texts: verses }];
}

function lookupCrossChapterVerses(data, abbr, ch1, v1, ch2, v2, bookMap) {
  const book = bookMap[abbr] ?? abbr;
  const results = [];

  for (let ch = parseInt(ch1); ch <= parseInt(ch2); ch++) {
    const chapIdx = ch - 1;
    const chapData = (data[book] || [])[chapIdx] || [];
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

// ─── 슬라이드 용량 추정 ───────────────────────────────────────────────────────
// 템플릿(template.pptx) 우측 패널 기준: 너비 7.93", 한글 높이 3.92", 영어 높이 2.83"
const KOR_BASE_CAPACITY = 140;  // 한글 26pt 기준 약 140자 (2~3절)
const ENG_BASE_CAPACITY = 280;  // 영어 18pt 기준 약 280자 (2~3절)

function estimateSlideCapacity(fontSize, isEnglish = false) {
  const baseCap = isEnglish ? ENG_BASE_CAPACITY : KOR_BASE_CAPACITY;
  const baseSize = isEnglish ? 18 : 26;
  if (!fontSize || fontSize <= 0) fontSize = baseSize;
  return Math.round(baseCap * (baseSize / fontSize) ** 2);
}

// ─── 청크 분할 ────────────────────────────────────────────────────────────────
function chunkAndAppend(result, label, mergedVerses, emphases, fontSize) {
  const capacity = estimateSlideCapacity(fontSize);

  // 절이 2개 이상일 때만 분할 시도
  if (mergedVerses.length >= 2) {
    const chunks = [];
    let currentChunk = [];
    let charCount = 0;

    for (const verse of mergedVerses) {
      const verseLen = verse.length;
      if (currentChunk.length > 0 && charCount + verseLen > capacity) {
        chunks.push(currentChunk);
        currentChunk = [verse];
        charCount = verseLen;
      } else {
        currentChunk.push(verse);
        charCount += verseLen;
      }
    }
    if (currentChunk.length) chunks.push(currentChunk);

    if (chunks.length > 1) {
      const mSingleChap = label.match(/^([^\n:]+\s+\d+):(\d+)-(\d+)/);
      for (const chunk of chunks) {
        let chunkLabel = label;
        if (mSingleChap) {
          const vStart = chunk[0].split(' ')[0];
          const vEnd   = chunk[chunk.length - 1].split(' ')[0];
          chunkLabel = `${mSingleChap[1]}:${vStart}-${vEnd}\n`;
        }
        result.push({ label: chunkLabel, verses: chunk.join('\n'), emphases });
      }
      return;
    }
  }
  result.push({ label, verses: mergedVerses.join('\n'), emphases });
}

// ─── 공개 추출 함수 ───────────────────────────────────────────────────────────
function _extractImpl(data, groupedRefs, bookMap, allowQuote = false, fontSize = null) {
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
          chunkAndAppend(result, label, texts, emphases, fontSize);
        }
      }
    }
  }
  return result;
}

function extractPassagesGrouped(data, groupedRefs, fontSize) {
  return _extractImpl(data, groupedRefs, BOOK_ABBR_MAP, true, fontSize);
}

function extractPassagesGroupedEng(data, groupedRefs, fontSize) {
  return _extractImpl(data, groupedRefs, BOOK_ABBR_MAP_ESV, false, fontSize);
}

function extractPassagesSynchronized(korData, engData, groupedRefs, korFontSize = 26, engFontSize = 18) {
  if (!korData && !engData) return { korEntries: [], engEntries: [] };
  if (!korData) return { korEntries: [], engEntries: extractPassagesGroupedEng(engData, groupedRefs, engFontSize) };
  if (!engData) return { korEntries: extractPassagesGrouped(korData, groupedRefs, korFontSize), engEntries: [] };

  const korCap = estimateSlideCapacity(korFontSize, false);
  const engCap = estimateSlideCapacity(engFontSize, true);

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

          const chunks = [];
          let curChunk = [];
          let kChars = 0;
          let eChars = 0;

          for (let vi = 0; vi < nVerses; vi++) {
            const kv = kItem.texts[vi] || '';
            const ev = eItem.texts[vi] || '';
            const kl = kv.length;
            const el = ev.length;

            if (curChunk.length > 0 && ((kChars + kl > korCap) || (eChars + el > engCap))) {
              chunks.push(curChunk);
              curChunk = [vi];
              kChars = kl;
              eChars = el;
            } else {
              curChunk.push(vi);
              kChars += kl;
              eChars += el;
            }
          }
          if (curChunk.length) chunks.push(curChunk);

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
                actualKLabel = `${mK[1]}:${vsK}-${veK}\n`;
              }

              const mE = eItem.label.match(/^([^\n:]+\s+\d+):(\d+)-(\d+)/);
              if (mE && eChunk.length) {
                const vsE = eChunk[0].split(' ')[0];
                const veE = eChunk[eChunk.length - 1].split(' ')[0];
                actualELabel = `${mE[1]}:${vsE}-${veE}\n`;
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
