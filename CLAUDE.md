# 고냥이 쇼츠 자동화 (gonyang-channel) — 작업 노트

유튜브 채널 **고냥이**(@gonyangcat, "고양이에 대한 모든 것")에 고양이 지식 쇼츠를
**하루 4편(07:00 · 12:00 · 18:00 · 21:00 KST)** 자동으로 만들어 예약 공개하는 프로그램.
부지런(buzirun-channel)과 **같은 시스템**을 복사해 고양이용으로 고친 것(11/22 시작). 어느 컴퓨터에서든 이 파일로 맥락을 이어간다.

> ⚠️ 이 파일 · 코드 · 커밋 메시지에 비밀번호 · 토큰 · API 키 · 채널 내부 번호를 절대 쓰지 말 것. **공개 저장소**로 쓸 예정.
> 비밀값은 노트북 `~/.gonyang/channel/`(저장소 밖)과 GitHub Secrets 에만 있음.

## 진행 상태 (11/22)
- [x] 코드 복사 · 고양이용 개조(카테고리 8개 · 대본 규칙 · 검수 · 면책 · 주황 디자인 · 슬로건 "고양이에 대한 모든 것")
- [x] 배경 영상 다양화(stock_video.py): 장면마다 다른 종류 고양이(치즈·검정·새끼·품종·길고양이) + 한국어 검색어 자동 추가, Pixabay 정렬·페이지 무작위, 다 탈락하면 일반 고양이 검색어로 대체, 제목에 품종 이름이 있으면 그 품종 영상·사진
- [ ] 로컬 시험 영상 확인(사용자)
- [ ] 구글 클라우드 새 프로젝트(gonyang) + OAuth 앱 게시 — 업로드 쿼터가 프로젝트당 하루 10,000 이라 부지런과 프로젝트를 따로 써야 함
- [ ] 유튜브 채널 '고냥이' 만들기(핸들 @gonyangcat, waynekim93 계정의 새 채널) + auth_login.py 로 로그인
- [ ] Gemini 키(새 프로젝트 권장 — 지금은 임시로 부지런 키 복사해 씀) · Pixabay 키(공유)
- [ ] 디스코드 서버 '고냥이' + 새 봇(알림 · 아이디어 채널)
- [ ] GitHub 새 저장소 waynekim93/gonyang-channel(공개) + Secrets 7개
- [ ] 사무소 페이지(site/office.html)를 고양이 버전으로 — 아직 부지런 부동산 사무소 그대로. 브랜딩 페이지(site/index · privacy · terms)도 고쳐야 함

## 한눈에
- 실행: GitHub Actions 가 전부 자동. 사람 손은 문제 생길 때만(디스코드 알림).
- 계정(이름만): 구글 · 유튜브 · GitHub · Vercel 모두 **waynekim93**. 부지런 · 캄모니 · 투게독과 저장소 · 비밀값 · 디스코드 모두 따로.
- 실행 분 겹침 방지: autopilot :08, health :33/:23/:43, stats 7·22·37·52분 (부지런 :23 · :03/:53/:13 · 0·15·30·45 와 다름).

## 파일
| 파일 | 하는 일 |
|---|---|
| `autopilot.py` | 주제(디스코드 아이디어 우선) → 대본 → 영상 → 예약 업로드 → `history.json`. 카테고리 · 시간대 · 공개 시각 · 내용 규칙 |
| `script_writer.py` | Gemini 대본 · 주제 · 아이디어 다듬기 · **검수(review_script: 고양이 상식 오류·과장·위험한 말)**. `research()`는 유료 키에서만(`RESEARCH=1`) |
| `shorts_maker.py` | 영상 편집 + 디자인(주황 `#ff9f43`) |
| `stock_video.py` | Pixabay 고양이 배경 — 위 '배경 영상 다양화' 참고. `CAT_TYPES` · `CAT_GENERIC` · `BREEDS`(고양이 품종) |
| `voice_gemini.py` | Gemini TTS + Whisper 정렬 |
| `ideas.py` · `alert.py` | 디스코드 아이디어 읽기 · 알림 |
| `healthcheck.py` · `health.yml` | 빈 회차 감시 |
| `youtube_uploader.py` · `auth_login.py` | 업로드(categoryId 15 애완동물) · 최초 로그인 |
| `settings.py` | 비밀값: 환경변수 → `.env` → `~/.gonyang/channel/*` |
| `office.py` · `site/` | AI 일터 · 브랜딩 페이지 (고양이 버전 작업 전) |

## 카테고리 (같은 카테고리 연달아 금지, 묶음 필수/궁금/재미 섞기)
필수: health 건강·이상신호 · food 사료·간식 · care 초보집사·돌봄 · danger 위험한 것·안전 / 궁금: behavior 행동·속마음 · breed 품종·성격 / 재미: trivia 고양이 잡학 · jipsa 집사의 세계

## 사용자 결정
- 채널명 **고냥이**(고양이를 귀엽게 부르는 말), 핸들 **@gonyangcat**(@gonyang · @고냥이 · @gonyangi · @gonyang_i 는 다른 사람이 씀), 하루 4편, 부지런과 같은 시스템, 계정 waynekim93.
- 배경 영상: 고양이 · cat 등 **최대한 다양한 종류**(11/22 요청).
- 내용 원칙: 진단 · 치료법 · 약 용량 · 특정 제품 추천 금지, 설명란에 수의사 대체 아니라는 면책, 뻔한 얘기 금지.

## 실행
- 로컬 시험(업로드 안 함): `C:\Users\SAMSUNG\togedog-channel\.venv\Scripts\python.exe -X utf8 autopilot.py --no-upload` (패키지 있는 파이썬을 빌려 씀)
- Secrets(만들 것): YT_CLIENT_SECRET · YT_TOKEN_GONYANG · GEMINI_API_KEY · PIXABAY_API_KEY · DISCORD_BOT_TOKEN · DISCORD_ALERT_CHANNEL · DISCORD_IDEA_CHANNEL (+ 사무소용 OFFICE_GIST · OFFICE_TOKEN)
- gh 는 `GH_CONFIG_DIR=~/.buzirun/gh` 로 waynekim93 계정 사용(기본 gh 는 nickkim). 이 저장소 로컬 git 자격도 그쪽으로.
- Vercel 배포는 `--global-config C:\Users\SAMSUNG\.buzirun\vercel` (이 옵션 빼면 다른 계정으로 올라감).
- **작업 전 `git pull`** — Actions 가 history.json 을 커밋함.

## 함정
- 새 Gemini 키는 2.5 계열 404 → 3.x 모델 + `discover_models()`. 구글 검색(grounding)은 무료 키 429.
- `shorts_maker.build_ass` 고칠 때 bash heredoc · re.sub 로 백슬래시를 다루면 `\\` 가 깨짐(자막 통째로 사라짐) → Edit 도구로 고치고 미리보기 렌더로 확인.
- Pixabay 키는 부지런 · 투게독과 공유(분당 100회 제한) — 다 같이 같은 시각에 돌지 않게 실행 분을 다르게 둠.
