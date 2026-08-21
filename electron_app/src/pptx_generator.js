'use strict';

const PptxGenJS = require('pptxgenjs');
const path      = require('path');
const { loadKorBible, loadEsvBible, parseMultiRefsLine,
        parseEmphasisFromRef,
        extractPassagesGrouped, extractPassagesGroupedEng,
        extractPassagesSynchronized } = require('./verse_loader');

// ─── 슬라이드 레이아웃 상수 (단위: 인치, 와이드스크린 13.33×7.5) ────────────
const SLIDE = {
  W: 13.33, H: 7.5,
  MARGIN_X: 0.55,
  KOR_ADDR_Y: 0.38, KOR_ADDR_H: 0.95,
  KOR_BODY_Y: 1.45, KOR_BODY_H: 3.65,
  LINE_Y:     5.28,
  ENG_ADDR_Y: 5.42, ENG_ADDR_H: 0.52,
  ENG_BODY_Y: 6.00, ENG_BODY_H: 1.35,
  CONTENT_W:  12.23,
};

// ─── 위첨자 변환 ──────────────────────────────────────────────────────────────
const SUP_MAP = { '0':'⁰','1':'¹','2':'²','3':'³','4':'⁴',
                  '5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹',':':'˸' };

function toSup(token) {
  return token.split('').map(c => SUP_MAP[c] ?? c).join('');
}

function verseBody(line) {
  return line.split(' ').slice(1).join(' ');
}

// ─── 강조 분할 ────────────────────────────────────────────────────────────────
function splitByEmphases(text, emphases) {
  if (!emphases?.length) return [{ text, kind: null }];

  const hits = emphases
    .map(e => { const i = text.indexOf(e.text); return i !== -1 ? { i, ...e } : null; })
    .filter(Boolean)
    .sort((a, b) => a.i - b.i);

  const segs = [];
  let cur = 0;
  for (const { i, text: et, kind } of hits) {
    if (i < cur) continue;
    if (i > cur) segs.push({ text: text.slice(cur, i), kind: null });
    segs.push({ text: et, kind });
    cur = i + et.length;
  }
  if (cur < text.length) segs.push({ text: text.slice(cur), kind: null });
  return segs.length ? segs : [{ text, kind: null }];
}

// ─── PptxGenJS run 배열 생성 ─────────────────────────────────────────────────

/**
 * 제목(주소) 텍스트 run 배열 생성.
 * - 단일 참조: "창세기 1:1-3" → ["창세기", "1:1-3"] 로 행 분리
 * - 복수 참조: 각 참조를 그대로 행으로
 */
function buildTitleRuns(address, style) {
  const addrLines = address.split('\n').filter(l => l.trim());
  const isMulti   = addrLines.length > 1;
  const lines     = isMulti
    ? addrLines
    : addrLines.flatMap(l => l.split(' ').filter(Boolean));

  return lines.map((word, i) => ({
    text: word,
    options: {
      fontFace:  style.font,
      fontSize:  style.size,
      color:     style.color.replace('#', ''),
      breakLine: i < lines.length - 1,
    },
  }));
}

/**
 * 본문 텍스트 run 배열 생성.
 * 각 절마다 위첨자 절 번호 + 본문, 강조 구간에 따라 분할.
 */
function buildBodyRuns(verse, address, style, boldFont) {
  const addrLines = address.split('\n').filter(l => l.trim());
  const bodyLines = verse.split('\n');
  const isMulti   = addrLines.length > 1;
  const fontSize  = style.size;
  const color     = style.color.replace('#', '');

  // emphases는 호출부에서 주입 — 여기서는 style 객체에 없으므로 별도 파라미터로 전달
  return { bodyLines, addrLines, isMulti, fontSize, color };
}

/**
 * 본문 run 배열 (emphases 포함 버전)
 */
