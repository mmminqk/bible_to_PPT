/**
 * electron-builder afterPack 훅
 * 빌드 후 배포에 불필요한 파일을 정리한다.
 *
 * 주의:
 *   - ffmpeg.dll: Electron 실행 파일(.exe) 로더의 필수 의존성이므로 삭제하지 않고 유지합니다.
 *   - locales/*.pak: Chromium 다국어 언어팩 — ko / en-US / en-GB 만 유지
 */

const fs   = require('fs');
const path = require('path');

module.exports = async ({ appOutDir }) => {
  // ── 불필요한 로케일 제거 (ko / en-US / en-GB 만 유지) ───────────────────
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