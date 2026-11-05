# 변경 사항: 구절 입력 화면 개편 (1b 항목 카드 안)

압축을 풀고 `electron_app_py/` 폴더를 저장소의 `bible_reference/electron_app_py/` 위에 덮어쓰세요.

## 바뀐 파일
- `renderer/index.html`: 탭을 왼쪽 세로 메뉴로 옮김, 입력 영역에 [카드/텍스트] 전환과 [+ 구절] [+ 교독문] [+ 인용] 버튼 추가, 오른쪽 미리보기를 실제 템플릿 배치로 교체
- `renderer/css/style.css`: 위 화면용 스타일 추가 (기존 예배 통합·서식 설정 스타일은 그대로)
- `renderer/js/renderer.js`: 줄별 인식·오류 표시, 약어 자동 수정, 카드 끌어서 순서 바꾸기, 선택한 카드 아래에 항목 추가, 번호 자동 재정렬, 선택 항목 슬라이드 미리보기
- `renderer/assets/leaf.svg` (새 파일): template.pptx의 잎 그림을 그대로 옮긴 것
- `preload.js`: `previewSlides` 추가
- `main.js`: `preview-slides` IPC 추가, 최소 창 너비 840 → 880
- `python/generate_ppt.py`: 항목 변환 로직을 `item_entries()`로 분리(변환 결과는 동일), `action: 'preview'` 추가 — PPTX를 저장하지 않고 항목별 실제 슬라이드 분할 결과를 JSON으로 돌려줌

## 동작
- 처음 켜면 항상 [텍스트] 모드로 시작합니다.
- 미리보기는 변환과 같은 Python 경로(parser/loader)로 구절을 불러오고 나누므로, 슬라이드 장 수와 줄바꿈 기준이 실제 PPT와 같습니다. 입력을 멈춘 뒤 약 0.5초 후 갱신됩니다.
- 오류 항목이 있으면 변환을 막고 해당 줄로 이동합니다.
- 카드 순서를 바꾸거나 항목을 추가하면 번호가 1부터 다시 매겨지고, 항목 사이 빈 줄은 정리됩니다.
