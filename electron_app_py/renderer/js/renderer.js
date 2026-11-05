// ── 저장소 키 상수 ─────────────────────────────────────────────────────────
  const STORAGE_KEY = 'ppt-style-v1';
  const LANG_STORAGE_KEY = 'ppt-lang-v1';
  const INTEGRATION_KEY = 'ppt-integrated-v1';
  const TAB_STORAGE_KEY = 'ppt-active-tab-v1';
  const CUSTOM_TMPL_STORAGE_KEY = 'ppt-custom-template-v1';

  let customTemplatePath = '';

  const STYLE_FIELDS = [
    'kor-title-font', 'kor-title-size', 'kor-title-color',
    'kor-body-font',  'kor-body-size',  'kor-body-color',
    'eng-title-font', 'eng-title-size', 'eng-title-color',
    'eng-body-font',  'eng-body-size',  'eng-body-color',
    'bold-font',
  ];

  // ── 템플릿별 슬롯 정의 ─────────────────────────────────────────────────────
  const TEMPLATE_SLOTS = {
    sunday: [
      { tag: '{{시작찬양}}', name: '시작찬양', type: 'file' },
      { tag: '{{마침찬양}}', name: '마침찬양', type: 'file' },
      { tag: '{{예배찬양}}', name: '예배찬양', type: 'file' },
      { tag: '{{말씀 참고구절}}', name: '말씀 참고구절', type: 'scripture' },
      { tag: '{{말씀 마침찬양}}', name: '말씀 마침찬양', type: 'file' },
    ],
    wednesday: [
      { tag: '{{예배찬양}}', name: '예배찬양', type: 'file' },
      { tag: '{{말씀 참고구절}}', name: '말씀 참고구절', type: 'scripture' },
    ],
    custom: [],
  };

  const selectedSlots = {};

  const escapeHtml = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // ── 탭 전환 로직 ───────────────────────────────────────────────────────────
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabPanels = {
    input: document.getElementById('panel-input'),
    integration: document.getElementById('panel-integration'),
    style: document.getElementById('panel-style'),
  };

  function switchTab(tabName) {
    tabBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    Object.entries(tabPanels).forEach(([key, panel]) => {
      panel.classList.toggle('active', key === tabName);
    });
    localStorage.setItem(TAB_STORAGE_KEY, tabName);
  }

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // ── 도움말 토글 ───────────────────────────────────────────────────────────
  const btnHelpToggle = document.getElementById('btn-help-toggle');
  const helpBox = document.getElementById('help-box');

  btnHelpToggle.addEventListener('click', () => {
    const isHidden = helpBox.style.display === 'none';
    helpBox.style.display = isHidden ? 'block' : 'none';
    btnHelpToggle.textContent = isHidden ? '문법 숨기기' : '입력 문법 보기';
  });

  // ── 언어 토글 ─────────────────────────────────────────────────────────────
  let langState = { kor: true, eng: true };
  const btnLangKor = document.getElementById('btn-lang-kor');
  const btnLangEng = document.getElementById('btn-lang-eng');

  function updateLangUI() {
    btnLangKor.classList.toggle('active', langState.kor);
    btnLangEng.classList.toggle('active', langState.eng);
    localStorage.setItem(LANG_STORAGE_KEY, JSON.stringify(langState));
    requestPreview();
  }

  btnLangKor.addEventListener('click', () => {
    langState.kor = !langState.kor;
    if (!langState.kor && !langState.eng) langState.eng = true;
    updateLangUI();
  });

  btnLangEng.addEventListener('click', () => {
    langState.eng = !langState.eng;
    if (!langState.kor && !langState.eng) langState.kor = true;
    updateLangUI();
  });

  // ── 예배 통합 모드 토글 ────────────────────────────────────────────────────
  const chkIntegrated = document.getElementById('chk-integrated');
  const worshipBody = document.getElementById('worship-body');
  const tabBadgeIntegrated = document.getElementById('tab-badge-integrated');
  const btnGenerateLabel = document.getElementById('btn-generate-label');
  let currentWorshipType = 'sunday';

  const worshipTypeBtns = {
    sunday: document.getElementById('btn-worship-sunday'),
    wednesday: document.getElementById('btn-worship-wednesday'),
    custom: document.getElementById('btn-worship-custom'),
  };

  const customTemplateBox = document.getElementById('custom-template-box');
  const customTemplatePathEl = document.getElementById('custom-template-path');
  const btnSelectCustomTemplate = document.getElementById('btn-select-custom-template');
  const btnClearAllSlots = document.getElementById('btn-clear-all-slots');

  function updateCustomTemplateDisplay() {
    if (!customTemplatePathEl) return;
    if (customTemplatePath) {
      customTemplatePathEl.textContent = customTemplatePath;
      customTemplatePathEl.className = 'custom-template-path';
      customTemplatePathEl.title = customTemplatePath;
    } else {
      customTemplatePathEl.textContent = '템플릿 PPT 파일을 선택하면 슬롯 태그가 자동 감지됩니다.';
      customTemplatePathEl.className = 'custom-template-path empty';
      customTemplatePathEl.title = '';
    }
  }

  async function scanAndApplyCustomTemplate(filePath) {
    if (!filePath) return;
    customTemplatePath = filePath;
    updateCustomTemplateDisplay();
    localStorage.setItem(CUSTOM_TMPL_STORAGE_KEY, customTemplatePath);

    showStatus('템플릿 슬롯 스캔 중…', false);
    try {
      const res = await window.api.scanTemplateSlots(filePath);
      if (res && res.success) {
        TEMPLATE_SLOTS.custom = res.slots || [];
        if (TEMPLATE_SLOTS.custom.length === 0) {
          showStatus('알림: 이 템플릿에는 {{태그}} 슬롯이 없습니다.', false);
        } else {
          showStatus(`✓ 슬롯 ${TEMPLATE_SLOTS.custom.length}개 자동 감지 완료`, false, true);
        }
        renderSlots();
      } else {
        showStatus(`✕ 템플릿 스캔 실패: ${res?.error || '알 수 없는 오류'}`, true);
      }
    } catch (err) {
      showStatus(`✕ 템플릿 스캔 오류: ${err.message}`, true);
    }
  }

  if (btnSelectCustomTemplate) {
    btnSelectCustomTemplate.addEventListener('click', async () => {
      if (window.api && window.api.selectPptxFile) {
        const picked = await window.api.selectPptxFile('사용자 정의 템플릿 PPTX 선택');
        if (picked) {
          await scanAndApplyCustomTemplate(picked);
        }
      }
    });
  }

  if (btnClearAllSlots) {
    btnClearAllSlots.addEventListener('click', () => {
      Object.keys(selectedSlots).forEach(key => delete selectedSlots[key]);
      renderSlots();
      showStatus('모든 슬롯의 파일 연결을 해제했습니다.', false);
    });
  }

  function updateIntegrationUI() {
    const isInt = chkIntegrated.checked;
    const isCustom = currentWorshipType === 'custom';
    worshipBody.style.display = isInt ? 'block' : 'none';
    if (customTemplateBox) {
      customTemplateBox.style.display = (isInt && isCustom) ? 'block' : 'none';
    }
    tabBadgeIntegrated.style.display = isInt ? 'inline-block' : 'none';
    btnGenerateLabel.textContent = isInt ? '예배 통합 PPT 생성' : 'PPT로 변환';

    Object.entries(worshipTypeBtns).forEach(([type, btn]) => {
      if (btn) btn.classList.toggle('active', type === currentWorshipType);
    });

    if (isCustom) updateCustomTemplateDisplay();
    if (isInt) renderSlots();

    localStorage.setItem(INTEGRATION_KEY, JSON.stringify({
      integrated: isInt,
      worshipType: currentWorshipType,
    }));
  }

  chkIntegrated.addEventListener('change', updateIntegrationUI);

  Object.entries(worshipTypeBtns).forEach(([type, btn]) => {
    if (btn) {
      btn.addEventListener('click', () => {
        currentWorshipType = type;
        updateIntegrationUI();
      });
    }
  });

  // ── 슬롯 렌더링 ────────────────────────────────────────────────────────────
  function renderSlots() {
    const slots = TEMPLATE_SLOTS[currentWorshipType] || [];
    const container = document.getElementById('slot-container');
    container.innerHTML = '';

    if (currentWorshipType === 'custom' && !customTemplatePath) {
      container.innerHTML = `
        <div style="padding: 16px 12px; text-align: center; color: var(--muted); font-size: 12.5px;">
          위 [템플릿 선택] 버튼을 눌러 교회의 PPT 템플릿 파일을 지정하세요.
        </div>
      `;
      return;
    }

    if (slots.length === 0) {
      container.innerHTML = `
        <div style="padding: 16px 12px; text-align: center; color: var(--muted); font-size: 12.5px;">
          등록된 {{태그}} 슬롯이 없습니다.
        </div>
      `;
      return;
    }

    slots.forEach(slot => {
      const row = document.createElement('div');
      row.className = 'slot-row';

      if (slot.type === 'scripture') {
        row.innerHTML = `
          <span class="slot-tag">${escapeHtml(slot.tag)}</span>
          <div class="slot-action">
            <span class="slot-scripture-badge">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
              </svg>
              현재 구절 입력 내용 자동 주입
            </span>
          </div>
        `;
      } else {
        const filePath = selectedSlots[slot.name] || '';
        const fileName = filePath ? filePath.split(/[\\/]/).pop() : '파일을 여기로 드래그하거나 선택하세요';
        const isEmpty = !filePath;

        row.innerHTML = `
          <span class="slot-tag">${escapeHtml(slot.tag)}</span>
          <div class="slot-action">
            <span class="slot-filename ${isEmpty ? 'empty' : ''}" title="${escapeHtml(filePath)}">${escapeHtml(fileName)}</span>
            <button type="button" class="btn-slot-select" data-slot="${escapeHtml(slot.name)}">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              선택
            </button>
            ${filePath ? `
              <button type="button" class="btn-slot-clear" data-slot="${escapeHtml(slot.name)}" title="제거">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            ` : ''}
          </div>
        `;

        row.querySelector('.btn-slot-select').addEventListener('click', async () => {
          if (window.api && window.api.selectPptxFile) {
            const picked = await window.api.selectPptxFile(`${slot.name} PPT 파일 선택`);
            if (picked) {
              selectedSlots[slot.name] = picked;
              renderSlots();
            }
          }
        });

        const clearBtn = row.querySelector('.btn-slot-clear');
        if (clearBtn) {
          clearBtn.addEventListener('click', () => {
            delete selectedSlots[slot.name];
            renderSlots();
          });
        }

        row.addEventListener('dragover', (e) => {
          e.preventDefault();
          row.classList.add('drag-over');
        });
        row.addEventListener('dragleave', () => row.classList.remove('drag-over'));
        row.addEventListener('drop', (e) => {
          e.preventDefault();
          row.classList.remove('drag-over');
          if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            const f = e.dataTransfer.files[0];
            if (f.name.endsWith('.pptx') || f.name.endsWith('.ppt')) {
              selectedSlots[slot.name] = f.path;
              renderSlots();
            } else {
              showStatus('PPT 파일(.pptx, .ppt)만 드롭할 수 있습니다.', true);
            }
          }
        });
      }

      container.appendChild(row);
    });
  }

  // ── 컬러 피커 ↔ 텍스트 동기화 및 서식 저장 ─────────────────────────────────
  const colorPairs = [
    ['kor-title-color-picker', 'kor-title-color'],
    ['kor-body-color-picker',  'kor-body-color'],
    ['eng-title-color-picker', 'eng-title-color'],
    ['eng-body-color-picker',  'eng-body-color'],
  ];

  colorPairs.forEach(([pickId, textId]) => {
    const picker = document.getElementById(pickId);
    const text   = document.getElementById(textId);

    picker.addEventListener('input', () => {
      text.value = picker.value.toUpperCase();
      saveStyle();
      renderPreview();
    });

    text.addEventListener('input', () => {
      let val = text.value.trim();
      if (!val.startsWith('#') && /^[0-9a-fA-F]{6}$/.test(val)) val = '#' + val;
      if (/^#[0-9a-fA-F]{6}$/.test(val)) {
        picker.value = val;
      }
      saveStyle();
      renderPreview();
    });
  });

  STYLE_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => {
        saveStyle();
        renderPreview();
        // 본문 크기는 슬라이드 분할에 영향을 주므로 다시 계산
        if (/-size$/.test(id)) requestPreview();
      });
    }
  });

  function saveStyle() {
    const saved = {};
    STYLE_FIELDS.forEach(id => {
      const el = document.getElementById(id);
      if (el) saved[id] = el.value;
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved));
  }

  function collectStyle() {
    return {
      kor_title: {
        font:  document.getElementById('kor-title-font').value,
        size:  parseFloat(document.getElementById('kor-title-size').value) || 37,
        color: document.getElementById('kor-title-color').value,
      },
      kor_body: {
        font:  document.getElementById('kor-body-font').value,
        size:  parseFloat(document.getElementById('kor-body-size').value) || 26,
        color: document.getElementById('kor-body-color').value,
      },
      eng_title: {
        font:  document.getElementById('eng-title-font').value,
        size:  parseFloat(document.getElementById('eng-title-size').value) || 28,
        color: document.getElementById('eng-title-color').value,
      },
      eng_body: {
        font:  document.getElementById('eng-body-font').value,
        size:  parseFloat(document.getElementById('eng-body-size').value) || 18,
        color: document.getElementById('eng-body-color').value,
      },
    };
  }

  function boldFontName() {
    return document.getElementById('bold-font').value.trim() || '나눔스퀘어 네오 ExtraBold';
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ── 입력 분석 (pptx_generator/parser.py 규칙을 따름) ──────────────────────
  // ══════════════════════════════════════════════════════════════════════════
  const BOOK_KOR = {
    '창':'창세기','출':'출애굽기','레':'레위기','민':'민수기','신':'신명기','수':'여호수아','삿':'사사기','룻':'룻기','삼상':'사무엘상','삼하':'사무엘하',
    '왕상':'열왕기상','왕하':'열왕기하','대상':'역대상','대하':'역대하','스':'에스라','느':'느헤미야','에':'에스더','욥':'욥기','시':'시편','잠':'잠언',
    '전':'전도서','아':'아가','사':'이사야','렘':'예레미야','애':'예레미야애가','겔':'에스겔','단':'다니엘','호':'호세아','욜':'요엘','암':'아모스',
    '옵':'오바댜','욘':'요나','미':'미가','나':'나훔','합':'하박국','습':'스바냐','학':'학개','슥':'스가랴','말':'말라기','마':'마태복음',
    '막':'마가복음','눅':'누가복음','요':'요한복음','행':'사도행전','롬':'로마서','고전':'고린도전서','고후':'고린도후서','갈':'갈라디아서','엡':'에베소서',
    '빌':'빌립보서','골':'골로새서','살전':'데살로니가전서','살후':'데살로니가후서','딤전':'디모데전서','딤후':'디모데후서','딛':'디도서','몬':'빌레몬서',
    '히':'히브리서','약':'야고보서','벧전':'베드로전서','벧후':'베드로후서','요일':'요한일서','요이':'요한이서','요삼':'요한삼서','유':'유다서','계':'요한계시록',
  };
  const ITEM_RE  = /^\d+\./;
  const QUOTE_RE = /^<\s*(?:인용|인용구)\s*>/;
  const RESP_RE  = /^<\s*교독문(?:\s+(.*?))?\s*>/;
  const EMPH_RE  = /'([^']+)'\s*(굵게|밑줄)/g;
  const ROLE_LEAD = /^(?:\[(?:인도|인도자)\]|\((?:인도|인도자)\)|<(?:인도|인도자)>|(?:인도|인도자)\s*:)/;
  const ROLE_CONG = /^(?:\[(?:회중|성도|교인)\]|\((?:회중|성도|교인)\)|<(?:회중|성도|교인)>|(?:회중|성도|교인)\s*:)/;
  const ROLE_ALL  = /^(?:\[(?:다함께|다같이|함께)\]|\((?:다함께|다같이|함께)\)|<(?:다함께|다같이|함께)>|(?:다함께|다같이|함께)\s*:)/;

  function suggestBooks(tok) {
    const out = [];
    Object.keys(BOOK_KOR).forEach(k => {
      const full = BOOK_KOR[k];
      if (full.startsWith(tok) || (tok.length > 1 && k.startsWith(tok[0]) && full.includes(tok))) out.push(k);
    });
    return out.slice(0, 3);
  }

  // split_items()와 같은 기준으로 줄을 항목 묶음으로 나눈다.
  function splitGroups(lines) {
    const groups = [];
    let cur = null;
    let started = false;
    lines.forEach((ln, i) => {
      const t = ln.trim();
      if (!started && !t) return;
      started = true;
      if (ITEM_RE.test(t) || (!cur && (RESP_RE.test(t) || QUOTE_RE.test(t)))) {
        cur = { lines: [i], head: i };
        groups.push(cur);
      } else if (cur) {
        cur.lines.push(i);
      } else {
        cur = { lines: [i], head: i };
        groups.push(cur);
      }
    });
    return groups;
  }

  function verseRefLabel(body) {
    const emph = [];
    let m; EMPH_RE.lastIndex = 0;
    while ((m = EMPH_RE.exec(body))) emph.push({ text: m[1], kind: m[2] });
    const refStr = body.replace(EMPH_RE, '').trim();
    if (!refStr) return { error: '구절 주소가 비어 있습니다', hint: '예: 1. 요 3:16' };
    const parts = refStr.split(/\t| {4,}/).flatMap(p => p.split(';')).map(p => p.trim()).filter(Boolean);
    const labels = [];
    let book = null;
    for (const p of parts) {
      let r = p.match(/^([가-힣]+)\s*(\d+):(\d+)-(\d+):(\d+)$/)
           || p.match(/^([가-힣]+)\s*(\d+:\d[\d,\-\s]*)$/)
           || p.match(/^([가-힣]+)\s*(\d+)$/);
      let rest;
      if (r) {
        if (!BOOK_KOR[r[1]]) {
          const sg = suggestBooks(r[1]);
          return { error: `‘${r[1]}’은(는) 알 수 없는 성경 약어입니다`, hint: sg.length ? '이 약어를 뜻하셨나요?' : '창, 출, 마, 요, 롬, 고전 … 형식의 약어를 사용하세요', bad: r[1], fixes: sg, emph };
        }
        book = r[1];
        rest = p.slice(r[1].length).trim();
      } else if (/^(\d+:\d+-\d+:\d+|\d+:\d[\d,\-\s]*|\d+)$/.test(p)) {
        if (!book) return { error: '성경 약어가 없습니다', hint: `‘${p}’ 앞에 책 약어를 붙여 주세요 (예: 요 ${p})`, emph };
        rest = p;
      } else {
        const lead = p.match(/^([가-힣]+)/);
        if (lead && !BOOK_KOR[lead[1]]) {
          const sg = suggestBooks(lead[1]);
          return { error: `‘${lead[1]}’은(는) 알 수 없는 성경 약어입니다`, hint: sg.length ? '이 약어를 뜻하셨나요?' : '예: 요 3:16, 창 1:1-3, 시 23', bad: lead[1], fixes: sg, emph };
        }
        return { error: `‘${p}’를 구절 주소로 읽을 수 없습니다`, hint: '예: 요 3:16, 창 1:1-3, 시 23', emph };
      }
      labels.push(`${BOOK_KOR[book]} ${rest.replace(/\s+/g, '')}`);
    }
    return { label: labels.join(' · '), count: labels.length, emph };
  }

  function analyzeText(text) {
    const lines = text.split('\n');
    const groups = splitGroups(lines);
    const lineInfo = lines.map((raw, i) => ({ i, raw, group: null, status: raw.trim() ? 'warn' : 'blank' }));
    groups.forEach((g, gi) => {
      g.index = gi;
      const headRaw = lines[g.head].trim();
      const numbered = ITEM_RE.test(headRaw);
      const body = headRaw.replace(/^\d+\.\s*/, '').trim();
      g.num = numbered ? headRaw.match(/^(\d+)\./)[1] : '?';
      g.numbered = numbered;
      g.lines.forEach(i => { lineInfo[i].group = gi; });
      const head = lineInfo[g.head];
      const cont = g.lines.filter(i => i !== g.head && lines[i].trim());

      if (RESP_RE.test(body)) {
        g.kind = 'responsive';
        const m = body.match(RESP_RE);
        const title = ((m[1] || '').trim() || body.replace(RESP_RE, '').trim()).replace(/^교독문\s*/, '');
        g.label = `교독문${title ? ' ' + title : ''}`;
        // 교독문 슬라이드 페어링 (parse_responsive_item 규칙)
        let slide = -1, inGroup = false, hasCong = false;
        const roleOf = t => ROLE_ALL.test(t) ? 'all' : ROLE_LEAD.test(t) ? 'leader' : ROLE_CONG.test(t) ? 'congregation' : 'plain';
        cont.forEach(i => {
          const t = lines[i].trim(); const role = roleOf(t);
          if (role === 'all') { slide++; inGroup = false; hasCong = false; }
          else if (role === 'leader') { if (!inGroup || hasCong) { slide++; inGroup = true; hasCong = false; } }
          else if (role === 'congregation') { if (!inGroup) { slide++; inGroup = true; } hasCong = true; }
          else { if (!inGroup) { slide++; inGroup = true; } }
          const name = { all: '다함께', leader: '인도', congregation: '회중', plain: '본문' }[role];
          Object.assign(lineInfo[i], { status: 'ok', tag: name, slide,
            label: role === 'plain' ? '역할 표시가 없는 줄' : `${name} 파트`,
            detail: role === 'plain' ? '앞 줄과 같은 슬라이드에 이어집니다' : (role === 'congregation' || role === 'all') ? '굵은 글씨로 표시됩니다' : '' });
        });
        g.estSlides = slide + 1;
        Object.assign(head, { status: cont.length ? 'ok' : 'warn', tag: '교독문', label: g.label, slide: 0,
          detail: cont.length ? `${cont.length}줄 · 인도 + 회중을 한 장에 짝지음` : '아래 줄에 [인도] [회중] [다함께]를 적어 주세요' });
      } else if (QUOTE_RE.test(body)) {
        g.kind = 'quote';
        const c = body.replace(QUOTE_RE, '').trim(); const k = c.indexOf('/');
        g.label = k >= 0 ? c.slice(0, k).trim() || '(제목 없음)' : '(제목 없음)';
        g.estSlides = 1;
        Object.assign(head, { status: 'ok', tag: '인용', label: g.label, slide: 0,
          detail: k >= 0 ? '‘/’ 앞은 제목, 뒤는 본문으로 들어갑니다' : '‘/’가 없어 전체가 본문으로 들어갑니다' });
        cont.forEach(i => Object.assign(lineInfo[i], { status: 'ok', tag: '본문', label: '인용 본문 이어짐', detail: '', slide: 0 }));
      } else {
        g.kind = 'verse';
        const v = verseRefLabel(body);
        if (v.error) {
          g.label = v.error; g.error = true;
          Object.assign(head, { status: 'error', tag: '오류', label: v.error, detail: v.hint, slide: 0,
            fixes: (v.fixes || []).map(abbr => ({ abbr, name: BOOK_KOR[abbr], text: lines[g.head].replace(v.bad, abbr) })) });
        } else {
          g.label = v.label;
          const em = (v.emph || []).map(e => `‘${e.text}’ ${e.kind}`).join(', ');
          Object.assign(head, { status: 'ok', tag: '구절', label: v.label, slide: 0, detail: em ? `강조: ${em}` : '' });
        }
        cont.forEach(i => Object.assign(lineInfo[i], { status: 'warn', tag: '확인', label: '번호가 없는 줄',
          detail: '구절 항목은 한 줄에 하나씩, “번호.”로 시작해 주세요 (예: 7. 요 3:16)', slide: 0 }));
      }
      if (!numbered && g.kind === 'verse' && !g.error) {
        Object.assign(head, { status: 'warn', tag: '확인', label: '번호가 없는 줄', detail: '항목은 “번호.”로 시작해야 합니다 (예: 1. 요 3:16)' });
      }
    });
    return { lines, groups, lineInfo };
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ── 입력 상태 (텍스트 / 카드) ─────────────────────────────────────────────
  // ══════════════════════════════════════════════════════════════════════════
  const inputTextEl = document.getElementById('input-text');
  const cardListEl  = document.getElementById('card-list');
  const textWrapEl  = document.getElementById('text-wrap');
  const modeBtns    = document.querySelectorAll('.seg-btn');
  const errBadge    = document.getElementById('tab-badge-errors');

  let inputMode = 'text';          // 처음 켜면 항상 텍스트 모드
  let selLine = 0;
  let selSlide = null;
  let analysis = analyzeText('');
  let dragFrom = null, dropAt = null;
  let previewItems = null;          // Python 미리보기 결과 (항목별 실제 슬라이드)
  let previewError = '';
  let explicitStatus = false;

  function getText() { return inputTextEl.value; }

  function setText(t, opts = {}) {
    inputTextEl.value = t;
    onTextChanged(opts);
  }

  function onTextChanged(opts = {}) {
    analysis = analyzeText(getText());
    if (selLine >= analysis.lines.length) selLine = Math.max(0, analysis.lines.length - 1);
    if (!opts.keepSlide) selSlide = null;
    if (explicitStatus) { explicitStatus = false; }
    if (inputMode === 'cards' && !opts.skipCards) renderCards();
    updateErrorBadge();
    renderPreview();
    requestPreview();
  }

  function setMode(m) {
    inputMode = m;
    modeBtns.forEach(b => b.classList.toggle('active', b.dataset.mode === m));
    cardListEl.style.display = m === 'cards' ? 'flex' : 'none';
    textWrapEl.style.display = m === 'text' ? 'flex' : 'none';
    if (m === 'cards') renderCards();
  }
  modeBtns.forEach(b => b.addEventListener('click', () => setMode(b.dataset.mode)));

  function selectLine(i, { keepSlide = false } = {}) {
    if (i === selLine && keepSlide) return;
    const prevGroup = analysis.lineInfo[selLine]?.group;
    selLine = i;
    if (!keepSlide) selSlide = null;
    if (inputMode === 'cards' && prevGroup !== analysis.lineInfo[i]?.group) {
      cardListEl.querySelectorAll('.item-card').forEach(c => c.classList.toggle('selected', +c.dataset.group === analysis.lineInfo[i]?.group));
    }
    renderPreview();
  }

  function caretLine() {
    const el = inputTextEl;
    return el.value.slice(0, el.selectionStart).split('\n').length - 1;
  }

  inputTextEl.addEventListener('input', () => { selLine = caretLine(); onTextChanged(); });
  ['click', 'keyup', 'select'].forEach(ev => inputTextEl.addEventListener(ev, () => {
    const i = caretLine(); if (i !== selLine) selectLine(i);
  }));

  function updateErrorBadge() {
    const errs = countErrors();
    errBadge.textContent = String(errs);
    errBadge.style.display = errs ? 'inline-block' : 'none';
    if (!explicitStatus) showSummary();
  }

  function countErrors() {
    let n = analysis.groups.filter(g => g.error).length;
    if (previewItems) analysis.groups.forEach((g, gi) => { if (!g.error && previewItems[gi] && previewItems[gi].error) n++; });
    return n;
  }

  // 항목 재배열/삽입 후 번호를 1부터 다시 매긴다.
  function rebuildFromGroups(order, insert) {
    const L = analysis.lines;
    const out = []; let n = 0; let markHead = 0;
    const emit = (lines, numbered, mark) => {
      if (mark) markHead = out.length;
      lines.forEach((t, k) => {
        if (k === 0 && numbered) { n++; t = t.replace(/^(\s*)\d+\./, `$1${n}.`); }
        out.push(t);
      });
    };
    order.forEach(g => {
      emit(g.lines.map(i => L[i]).filter((t, k) => k === 0 || t.trim()), g.numbered, g === insert?.markGroup);
      if (insert && insert.after === g) emit(insert.lines, true, true);
    });
    if (insert && insert.after == null) emit(insert.lines, true, true);
    return { text: out.join('\n'), head: markHead };
  }

  const ADD_TEMPLATES = {
    verse: ['0. 요 3:16'],
    responsive: ['0. <교독문> 제목', '[인도] ', '[회중] '],
    quote: ['0. <인용> 제목 / 본문'],
  };

  document.querySelectorAll('.btn-add').forEach(btn => btn.addEventListener('click', () => {
    const G = analysis.groups;
    const sel = G[analysis.lineInfo[selLine]?.group] || G[G.length - 1] || null;
    const r = rebuildFromGroups(G, { after: sel, lines: ADD_TEMPLATES[btn.dataset.add] });
    selLine = r.head;
    switchTab('input');
    setText(r.text);
    setMode('cards');
    const card = cardListEl.querySelector(`.item-card[data-group="${analysis.lineInfo[selLine]?.group}"]`);
    if (card) {
      const f = card.querySelector('.item-field');
      if (f) { f.focus(); f.select(); }
      cardListEl.scrollTop = Math.max(0, card.offsetTop - cardListEl.offsetTop - 40);
    }
  }));

  function moveGroup(from, to) {
    const G = analysis.groups.slice();
    if (from == null || to == null) return;
    if (to > from) to -= 1;
    if (to === from) return;
    const [g] = G.splice(from, 1); G.splice(to, 0, g);
    const r = rebuildFromGroups(G, { markGroup: g });
    selLine = r.head;
    setText(r.text);
  }

  function deleteGroup(gi) {
    const G = analysis.groups.filter((_, i) => i !== gi);
    const r = rebuildFromGroups(G);
    selLine = 0;
    setText(r.text);
  }

  // ── 카드 렌더링 ────────────────────────────────────────────────────────────
  const GRIP = '<svg width="10" height="16" viewBox="0 0 10 16" fill="currentColor"><circle cx="2.5" cy="3" r="1.4"></circle><circle cx="7.5" cy="3" r="1.4"></circle><circle cx="2.5" cy="8" r="1.4"></circle><circle cx="7.5" cy="8" r="1.4"></circle><circle cx="2.5" cy="13" r="1.4"></circle><circle cx="7.5" cy="13" r="1.4"></circle></svg>';
  const XICON = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';

  function groupView(g, gi) {
    const head = analysis.lineInfo[g.head];
    const pv = previewItems && previewItems[gi];
    let status = head.status, label = head.label, detail = head.detail || '';
    if (status === 'ok' && pv && pv.error) { status = 'error'; label = g.label; detail = pv.error; }
    if (status === 'ok' && pv && !pv.error && pv.slides.length === 0 && g.kind === 'verse') { status = 'warn'; detail = '해당 구절을 성경 데이터에서 찾지 못했습니다'; }
    const n = pv && !pv.error ? pv.slides.length : null;
    const metaParts = [];
    if (g.kind === 'verse' && status === 'ok') metaParts.push(detail);
    else if (detail) metaParts.push(detail);
    const chip = status === 'error' ? '오류' : (status === 'warn' && head.tag !== '교독문') ? '확인' : head.tag;
    return { status, label, detail: metaParts.filter(Boolean).join(' · '), chip, count: n != null ? `${n}장` : '' };
  }

  function renderCards() {
    const active = document.activeElement;
    const focusLine = active && active.classList && active.classList.contains('item-field') ? +active.dataset.line : null;
    const caret = focusLine != null ? [active.selectionStart, active.selectionEnd] : null;

    const G = analysis.groups;
    if (!G.length) {
      cardListEl.innerHTML = '<div class="card-empty">위의 [+ 구절] [+ 교독문] [+ 인용] 버튼으로 항목을 추가하거나<br>[텍스트] 모드에서 붙여 넣으세요.</div>';
      return;
    }
    const selGroup = analysis.lineInfo[selLine]?.group;
    cardListEl.innerHTML = G.map((g, gi) => {
      const v = groupView(g, gi);
      const fields = g.lines.filter(i => i === g.head || analysis.lines[i].trim()).map(i => {
        const st = analysis.lineInfo[i].status;
        return `<input type="text" class="item-field ${st === 'error' || st === 'warn' ? st : ''}" data-line="${i}" value="${escapeHtml(analysis.lines[i])}" spellcheck="false" draggable="false">`;
      }).join('');
      const fixes = (analysis.lineInfo[g.head].fixes || []).map((f, k) =>
        `<button type="button" class="btn-fix" data-fix="${k}" data-line="${g.head}">‘${escapeHtml(f.abbr)}’(${escapeHtml(f.name)})로 바꾸기</button>`).join('');
      return `
        <div class="item-card ${v.status === 'error' ? 'error' : v.status === 'warn' ? 'warn' : ''} ${gi === selGroup ? 'selected' : ''}" data-group="${gi}" draggable="true">
          <div class="item-head">
            <span class="item-grip" title="끌어서 순서 바꾸기">${GRIP}</span>
            <span class="item-num">${escapeHtml(g.num)}</span>
            <span class="item-chip">${escapeHtml(v.chip)}</span>
            <span class="item-label">${escapeHtml(v.label)}</span>
            <span class="item-count">${escapeHtml(v.count)}</span>
            <button type="button" class="btn-item-del" data-del="${gi}" title="항목 삭제">${XICON}</button>
          </div>
          ${v.detail ? `<div class="item-detail">${escapeHtml(v.detail)}</div>` : ''}
          <div class="item-fields">${fields}</div>
          ${fixes ? `<div class="item-fixes">${fixes}</div>` : ''}
        </div>`;
    }).join('');

    if (focusLine != null) {
      const f = cardListEl.querySelector(`.item-field[data-line="${focusLine}"]`);
      if (f) { f.focus(); try { f.setSelectionRange(caret[0], caret[1]); } catch {} }
    }
  }

  // 카드 이벤트 (위임)
  cardListEl.addEventListener('click', e => {
    const del = e.target.closest('.btn-item-del');
    if (del) { e.stopPropagation(); deleteGroup(+del.dataset.del); return; }
    const fix = e.target.closest('.btn-fix');
    if (fix) {
      e.stopPropagation();
      const i = +fix.dataset.line; const f = analysis.lineInfo[i].fixes[+fix.dataset.fix];
      const L = analysis.lines.slice(); L[i] = f.text; setText(L.join('\n'));
      return;
    }
    const card = e.target.closest('.item-card');
    if (card && !e.target.classList.contains('item-field')) {
      const g = analysis.groups[+card.dataset.group];
      if (g && !g.lines.includes(selLine)) selectLine(g.head);
    }
  });

  cardListEl.addEventListener('focusin', e => {
    if (e.target.classList.contains('item-field')) {
      const i = +e.target.dataset.line;
      if (i !== selLine) selectLine(i);
    }
  });

  cardListEl.addEventListener('input', e => {
    if (!e.target.classList.contains('item-field')) return;
    const i = +e.target.dataset.line;
    const L = analysis.lines.slice(); L[i] = e.target.value;
    inputTextEl.value = L.join('\n');
    selLine = i;
    onTextChanged();
  });

  cardListEl.addEventListener('dragstart', e => {
    const card = e.target.closest && e.target.closest('.item-card');
    if (!card || e.target.tagName === 'INPUT') return;
    dragFrom = +card.dataset.group; dropAt = null;
    e.dataTransfer.effectAllowed = 'move';
    try { e.dataTransfer.setData('text/plain', String(dragFrom)); } catch {}
    requestAnimationFrame(() => card.classList.add('dragging'));
  });

  cardListEl.addEventListener('dragover', e => {
    if (dragFrom == null) return;
    const card = e.target.closest('.item-card');
    if (!card) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    const gi = +card.dataset.group;
    const r = card.getBoundingClientRect();
    const pos = e.clientY < r.top + r.height / 2 ? gi : gi + 1;
    if (pos === dropAt) return;
    dropAt = pos;
    const cards = cardListEl.querySelectorAll('.item-card');
    cards.forEach(c => c.classList.remove('drop-before', 'drop-after'));
    const noop = pos === dragFrom || pos === dragFrom + 1;
    if (noop) return;
    if (pos < cards.length) cards[pos].classList.add('drop-before');
    else cards[cards.length - 1].classList.add('drop-after');
  });

  cardListEl.addEventListener('drop', e => {
    if (dragFrom == null) return;
    e.preventDefault();
    const from = dragFrom, to = dropAt;
    dragFrom = dropAt = null;
    moveGroup(from, to);
    renderCards();
  });

  cardListEl.addEventListener('dragend', () => {
    dragFrom = dropAt = null;
    cardListEl.querySelectorAll('.item-card').forEach(c => c.classList.remove('dragging', 'drop-before', 'drop-after'));
  });

  // ══════════════════════════════════════════════════════════════════════════
  // ── 슬라이드 미리보기 (template.pptx 도형 배치 + generator._fill_slide 규칙) ─
  // ══════════════════════════════════════════════════════════════════════════
  const slideFrame   = document.getElementById('slide-frame');
  const slideStage   = document.getElementById('slide-stage');
  const slTitle      = document.getElementById('sl-title');
  const slEngTitle   = document.getElementById('sl-eng-title');
  const slKorBody    = document.getElementById('sl-kor-body');
  const slEngBody    = document.getElementById('sl-eng-body');
  const slEmpty      = document.getElementById('sl-empty');
  const previewItemEl = document.getElementById('preview-item');
  const pagerDots    = document.getElementById('pager-dots');
  const pagerCount   = document.getElementById('pager-count');
  const btnPrevSlide = document.getElementById('btn-prev-slide');
  const btnNextSlide = document.getElementById('btn-next-slide');

  function fitSlide() {
    const w = slideFrame.getBoundingClientRect().width || slideFrame.clientWidth;
    if (w) slideStage.style.transform = `scale(${w / 1920})`;
  }
  if (window.ResizeObserver) new ResizeObserver(fitSlide).observe(slideFrame);
  window.addEventListener('resize', fitSlide);
  requestAnimationFrame(fitSlide);

  const SUP = { '0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹',':':'˸' };
  const sup = s => String(s).split('').map(c => SUP[c] || c).join('');
  const RESP_ALL_PREFIXES  = ['(인도)','[인도]','<인도>','(회중)','[회중]','<회중>','(다함께)','[다함께]','<다함께>','(성도)','[성도]','(교인)','[교인]','(다같이)','[다같이]','(함께)','[함께]'];
  const RESP_BOLD_PREFIXES = ['(회중)','[회중]','<회중>','(성도)','[성도]','(교인)','[교인]','(다함께)','[다함께]','<다함께>','(다같이)','[다같이]','(함께)','[함께]'];

  function fontCss(name) {
    const n = name || '';
    let w;
    if (/nanum|나눔/i.test(n)) w = /heavy/i.test(n) ? 800 : /extrabold/i.test(n) ? 700 : /bold/i.test(n) ? 500 : /light/i.test(n) ? 100 : 300;
    else w = /extrabold|heavy|black/i.test(n) ? 800 : /bold/i.test(n) ? 700 : 400;
    return `font-family: '${n.replace(/'/g, '')}', 'NanumSquareNeo', 'Pretendard', sans-serif; font-weight: ${w};`;
  }

  function splitByEmphases(text, emphases) {
    if (!emphases || !emphases.length) return [[text, null]];
    const hits = emphases.map(e => [text.indexOf(e.text), e.text, e.kind]).filter(h => h[0] !== -1).sort((a, b) => a[0] - b[0]);
    const segs = []; let cur = 0;
    hits.forEach(([s, t, k]) => {
      if (s < cur) return;
      if (s > cur) segs.push([text.slice(cur, s), null]);
      segs.push([t, k]); cur = s + t.length;
    });
    if (cur < text.length) segs.push([text.slice(cur), null]);
    return segs.length ? segs : [[text, null]];
  }

  // generator._fill_slide 와 같은 규칙으로 제목/본문을 만든다.
  function fillSlide(entry, useRun) {
    const [address, verse, emphases] = entry || ['', '', []];
    const addr = address ? address.split('\n').map(l => l.trim()).filter(Boolean) : [];
    const isMulti = addr.length > 2;
    let title = [];
    if (address && address.trim()) title = useRun ? (isMulti ? addr : addr.flatMap(l => l.split(/\s+/).filter(Boolean))) : addr;
    const paras = [];
    if (verse && verse.trim()) {
      verse.split('\n').forEach((line, i) => {
        const s = line.trim();
        const isResp = RESP_ALL_PREFIXES.some(p => s.startsWith(p));
        const toks = line.split(/\s+/).filter(Boolean);
        const bodyOf = l => l.split(' ').slice(1).join(' ');
        let full;
        if (!toks.length) full = '';
        else if (isMulti) { const at = (addr[i] || '').split(/\s+/); const st = at[1] || ''; full = st ? `${sup(st)} ${bodyOf(line)}` : line; }
        else if (/^\d+$/.test(toks[0])) full = `${sup(toks[0])} ${bodyOf(line)}`;
        else full = line;
        const boldPara = RESP_BOLD_PREFIXES.some(p => full.trim().startsWith(p));
        paras.push({ role: isResp, boldPara, segs: splitByEmphases(full, emphases) });
      });
    }
    return { title, paras };
  }

  function paintBox(el, paras, sec, boldFont) {
    el.innerHTML = paras.map(p => `<div class="sl-p ${p.role ? 'role' : ''}" style="font-size:${sec.size * 2}px; color:${escapeHtml(sec.color)};">${
      p.segs.map(([t, k]) => `<span style="${fontCss(k === 'bold' || p.boldPara ? boldFont : sec.font)}${k === 'underline' ? ' text-decoration: underline;' : ''}">${escapeHtml(t)}</span>`).join('')
    }</div>`).join('');
  }

  function paintTitle(el, lines, sec) {
    el.setAttribute('style', `font-size:${sec.size * 2}px; color:${escapeHtml(sec.color)}; ${fontCss(sec.font)}`);
    el.innerHTML = lines.map(l => `<div>${escapeHtml(l)}</div>`).join('');
  }

  function clearSlide(msg) {
    slTitle.innerHTML = ''; slEngTitle.innerHTML = ''; slKorBody.innerHTML = ''; slEngBody.innerHTML = '';
    slEmpty.textContent = msg || '';
  }

  function renderPreview() {
    fitSlide();
    const info = analysis.lineInfo[selLine];
    const gi = info ? info.group : null;
    const g = gi != null ? analysis.groups[gi] : null;
    const pv = previewItems && gi != null ? previewItems[gi] : null;
    const slides = pv && !pv.error ? pv.slides : [];
    previewItemEl.textContent = g ? `${g.num}번 항목` : '';

    let si = selSlide ?? (info && info.slide) ?? 0;
    si = Math.max(0, Math.min(si, slides.length - 1));

    pagerDots.innerHTML = slides.map((_, i) => `<span class="pager-dot ${i === si ? 'active' : ''}" data-i="${i}"></span>`).join('');
    pagerCount.textContent = slides.length ? `${si + 1} / ${slides.length}` : '0 / 0';
    btnPrevSlide.disabled = si <= 0;
    btnNextSlide.disabled = si >= slides.length - 1;

    if (!g) return clearSlide('미리볼 항목이 없습니다');
    if (g.error || (pv && pv.error)) return clearSlide('오류를 고치면 슬라이드가 보입니다');
    if (!previewItems) return clearSlide(previewError || '미리보기를 불러오는 중…');
    if (!slides.length) return clearSlide('표시할 슬라이드가 없습니다');

    const st = collectStyle(); const bf = boldFontName();
    const main = fillSlide(slides[si].main, true);
    const sub = fillSlide(slides[si].sub, false);
    slEmpty.textContent = '';
    paintTitle(slTitle, main.title, st.kor_title);
    paintBox(slKorBody, main.paras, st.kor_body, bf);
    paintTitle(slEngTitle, sub.title, st.eng_title);
    paintBox(slEngBody, sub.paras, st.eng_body, bf);
  }

  pagerDots.addEventListener('click', e => { const d = e.target.closest('.pager-dot'); if (d) { selSlide = +d.dataset.i; renderPreview(); } });
  btnPrevSlide.addEventListener('click', () => { const cur = +(pagerCount.textContent.split('/')[0]) - 1; selSlide = Math.max(0, cur - 1); renderPreview(); });
  btnNextSlide.addEventListener('click', () => { const cur = +(pagerCount.textContent.split('/')[0]) - 1; selSlide = cur + 1; renderPreview(); });

  // Python(실제 변환 로직)으로 항목별 슬라이드 분할 결과를 받아온다.
  let previewTimer = null, previewSeq = 0;
  function requestPreview() {
    clearTimeout(previewTimer);
    slideFrame.classList.add('loading');
    previewTimer = setTimeout(async () => {
      const seq = ++previewSeq;
      const rawText = getText().trim();
      if (!window.api || !window.api.previewSlides) {
        previewItems = null; previewError = '미리보기 기능을 사용할 수 없습니다';
        slideFrame.classList.remove('loading'); renderPreview(); return;
      }
      try {
        const res = rawText ? await window.api.previewSlides({ rawText, languages: { ...langState }, style: collectStyle() }) : { success: true, items: [] };
        if (seq !== previewSeq) return;
        if (res && res.success) { previewItems = res.items || []; previewError = ''; }
        else { previewItems = null; previewError = `미리보기 오류: ${res?.error || '알 수 없는 오류'}`; }
      } catch (err) {
        if (seq !== previewSeq) return;
        previewItems = null; previewError = `미리보기 오류: ${err.message}`;
      }
      slideFrame.classList.remove('loading');
      if (inputMode === 'cards') renderCards();
      updateErrorBadge();
      renderPreview();
    }, 450);
  }

  // ── 저장된 환경설정 불러오기 ───────────────────────────────────────────────
  function loadSavedPreferences() {
    try {
      const savedTab = localStorage.getItem(TAB_STORAGE_KEY);
      if (savedTab && tabPanels[savedTab]) switchTab(savedTab);
    } catch {}

    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
      if (saved) {
        STYLE_FIELDS.forEach(id => {
          if (saved[id] === undefined) return;
          const el = document.getElementById(id);
          if (el) el.value = saved[id];
        });
        colorPairs.forEach(([pickId, textId]) => {
          const val = saved[textId];
          if (val && /^#[0-9a-fA-F]{6}$/.test(val)) {
            document.getElementById(pickId).value = val;
          }
        });
      }
    } catch {}

    try {
      const savedLangs = JSON.parse(localStorage.getItem(LANG_STORAGE_KEY));
      if (savedLangs) {
        if (savedLangs.kor !== undefined) langState.kor = !!savedLangs.kor;
        if (savedLangs.eng !== undefined) langState.eng = !!savedLangs.eng;
      }
    } catch {}

    try {
      const savedInt = JSON.parse(localStorage.getItem(INTEGRATION_KEY));
      if (savedInt) {
        chkIntegrated.checked = !!savedInt.integrated;
        if (savedInt.worshipType) currentWorshipType = savedInt.worshipType;
      }
    } catch {}

    try {
      const savedCustomTmpl = localStorage.getItem(CUSTOM_TMPL_STORAGE_KEY);
      if (savedCustomTmpl) {
        customTemplatePath = savedCustomTmpl;
        if (window.api && window.api.scanTemplateSlots) {
          window.api.scanTemplateSlots(customTemplatePath).then(res => {
            if (res && res.success) {
              TEMPLATE_SLOTS.custom = res.slots || [];
              if (currentWorshipType === 'custom') renderSlots();
            }
          }).catch(() => {});
        }
      }
    } catch {}

    setMode('text');
    updateIntegrationUI();
    onTextChanged();
    updateLangUI();
  }

  // ── 변환 Payload 수집 ───────────────────────────────────────────────────────
  const btnGenerate = document.getElementById('btn-generate');
  const btnSaveAs   = document.getElementById('btn-save-as');
  const statusEl    = document.getElementById('status');

  function focusLine(i) {
    switchTab('input');
    selectLine(i);
    if (inputMode === 'text') {
      const L = analysis.lines; let pos = 0;
      for (let k = 0; k < i; k++) pos += L[k].length + 1;
      inputTextEl.focus();
      inputTextEl.setSelectionRange(pos, pos + (L[i] || '').length);
    } else {
      renderCards();
      const f = cardListEl.querySelector(`.item-field[data-line="${i}"]`);
      if (f) f.focus();
    }
  }

  function firstErrorLine() {
    const gErr = analysis.groups.find((g, gi) => g.error || (previewItems && previewItems[gi] && previewItems[gi].error));
    return gErr ? gErr.head : -1;
  }

  function collectPayload() {
    const rawText = inputTextEl.value.trim();
    const isIntegrated = chkIntegrated.checked;

    if (!isIntegrated && !rawText) {
      showStatus('말씀 구절을 입력하세요.', true);
      switchTab('input');
      inputTextEl.focus();
      return null;
    }

    const errLine = firstErrorLine();
    if (rawText && errLine >= 0) {
      showStatus(`✕ ${analysis.groups[analysis.lineInfo[errLine].group].num}번 항목을 고친 뒤 다시 변환해 주세요.`, true);
      focusLine(errLine);
      return null;
    }

    if (!langState.kor && !langState.eng) {
      showStatus('최소 하나의 언어를 선택해야 합니다.', true);
      return null;
    }

    if (isIntegrated && currentWorshipType === 'custom' && !customTemplatePath) {
      showStatus('사용자 정의 템플릿 PPTX 파일을 먼저 선택하세요.', true);
      switchTab('integration');
      return null;
    }

    return {
      rawText,
      languages: { kor: langState.kor, eng: langState.eng },
      style: collectStyle(),
      boldFont: boldFontName(),
      isIntegrated,
      worshipType: currentWorshipType,
      customTemplatePath: (isIntegrated && currentWorshipType === 'custom') ? customTemplatePath : undefined,
      slots: selectedSlots,
    };
  }

  // ── PPT 생성 실행 ──────────────────────────────────────────────────────────
  async function handleGenerate(isSaveAs = false) {
    const payload = collectPayload();
    if (!payload) return;

    btnGenerate.disabled = btnSaveAs.disabled = true;
    showStatus(isSaveAs ? '저장 위치 선택 및 변환 중…' : 'PPT 변환 중…', false);

    try {
      const result = isSaveAs
        ? await window.api.generatePPTSaveAs(payload)
        : await window.api.generatePPT(payload);

      btnGenerate.disabled = btnSaveAs.disabled = false;

      if (result.canceled) {
        explicitStatus = false; showSummary();
      } else if (result.success) {
        const modeDesc = payload.isIntegrated ? '예배 통합 슬라이드' : '성경 구절 PPT';
        showStatus(`✓ ${modeDesc} 생성 완료! PowerPoint가 열립니다.`, false, true);
      } else {
        let err = result.error || '알 수 없는 오류';
        if (err.includes('PermissionError') || err.includes('EBUSY')) {
          err = 'PowerPoint 파일이 이미 열려 있습니다. 파일을 닫고 다시 시도해 주세요.';
        }
        showStatus(`✕ 오류: ${err}`, true);
      }
    } catch (e) {
      btnGenerate.disabled = btnSaveAs.disabled = false;
      showStatus(`✕ 실행 오류: ${e.message}`, true);
    }
  }

  btnGenerate.addEventListener('click', () => handleGenerate(false));
  btnSaveAs.addEventListener('click', () => handleGenerate(true));

  // ── 단축키 지원 (Ctrl+Enter / Cmd+Enter) ────────────────────────────────────
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      handleGenerate(false);
    }
  });

  function showStatus(msg, isError = false, isSuccess = false) {
    explicitStatus = !!msg;
    statusEl.textContent = msg;
    statusEl.className = isError ? 'error' : (isSuccess ? 'success' : '');
  }

  function showSummary() {
    const G = analysis.groups;
    if (!G.length) { statusEl.textContent = ''; statusEl.className = ''; return; }
    const total = previewItems ? previewItems.reduce((a, it) => a + (it.error ? 0 : it.slides.length), 0) : null;
    const errs = countErrors();
    statusEl.className = 'summary';
    statusEl.textContent = `항목 ${G.length}개${total != null ? ` · 슬라이드 ${total}장` : ''}${errs ? ` · 오류 ${errs}개` : ''}`;
  }

  // ── 초기화 실행 ────────────────────────────────────────────────────
  loadSavedPreferences();
