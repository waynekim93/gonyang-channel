"""무료 스톡 영상 검색/다운로드 (Pixabay / Pexels, 로컬 캐시).

.env에 PIXABAY_API_KEY 또는 PEXELS_API_KEY 중 있는 것을 사용 (둘 다 있으면 Pexels 먼저).
- 최근 영상들에 쓴 클립은 다시 안 씀 (history.json의 clips)
- 문장(context)을 주면 Gemini가 후보 미리보기 사진을 보고 내용에 맞는 영상을 고름
"""
import json
import os
import random
import re
from pathlib import Path

import requests

from settings import BASE, load_env

CACHE = BASE / "cache"
HISTORY = BASE / "history.json"
RECENT_VIDEOS = 90  # 최근 이만큼의 영상(약 한 달)에 쓴 클립은 제외
PICKED: list[str] = []  # 이번 영상에서 고른 클립 → autopilot이 history에 기록 (take_picked)
ANIM_MAX = 2            # 한 영상에 애니메이션·일러스트 장면은 최대 이만큼 (스타일이 어색하게 섞이지 않게)
ANIM_USED = [0]
ANIM_PREFIX = "anim:"   # 검색어 앞에 붙이면 Pixabay 애니메이션 영상에서 찾음


def take_picked() -> list[str]:
    """이번 영상에 쓴 클립 id 목록을 꺼내고 비움."""
    out = list(dict.fromkeys(PICKED))
    PICKED.clear()
    ANIM_USED[0] = 0
    return out


def _recent_ids() -> set[str]:
    try:
        history = json.loads(HISTORY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        history = []
    return {c for h in history[-RECENT_VIDEOS:] for c in h.get("clips", [])} | set(PICKED)


def _download(url: str, path) -> str:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, stream=True, timeout=90, headers={"User-Agent": "Mozilla/5.0"}) as d:
            d.raise_for_status()
            tmp = path.with_suffix(".part")
            with open(tmp, "wb") as out:
                for chunk in d.iter_content(1 << 20):
                    out.write(chunk)
            tmp.replace(path)
    return str(path)


# ---------- Pexels ----------
def _pexels(query, used, min_sec, key):
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": key}, timeout=20,
                     params={"query": query, "orientation": "portrait", "per_page": 15})
    r.raise_for_status()
    recent = _recent_ids()
    videos = [v for v in r.json().get("videos", [])
              if ("pexels", v["id"]) not in used and f"pexels:{v['id']}" not in recent]
    candidates = ([v for v in videos if v.get("duration", 0) >= min_sec] or videos)[:6]
    random.shuffle(candidates)
    for v in candidates:
        files = [f for f in v.get("video_files", []) if f.get("height") and f.get("width")
                 and f["height"] > f["width"] and f.get("file_type") == "video/mp4"]
        if not files:
            continue
        good = [f for f in files if f["height"] >= 1920]
        f = min(good, key=lambda x: x["height"]) if good else max(files, key=lambda x: x["height"])
        used.add(("pexels", v["id"]))
        PICKED.append(f"pexels:{v['id']}")
        return _download(f["link"], CACHE / "pexels" / f"{v['id']}_{f['height']}.mp4")
    return None


# ---------- Pixabay ----------
# 검색어 첫 단어 = 장면의 주인공. 태그에 이게 없으면 버림 (예: "cute puppy tilting head" → 다람쥐 'cute, head' 배제)
SYNONYMS = {"puppy": "dog", "puppies": "dog", "doggy": "dog", "kitten": "cat", "kitty": "cat", "kittens": "cat"}
SKIP_TAGS = {"cartoon", "animation", "illustration", "render", "3d"}
# 'cat' 태그가 붙은 야생 큰고양이 — 고양이 채널엔 안 씀 (11/22 시험 2호에 호랑이가 나옴). 실사 · 애니메이션 모두 제외
BIG_CATS = {"tiger", "lion", "leopard", "cheetah", "jaguar", "panther", "puma", "cougar", "lynx", "bobcat", "ocelot",
            "serval", "caracal", "wildcat", "predator", "zoo", "safari", "wildlife", "mammal"}
