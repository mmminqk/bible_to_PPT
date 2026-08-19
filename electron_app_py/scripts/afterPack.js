'use strict';

/**
 * electron-builder afterPack 훅
 * 빌드 후 실행에 불필요한 파일을 자동으로 제거한다.
 *
 * 제거 대상:
 *   - ffmpeg.dll      : HTML5 미디어(오디오/비디오) 코덱 — 이 앱은 미디어 미사용
 *   - locales/*.pak   : Chromium 언어팩 — ko / en-US / en-GB 만 유지
 */

const fs   = require('fs');
const path = require('path');

module.exports = async ({ appOutDir }) => {
  // ── 1. ffmpeg.dll 제거 ──────────────────────────────────────────────────────
  const ffmpegPath = path.join(appOutDir, 'ffmpeg.dll');
  if (fs.existsSync(ffmpegPath)) {
    fs.rmSync(ffmpegPath);
    console.log('[afterPack] 제거됨: ffmpeg.dll');
  }

  // ── 2. 불필요한 로케일 제거 (ko / en-US / en-GB 만 유지) ───────────────────
  const KEEP_LOCALES = new Set(['ko.pak', 'en-US.pak', 'en-GB.pak']);
  const localesDir   = path.join(appOutDir, 'locales');

  if (fs.existsSync(localesDir)) {
    const files   = fs.readdirSync(localesDir);
    let   removed = 0;
    for (const file of files) {
      if (!KEEP_LOCALES.has(file)) {
        fs.rmSync(path.join(localesDir, file));
        removed++;
      }
    }
    console.log(`[afterPack] 로케일 ${removed}개 제거 (${files.length - removed}개 유지)`);
  }
};
