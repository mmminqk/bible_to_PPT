'use strict';

const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron');
const path    = require('path');
const { spawn } = require('child_process');
const fs      = require('fs');

// ─── 경로 상수 ───────────────────────────────────────────────────────────────
const IS_PACKAGED = app.isPackaged;
const ROOT = IS_PACKAGED
  ? process.resourcesPath
  : path.join(__dirname, '..');

const OUTPUT_PATH  = path.join(ROOT, 'pptx_template', 'output.pptx');
const PYTHON_SCRIPT = IS_PACKAGED
  ? path.join(process.resourcesPath, 'python', 'generate_ppt.py')
  : path.join(__dirname, 'python', 'generate_ppt.py');

// ─── Python 프로세스 타임아웃 (ms) ────────────────────────────────────────────
const PYTHON_TIMEOUT_MS = 60_000;

// ─── 창 생성 ─────────────────────────────────────────────────────────────────
function buildTimestampFilename(prefix = '성경구절') {
  const now = new Date();
  const pad = (n, len = 2) => String(n).padStart(len, '0');
  const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  return `${prefix}_${stamp}.pptx`;
}

function createWindow() {
  const win = new BrowserWindow({
    width:     960,
    height:    800,
    minWidth:  840,
    minHeight: 640,
    title: '말씀 & 예배 PPT 변환기',
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

      const timer = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          proc.kill('SIGKILL');
          resolve({
            success: false,
            error: `Python 프로세스가 ${PYTHON_TIMEOUT_MS / 1000}초 내에 응답하지 않아 중단되었습니다. 다시 시도해 주세요.`,
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

// ─── IPC: 파일 선택 다이얼로그 ────────────────────────────────────────────────
ipcMain.handle('select-pptx-file', async (_event, title = 'PPT 파일 선택') => {
  const win = BrowserWindow.getFocusedWindow();
  const { canceled, filePaths } = await dialog.showOpenDialog(win, {
    title,
    filters: [{ name: 'PowerPoint Files', extensions: ['pptx', 'ppt'] }],
    properties: ['openFile'],
  });
  if (canceled || !filePaths.length) return null;
  return filePaths[0];
});

// ─── IPC: PPT 생성 ────────────────────────────────────────────────────────────
ipcMain.handle('generate-ppt', async (_event, payload) => {
  const outDir = path.dirname(OUTPUT_PATH);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const input = JSON.stringify({
    ...payload,
    outputPath: OUTPUT_PATH,
    rootPath:   ROOT,
  });

  const result = await runPython(input);
  if (result.success) shell.openPath(OUTPUT_PATH);
  return result;
});

ipcMain.handle('generate-ppt-save-as', async (_event, payload) => {
  const win = BrowserWindow.getFocusedWindow();
  const prefix = payload.isIntegrated
    ? (payload.worshipType === 'wednesday' ? '수요예배' : '주일예배')
    : '성경구절';

  const { canceled, filePath } = await dialog.showSaveDialog(win, {
    title: '다른 이름으로 저장',
    defaultPath: path.join(app.getPath('desktop'), buildTimestampFilename(prefix)),
    filters: [{ name: 'PowerPoint', extensions: ['pptx'] }],
  });
  if (canceled || !filePath) return { success: false, canceled: true };

  const outDir = path.dirname(filePath);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const input = JSON.stringify({
    ...payload,
    outputPath: filePath,
    rootPath:   ROOT,
  });

  const result = await runPython(input);
  if (result.success) shell.openPath(filePath);
  return result;
});