ADJECTIVES = {"cute", "happy", "little", "small", "big", "beautiful", "young", "old", "calm", "cozy", "bright", "golden",
              "tabby", "black", "white", "orange", "calico", "gray", "grey", "ginger", "fluffy", "furry", "baby", "tiny",
              "fat", "stray", "street", "domestic", "adorable", "funny"}
JUDGE_MAX = 10  # Gemini에게 한 번에 보여 줄 후보 수

# ---------- 고양이 영상을 최대한 다양하게 ----------
# 장면마다 원래 검색어에 "다른 종류의 고양이 + 같은 행동"을 섞어 후보 폭을 넓힘 (치즈 · 검은 고양이 · 새끼 · 품종 · 길고양이 …)
CAT_TYPES = ["kitten", "tabby cat", "black cat", "white cat", "orange cat", "ginger cat", "calico cat", "gray cat",
             "siamese cat", "persian cat", "british shorthair", "maine coon", "bengal cat", "ragdoll cat",
             "scottish fold", "russian blue", "sphynx cat", "street cat", "fluffy cat", "baby cat", "tuxedo cat",
             "abyssinian cat", "norwegian forest cat", "munchkin cat", "domestic cat", "house cat", "stray cat"]
# 장면과 상관없이 쓸 수 있는 넓은 고양이 영상 검색어 (영어 · 한국어) — 후보가 부족하거나 다 탈락했을 때
CAT_GENERIC = ["cat", "kitten", "cat sitting", "cat lying", "cat walking", "cat playing", "cat sleeping", "cat eyes",
               "cat face", "cat sunlight", "cat window", "cat garden", "cat sofa", "cat bed", "cat looking camera",
               "cat paws", "cat fur", "cat whiskers", "cat tail", "cat resting", "cat relaxing", "cat curious",
               "고양이", "아기 고양이", "새끼 고양이", "길고양이", "집고양이", "치즈 고양이", "검은 고양이", "하얀 고양이",
               "고양이 낮잠", "고양이 놀이", "고양이 얼굴", "고양이 눈", "고양이 발", "고양이 창밖", "고양이 햇살", "냥이"]
CAT_WORDS = {"cat", "kitten", "kitty", "고양이", "냥이"}


def _cat_extras(query: str, extras: list[str]) -> list[str]:
    """장면 검색어 + 다른 종류 고양이/한국어 검색어 몇 개를 더해 후보를 넓힘. 고양이 장면이 아니면 그대로."""
    words = query.lower().split()
    if not (CAT_WORDS & set(words)):
        return extras
    action = " ".join(w for w in words if w not in CAT_WORDS and w not in ADJECTIVES)[:30]  # 예: "cat sleeping sofa" → "sleeping sofa"
    action1 = action.split()[0] if action else ""
    more = []
    for t in random.sample(CAT_TYPES, 3):
        more.append(f"{t} {action1}".strip())  # 같은 행동, 다른 고양이 (예: "black cat sleeping")
    more.append(random.choice([g for g in CAT_GENERIC if re.search("[가-힣]", g)]))  # 한국어 일반 검색어 하나
    # 가끔은 애니메이션·일러스트 스타일 고양이도 후보에 (사용자 11/22 요청) — 한 영상에 ANIM_MAX 장면까지
    if ANIM_USED[0] < ANIM_MAX and random.random() < 0.45:
        more.append(ANIM_PREFIX + random.choice(["cat", f"cat {action1}".strip(), "cartoon cat", "kitten", "cute cat"]))
    return list(dict.fromkeys([*extras, *more]))
JUDGE_ROUNDS = 4  # 장면 하나에 판단 최대 횟수 (시간·무료 한도 보호)
JUDGE_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash"]


def _norm(w: str) -> str:
    w = w.lower().strip()
    w = SYNONYMS.get(w, w)
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


def _tag_words(tags: str) -> set[str]:
    return {_norm(w) for t in tags.split(",") for w in t.split()}