function buildBodyRunsFull(verse, address, emphases, style, boldFont) {
  const addrLines = address.split('\n').filter(l => l.trim());
  const bodyLines = verse.split('\n');
  const isMulti   = addrLines.length > 1;
  const fontSize  = style.size;
  const color     = style.color.replace('#', '');

  const runs = [];
  for (let i = 0; i < bodyLines.length; i++) {
    const line     = bodyLines[i];
    let fullText;
    const isResp = /^\s*(?:\([인도회중다함께성도교인다같이함께]+\)|\[[인도회중다함께성도교인다같이함께]+\]|<[인도회중다함께성도교인다같이함께]+>)/.test(line);
    const firstWord = line.trim().split(' ')[0] || '';
    if (isResp || !/^\d+$/.test(firstWord)) {
      fullText = line;
    } else if (isMulti) {
      const supToken = addrLines[i] ? addrLines[i].split(' ')[1] : '';
      fullText = supToken ? `${toSup(supToken)} ${verseBody(line)}` : line;
    } else {
      const supToken = firstWord;
      fullText = `${toSup(supToken)} ${verseBody(line)}`;
    }

    const isBoldLine = /^\s*(?:\((?:회중|성도|교인|다함께|다같이|함께)\)|\[(?:회중|성도|교인|다함께|다같이|함께)\]|<(?:회중|성도|교인|다함께|다같이|함께)>)/.test(fullText);
    const segs       = splitByEmphases(fullText, emphases);

    segs.forEach((seg, si) => {
      const isLast = si === segs.length - 1;
      runs.push({
        text: seg.text,
        options: {
          fontFace:  (seg.kind === 'bold' || isBoldLine) ? boldFont : style.font,
          fontSize,
          color,
          underline: seg.kind === 'underline' ? { style: 'single' } : undefined,
          breakLine: isLast && i < bodyLines.length - 1,
        },
      });
    });
  }
  return runs;
}

// ─── 슬라이드 1장 채우기 ─────────────────────────────────────────────────────
function fillSlide(slide, mainEntry, subEntry, style, boldFont) {
  const { label: mainAddr, verses: mainVerse, emphases } = mainEntry;
  const { label: subAddr,  verses: subVerse  }           = subEntry || {};

  // ── 상단(메인) 제목 ────────────────────────────────────────────────────────
  if (mainAddr) {
    slide.addText(buildTitleRuns(mainAddr, style.kor_title), {
      x: SLIDE.MARGIN_X, y: SLIDE.KOR_ADDR_Y,
      w: SLIDE.CONTENT_W, h: SLIDE.KOR_ADDR_H,
      valign: 'middle',
    });
  }

  // ── 상단(메인) 본문 ────────────────────────────────────────────────────────
  if (mainVerse) {
    slide.addText(
      buildBodyRunsFull(mainVerse, mainAddr, emphases, style.kor_body, boldFont),
      {
        x: SLIDE.MARGIN_X, y: SLIDE.KOR_BODY_Y,
        w: SLIDE.CONTENT_W, h: SLIDE.KOR_BODY_H,
        valign: 'top',
      }
    );
  }

  // ── 서브(영어) 영역이 있을 경우에만 구분선 및 서브 텍스트 추가 ─────────────
  if (subAddr || subVerse) {
    // ── 구분선 ──
    slide.addShape('line', {
      x: SLIDE.MARGIN_X, y: SLIDE.LINE_Y,
      w: SLIDE.CONTENT_W, h: 0,
      line: { color: 'D0D8D5', width: 0.75 },
    });

    // ── 하단(영어) 제목 ──
    if (subAddr) {
      slide.addText(
        [{
          text: subAddr,
          options: {
            fontFace: style.eng_title.font,
            fontSize: style.eng_title.size,
            color:    style.eng_title.color.replace('#', ''),
          },
        }],
        {
          x: SLIDE.MARGIN_X, y: SLIDE.ENG_ADDR_Y,
          w: SLIDE.CONTENT_W, h: SLIDE.ENG_ADDR_H,
          valign: 'middle',
        }
      );
    }

    // ── 하단(영어) 본문 ──
    if (subVerse) {
      slide.addText(
        [{
          text: subVerse,
          options: {
            fontFace: style.eng_body.font,
            fontSize: style.eng_body.size,
            color:    style.eng_body.color.replace('#', ''),
          },
        }],
        {
          x: SLIDE.MARGIN_X, y: SLIDE.ENG_BODY_Y,
          w: SLIDE.CONTENT_W, h: SLIDE.ENG_BODY_H,
          valign: 'top',
        }
      );
    }
  }
}

// ─── 교독문 및 항목 분리 ──────────────────────────────────────────────────────
const QUOTE_PATTERN      = /^<\s*(?:인용|인용구)\s*>/u;
const RESPONSIVE_PATTERN = /^<\s*교독문(?:\s+(.*?))?\s*>/u;

