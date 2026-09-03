// ── 저장소 키 상수 ─────────────────────────────────────────────────────────
  const STORAGE_KEY = 'ppt-style-v1';
  const LANG_STORAGE_KEY = 'ppt-lang-v1';
  const INTEGRATION_KEY = 'ppt-integrated-v1';
  const TAB_STORAGE_KEY = 'ppt-active-tab-v1';

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
  };

  const selectedSlots = {};

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
    updateLivePreview();
    localStorage.setItem(LANG_STORAGE_KEY, JSON.stringify(langState));
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
  };

  function updateIntegrationUI() {
    const isInt = chkIntegrated.checked;
    worshipBody.style.display = isInt ? 'block' : 'none';
    tabBadgeIntegrated.style.display = isInt ? 'inline-block' : 'none';
    btnGenerateLabel.textContent = isInt ? '예배 통합 PPT 생성' : 'PPT로 변환';

    Object.entries(worshipTypeBtns).forEach(([type, btn]) => {
      btn.classList.toggle('active', type === currentWorshipType);
    });

    if (isInt) renderSlots();

    localStorage.setItem(INTEGRATION_KEY, JSON.stringify({
      integrated: isInt,
      worshipType: currentWorshipType,
    }));
  }

  chkIntegrated.addEventListener('change', updateIntegrationUI);

  Object.entries(worshipTypeBtns).forEach(([type, btn]) => {
    btn.addEventListener('click', () => {
      currentWorshipType = type;
      updateIntegrationUI();
      renderSlots();
    });
  });

  // ── 슬롯 렌더링 ────────────────────────────────────────────────────────────
  function renderSlots() {
    const slots = TEMPLATE_SLOTS[currentWorshipType] || [];
    const container = document.getElementById('slot-container');
    container.innerHTML = '';

    slots.forEach(slot => {
      const row = document.createElement('div');
      row.className = 'slot-row';

      if (slot.type === 'scripture') {
        row.innerHTML = `
          <span class="slot-tag">${slot.tag}</span>
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
          <span class="slot-tag">${slot.tag}</span>
          <div class="slot-action">
            <span class="slot-filename ${isEmpty ? 'empty' : ''}" title="${filePath}">${fileName}</span>
            <button type="button" class="btn-slot-select" data-slot="${slot.name}">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              선택
            </button>
            ${filePath ? `
              <button type="button" class="btn-slot-clear" data-slot="${slot.name}" title="제거">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            ` : ''}
          </div>
        `;

        // 파일 선택 버튼
        row.querySelector('.btn-slot-select').addEventListener('click', async () => {
          if (window.api && window.api.selectPptxFile) {
            const picked = await window.api.selectPptxFile(`${slot.name} PPT 파일 선택`);
            if (picked) {
              selectedSlots[slot.name] = picked;
              renderSlots();
            }
          }
        });

        // 파일 삭제 버튼
        const clearBtn = row.querySelector('.btn-slot-clear');
        if (clearBtn) {
          clearBtn.addEventListener('click', () => {
            delete selectedSlots[slot.name];
            renderSlots();
          });
        }

        // 드래그 & 드롭 지원
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
      updateLivePreview();
    });

    text.addEventListener('input', () => {
      let val = text.value.trim();
      if (!val.startsWith('#') && /^[0-9a-fA-F]{6}$/.test(val)) val = '#' + val;
      if (/^#[0-9a-fA-F]{6}$/.test(val)) {
        picker.value = val;
      }
      saveStyle();
      updateLivePreview();
    });
  });

  STYLE_FIELDS.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener('input', () => {
        saveStyle();
        updateLivePreview();
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

  // ── 실시간 슬라이드 미리보기 업데이트 ───────────────────────────────────────
  const inputTextEl = document.getElementById('input-text');
  const previewTitleEl = document.getElementById('preview-title');
  const previewKorEl = document.getElementById('preview-kor-body');
  const previewEngEl = document.getElementById('preview-eng-body');

  function parseFirstItem(raw) {
    const lines = raw.split('\n').map(l => l.trim()).filter(Boolean);
    if (lines.length === 0) {
      return {
        title: '고전 13:4-7',
        kor: '사랑은 오래 참고 사랑은 온유하며 시기하지 아니하며',
        eng: 'Love is patient, love is kind. It does not envy, it does not boast.',
      };
    }

    const firstLine = lines[0];

    // 교독문 파싱
    if (firstLine.includes('<교독문>')) {
      const title = firstLine.replace(/^[0-9]+[\.\)]\s*/, '').replace('<교독문>', '교독문 |').trim();
      const korLines = lines.slice(1, 4).filter(l => l.startsWith('[')).join('\n');
      return {
        title: title || '교독문',
        kor: korLines || '[인도] 여호와는 나의 목자시니\n[회중] 그가 나를 푸른 풀밭에 누이시며',
        eng: '',
      };
    }

    // 인용문 파싱
    if (firstLine.includes('<인용>')) {
      const clean = firstLine.replace(/^[0-9]+[\.\)]\s*/, '').replace('<인용>', '').trim();
      const parts = clean.split('/');
      return {
        title: parts[0]?.trim() || '인용구',
        kor: parts[1]?.trim() || lines[1] || '인용 본문 내용이 여기에 표시됩니다.',
        eng: '',
      };
    }

    // 일반 성경 구절
    // 번호 및 강조 수식어 분리
    let ref = firstLine.replace(/^[0-9]+[\.\)]\s*/, '');
    ref = ref.replace(/'.*?'\s*(굵게|밑줄)/g, '').trim();

    return {
      title: ref || '성경 구절',
      kor: '태초에 하나님이 천지를 창조하시니라 (예시 본문)',
      eng: 'In the beginning God created the heavens and the earth. (Sample)',
    };
  }

  function updateLivePreview() {
    const st = collectStyle();
    const parsed = parseFirstItem(inputTextEl.value);

    // 제목 스타일 적용
    previewTitleEl.textContent = parsed.title;
    previewTitleEl.style.color = st.kor_title.color;
    previewTitleEl.style.fontFamily = `'${st.kor_title.font}', 'Pretendard', sans-serif`;

    // 한국어 본문 스타일 및 가시성
    if (langState.kor && parsed.kor) {
      previewKorEl.style.display = 'block';
      previewKorEl.textContent = parsed.kor;
      previewKorEl.style.color = st.kor_body.color;
      previewKorEl.style.fontFamily = `'${st.kor_body.font}', 'Pretendard', sans-serif`;
    } else {
      previewKorEl.style.display = 'none';
    }

    // 영어 본문 스타일 및 가시성
    if (langState.eng && parsed.eng) {
      previewEngEl.style.display = 'block';
      previewEngEl.textContent = parsed.eng;
      previewEngEl.style.color = st.eng_body.color;
      previewEngEl.style.fontFamily = `'${st.eng_body.font}', 'Pretendard', sans-serif`;
    } else {
      previewEngEl.style.display = 'none';
    }
  }

  inputTextEl.addEventListener('input', updateLivePreview);

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

    updateLangUI();
    updateIntegrationUI();
    updateLivePreview();
  }

  // ── 변환 Payload 수집 ───────────────────────────────────────────────────────
  const btnGenerate = document.getElementById('btn-generate');
  const btnSaveAs   = document.getElementById('btn-save-as');
  const statusEl    = document.getElementById('status');

  function collectPayload() {
    const rawText = inputTextEl.value.trim();
    const isIntegrated = chkIntegrated.checked;

    if (!isIntegrated && !rawText) {
      showStatus('말씀 구절을 입력하세요.', true);
      switchTab('input');
      inputTextEl.focus();
      return null;
    }

    if (!langState.kor && !langState.eng) {
      showStatus('최소 하나의 언어를 선택해야 합니다.', true);
      return null;
    }

    return {
      rawText,
      languages: { kor: langState.kor, eng: langState.eng },
      style: collectStyle(),
      boldFont: document.getElementById('bold-font').value.trim() || '나눔스퀘어 네오 ExtraBold',
      isIntegrated,
      worshipType: currentWorshipType,
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
        showStatus('', false);
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
    statusEl.textContent = msg;
    statusEl.className = isError ? 'error' : (isSuccess ? 'success' : '');
  }

  // ── 초기화 실행 ────────────────────────────────────────────────────
  loadSavedPreferences();