def _best_file(h):
    """세로 영상 우선, 그다음 해상도 높은 것 (가로 영상은 가운데를 세로로 잘라 씀)."""
    vids = [v for v in h["videos"].values() if v.get("url")]
    if not vids:
        return None
    portrait = [v for v in vids if v["height"] > v["width"]]
    pool = portrait or vids
    # 1080p 이상 중 가장 작은 것 (4K는 다운로드가 커서 1080p 우선)
    ok = [v for v in pool if min(v["width"], v["height"]) >= 1080]
    return min(ok, key=lambda v: v["width"]) if ok else max(pool, key=lambda v: v["width"])


def _pixabay_cands(query, used, min_sec, key, strict=True, lang="en") -> list[tuple]:
    """관련도 순으로 정렬한 후보 [(점수, 세로?, 충분히 김?, hit, 파일)]. 최근 영상에 쓴 클립은 제외.
    lang: 검색어 언어 (Pixabay 는 ko 등 여러 언어 검색 지원)."""
    anim = query.startswith(ANIM_PREFIX)  # 애니메이션·일러스트 스타일 검색
    query = query.removeprefix(ANIM_PREFIX).strip()
    # 인기순 1페이지만 쓰면 늘 같은 영상 → 정렬 · 페이지를 섞어 다양하게 (2페이지가 없으면 1페이지로)
    params = {"key": key, "q": query[:100], "lang": lang, "per_page": 100, "safesearch": "true",
              "order": random.choices(["popular", "latest"], weights=[3, 2])[0],
              "video_type": "animation" if anim else "film"}  # 기본은 실사만, anim 이면 애니메이션
    page = random.choices([1, 2, 3], weights=[5, 3, 2])[0]
    r = requests.get("https://pixabay.com/api/videos/", timeout=20, params={**params, "page": page})
    if r.status_code == 400 and page > 1:  # 그 페이지까지 결과가 없음
        r = requests.get("https://pixabay.com/api/videos/", timeout=20, params=params)
    r.raise_for_status()
    recent = _recent_ids()
    hits = [h for h in r.json().get("hits", [])
            if ("pixabay", h["id"]) not in used and f"pixabay:{h['id']}" not in recent]

    qwords = [_norm(w) for w in query.split() if len(w) > 2]
    subject = next((w for w in qwords if w not in ADJECTIVES), "")
    scored = []
    for h in hits:
        v = _best_file(h)
        tags = _tag_words(h.get("tags", ""))
        if not v or (tags & SKIP_TAGS and not anim) or tags & BIG_CATS or (strict and subject and subject not in tags):
            continue
        if anim:
            h["_anim"] = True  # _take 에서 애니메이션 장면 수를 셈
        # 태그가 검색어와 많이 겹칠수록 관련도 높음 (주인공 단어는 2점)
        match = sum(w in tags for w in qwords) + (subject in tags)
        scored.append((match, v["height"] > v["width"], h.get("duration", 0) >= min_sec, h, v))
    # 관련도 → 세로 → 충분히 긴 것 순
    scored.sort(key=lambda x: x[:3], reverse=True)
    return scored


def _thumb(h) -> bytes | None:
    urls = ([h["videos"].get(size, {}).get("thumbnail") for size in ("small", "medium", "tiny", "large")]
            if "videos" in h else [h.get("webformatURL"), h.get("previewURL")])
    for url in urls:
        if not url:
            continue
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.content
        except requests.RequestException:
            continue
    return None


