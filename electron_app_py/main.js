'use strict';

const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron');
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

// ─── Python 프로세스 타임아웃 (ms) ────────────────────────────────────────────
const PYTHON_TIMEOUT_MS = 30_000;

// ─── 창 생성 ─────────────────────────────────────────────────────────────────
function buildTimestampFilename() {
  const now = new Date();
  const pad = (n, len = 2) => String(n).padStart(len, '0');
  const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  return `성경구절_${stamp}.pptx`;
}

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

// ─── Python 실행 헬퍼 ─────────────────────────────────────────────────────────
/**
 * Python generate_ppt.py를 실행하고 JSON 결과를 반환합니다.
 * - 여러 python 후보(python / python3)를 순차 시도
 * - PYTHON_TIMEOUT_MS 초과 시 프로세스 kill 및 타임아웃 에러 반환
 */
function runPython(inputJson) {
  return new Promise((resolve) => {
    const pythonCandidates = process.platform === 'win32'
      ? ['python', 'python3']
      : ['python3', 'python'];

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

      // ── 타임아웃 설정 ──
      const timer = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          proc.kill('SIGKILL');
          resolve({
            success: false,
            error: `Python 프로세스가 ${PYTHON_TIMEOUT_MS / 1000}초 내에 응답하지 않아 중단되었습니다. 입력 구절 수를 줄이거나 다시 시도해 주세요.`,
          });
        }
      }, PYTHON_TIMEOUT_MS);

      proc.stdout.on('data', d => { stdout += d.toString(); });
      proc.stderr.on('data', d => { stderr += d.toString(); });

      proc.on('error', () => {
        clearTimeout(timer);
        if (!resolved) tryNext(rest);
      });

      proc.on('close', code => {
        clearTimeout(timer);
        if (resolved) return;
        resolved = true;
        try {
          const result = JSON.parse(stdout.trim());
          resolve(result);
        } catch {
          resolve({ success: false, error: stderr.trim() || `Python 종료 코드: ${code}` });
        }
      });

      proc.stdin.write(inputJson);
      proc.stdin.end();
    }

    tryNext(pythonCandidates);
  });
}

// ─── IPC: PPT 생성 ────────────────────────────────────────────────────────────
ipcMain.handle('generate-ppt', async (_event, { rawText, style, boldFont, languages }) => {
  // pptx_template 폴더 없으면 생성
  const outDir = path.dirname(OUTPUT_PATH);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const input = JSON.stringify({
    rawText,
    style,
    boldFont: boldFont || '나눔스퀘어 네오 ExtraBold',
    languages: languages || { kor: true, eng: true },
    outputPath: OUTPUT_PATH,
    rootPath:   ROOT,
  });

  const result = await runPython(input);
  if (result.success) shell.openPath(OUTPUT_PATH);
  return result;
});

ipcMain.handle('generate-ppt-save-as', async (_event, { rawText, style, boldFont, languages }) => {
  const win = BrowserWindow.getFocusedWindow();
  const { canceled, filePath } = await dialog.showSaveDialog(win, {
    title: '다른 이름으로 저장',
    defaultPath: path.join(app.getPath('desktop'), buildTimestampFilename()),
    filters: [{ name: 'PowerPoint', extensions: ['pptx'] }],
  });
  if (canceled || !filePath) return { success: false, canceled: true };

  const outDir = path.dirname(filePath);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const input = JSON.stringify({
    rawText,
    style,
    boldFont: boldFont || '나눔스퀘어 네오 ExtraBold',
    languages: languages || { kor: true, eng: true },
    outputPath: filePath,
    rootPath:   ROOT,
  });

  const result = await runPython(input);
  if (result.success) shell.openPath(filePath);
  return result;
});
