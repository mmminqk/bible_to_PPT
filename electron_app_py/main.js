'use strict';

const { app, BrowserWindow, ipcMain, shell, dialog } = require('electron');
const path    = require('path');
const fs      = require('fs');
const { createPythonRunner } = require('./src/python-runner');

// ─── 경로 상수 ───────────────────────────────────────────────────────────────
const IS_PACKAGED = app.isPackaged;
const ROOT = IS_PACKAGED
  ? process.resourcesPath
  : path.join(__dirname, '..');

// [PPT로 변환] 결과 파일 위치.
// 배포판은 설치 폴더에 쓸 수 없을 수 있으므로 사용자 데이터 폴더를 쓴다.
const OUTPUT_PATH = IS_PACKAGED
  ? path.join(app.getPath('userData'), 'output', 'output.pptx')
  : path.join(ROOT, 'pptx_template', 'output.pptx');

const python = createPythonRunner({
  isPackaged:    IS_PACKAGED,
  appDir:        __dirname,
  resourcesPath: process.resourcesPath,
});

/** 모든 요청에 프로젝트 루트 경로를 붙여 Python 브릿지를 호출한다. */
function runBridge(payload) {
  return python.run({ ...payload, rootPath: ROOT });
}

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
    minWidth:  880,
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

// ─── IPC: 템플릿 슬롯 스캔 ──────────────────────────────────────────────────
ipcMain.handle('scan-template-slots', async (_event, templatePath) => {
  if (!templatePath || !fs.existsSync(templatePath)) {
    return { success: false, error: '템플릿 파일이 존재하지 않습니다.' };
  }
  return runBridge({ action: 'scanTemplate', templatePath });
});

// ─── IPC: 슬라이드 미리보기 데이터 (PPTX 저장 없이 항목별 실제 분할 결과) ─────────
ipcMain.handle('preview-slides', async (_event, payload) => {
  return runBridge({ ...payload, action: 'preview' });
});

// ─── IPC: PPT 생성 ────────────────────────────────────────────────────────────
ipcMain.handle('generate-ppt', async (_event, payload) => {
  const outDir = path.dirname(OUTPUT_PATH);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  const result = await runBridge({ ...payload, outputPath: OUTPUT_PATH });
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

  const result = await runBridge({ ...payload, outputPath: filePath });
  if (result.success) shell.openPath(filePath);
  return result;
});