JUDGE_PROMPT = """유튜브 쇼츠 배경 영상을 고르는 중이야.
{context}
검색어: {query}

아래 사진 {n}장은 후보 영상의 한 장면이야 (순서대로 1번~{n}번).
이 문장이 나오는 동안 뒤에 깔렸을 때 가장 잘 어울리는 영상 번호를 골라.
- 문장이 말하는 대상(음식·동물·물건·장소·행동)이 실제로 화면에 보여야 함. 예: 돈가스 이야기인데 꽃이나 깃발이면 탈락
- 고양이 이야기면 고양이가 화면에 크게 잘 보여야 함 (멀리 작게 보이면 감점), 품종이 나오면 그 품종에 가까울수록 좋음
- 실사든 애니메이션 · 일러스트 · 만화 스타일이든 고양이가 또렷하고 귀여우면 OK (애니메이션이라고 감점하지 않음)
- 고양이가 아닌 다른 동물(강아지 등)이나 사람 얼굴 클로즈업이 주인공이면 탈락. 호랑이 · 사자 · 표범 같은 야생 큰고양이도 탈락 (집에서 키우는 고양이만)
- 후보들 중에서는 이미 흔한 장면보다 표정 · 움직임이 또렷하고 눈길을 끄는 영상을 우선
- 큰 글자·로고·워터마크가 있거나, 너무 어둡거나, 흐릿하면 감점
- 문장의 핵심 대상 하나만 분명히 보이면 충분함 (문장 내용을 전부 담을 필요는 없음)
- 어울리는 게 하나도 없으면 0
JSON으로만 답해: {{"pick": 번호, "alt": "0일 때 다시 찾아볼 영어 검색어 2~3단어 — 지금 검색어보다 더 넓고 흔한 장면 (예: 돈가스→fried food plate, 양배추 보관→vegetables kitchen counter), 주인공 명사로 시작"}}"""


