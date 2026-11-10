'use strict';
/**
 * 앱 전용 Python 런타임 준비 스크립트
 *
 * python.org의 Windows embeddable 배포판을 electron_app_py/python-runtime/ 에 풀고
 * requirements.txt의 패키지를 그 안에 설치한다.
 *
 * 이렇게 하면 사용자 PC에 Python을 설치하거나 PATH를 건드릴 필요가 없고,
 * 빌드 시 이 폴더를 그대로 앱에 넣어 배포할 수 있다.
 *
 *   node scripts/prepare-python.js          # 이미 준비돼 있으면 건너뜀
 *   node scripts/prepare-python.js --force  # 지우고 다시 준비
 */

const fs     = require('fs');
const path   = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const PYTHON_VERSION = '3.12.10';
const EMBED_ZIP      = `python-${PYTHON_VERSION}-embed-amd64.zip`;
const EMBED_URL      = `https://www.python.org/ftp/python/${PYTHON_VERSION}/${EMBED_ZIP}`;
const EMBED_SHA256   = '4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3';
const GET_PIP_URL    = 'https://bootstrap.pypa.io/get-pip.py';

const APP_DIR      = path.join(__dirname, '..');
const RUNTIME_DIR  = path.join(APP_DIR, 'python-runtime');
const PYTHON_EXE   = path.join(RUNTIME_DIR, 'python.exe');
const SITE_DIR     = path.join(RUNTIME_DIR, 'Lib', 'site-packages');
const REQUIREMENTS = path.join(APP_DIR, 'requirements.txt');
const MARKER       = path.join(RUNTIME_DIR, '.ready');

function log(msg) {
  console.log(`[prepare-python] ${msg}`);
}

/** 런타임이 현재 설정(파이썬 버전 + requirements.txt)과 일치하는지 판별하는 지문 */
function fingerprint() {
  const req = fs.readFileSync(REQUIREMENTS, 'utf8').replace(/\r\n/g, '\n');
  return crypto.createHash('sha256').update(`${PYTHON_VERSION}\n${req}`).digest('hex');
}

function isReady() {
  try {
    return fs.existsSync(PYTHON_EXE) && fs.readFileSync(MARKER, 'utf8').trim() === fingerprint();
  } catch {
    return false;
  }
}

async function download(url, dest) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`다운로드 실패 (${res.status}): ${url}`);
  const buf = Buffer.from(await res.arrayBuffer());
  fs.writeFileSync(dest, buf);
  return buf;
}

function run(exe, args, opts = {}) {
  execFileSync(exe, args, { stdio: 'inherit', ...opts });
}

async function main() {
  if (process.platform !== 'win32') {
    log('Windows가 아니므로 건너뜁니다. (시스템의 python3 + python-pptx를 사용합니다)');
    return;
  }

  const force = process.argv.includes('--force');
  if (!force && isReady()) {
    log('이미 준비되어 있습니다.');
    return;
  }

  fs.rmSync(RUNTIME_DIR, { recursive: true, force: true });
  fs.mkdirSync(RUNTIME_DIR, { recursive: true });

  // 1) embeddable Python 내려받기 + 무결성 확인
  log(`Python ${PYTHON_VERSION} 내려받는 중...`);
  const zipPath = path.join(RUNTIME_DIR, EMBED_ZIP);
  const zipBuf  = await download(EMBED_URL, zipPath);
  const sha     = crypto.createHash('sha256').update(zipBuf).digest('hex');
  if (sha !== EMBED_SHA256) {
    throw new Error(`Python 압축 파일의 해시가 예상과 다릅니다.\n  예상: ${EMBED_SHA256}\n  실제: ${sha}`);
  }

  // 2) 압축 풀기 (Windows 10 이상에 기본 포함된 tar 사용)
  const tarExe = path.join(process.env.SystemRoot || 'C:\\Windows', 'System32', 'tar.exe');
  run(tarExe, ['-xf', zipPath, '-C', RUNTIME_DIR]);
  fs.rmSync(zipPath);

  // 3) site-packages를 모듈 검색 경로에 추가
  //    embeddable 배포판은 ._pth 파일에 적힌 경로만 사용한다.
  const pthName = fs.readdirSync(RUNTIME_DIR).find(f => /^python\d+\._pth$/.test(f));
  if (!pthName) throw new Error('._pth 파일을 찾을 수 없습니다.');
  const zipName = pthName.replace('._pth', '.zip');
  fs.writeFileSync(
    path.join(RUNTIME_DIR, pthName),
    [zipName, '.', 'Lib\\site-packages', ''].join('\r\n')
  );
  fs.mkdirSync(SITE_DIR, { recursive: true });

  // 4) pip을 임시 폴더에 받아 패키지 설치 (pip 자체는 배포물에 넣지 않는다)
  log('패키지 설치 중...');
  const tmpDir = fs.mkdtempSync(path.join(RUNTIME_DIR, '_pip-'));
  try {
    const getPip = path.join(tmpDir, 'get-pip.py');
    await download(GET_PIP_URL, getPip);
    const pipDir = path.join(tmpDir, 'pip');
    const quiet  = ['--no-warn-script-location', '--disable-pip-version-check', '--quiet'];
    run(PYTHON_EXE, [getPip, '--target', pipDir, '--no-setuptools', '--no-wheel', ...quiet]);
    // pip 폴더를 직접 실행한다 (._pth 때문에 `-m pip`으로는 찾을 수 없음)
    run(PYTHON_EXE, [
      path.join(pipDir, 'pip'), 'install',
      '--target', SITE_DIR,
      '--only-binary', ':all:',
      '--no-compile',
      '-r', REQUIREMENTS,
      ...quiet,
    ]);
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }

  // 5) python-pptx가 쓰지 않는 lxml 부속 자료 제거
  //    (경로가 매우 길어서, 깊은 폴더에 압축을 풀면 Windows 경로 길이 제한에 걸린다)
  fs.rmSync(path.join(SITE_DIR, 'lxml', 'isoschematron'), { recursive: true, force: true });

  // 6) 동작 확인
  run(PYTHON_EXE, ['-c', 'import pptx, lxml, PIL; print("python-pptx", pptx.__version__)']);

  fs.writeFileSync(MARKER, fingerprint());
  log(`완료: ${RUNTIME_DIR}`);
}

main().catch(err => {
  console.error(`[prepare-python] 실패: ${err.message}`);
  process.exit(1);
});
