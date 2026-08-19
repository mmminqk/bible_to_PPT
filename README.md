# 📖 성경 구절 PPT 자동 변환기 (Bible to PPT)

성경 구절 주소를 입력하면 PowerPoint(PPTX) 슬라이드를 자동으로 생성해 주는 Electron 기반 데스크톱 애플리케이션입니다.  
설교, 예배, 성경공부 등에 필요한 성경 구절 슬라이드를 빠르고 편리하게 제작할 수 있습니다.

---

## ✨ 주요 기능

- **한/영 성경 듀얼 지원**: 개역개정(한글) 및 ESV(영어) 성경 데이터 내장
- **언어별 선택 옵션**:
  - `한국어 + 영어`: 상단에 한글 구절, 하단에 영어 구절 동시 출력
  - `한국어만 선택`: 한글 구절만 출력 (하단 영어 영역은 깨끗하게 비움)
  - `영어만 선택`: 메인 영역에 영어 구절 출력 (하단 영역은 비움)
- **강조 서식 지원**: 구절 내 특정 단어에 `'단어' 굵게` 또는 `'단어' 밑줄` 적용
- **인용구 지원**: `<인용> 텍스트` 형식으로 일반 텍스트 및 인용문 슬라이드 생성
- **자동 슬라이드 분할 (청킹)**: 긴 구절(3절 이상)은 가독성을 위해 슬라이드를 자동 분할하고 주소 범위를 통일
- **검은 슬라이드 자동 삽입**: 번호 항목(예: 1번, 2번 등) 간 구분을 위한 검은색 구분 슬라이드 자동 생성
- **서식 커스터마이징**:
  - 한글/영어 제목 및 본문 폰트, 크기(pt), 색상(컬러 피커 지원) 자유롭게 설정
  - '굵게' 전용 폰트 별도 지정 가능
  - 설정한 서식 및 언어 선택 상태는 로컬 스토리지에 자동 저장되어 재실행 시 유지

---

## 📝 입력 문법 가이드

`구절 입력` 창에 아래와 같은 형식으로 입력할 수 있습니다.

### 1. 기본 구절 입력
```text
1. 창 1:1-3
2. 요 3:16
3. 시 23
```
- `번호. 구절주소` 형식으로 입력합니다.
- `시 23`과 같이 장 번호만 입력하면 해당 장 전체를 가져옵니다.

### 2. 한 슬라이드에 여러 구절 넣기 (세미콜론 또는 탭)
```text
1. 창 1:1; 1:3; 롬 8:28
```
- 세미콜론(`;`)으로 연결하면 같은 책의 장/절을 이어서 지정할 수 있습니다.

### 3. 단어 강조 (굵게 / 밑줄)
```text
1. 고전 13:4-7 '사랑은' 굵게 '온유하며' 밑줄
2. 창 1:1 '태초에' 굵게
```

### 4. 인용구 입력
```text
1. <인용> 항상 기뻐하라 쉬지 말고 기도하라 범사에 감사하라
```
- `<인용>` 태그 뒤에 입력한 문장은 성경 DB 조회 없이 본문 영역에 그대로 출력됩니다.

---

## 🚀 시작하기 (Getting Started)

### 사전 요구사항 (Prerequisites)
- [Node.js](https://nodejs.org/) (v18.0.0 이상 권장)
- [Python](https://www.python.org/) (v3.10 이상)

### 1. Python 패키지 설치
Python 파워포인트 생성 라이브러리를 설치합니다.
```bash
pip install python-pptx
```

### 2. 저장소 클론 및 패키지 설치
```bash
git clone https://github.com/mmminqk/bible_to_PPT.git
cd bible_to_PPT/electron_app_py
npm install
```

### 3. 애플리케이션 실행
```bash
npm start
```

---

## 📦 실행 파일 빌드 (Packaging)

Windows 독립 실행형 프로그램으로 빌드하려면 아래 명령어를 실행합니다.

```bash
cd electron_app_py
npm run build
```

빌드가 완료되면 `electron_app_py/dist/` 폴더 내에 실행 파일 및 패키징된 폴더가 생성됩니다.

---

## 📂 프로젝트 구조

```text
bible_reference/
├── electron_app_py/          # Electron + Python 연동 앱 (메인 애플리케이션)
│   ├── main.js               # Electron 메인 프로세스
│   ├── preload.js            # IPC 브릿지 프리로드 스크립트
│   ├── package.json          # Node.js 의존성 및 빌드 설정
│   ├── renderer/
│   │   └── index.html        # UI 렌더러 (서식/언어 설정 및 입력 화면)
│   └── python/
│       └── generate_ppt.py   # PPT 생성 IPC 브릿지 스크립트
├── pptx_generator/           # 성경 파싱 및 PPT 생성 핵심 모듈
│   ├── pptx_generator5.py    # PPT 생성 엔진 (python-pptx 기반)
│   └── verse_loader5.py      # 성경 구절 로더 및 입력 구문 분석기
├── pptx_template/            # 파워포인트 템플릿 파일
│   └── template.pptx         # 기본 디자인 템플릿
├── text_DB/                  # 성경 텍스트 데이터베이스
│   ├── 개역개정-text/         # 한글 개역개정 66권 텍스트 파일
│   └── ESV-text/             # 영어 ESV 텍스트 파일
└── README.md
```

---

## 📄 License
This project is licensed under the MIT License.