def _judge(pool: list, query: str, context: str) -> tuple[int | None, str]:
    """Gemini가 미리보기 사진으로 고르기 → (pool 인덱스 / -1 = 다 안 맞음 / None = 판단 실패, 대체 검색어)."""
    try:
        from google import genai
        from google.genai import types

        from script_writer import HTTP, _generate

        shown, parts = [], []
        for i, c in enumerate(pool):
            img = _thumb(c[3])
            if img:
                shown.append(i)
                parts.append(types.Part.from_bytes(data=img, mime_type="image/jpeg"))
        if not shown:
            return None, ""
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"], http_options=HTTP)
        resp = _generate(client, JUDGE_MODELS, [JUDGE_PROMPT.format(context=context, query=query, n=len(shown)), *parts],
                         types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
        data = json.loads(resp.text)
        pick, alt = int(data.get("pick") or 0), str(data.get("alt") or "").strip()
        return (shown[pick - 1] if 1 <= pick <= len(shown) else -1), alt
    except (Exception, SystemExit) as e:  # 판단이 실패해도 영상 제작은 계속 (예전 방식으로)
        print(f"    (배경 판단 건너뜀: {str(e)[:100]})")
        return None, ""


def _take(cand, used) -> str:
    *_, h, v = cand
    used.add(("pixabay", h["id"]))
    PICKED.append(f"pixabay:{h['id']}")
    if h.get("_anim"):
        ANIM_USED[0] += 1
    return _download(v["url"], CACHE / "pixabay" / f"{h['id']}_{v['width']}x{v['height']}.mp4")


def _lang(q: str) -> str:
    return "ko" if re.search("[가-힣]", q) else "en"


def _mixed_pool(queries: list[str], used, min_sec, key) -> list:
    """여러 검색어(영어 · 다른 영어 표현 · 한국어)의 상위 후보를 번갈아 섞어 한 묶음으로 — 더 다양한 영상 중에서 고르게."""
    lists = []
    for q in queries:
        try:
            sc = _pixabay_cands(q, used, min_sec, key, strict=_lang(q) == "en", lang=_lang(q))
        except requests.RequestException as e:
            print(f"    pixabay 검색 실패({q}): {e}")
            continue
        if sc:
            sc = [x for x in sc if x[0] >= sc[0][0] - 1][:JUDGE_MAX * 2]
            random.shuffle(sc)
            lists.append(sc)
    pool, seen = [], set()
    while len(pool) < JUDGE_MAX and any(lists):
        for lst in lists:
            while lst:
                c = lst.pop(0)
                if c[3]["id"] not in seen:
                    seen.add(c[3]["id"])
                    pool.append(c)
                    break
            if len(pool) >= JUDGE_MAX:
                break
    return pool


def _pixabay_pick(tries: list[tuple[str, bool]], used, min_sec, key, context: str, extras=()) -> str | None:
    """검색어를 차례로 넓혀 가며 후보를 모으고, 문장에 맞는 영상을 골라 다운로드.
    extras(다른 영어 표현 · 한국어 검색어)가 있으면 첫 판단은 모든 검색어 후보를 섞은 묶음으로."""
    judging = bool(context and os.environ.get("GEMINI_API_KEY"))
    queue, tried, first, alts, judged = list(tries), set(), None, 0, 0
    if extras and judging:
        queries = list(dict.fromkeys([tries[0][0], *extras]))
        pool = _mixed_pool(queries, used, min_sec, key)
        tried.add(tries[0])
        if pool:
            idx, alt = _judge(pool, " / ".join(queries), context)
            judged += 1
            if idx is None:
                return _take(pool[0], used)
            if idx >= 0:
                print(f"    ✔ 검색어 {len(queries)}개({' / '.join(queries)}) 후보 {len(pool)}개 중 선택")
                return _take(pool[idx], used)
            print(f"    ✘ 섞은 후보 {len(pool)}개 모두 내용과 안 맞음" + (f" → '{alt}' 로 다시" if alt else ""))
            first = pool[0]
            if alt:
                queue.insert(0, (alt, True))
                alts += 1
    while queue and judged < JUDGE_ROUNDS:
        q, strict = queue.pop(0)
        if (q, strict) in tried:
            continue
        tried.add((q, strict))
        scored = _pixabay_cands(q, used, min_sec, key, strict)
        if not scored:
            continue
        if not judging:
            # 판단 없이: 관련도 최고점 후보 몇 개 중 랜덤 (매번 같은 영상 안 나오게)
            return _take(random.choice([x for x in scored if x[0] == scored[0][0]][:6]), used)
        # 관련도 최고점 -1 까지 넓게 모아 섞은 뒤 Gemini가 고름
        pool = [x for x in scored if x[0] >= scored[0][0] - 1][:JUDGE_MAX * 3]
        random.shuffle(pool)
        pool = pool[:JUDGE_MAX]
        idx, alt = _judge(pool, q, context)
        judged += 1
        if idx is None:
            return _take(pool[0], used)
        if idx >= 0:
            print(f"    ✔ '{q}' 후보 {len(pool)}개 중 내용에 맞는 영상 선택")
            return _take(pool[idx], used)
        print(f"    ✘ '{q}' 후보 {len(pool)}개 모두 내용과 안 맞음" + (f" → '{alt}' 로 다시" if alt and alts < 2 else ""))
        first = first or pool[0]
        if alt and alts < 2:  # Gemini가 제안한 더 넓은 검색어를 바로 다음에 (최대 2번)
            queue.insert(0, (alt, True))
            alts += 1
    # 끝까지 맞는 게 없으면 처음 후보 (그라데이션 배경보다는 나음)
    return _take(first, used) if first else None


# ---------- 품종 ----------
# 품종 이야기 장면엔 반드시 그 품종이 나와야 함. Pixabay 에 그 품종 영상이 적으면 사진(수십~수백 장)에 천천히 확대되는 움직임을 줘서 씀.
# 한국어 이름 → (Pixabay 검색어, 태그에 있어야 할 단어 묶음 — 묶음 하나의 단어가 다 있으면 그 품종)
BREEDS = {
    "러시안블루": ("russian blue cat", [{"russian", "blue"}]),
    "브리티시숏헤어": ("british shorthair cat", [{"british"}]), "브숏": ("british shorthair cat", [{"british"}]),
    "페르시안": ("persian cat", [{"persian"}]),
    "샴고양이": ("siamese cat", [{"siamese"}]), "샴": ("siamese cat", [{"siamese"}]),
    "메인쿤": ("maine coon cat", [{"maine", "coon"}, {"mainecoon"}]),
    "랙돌": ("ragdoll cat", [{"ragdoll"}]),
    "벵갈": ("bengal cat", [{"bengal"}]), "뱅갈": ("bengal cat", [{"bengal"}]),
    "스코티시폴드": ("scottish fold cat", [{"scottish"}]), "스코티시": ("scottish fold cat", [{"scottish"}]),
    "아비시니안": ("abyssinian cat", [{"abyssinian"}]),
    "노르웨이숲": ("norwegian forest cat", [{"norwegian"}]),
    "스핑크스": ("sphynx cat", [{"sphynx"}]),
    "먼치킨": ("munchkin cat", [{"munchkin"}]),
    "터키시앙고라": ("turkish angora cat", [{"angora"}]), "앙고라": ("turkish angora cat", [{"angora"}]),
    "아메리칸숏헤어": ("american shorthair cat", [{"american", "shorthair"}]),
    "히말라얀": ("himalayan cat", [{"himalayan"}]),
    "샤트룩스": ("chartreux cat", [{"chartreux"}]),
    "코리안숏헤어": ("korean shorthair cat", [{"korean", "shorthair"}]),
    "치즈냥": ("orange tabby cat", [{"orange", "tabby"}, {"ginger"}]),
    "턱시도": ("tuxedo cat", [{"tuxedo"}]),
    "삼색이": ("calico cat", [{"calico"}]), "삼색냥": ("calico cat", [{"calico"}]),
}


def detect_breed(text: str) -> str:
    """글에 나온 품종(한국어 이름) — 긴 이름부터 찾음 ('토이푸들'이 '푸들'보다 먼저). 없으면 ''."""
    flat = (text or "").replace(" ", "")
    return next((k for k in sorted(BREEDS, key=len, reverse=True) if k in flat), "")


def _breed_hits(kind: str, breed: str, used, key, allow_recent: bool) -> list[dict]:
    q, groups = BREEDS[breed]
    url = "https://pixabay.com/api/videos/" if kind == "video" else "https://pixabay.com/api/"
    params = {"key": key, "q": q, "per_page": 100, "safesearch": "true", "order": "popular"}
    params.update({"video_type": "film"} if kind == "video" else {"image_type": "photo"})
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    tag = "pixabay" if kind == "video" else "pixabay-img"
    recent = set() if allow_recent else _recent_ids()
    out = []
    for h in r.json().get("hits", []):
        tags = _tag_words(h.get("tags", ""))
        if (tag, h["id"]) in used or f"{tag}:{h['id']}" in recent or tags & SKIP_TAGS:
            continue
        if any(g <= tags for g in groups):
            out.append(h)
    return out


def _photo_clip(img: Path, sec: float) -> str:
    """사진 → 1080x1920 영상 (흐린 배경 위에 사진 전체, 천천히 확대)."""
    import subprocess

    from shorts_maker import FFMPEG
    n = max(int((sec + 1) * 30), 60)
    out = img.with_name(f"{img.stem}_{n}.mp4")
    if not out.exists():
        vf = ("split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
              "boxblur=24:2,eq=brightness=-0.08[bg];[b]scale=1080:1920:force_original_aspect_ratio=decrease[fg];"
              "[bg][fg]overlay=(W-w)/2:(H-h)/2,scale=2160:3840,"
              f"zoompan=z='1+0.08*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,"
              "format=yuv420p")
        subprocess.run([FFMPEG, "-y", "-loop", "1", "-framerate", "30", "-i", str(img), "-frames:v", str(n),
                        "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", str(out)],
                       check=True, capture_output=True)
    return str(out)


def _breed_clip(breed: str, used, min_sec, key, context: str) -> str | None:
    """그 품종 영상 → 없으면 그 품종 사진. 최근 영상에 쓴 것밖에 없으면 다시 씀 (다른 품종보다는 나음)."""
    q = BREEDS[breed][0]
    ctx = f"{context}\n⚠️ 이 장면엔 반드시 {breed}({q})가 보여야 함. 다른 품종이면 0."
    judging = bool(context and os.environ.get("GEMINI_API_KEY"))
    rejected = set()  # 이미 안 맞는다고 본 후보는 다시 판단 안 함
    for kind in ("video", "photo"):
        for allow_recent in (False, True):
            hits = [h for h in _breed_hits(kind, breed, used, key, allow_recent) if (kind, h["id"]) not in rejected]
            if kind == "video":
                hits = [h for h in hits if _best_file(h)]
            if not hits:
                continue
            random.shuffle(hits)
            pool = [(0, 0, 0, h, _best_file(h) if kind == "video" else None) for h in hits[:JUDGE_MAX]]
            idx, _ = _judge(pool, q, ctx) if judging else (None, "")
            if idx == -1:
                rejected.update((kind, c[3]["id"]) for c in pool)
                print(f"    ✘ {breed} {'영상' if kind == 'video' else '사진'} {len(pool)}개 모두 장면과 안 맞음")
                continue
            pick = pool[idx if idx is not None else 0]
            if kind == "video":
                print(f"    🐱 {breed} 영상 사용")
                return _take(pick, used)
            h = pick[3]
            used.add(("pixabay-img", h["id"]))
            PICKED.append(f"pixabay-img:{h['id']}")
            img = Path(_download(h.get("largeImageURL") or h["webformatURL"], CACHE / "pixabay_img" / f"{h['id']}.jpg"))
            print(f"    🐱 {breed} 영상이 없어 {breed} 사진으로")
            return _photo_clip(img, min_sec)
    return None


def fetch_clip(query: str, used: set, min_sec: float = 0, context: str = "", breed: str = "") -> str | None:
    """검색어에 맞는 영상 1개를 받아 로컬 경로 반환 (없으면 None → 그라데이션 배경).
    context = 영상 제목 + 이 장면의 문장 — 있으면 Gemini가 내용에 맞는 영상을 고름.
    breed = 이 장면의 품종(한국어, detect_breed) — 있으면 그 품종 영상·사진만.
    query 를 '|' 로 이어 주면 (예: "apartment complex aerial | residential towers drone | 아파트 단지")
    첫 번째가 기본 검색어, 나머지는 다른 표현 · 한국어 검색어로 후보를 더 모음."""
    load_env()
    query, *extras = [q.strip() for q in query.split("|") if q.strip()] or [query]
    extras = _cat_extras(query, extras)  # 다른 종류 고양이 · 한국어 검색어로 후보 넓히기
    if breed in BREEDS and os.environ.get("PIXABAY_API_KEY"):
        try:
            path = _breed_clip(breed, used, min_sec, os.environ["PIXABAY_API_KEY"], context)
            if path:
                return path
        except Exception as e:  # 품종 찾기가 실패해도 영상 제작은 계속 (일반 검색으로)
            print(f"    ({breed} 찾기 실패, 일반 검색으로: {str(e)[:100]})")
    words = query.split()
    # 주인공 단어가 태그에 있는 영상만 → 검색어 줄여서(주인공+1단어, 주인공만) → 그래도 없으면 제한 없이
    words = [w for w in words if w.lower() not in ADJECTIVES] or words
    tries = [(q, True) for q in dict.fromkeys([query, " ".join(words[:2]), " ".join(words[:1])])] + [(query, False)]
    if os.environ.get("PEXELS_API_KEY"):
        for q, _ in tries[:-1]:
            try:
                path = _pexels(q, used, min_sec, os.environ["PEXELS_API_KEY"])
            except requests.RequestException as e:
                print(f"    pexels 검색 실패({q}): {e}")
                break
            if path:
                return path
    if os.environ.get("PIXABAY_API_KEY"):
        key = os.environ["PIXABAY_API_KEY"]
        try:
            path = _pixabay_pick(tries, used, min_sec, key, context, extras)
            if path:
                return path
        except requests.RequestException as e:
            print(f"    pixabay 검색 실패({query}): {e}")
        # 그래도 없으면 일반 고양이 검색어를 무작위로 (그라데이션 배경보다는 고양이 영상이 나음)
        if CAT_WORDS & set(query.lower().split()):
            for q in random.sample(CAT_GENERIC, 4):
                try:
                    scored = _pixabay_cands(q, used, min_sec, key, strict=not re.search("[가-힣]", q),
                                            lang=_lang(q))
                except requests.RequestException:
                    continue
                if scored:
                    print(f"    (일반 고양이 검색 '{q}' 로 대체)")
                    return _take(random.choice(scored[:6]), used)
    return None
