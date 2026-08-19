'use strict';

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path    = require('path');
const { spawn } = require('child_process');
const fs      = require('fs');

// ─── 경로 상수 ───────────────────────────────────────────────────────────────
// 개발: electron_app_py/ 기준으로 한 단계 위가 참고구절_최종(3.16)/
// 패키징: process.resourcesPath 아래 extraResources가 복사됨
const IS_PACKAGED = app.isPackaged;
const ROOT = IS_PACKAGED
  ? process.resourcesPath
  : path.join(__dirname, '..');

const OUTPUT_PATH  = path.join(ROOT, 'pptx_template', 'output.pptx');
const PYTHON_SCRIPT = IS_PACKAGED
  ? path.join(process.resourcesPath, 'python', 'generate_ppt.py')
  : path.join(__dirname, 'python', 'generate_ppt.py');

// ─── 창 생성 ─────────────────────────────────────────────────────────────────
function createWindow() {
  const win = new BrowserWindow({
    width:     860,
    height:    780,
    minWidth:  700,
    minHeight: 600,
    title: '성경 구절 PPT 변환기',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  win.setMenu(null);
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// ─── IPC: PPT 생성 ────────────────────────────────────────────────────────────
ipcMain.handle('generate-ppt', (_event, { rawText, style, boldFont, languages }) => {
  return new Promise((resolve) => {
    // pptx_template 폴더 없으면 생성
    const outDir = path.dirname(OUTPUT_PATH);
    if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

    // Python 실행 파일 탐색 (venv > system python)
    const pythonCandidates = process.platform === 'win32'
      ? ['python', 'python3']
      : ['python3', 'python'];

    const input = JSON.stringify({
      rawText,
      style,
      boldFont: boldFont || '나눔스퀘어 네오 ExtraBold',
      languages: languages || { kor: true, eng: true },
      outputPath: OUTPUT_PATH,
      rootPath:   ROOT,
    });

    let resolved = false;
    function tryNext(candidates) {
      if (!candidates.length) {
        resolve({ success: false, error: 'Python을 찾을 수 없습니다. Python 3을 설치하세요.' });
        return;
      }
      const [exe, ...rest] = candidates;
      const proc = spawn(exe, [PYTHON_SCRIPT], {
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      let stdout = '';
      let stderr = '';

      proc.stdout.on('data', d => { stdout += d.toString(); });
      proc.stderr.on('data', d => { stderr += d.toString(); });

      proc.on('error', () => tryNext(rest));

      proc.on('close', code => {
        if (resolved) return;
        resolved = true;
        try {
          const result = JSON.parse(stdout.trim());
          if (result.success) shell.openPath(OUTPUT_PATH);
          resolve(result);
        } catch {
          resolve({ success: false, error: stderr.trim() || `Python 종료 코드: ${code}` });
        }
      });

      proc.stdin.write(input);
      proc.stdin.end();
    }

    tryNext(pythonCandidates);
  });
});