const ROLE_LEADER_PAT = /^(?:\[(?:인도|인도자)\]|\((?:인도|인도자)\)|<(?:인도|인도자)>|(?:인도|인도자)\s*:)\s*(.*)$/u;
const ROLE_CONG_PAT   = /^(?:\[(?:회중|성도|교인)\]|\((?:회중|성도|교인)\)|<(?:회중|성도|교인)>|(?:회중|성도|교인)\s*:)\s*(.*)$/u;
const ROLE_ALL_PAT    = /^(?:\[(?:다함께|다같이|함께)\]|\((?:다함께|다같이|함께)\)|<(?:다함께|다같이|함께)>|(?:다함께|다같이|함께)\s*:)\s*(.*)$/u;

function isQuoteBody(body) {
  return QUOTE_PATTERN.test(body.trim());
}

function stripQuoteTag(body) {
  return body.trim().replace(QUOTE_PATTERN, '').trim();
}

function isResponsiveBody(body) {
  return RESPONSIVE_PATTERN.test(body.trim());
}

function normalizeResponsiveLine(line) {
  line = line.trim();
  if (!line) return null;
  const mLead = ROLE_LEADER_PAT.exec(line);
  if (mLead) return { role: 'leader', text: `(인도) ${mLead[1].trim()}` };
  const mCong = ROLE_CONG_PAT.exec(line);
  if (mCong) return { role: 'congregation', text: `(회중) ${mCong[1].trim()}` };
  const mAll = ROLE_ALL_PAT.exec(line);
  if (mAll) return { role: 'all', text: `(다함께) ${mAll[1].trim()}` };
  return { role: 'plain', text: line };
}

function parseResponsiveItem(body) {
  const lines = body.trim().split(/\r?\n/);
  if (!lines.length) return { title: '교독문', slides: [] };

  const firstLine = lines[0].trim();
  const m = RESPONSIVE_PATTERN.exec(firstLine);
  let titleExtra = '';
  let contentLines = lines;
  if (m) {
    const inside = (m[1] || '').trim();
    const outside = firstLine.replace(RESPONSIVE_PATTERN, '').trim();
    titleExtra = inside || outside;
    contentLines = lines.slice(1);
  }

  let title = '교독문';
  if (titleExtra) {
    const sub = titleExtra.replace(/^교독문\s*/, '').trim();
    title = sub ? `교독문\n${sub}` : '교독문';
  }

  const parsedLines = [];
  for (const cl of contentLines) {
    const item = normalizeResponsiveLine(cl);
    if (item) parsedLines.push(item);
  }

  if (!parsedLines.length) return { title, slides: [] };

  const slides = [];
  let currentGroup = [];
  let hasCong = false;

  for (const { role, text } of parsedLines) {
    if (role === 'all') {
      if (currentGroup.length) {
        slides.push(currentGroup.map(g => g.text).join('\n'));
        currentGroup = [];
        hasCong = false;
      }
      slides.push(text);
    } else if (role === 'leader') {
      if (hasCong) {
        slides.push(currentGroup.map(g => g.text).join('\n'));
        currentGroup = [{ role, text }];
        hasCong = false;
      } else {
        currentGroup.push({ role, text });
      }
    } else if (role === 'congregation') {
      currentGroup.push({ role, text });
      hasCong = true;
    } else {
      if (!currentGroup.length) {
        currentGroup.push({ role: 'leader', text: `(인도) ${text}` });
      } else {
        currentGroup.push({ role, text });
      }
    }
  }

  if (currentGroup.length) {
    slides.push(currentGroup.map(g => g.text).join('\n'));
  }

  return { title, slides };
}

function parseQuoteContent(content) {
  let qTitle = '';
  let rawBody = content.trim();
  if (content.includes('/')) {
    const parts = content.split('/');
    qTitle = parts[0].trim();
    rawBody = parts.slice(1).join('/').trim();
  }

  const emphases = [];
  let m;
  const re = /'([^']+)'\s*(굵게|밑줄)/gu;
  while ((m = re.exec(rawBody)) !== null) {
    emphases.push({
      text: m[1],
      kind: m[2] === '굵게' ? 'bold' : 'underline',
    });
  }

  if (!emphases.length) {
    return { title: qTitle, body: rawBody, emphases: [] };
  }

  const textWithoutEmp = rawBody.replace(re, '').trim();
  const allInText = emphases.every(emp => textWithoutEmp.includes(emp.text));
  const cleanBody = allInText ? textWithoutEmp : rawBody.replace(re, '$1').trim();

  return { title: qTitle, body: cleanBody, emphases };
}

