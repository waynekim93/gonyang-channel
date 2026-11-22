"""주제 → 쇼츠 대본(제목/문장/설명/태그) 자동 작성 (Gemini). 건강·안전 주제는 research()로 검색 확인 먼저(유료 키에서만)."""
import json
import os
import time

import httpx
from google import genai
from google.genai import errors, types

from settings import BASE, load_env
# 순서대로 시도 (과부하/한도 초과 시 다음 모델로). 특정 모델 고정 시 .env에 GEMINI_MODEL=
HTTP = types.HttpOptions(timeout=90_000)  # ms — 응답 없이 몇 분씩 멈추는 것 방지
# gemini-flash-latest 별칭은 11/09 기준 404(종료) — 목록이 다 죽어도 discover_models()가 대체 모델을 찾음
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.5-flash-lite"]

PROMPT = """너는 유튜브 쇼츠 대본 작가야. 주제: "{topic}"

조건:
- 한국어, 소리 내어 읽었을 때 약 {seconds}초 분량 (대략 {chars}자 내외)
- 문장 {n_min}~{n_max}개. 각 문장은 화면 자막 한 장면이 되므로 짧고 임팩트 있게 (한 문장 35자 이내)
- 첫 문장은 스크롤을 멈추게 하는 강한 후킹, 마지막 문장은 여운이나 행동 유도
- 주제 뒤에 붙은 카테고리 지침의 형식과 말투를 우선으로 따를 것
- 이모지, 해시태그, 따옴표, 괄호, 화자 표시 없이 읽을 문장만

- scenes: 각 문장 뒤에 깔릴 배경 영상의 영어 검색어 (sentences와 같은 개수).
  2~4단어, 실제 촬영한 고양이 장면 (예: "cat sleeping sofa", "kitten playing toy", "cat eating food bowl",
  "cat looking window", "cat paw closeup", "cat yawning", "cat grooming licking", "cat cardboard box", "cat litter box",
  "cat veterinarian", "cat tail", "cat jumping", "cat purring lap", "cat scratching post", "cat sunbathing").
  첫 단어는 반드시 장면의 주인공 명사 하나 (cat, kitten, paw, tail 등 — 형용사로 시작 금지). 주제가 고양이가 아닌 장면
  (사료 그릇, 장난감, 동물병원, 집 안 풍경)도 cat 이 함께 나오게 검색어를 잡을 것.
  너무 어둡거나 추상적인 검색어(dark, particles, abstract, space)는 피할 것.
  사람 얼굴 클로즈업, 글자, 로고는 피할 것. 문장 내용에 어울리되 장면이 서로 다양하게.
- scenes_alt: scenes와 같은 개수. 각 장면을 다른 말로 찾을 검색어 2개 [같은 장면의 다른 영어 표현, 한국어 검색어]
  (예: "cat sleeping sofa" → ["kitten napping couch", "고양이 낮잠"],
  "cat eating food bowl" → ["cat feeding dish", "고양이 밥"]). 한국어는 2~3단어 명사 위주.

JSON으로만 답해:
{{"title": "영상 제목(25자 이내, 해시태그 없이)",
  "title_point": "제목 안에서 강조색으로 표시할 핵심 말 (제목에 그대로 있는 2~6글자, 예: '골골송의 정체')",
  "sentences": ["문장1", "문장2", ...],
  "scenes": ["english query 1", "english query 2", ...],
  "scenes_alt": [["other english 1", "한국어 1"], ["other english 2", "한국어 2"], ...],
  "description": "영상 설명 2~3줄",
  "tags": ["태그1", "태그2", "태그3", "태그4", "태그5"]}}"""


def discover_models(client, kind: str = "text") -> list[str]:
    """지금 키로 쓸 수 있는 모델 목록에서 대체 후보 찾기 (구글이 모델을 종료해도 멈추지 않게).
    text = 일반 flash 계열(최신 버전 먼저, lite는 뒤로), tts = 이름에 tts가 들어간 모델."""
    import re
    try:
        names = [m.name.removeprefix("models/") for m in client.models.list()]
    except Exception as e:
        print(f"  (모델 목록 조회 실패: {str(e)[:100]})")
        return []
    if kind == "tts":
        return [n for n in names if "tts" in n]
    skip = ("image", "tts", "audio", "live", "embedding", "omni", "research", "preview", "exp", "banana")
    cands = [n for n in names if n.startswith("gemini-") and "flash" in n and not any(k in n for k in skip)]
    ver = lambda n: [int(x) for x in re.findall(r"\d+", n.split("-")[1])] if len(n.split("-")) > 1 else [0]
    return sorted(cands, key=lambda n: ("lite" in n, [-x for x in ver(n)]))


