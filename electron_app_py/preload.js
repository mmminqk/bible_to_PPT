'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  generatePPT: (data) => ipcRenderer.invoke('generate-ppt', data),
  generatePPTSaveAs: (data) => ipcRenderer.invoke('generate-ppt-save-as', data),
  selectPptxFile: (title) => ipcRenderer.invoke('select-pptx-file', title),
});