function splitItems(rawText) {
  const items = [];
  const lines = rawText.trim().split(/\r?\n/);
  let currentLines = [];

  function flush(buf) {
    if (!buf.length) return;
    const joined = buf.join('\n').trim();
    const body = joined.replace(/^\d+\.\s*/, '').trim();
    if (isResponsiveBody(body)) {
      items.push({ kind: 'responsive', content: body });
    } else if (isQuoteBody(body)) {
      items.push({ kind: 'quote', content: stripQuoteTag(body) });
    } else {
      items.push({ kind: 'verse', content: `1. ${body}` });
    }
  }

  for (const line of lines) {
    if (/^\d+\./.test(line.trim())) {
      flush(currentLines);
      currentLines = [line];
    } else if (!currentLines.length && (isResponsiveBody(line.trim()) || isQuoteBody(line.trim()))) {
      flush(currentLines);
      currentLines = [line];
    } else {
      currentLines.push(line);
    }
  }
  flush(currentLines);
  return items;
}

// ─── 메인 생성 함수 ───────────────────────────────────────────────────────────
async function generatePPT({ rawText, languages, style, boldFont, outputPath }) {
  const incKor = languages ? Boolean(languages.kor) : true;
  const incEng = languages ? Boolean(languages.eng) : true;

  if (!incKor && !incEng) {
    throw new Error('최소 하나의 언어를 선택해야 합니다.');
  }

  // 성경 데이터 로드
  const korData = incKor ? loadKorBible() : null;
  const engData = incEng ? loadEsvBible() : null;

  const korBodySize = style?.kor_body?.size || 28;
  const engBodySize = style?.eng_body?.size || 18;

  const items = splitItems(rawText);
  if (!items.length) throw new Error('입력된 항목이 없습니다.');

  let mainEntries = [];
  let subEntries  = [];

  for (const { kind, content } of items) {
    if (kind === 'responsive') {
      const { title, slides } = parseResponsiveItem(content);
      for (const st of slides) {
        mainEntries.push({ label: title, verses: st, emphases: [] });
        subEntries.push({ label: '', verses: '', emphases: [] });
      }
    } else if (kind === 'quote') {
      const { title, body, emphases } = parseQuoteContent(content);
      mainEntries.push({ label: title, verses: body, emphases });
      subEntries.push({ label: '', verses: '', emphases: [] });
    } else {
      const groupedRefs = parseMultiRefsLine(content);
      if (!groupedRefs || !groupedRefs.length) continue;

      if (incKor && incEng) {
        const { korEntries, engEntries } = extractPassagesSynchronized(korData, engData, groupedRefs, korBodySize, engBodySize);
        mainEntries.push(...korEntries);
        subEntries.push(...engEntries);
      } else if (incKor) {
        const korEntries = extractPassagesGrouped(korData, groupedRefs, korBodySize);
        mainEntries.push(...korEntries);
        subEntries.push(...korEntries.map(() => ({ label: '', verses: '', emphases: [] })));
      } else {
        const engEntries = extractPassagesGroupedEng(engData, groupedRefs, engBodySize);
        mainEntries.push(...engEntries);
        subEntries.push(...engEntries.map(() => ({ label: '', verses: '', emphases: [] })));
      }
    }
  }

  if (!mainEntries.length) throw new Error('유효한 구절을 찾을 수 없습니다.');

  // PptxGenJS 생성
  const pptx   = new PptxGenJS();
  pptx.layout  = 'LAYOUT_WIDE';   // 13.33" × 7.5"
  pptx.author  = '성경 구절 PPT 변환기';
  pptx.subject = 'Bible Verses';

  for (let i = 0; i < mainEntries.length; i++) {
    const slide    = pptx.addSlide();
    const subEntry = subEntries[i] ?? { label: '', verses: '', emphases: [] };
    fillSlide(slide, mainEntries[i], subEntry, style, boldFont);
  }

  await pptx.writeFile({ fileName: outputPath });
}

module.exports = { generatePPT };