def _generate(client, models, prompt, config):
    """모델별 최대 2회 시도. 과부하(429/5xx)·연결 끊김이면 재시도, 없는 모델(404)이면 바로 다음 모델.
    목록이 전부 실패하면 지금 쓸 수 있는 모델을 찾아 최대 3개 더 시도."""
    try:
        return _try_models(client, models, prompt, config)
    except SystemExit:
        extra = [m for m in discover_models(client) if m not in models][:3]
        if not extra:
            raise
        print(f"  대체 모델 시도: {', '.join(extra)}")
        return _try_models(client, extra, prompt, config)


def _try_models(client, models, prompt, config):
    last_err = None
    for m in models:
        for attempt in range(2):
            try:
                return client.models.generate_content(model=m, contents=prompt, config=config)
            except errors.APIError as e:
                if e.code not in (404, 429, 500, 502, 503, 504):
                    raise
                last_err = e
                print(f"  {m} 응답 없음({e.code})")
                if e.code == 404:
                    break
            except (httpx.HTTPError, ConnectionError) as e:  # 서버가 응답 없이 끊음·시간 초과
                last_err = e
                print(f"  {m} 연결 끊김({type(e).__name__})")
            if attempt == 0:
                time.sleep(5)
    raise SystemExit(f"모든 Gemini 모델이 응답하지 않습니다. 잠시 후 다시 시도하세요. ({last_err})")


TOPIC_PROMPT = """너는 유튜브 쇼츠 채널의 기획자야.
채널 콘셉트: {profile}
이번 업로드 시간대: {slot_desc}

최근에 이미 다룬 주제 (겹치거나 비슷하면 안 됨):
{recent}

이 시간대 시청자가 스크롤을 멈출 만한, 이번 카테고리에 맞는 새 주제 하나를 정해.
구체적이고 궁금증이 생기게 (예: "고양이가 꾹꾹이를 하는 진짜 이유", "냉장고에 넣으면 안 되는 의외의 음식",
"아재개그 넌센스 퀴즈 3탄", "작심삼일을 끝내는 2분 규칙", "괜찮아, 오늘은 쉬어가도 돼").
너무 무겁거나 우울한 주제는 피하고, 최근 주제와 소재가 겹치지 않게.
JSON으로만 답해: {{"topic": "주제"}}"""


def pick_topic(profile: str, slot_desc: str, recent: list[str]) -> str:
    load_env()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=HTTP)
    prompt = TOPIC_PROMPT.format(profile=profile, slot_desc=slot_desc,
                                 recent="\n".join(f"- {t}" for t in recent[-60:]) or "(없음)")
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=1.0)
    fixed = os.environ.get("GEMINI_MODEL")
    resp = _generate(client, [fixed] if fixed else FALLBACK_MODELS, prompt, config)
    return json.loads(resp.text)["topic"].strip()


IDEA_PROMPT = """너는 유튜브 쇼츠 채널의 기획자야.
채널 콘셉트: {profile}
대표님이 길에서 떠올린 아이디어를 메신저로 보냈어 (말투가 짧거나 구어체일 수 있음):
"{idea}"

이 아이디어의 핵심을 살려 쇼츠 주제 한 줄로 다듬고, 가장 잘 맞는 카테고리 키를 골라.
카테고리:
{categories}
주제는 구체적이고 궁금증이 생기게 (예: "고양이가 상자를 좋아하는 진짜 이유"). 대표님 의도를 바꾸지 말 것.
JSON으로만 답해: {{"topic": "주제", "category": "카테고리 키"}}"""


def shape_idea(profile: str, idea: str, categories: dict[str, str]) -> dict:
    """대표님 아이디어(디스코드) → 쇼츠 주제 + 카테고리."""
    load_env()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=HTTP)
    prompt = IDEA_PROMPT.format(profile=profile, idea=idea, categories="\n".join(f"- {k}: {v}" for k, v in categories.items()))
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.6)
    fixed = os.environ.get("GEMINI_MODEL")
    out = json.loads(_generate(client, [fixed] if fixed else FALLBACK_MODELS, prompt, config).text)
    return {"topic": out["topic"].strip(), "category": out.get("category") if out.get("category") in categories else None}


def write_script(topic: str, seconds: int = 30, model: str | None = None) -> dict:
    load_env()
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit(f"GEMINI_API_KEY가 없습니다. {BASE / '.env'} 파일에 GEMINI_API_KEY=키값 을 넣어주세요.")
    client = genai.Client(api_key=key, http_options=HTTP)
    n = max(2, round(seconds / 4.5))
    prompt = PROMPT.format(topic=topic, seconds=seconds, chars=seconds * 7, n_min=n - 1, n_max=n + 1)
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.9)
    fixed = model or os.environ.get("GEMINI_MODEL")
    resp = _generate(client, [fixed] if fixed else FALLBACK_MODELS, prompt, config)
    data = json.loads(resp.text)
    data["sentences"] = [s.strip() for s in data["sentences"] if s.strip()]
    return review_script(client, data, fixed)


