# 고냥이 쇼츠 자동화 (gonyang-channel) — 작업 노트

유튜브 채널 **고냥이**(@gonyangcat, "고양이에 대한 모든 것")에 고양이 지식 쇼츠를
**하루 4편(12:00 · 18:00 · 20:00 · 22:00 KST)** 자동으로 만들어 예약 공개하는 프로그램.
부지런(buzirun-channel)과 **같은 시스템**을 복사해 고양이용으로 고친 것(11/22 시작). 어느 컴퓨터에서든 이 파일로 맥락을 이어간다.

> ⚠️ 이 파일 · 코드 · 커밋 메시지에 비밀번호 · 토큰 · API 키 · 채널 내부 번호를 절대 쓰지 말 것. **공개 저장소**로 쓸 예정.
> 비밀값은 노트북 `~/.gonyang/channel/`(저장소 밖)과 GitHub Secrets 에만 있음.

## 진행 상태 (11/22 저녁 — 자동 운영 시작)
- [x] 코드 복사 · 고양이용 개조(카테고리 8개 · 대본 규칙 · 검수 · 면책 · 주황 디자인 · 슬로건 "고양이에 대한 모든 것" · 전문 용어 풀이 · 군더더기 금지 · 29초 목표)
- [x] 배경 영상 다양화(stock_video.py): 장면마다 다른 종류 고양이 + 한국어 검색어 자동 추가, Pixabay 정렬·페이지 무작위, 가끔 애니메이션 스타일(한 영상 최대 2장면), 호랑이·사자 등 큰고양이 제외, 다 탈락하면 일반 고양이 검색어, 제목에 품종 이름이 있으면 그 품종 영상·사진
- [x] 구글 클라우드 프로젝트 gonyang(쿼터 분리) · OAuth 앱 '고냥이 업로더' 프로덕션 게시 · 유튜브 로그인(채널 고냥이 @gonyangcat)
- [x] Gemini 새 키 · Pixabay 키(공유) · 디스코드 서버 '고냥이' + 봇 · GitHub waynekim93/gonyang-channel(공개) + Secrets 9개(YT_CLIENT_SECRET · YT_TOKEN_GONYANG · GEMINI_API_KEY · PIXABAY_API_KEY · DISCORD_BOT_TOKEN · DISCORD_ALERT_CHANNEL · DISCORD_IDEA_CHANNEL · OFFICE_GIST · OFFICE_TOKEN)
- [x] 클라우드 시험(dry_run) 통과 · 첫 영상 즉시 공개 업로드 성공(https://youtube.com/shorts/NCARla4HSTI) · autopilot/health 켬
- [x] 프로필 · 배너 · 소개글 · 키워드 만들어 사용자가 유튜브에 적용(바탕화면 고냥이-채널아트)
- [x] AI 일터(고양이 버전) https://gonyang-cat.vercel.app/office — 직원 고양이 귀, 비밀 Gist 실시간 연결, stats.yml 15분 갱신
- [ ] 22:08 첫 예약 실행 결과 확인(내일 12·18·20·22시 4편) · 사용자 영상 피드백 반영
- [ ] 구독자 500명(1차 목표) 추적 · 반응 좋은 영상 채널 첫 화면에 고정 제안

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
| `office.py` · `site/` | AI 일터(고양이 버전, 비밀 Gist c0da…) · 브랜딩 페이지 · 배포 `vercel deploy --prod --global-config ~/.buzirun/vercel` (프로젝트 gonyang-cat) |

## 카테고리 (같은 카테고리 연달아 금지, 묶음 필수/궁금/재미 섞기)
필수: health 건강·이상신호 · food 사료·간식 · care 초보집사·돌봄 · danger 위험한 것·안전 / 궁금: behavior 행동·속마음 · breed 품종·성격 / 재미: trivia 고양이 잡학 · jipsa 집사의 세계

## 사용자 결정
- 11/25 업로드 시간 변경: 07·12·18·21시 → **12·18·20·22시**(아침 7시 폐지. 조사: 7시 편당 평균 300회 vs 18·21시 1,200~1,300회, 표본 작아 1주일 뒤 시간대별 재비교). 슬롯 이름 noon/evening/night(20시)/late(22시).
- 채널명 **고냥이**(고양이를 귀엽게 부르는 말), 핸들 **@gonyangcat**(@gonyang · @고냥이 · @gonyangi · @gonyang_i 는 다른 사람이 씀), 하루 4편, 부지런과 같은 시스템, 계정 waynekim93.
- 배경 영상: 고양이 · cat 등 **최대한 다양한 종류**(11/22 요청).
- 내용 원칙: 진단 · 치료법 · 약 용량 · 특정 제품 추천 금지, 설명란에 수의사 대체 아니라는 면책, 뻔한 얘기 금지.

## 실행
- 로컬 시험(업로드 안 함): `C:\Users\SAMSUNG\togedog-channel\.venv\Scripts\python.exe -X utf8 autopilot.py --no-upload` (패키지 있는 파이썬을 빌려 씀)
- Secrets(등록됨): YT_CLIENT_SECRET · YT_TOKEN_GONYANG · GEMINI_API_KEY · PIXABAY_API_KEY · DISCORD_BOT_TOKEN · DISCORD_ALERT_CHANNEL · DISCORD_IDEA_CHANNEL (+ 사무소용 OFFICE_GIST · OFFICE_TOKEN)
- gh 는 `GH_CONFIG_DIR=~/.buzirun/gh` 로 waynekim93 계정 사용(기본 gh 는 nickkim). 이 저장소 로컬 git 자격도 그쪽으로.
- Vercel 배포는 `--global-config C:\Users\SAMSUNG\.buzirun\vercel` (이 옵션 빼면 다른 계정으로 올라감).
- **작업 전 `git pull`** — Actions 가 history.json 을 커밋함.

## 함정
- 새 Gemini 키는 2.5 계열 404 → 3.x 모델 + `discover_models()`. 구글 검색(grounding)은 무료 키 429.
- `shorts_maker.build_ass` 고칠 때 bash heredoc · re.sub 로 백슬래시를 다루면 `\\` 가 깨짐(자막 통째로 사라짐) → Edit 도구로 고치고 미리보기 렌더로 확인.
- Pixabay 키는 부지런 · 투게독과 공유(분당 100회 제한) — 다 같이 같은 시각에 돌지 않게 실행 분을 다르게 둠.
- **Secrets 를 PowerShell 로 등록할 때**: 파이프(`$v | gh secret set`)는 값 앞에 BOM 이 붙을 수 있음 → 텍스트 키는 `-b $값`, JSON 두 개(YT_CLIENT_SECRET · YT_TOKEN_GONYANG)는 따옴표 때문에 파이프(워크플로가 BOM 을 지움). 함수 이름을 `Rd` 같은 별칭(rd=Remove-Item)으로 짓지 말 것. `Set-Content -Encoding utf8` 는 BOM 을 붙이니 코드 파일엔 쓰지 말 것.
- 사무소 문구 교체는 office.html 의 한글을 PowerShell 로 만든 스크립트에 넣지 말 것(인코딩 깨짐) — Python 파일을 Write 도구로 만들어 실행.
