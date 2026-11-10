'use strict';
/**
 * Python 브릿지 실행기
 *
 * generate_ppt.py에 JSON을 stdin으로 넘기고, stdout의 JSON 결과를 돌려준다.
 *
 * 사용할 Python을 고르는 순서:
 *   1) 앱에 내장된 런타임 (python-runtime/python.exe) — 배포판과 일반적인 개발 환경
 *   2) 시스템에 설치된 Python — 내장 런타임이 없을 때만 (macOS/Linux 개발 등)
 */

const path = require('path');
const fs   = require('fs');
const { spawn } = require('child_process');

const PYTHON_TIMEOUT_MS = 60_000;

/**
 * @param {object} opts
 * @param {boolean} opts.isPackaged     app.isPackaged
 * @param {string}  opts.appDir         electron_app_py 폴더 (개발 환경)
 * @param {string}  opts.resourcesPath  process.resourcesPath (배포 환경)
 */
function createPythonRunner({ isPackaged, appDir, resourcesPath }) {
  const base       = isPackaged ? resourcesPath : appDir;
  const scriptPath = path.join(base, 'python', 'generate_ppt.py');
  const bundledExe = path.join(base, 'python-runtime', 'python.exe');

  /** 시도할 [실행 파일, 앞에 붙일 인자] 목록 */
  function candidates() {
    if (fs.existsSync(bundledExe)) return [[bundledExe, []]];
    if (isPackaged) return [];
    return process.platform === 'win32'
      ? [['py', ['-3']], ['python', []], ['python3', []]]
      : [['python3', []], ['python', []]];
  }

  function notFoundMessage() {
    if (isPackaged) {
      return '프로그램에 포함된 Python 실행 파일을 찾을 수 없습니다. 프로그램을 다시 설치해 주세요.\n'
        + `(${bundledExe})`;
    }
    return 'Python 실행 환경이 준비되지 않았습니다. '
      + 'start.bat을 다시 실행하거나, electron_app_py 폴더에서 "npm install"을 실행해 주세요.';
  }

  function runOnce(exe, prefixArgs, inputJson) {
    return new Promise((resolve) => {
      let settled = false;
      const finish = (value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve(value);
      };

      // -B: 설치 폴더에 __pycache__를 만들지 않는다
      const proc = spawn(exe, [...prefixArgs, '-B', scriptPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        windowsHide: true,
      });

      let stdout = '';
      let stderr = '';
      proc.stdout.setEncoding('utf8');
      proc.stderr.setEncoding('utf8');
      proc.stdout.on('data', d => { stdout += d; });
      proc.stderr.on('data', d => { stderr += d; });

      const timer = setTimeout(() => {
        proc.kill();
        finish({
          result: {
            success: false,
            error: `Python 프로세스가 ${PYTHON_TIMEOUT_MS / 1000}초 내에 응답하지 않아 중단되었습니다. 다시 시도해 주세요.`,
          },
        });
      }, PYTHON_TIMEOUT_MS);

      // 실행 파일 자체를 찾지 못한 경우 → 다음 후보로
      proc.on('error', () => finish({ notFound: true }));

      proc.on('close', (code) => {
        try {
          finish({ result: JSON.parse(stdout.trim()) });
        } catch {
          // Windows의 Microsoft Store 가짜 python.exe 등: 출력 없이 9009로 끝난다
          if (code === 9009 && !stdout.trim()) return finish({ notFound: true });
          finish({ result: { success: false, error: stderr.trim() || `Python 종료 코드: ${code}` } });
        }
      });

      proc.stdin.on('error', () => {});  // 프로세스가 먼저 죽었을 때의 EPIPE 무시
      proc.stdin.end(inputJson);
    });
  }

  /** @param {object} payload generate_ppt.py에 전달할 데이터 */
  async function run(payload) {
    const inputJson = JSON.stringify(payload);
    for (const [exe, prefixArgs] of candidates()) {
      const { result, notFound } = await runOnce(exe, prefixArgs, inputJson);
      if (!notFound) return result;
    }
    return { success: false, error: notFoundMessage() };
  }

  return { run };
}

module.exports = { createPythonRunner };