REVIEW_PROMPT = """너는 고양이 행동학 · 수의학 · 영양학 상식에 밝은 꼼꼼한 검수자야. 아래는 유튜브 쇼츠 대본(JSON)이야.

{script}

다음을 찾아서 고쳐:
- 사실과 다르거나 고양이를 위험하게 만들 수 있는 문장 (잘못된 먹이 · 약 · 치료 · 응급 대처, 근거 없는 속설을 사실처럼 말한 것)
- 과장 · 단정 표현 ('절대', '무조건', '100%', '모든 고양이는') → 사실에 맞는 정도로 ('대부분', '~일 수 있어요')
- 확실하지 않은 구체적 숫자(용량 · 기간 · 나이 · 체중 · 수치) → 빼거나 원리로. 약 · 영양제 용량은 절대 말하지 않기
- 병을 진단하거나 치료법을 단정하는 말 → '이런 모습이 보이면 병원에서 확인' 으로
- 사람 음식 · 식물 · 용품이 안전하다고 말하는 문장은 특히 엄격하게 (확실히 안전하다고 알려진 것만)
- 군더더기: 앞 문장을 반복하거나 근거가 약한 덕담 · 조언으로 채운 문장은 빼거나, 확실한 새 정보로 바꾸기 (문장 수는 1개까지만 줄일 수 있음)
- 오탈자 · 어색한 말, 제목이 내용과 안 맞는 것 (title_point 는 고친 제목 안에 그대로 있어야 함)
문제가 없는 문장은 그대로 두고, 재미 · 훅 · 말투 · 문장 수 · 문장 길이는 최대한 유지해.
같은 JSON 구조 그대로(모든 키 유지) + "fixes": ["고친 내용 한 줄씩"] 를 더해서 JSON으로만 답해."""


def review_script(client, data: dict, model: str | None = None) -> dict:
    """대본 검수: 사실 오류 · 과장 · 오탈자 고치기. 실패하거나 결과가 이상하면 원래 대본 그대로."""
    from office import report
    report("review", "초안 받았습니다. 고양이 상식 오류랑 과장 표현 검수할게요 🔍", "reviewer", stage="review")
    config = types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2)
    try:
        resp = _generate(client, [model] if model else FALLBACK_MODELS,
                         REVIEW_PROMPT.format(script=json.dumps(data, ensure_ascii=False, indent=1)), config)
        out = json.loads(resp.text)
        sents = [s.strip() for s in out.get("sentences", []) if isinstance(s, str) and s.strip()]
        if not out.get("title") or abs(len(sents) - len(data["sentences"])) > 1:
            raise ValueError("검수 결과 형식이 달라짐")
        for k in ("title", "title_point", "description", "tags"):
            if out.get(k):
                data[k] = out[k]
        data["sentences"] = sents
        if len(sents) != len(data.get("scenes") or sents):  # 문장 수가 바뀌면 장면 수도 맞춤
            data["scenes"] = [(data["scenes"] * 2)[i] for i in range(len(sents))] if data.get("scenes") else None
            data["scenes_alt"] = None
        for f in out.get("fixes") or []:
            print(f"  ✏️ 검수: {f}")
            report("review", f"수정: {f}"[:140], "reviewer")
    except (Exception, SystemExit) as e:
        print(f"  (검수 건너뜀: {str(e)[:100]})")
    return data


RESEARCH_PROMPT = """고양이 유튜브 쇼츠 대본을 쓰기 전 사실 확인이 필요해. 오늘은 {today}.
주제: "{topic}"

구글 검색으로 수의학 · 동물행동학 근거(수의과대학 · 동물병원 협회 · 대한수의사회 · ASPCA · Cornell Feline Health Center ·
International Cat Care 등 공식 · 전문 출처 우선)를 확인해서 대본에 쓸 핵심 사실 5개 이내를 한 줄씩 적어. 각 줄 끝에 (출처 이름).
숫자(나이 · 기간 · 체중 · 용량)는 전문 출처에서 확인된 것만, 출처마다 다르면 그 줄 앞에 [불확실] 이라고 표시.
설명 없이 목록만."""


def research(topic: str) -> str:
    """구글 검색으로 최신 기준 확인 → 대본 작가에게 줄 사실 목록. 실패하면 '' (대본은 원리 위주로)."""
    from datetime import date
    load_env()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=HTTP)
    config = types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0.2)
    fixed = os.environ.get("GEMINI_MODEL")
    try:
        resp = _generate(client, [fixed] if fixed else FALLBACK_MODELS,
                         RESEARCH_PROMPT.format(today=date.today().isoformat(), topic=topic), config)
        return (resp.text or "").strip()
    except (Exception, SystemExit) as e:
        print(f"  (검색 확인 실패 — 숫자 없이 원리 위주로: {str(e)[:120]})")
        return ""
