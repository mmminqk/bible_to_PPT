'use strict';

const PptxGenJS = require('pptxgenjs');
const path      = require('path');
const { loadKorBible, loadEsvBible, parseMultiRefsLine,
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
function buildBodyRuns(verse, address, style, boldFont, bodyScale = 1.0) {
  const addrLines = address.split('\n').filter(l => l.trim());
  const bodyLines = verse.split('\n');
  const isMulti   = addrLines.length > 1;
  const fontSize  = Math.round(style.size * bodyScale * 10) / 10;
  const color     = style.color.replace('#', '');

  // emphases는 호출부에서 주입 — 여기서는 style 객체에 없으므로 별도 파라미터로 전달
  return { bodyLines, addrLines, isMulti, fontSize, color };
}

/**
 * 본문 run 배열 (emphases 포함 버전)
 */
function buildBodyRunsFull(verse, address, emphases, style, boldFont, bodyScale = 1.0) {
  const addrLines = address.split('\n').filter(l => l.trim());
  const bodyLines = verse.split('\n');
  const isMulti   = addrLines.length > 1;
  const fontSize  = Math.round(style.size * bodyScale * 10) / 10;
  const color     = style.color.replace('#', '');

  const runs = [];
  for (let i = 0; i < bodyLines.length; i++) {
    const line     = bodyLines[i];
    const supToken = isMulti ? addrLines[i].split(' ')[1] : line.split(' ')[0];
    const fullText = `${toSup(supToken)} ${verseBody(line)}`;
    const segs     = splitByEmphases(fullText, emphases);

    segs.forEach((seg, si) => {
      const isLast = si === segs.length - 1;
      runs.push({
        text: seg.text,
        options: {
          fontFace:  seg.kind === 'bold' ? boldFont : style.font,
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

  // 본문 길이에 따른 폰트 크기 자동 조정
  const bodyScale = (mainVerse && mainVerse.length > 130) ? 0.88 : 1.0;

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
      buildBodyRunsFull(mainVerse, mainAddr, emphases, style.kor_body, boldFont, bodyScale),
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

    // ── 서브 제목 ──
    if (subAddr) {
      slide.addText(buildTitleRuns(subAddr, style.eng_title), {
        x: SLIDE.MARGIN_X, y: SLIDE.ENG_ADDR_Y,
        w: SLIDE.CONTENT_W, h: SLIDE.ENG_ADDR_H,
        valign: 'middle',
      });
    }

    // ── 서브 본문 ──
    if (subVerse) {
      slide.addText(
        buildBodyRunsFull(subVerse, subAddr, emphases, style.eng_body, boldFont),
        {
          x: SLIDE.MARGIN_X, y: SLIDE.ENG_BODY_Y,
          w: SLIDE.CONTENT_W, h: SLIDE.ENG_BODY_H,
          valign: 'top',
        }
      );
    }
  }
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

  // 입력 파싱
  const groupedRefs = parseMultiRefsLine(rawText);
  const korBodySize = style?.kor_body?.size || 28;
  const engBodySize = style?.eng_body?.size || 18;

  let mainEntries = [];
  let subEntries  = [];

  if (incKor && incEng) {
    const { korEntries, engEntries } = extractPassagesSynchronized(korData, engData, groupedRefs, korBodySize, engBodySize);
    mainEntries = korEntries;
    subEntries  = engEntries;
  } else if (incKor) {
    mainEntries = extractPassagesGrouped(korData, groupedRefs, korBodySize);
    subEntries  = [];
  } else {
    // 영어만 선택: 원래 한글 박스(메인 영역)에 영어를 출력하고 하단은 비움
    mainEntries = extractPassagesGroupedEng(engData, groupedRefs, engBodySize);
    subEntries  = [];
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
