'use strict';

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const os   = require('os');

const ROOT       = path.join(__dirname, '..');
const OUTPUT_DIR = path.join(ROOT, 'pptx_template');
const OUTPUT_PATH = path.join(OUTPUT_DIR, 'output.pptx');

function createWindow() {
  const win = new BrowserWindow({
    width:  860,
    height: 780,
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
ipcMain.handle('generate-ppt', async (_event, { rawText, style, boldFont, languages }) => {
  try {
    const { generatePPT } = require('./src/pptx_generator');
    await generatePPT({ rawText, style, boldFont, languages, outputPath: OUTPUT_PATH });
    await shell.openPath(OUTPUT_PATH);
    return { success: true };
  } catch (err) {
    console.error(err);
    return { success: false, error: err.message };
  }
});
