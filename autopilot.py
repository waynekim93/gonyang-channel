"""고냥이 채널 완전 자동: 주제 선정(디스코드 아이디어 우선) → (선택) 사실 확인 → 대본 → 검수 → 영상 → 예약 업로드 → 기록.
부지런(buzirun-channel) 시스템을 그대로 복사해 고양이용으로 고친 것 — 부지런 · 캄모니 · 투게독과 저장소 · 비밀값 모두 따로.

  python autopilot.py --schedule        # 예약 대기열 채우기 (07:00 / 12:00 / 18:00 / 21:00 KST) — 자동 실행은 이것
  python autopilot.py --plan            # 만들 회차 수만 출력
  python autopilot.py --no-upload       # 업로드 없이 1편 시험 제작
  python autopilot.py --category health --topic "..."   # 카테고리 · 주제 지정
"""
import argparse
import json
import os
import random
import re
import traceback
from datetime import datetime, timedelta, timezone

from office import report
from settings import BASE

KST = timezone(timedelta(hours=9))
CHANNEL = "고냥이"
HISTORY = BASE / "history.json"
PROFILE = ("고냥이 — '고양이에 대한 모든 것'. 고양이를 키우는 집사(초보부터 베테랑까지)와 고양이를 좋아하는 사람을 위한 "
           "쉽고 짧은 지식 쇼츠 채널. 행동 · 건강 · 사료 · 돌봄 · 품종 · 생활 안전 · 잡학을 다룸. "
           "말투는 고양이를 잘 아는 다정한 집사 선배가 알려 주듯 친근하고 따뜻한 존댓말. "
           "병을 진단하거나 치료법 · 약 · 영양제 용량을 단정하는 말 금지, 특정 제품 · 브랜드 추천 금지, "
           "동물 학대 · 유기 · 번식장 조장 금지. 사실로 확인된 것만 쓰고, 애매하면 '~일 수 있어요'. "
           "주제는 누구나 아는 뻔한 얘기가 아니라 '아, 그래서 그랬구나!' 하고 무릎을 치게 되는 한 끗 차이 지식 "
           "(예: '고양이가 새벽 4시에 우다다 뛰는 진짜 이유', '골골송이 기분 좋을 때만 나오는 소리가 아닌 이유', "
           "'고양이가 눈을 천천히 깜빡일 때 하는 말', '밥을 먹고 토하는 고양이, 괜찮은 경우와 병원 가야 하는 경우').")
FORMAT = ("구성: 첫 문장은 2초 안에 스크롤을 멈추게 하는 훅(몰랐던 사실 · 오해 · 걱정되는 행동), "
          "중간은 핵심 3가지를 '첫째·둘째·셋째'처럼 또렷하게, 마지막 두 문장은 한 줄 정리 + 아래 (마무리) 지시. "
          "제목은 사람들이 실제로 검색하는 말(고양이 + 행동 · 구토 · 사료 · 골골송 · 꾹꾹이 · 중성화 · 합사 등)을 맨 앞에 두고, "
          "궁금증이 생기게 (예: '고양이가 꾹꾹이 하는 진짜 이유'). "
          "⚠️ 누구나 아는 뻔한 말 금지 (예: '고양이는 귀엽다', '물을 잘 챙겨 주세요', '사랑으로 키우세요', "
          "'병원에 가 보세요' 한 줄로 끝내기) — 핵심 3가지는 각각 '이건 몰랐네' 싶은 구체적인 내용이어야 함: "
          "행동의 진짜 이유, 사람들이 흔히 잘못 아는 것, 집사가 오늘 바로 할 수 있는 한 가지, 병원에 가야 하는 신호. "
          "'절대 · 무조건 · 모든 고양이는' 같은 단정 금지 ('대부분', '~일 수 있어요'). "
          "⚠️ 군더더기 금지: 모든 문장은 새로운 정보 하나를 담을 것. 같은 말을 바꿔 반복하거나, 근거가 약한 덕담 · 조언 "
          "('이름을 불러 주면 행복해해요' 같은)으로 3가지를 억지로 채우지 말 것 — 확실한 포인트가 둘뿐이면 둘만 쓰고 짧게. "
          "문장은 한 문장당 25자 안팎으로 짧게, 전체 6~7문장. "
          "행동 설명이 병과 헷갈릴 수 있는 주제면 '이런 모습이 같이 보이면 동물병원에서 확인' 한 마디를 정리 문장에 살짝. ")

# 카테고리: (설명, 대본 지시, 목소리 톤, 태그, 묶음) — 묶음이 같은 영상이 두 편 연달아 나오지 않게 섞음(필수 / 궁금 / 재미)
CATEGORIES = {
    "behavior": ("행동 · 속마음 — 꾹꾹이 · 골골송 · 그루밍 · 꼬리 · 새벽 우다다 · 박스 사랑 · 눈 깜빡임 · 갑자기 물기 · 스크래칭 · 높은 곳을 좋아하는 이유",
                 FORMAT + "'우리 냥이가 이래서 그랬구나' 싶게 고양이 입장에서 설명. 귀엽게, 하지만 근거 있는 내용으로.",
                 "다정하고 호기심을 건드리듯 생생하게",
                 ["고양이행동", "고양이속마음", "집사", "냥이"], "궁금"),
    "health": ("건강 · 이상 신호 — 구토 · 설사 · 헤어볼 · 재채기 · 눈곱 · 많이 마시는 물 · 화장실 변화 · 숨소리 · 중성화 · 예방접종 · 나이 든 고양이",
               FORMAT + "병 진단 · 치료법 · 약 · 용량 단정 금지. '집에서 지켜봐도 되는 경우'와 '바로 병원 가야 하는 경우'를 구분해 알려 주기. "
               "마지막에 걱정되면 동물병원에서 확인하라는 뉘앙스.",
               "차분하고 믿음직하게 또렷하게",
               ["고양이건강", "고양이병원", "집사", "냥이"], "필수"),
    "food": ("사료 · 간식 · 급여 — 사료 성분 읽는 법 · 습식과 건식 · 물 먹이는 법 · 간식 주는 법 · 급여 횟수 · 비만 · 먹다 남기는 이유",
             FORMAT + "특정 브랜드 · 제품 추천 금지, 정확한 급여량 · 칼로리 숫자 단정 금지. 원리와 체크 포인트 위주.",
             "친절하게 하나하나 짚어 주듯 또렷하게",
             ["고양이사료", "고양이간식", "집사", "냥이"], "필수"),
    "care": ("초보 집사 · 돌봄 — 입양 전 준비물 · 첫 일주일 · 화장실 모래 · 합사 · 이사 · 발톱 · 양치 · 빗질 · 병원 데려가기 · 캣타워",
             FORMAT + "처음 키우는 사람도 바로 따라 할 수 있게 쉬운 말로. 실수하기 쉬운 포인트 위주로.",
             "든든한 선배처럼 따뜻하고 또렷하게",
             ["초보집사", "고양이키우기", "집사", "냥이"], "필수"),
    "breed": ("품종 · 성격 — 코숏 · 러시안블루 · 브리티시숏헤어 · 페르시안 · 샴 · 아비시니안 · 스코티시폴드 등 품종별 특징 · 털 색깔과 성격 · 치즈냥 · 고등어냥 · 턱시도냥",
              FORMAT + "품종 단정 · 편견 금지('이 품종은 무조건 성격이 ~'), 개체마다 다르다는 점도 살짝. 유전 질환 얘기는 겁주지 말고 차분하게.",
              "흥미로운 이야기를 들려주듯 생생하게",
              ["고양이품종", "고양이성격", "집사", "냥이"], "궁금"),
    "danger": ("위험한 것 · 생활 안전 — 먹으면 위험한 음식(양파 · 초콜릿 · 포도 등) · 위험한 식물(백합 등) · 집 안 위험 물건 · 창문 · 줄 · 여름 · 겨울 안전",
               FORMAT + "집사가 오늘 바로 확인할 수 있게. 확실히 위험하다고 알려진 것만 말하고, 안전하다는 단정은 신중하게. "
               "증상이 보이면 바로 동물병원이라는 점 강조.",
               "중요한 걸 알려 주듯 또렷하고 힘 있게",
               ["고양이위험음식", "고양이안전", "집사", "냥이"], "필수"),
    # 재미 — 가볍게 보다가 구독하게
    "trivia": ("고양이 잡학 · 역사 — 쏠쏠하고 신기한 고양이 이야기: 고양이 수염의 역할 · 고양이 눈이 어두운 곳에서 빛나는 이유 · "
               "고대 이집트와 고양이 · 고양이가 사람에게 야옹 하는 이유 · 고양이가 떨어져도 착지하는 이유 · 세계의 유명한 고양이",
               FORMAT + "'이건 친구한테 말해 주고 싶다' 싶은 재미있는 사실 위주. 역사 · 연도 · 숫자가 확실하지 않으면 빼고 이야기 흐름으로.",
               "재미있는 비밀을 알려 주듯 리듬감 있게",
               ["고양이잡학", "고양이상식", "신기한동물", "냥이"], "재미"),
    "jipsa": ("집사의 세계 — 집사라면 공감하는 이야기: 새벽에 깨우는 냥이 · 박스만 사면 박스에 들어가는 이유 · 키보드 위에 눕는 이유 · "
              "집사를 시종으로 보는 냥이 · 집사가 되는 순간 · 고양이와 함께 사는 일상",
              FORMAT + "'아, 이거 우리 집 얘기다!' 싶은 공감과 웃음 위주. 고양이를 깎아내리거나 집사를 비하하지 말고 따뜻하게.",
              "웃음기 섞인 친근한 말투로 리듬감 있게",
              ["집사", "집사일상", "고양이일상", "냥이"], "재미"),
}
LABELS = {"behavior": "행동·속마음", "health": "건강·이상신호", "food": "사료·간식", "care": "초보집사·돌봄",
          "breed": "품종·성격", "danger": "위험한 것·안전", "trivia": "고양이 잡학", "jipsa": "집사의 세계"}
SLOTS = {
    "morning": ("아침 7시. 출근 · 등교길에 폰으로 보는 집사들 · 고양이 키울까 고민하는 사람들",
                {"behavior": 2, "health": 2, "food": 3, "care": 3, "breed": 1, "danger": 3, "trivia": 1, "jipsa": 1}),
    "noon": ("점심 12시. 점심시간에 잠깐 쉬며 가볍게 보는 사람들",
             {"behavior": 3, "health": 1, "food": 1, "care": 1, "breed": 2, "danger": 1, "trivia": 3, "jipsa": 3}),
    "evening": ("저녁 6시. 퇴근길에 우리 냥이 생각하며 보는 집사들",
                {"behavior": 3, "health": 3, "food": 2, "care": 2, "breed": 2, "danger": 2, "trivia": 1, "jipsa": 2}),
    "night": ("밤 9시. 집에서 냥이와 함께 쉬며 여유 있게 보는 집사들",
              {"behavior": 3, "health": 2, "food": 1, "care": 1, "breed": 2, "danger": 1, "trivia": 3, "jipsa": 3}),
}
BASE_TAGS = ["고양이", "고양이상식", "집사", "냥이", "고양이행동", "고냥이", "Shorts"]
SUBSCRIBE = "https://www.youtube.com/@gonyangcat?sub_confirmation=1"
# 마무리 문장: 매번 구독 유도는 피하고 댓글 질문 위주로 섞음 — 직전 영상과 같은 종류는 안 씀
CTAS = {
    "comment": ("마지막 문장은 시청자가 자기 고양이 이야기를 댓글로 쓰고 싶어지는 짧은 질문. 주제에 딱 맞게, 답하기 쉽게 "
                "(예: '여러분 집 냥이는 이럴 때 어떻게 하나요?', '우리 냥이도 이러는지 댓글로 알려 주세요'). '댓글로!'는 붙여도 되고 안 붙여도 됨.", 4),
    "debate": ("마지막 문장은 의견이 갈릴 만한 양자택일 질문 (예: '습식 vs 건식, 우리 집 냥이의 선택은?').", 2),
    "subscribe": ("마지막 문장은 짧고 자연스러운 구독 권유. 부담스럽지 않게 한 마디 "
                  "(예: '냥이에 대한 모든 것, 고냥이가 알려 드릴게요.').", 2),
    "save": ("마지막 문장은 '나중에 우리 냥이한테 필요할 때 보시게 저장해 두세요' 같은 저장 유도.", 1),
    "none": ("마지막 문장은 따로 행동을 권하지 말고, 여운이 남는 한 줄 정리로 끝내기.", 1),
}
# 유튜브 예약 공개 시각 (KST) — 하루 4편 07:00 / 12:00 / 18:00 / 21:00
PUBLISH_TIMES = {"morning": (7, 0), "noon": (12, 0), "evening": (18, 0), "night": (21, 0)}
HORIZON = timedelta(hours=26)    # 이 시간 안에 공개될 회차만 미리 만듦
LEAD = timedelta(minutes=25)     # 1편 제작·업로드 여유
SECONDS = 29                     # 쇼츠는 끝까지 보는 비율이 노출에 중요 — 35초 안팎 (11/22 시험: 35 로 두면 문장 8개·43초 → 29 로 낮춤)
DISCLAIMER = ("※ 이 영상은 일반적인 고양이 정보이며 수의사의 진단 · 치료를 대신하지 않습니다. "
              "고양이마다 상태가 다르니 몸이 이상해 보이거나 걱정될 때는 꼭 동물병원에서 확인하세요.")


def pick_category(slot: str, history: list[dict]) -> str:
    """시간대 비중대로 랜덤, 단 직전 영상과 같은 카테고리는 피하고 직전 두 편이 같은 묶음(필수/궁금/재미)이면 다른 묶음으로."""
    weights = dict(SLOTS[slot][1])
    last = [h.get("category") for h in history[-2:] if h.get("category") in CATEGORIES]
    if last:
        weights.pop(last[-1], None)
    if len(last) == 2 and CATEGORIES[last[0]][4] == CATEGORIES[last[1]][4]:
        weights = {k: v for k, v in weights.items() if CATEGORIES[k][4] != CATEGORIES[last[1]][4]} or weights
    return random.choices(list(weights), weights=list(weights.values()))[0]


def current_slot(now: datetime) -> str:
    if 4 <= now.hour < 10:
        return "morning"
    if 10 <= now.hour < 15:
        return "noon"
    return "evening" if 15 <= now.hour < 19 else "night"


def load_history() -> list[dict]:
    return json.loads(HISTORY.read_text(encoding="utf-8")) if HISTORY.exists() else []


def pending_slots(now: datetime, history: list[dict]) -> list[tuple[str, datetime]]:
    """앞으로 HORIZON 안에 공개될 회차 중 아직 예약 업로드 안 된 것 (공개 시각 순)."""
    done = {h["publish_at"] for h in history if h.get("publish_at") and h.get("video_id")}
    todo = []
    for day in range(3):
        d = (now + timedelta(days=day)).date()
        for slot, (hh, mm) in PUBLISH_TIMES.items():
            at = datetime(d.year, d.month, d.day, hh, mm, tzinfo=KST)
            if at - now <= HORIZON and at.isoformat() not in done:
                todo.append((slot, at))
    todo.sort(key=lambda x: x[1])
    return [(slot, at) for i, (slot, at) in enumerate(todo) if at - now > LEAD * (i + 1)]


def run_once(slot: str, topic: str | None, upload: bool, privacy: str, category: str | None = None,
             publish_at: datetime | None = None) -> dict:
    from ideas import next_idea
    from script_writer import pick_topic, research, shape_idea, write_script
    from shorts_maker import make_shorts

    history = load_history()
    idea = None
    if not topic:
        report("idea", "상담 창구 접수함 확인할게요! 대표님 아이디어 들어온 거 있나…", "discord", stage="idea",
               slot=slot, publish_at=publish_at.isoformat() if publish_at else None,
               category=None, label=None, topic=None, title=None, voice=None, progress=None)
        idea = next_idea()
        report("idea", f"대표님 아이디어 접수! \"{idea['text'][:40]}\"" if idea else "새 접수는 없어요. 기획실로 넘길게요",
               "discord", kind="report" if idea else "work", idea=idea["text"][:80] if idea else None)
        if idea:
            shaped = shape_idea(PROFILE, idea["text"], {k: v[0] for k, v in CATEGORIES.items()})
            topic, category = shaped["topic"], category or shaped["category"]
            print(f"💡 디스코드 아이디어 사용: {idea['text'][:60]}")
    category = category or pick_category(slot, history)
    cat_desc, guide, tone, cat_tags, _ = CATEGORIES[category]
    report("plan", f"이번 건은 '{LABELS[category]}'로 갑니다!", "pd", stage="plan", category=category,
           label=LABELS[category])
    if not topic:
        report("plan", "기획 회의 시작! 지난 영상이랑 안 겹치게 고를게요", "gemini")
        topic = pick_topic(PROFILE, f"{SLOTS[slot][0]}\n이번 카테고리: {cat_desc}\n"
                           "새 시청자 유입이 목표: 집사들이 유튜브에서 실제로 많이 검색하는 궁금증 "
                           "(고양이 새벽 우다다 · 꾹꾹이 · 골골송 · 구토 · 사료 고르기 · 합사 · 중성화 · 위험한 음식 등)과 바로 연결되는 주제로",
                           [h["topic"] for h in history])
    print(f"▶ [{slot}/{category}] 주제: {topic}")
    report("plan", f"주제 확정: {topic}", "gemini", topic=topic)
    report("script", "카피 쓰기 시작합니다 ✍️", "gemini", stage="script")
    # 구글 검색 확인은 유료 Gemini 키에서만 됨 — 사용자 11/20 결정: 무료 유지(B) → 꺼 둠, 숫자 없이 원리 위주
    facts = research(f"{topic} ({LABELS[category]})") if os.environ.get("RESEARCH") == "1" else ""
    if facts:
        print("  확인된 사실:\n" + "\n".join("    " + x for x in facts.splitlines() if x.strip()))
    last_cta = history[-1].get("cta") if history else None
    pool = {k: v for k, v in CTAS.items() if k != last_cta}
    cta_key = random.choices(list(pool), weights=[w for _, w in pool.values()])[0]
    cta = pool[cta_key][0]
    s = write_script(f"{topic}\n(채널 콘셉트: {PROFILE})\n(카테고리 지침: {guide})\n(마무리: {cta})"
                     + (f"\n(확인된 사실 — 숫자는 여기 있는 것만, [불확실]은 숫자 빼고:\n{facts})" if facts else
                        "\n(검색 확인을 못 함 — 약 용량·나이·체중·기간·횟수 같은 구체적 숫자와 병 진단 · 치료법 단정은 "
                        "쓰지 말고, 행동의 이유 · 원리 · 집사가 할 수 있는 일 · 병원에 가야 하는 신호 위주로. "
                        "숫자가 필요하면 '수의사와 꼭 확인하세요'로)"),
                     seconds=SECONDS)
    title, sentences = s["title"], s["sentences"]
    report("review", f"검수 끝! 제목 '{title}', 문장 {len(sentences)}개로 확정", "reviewer", title=title)
    print(f"  제목: {title}\n" + "\n".join(f"  - {x}" for x in sentences) + "\n  장면: " + " / ".join(s.get("scenes") or []))

    now = datetime.now(KST)
    safe = re.sub(r'[\\/:*?"<>|\s]+', "_", title).strip("_")[:40]
    out = BASE / "output" / f"{now:%Y%m%d_%H%M}_{slot}_{safe}.mp4"
    out.parent.mkdir(exist_ok=True)
    # 장면 검색어 = "영어 | 다른 영어 표현 | 한국어" (stock_video 가 세 가지로 후보를 모아 고름)
    alts = s.get("scenes_alt") or []
    scenes = [" | ".join([q, *[a for a in (alts[i] if i < len(alts) and isinstance(alts[i], list) else [])
                               if isinstance(a, str) and a.strip()]])
              for i, q in enumerate(s.get("scenes") or [])]
    make_shorts("\n".join(sentences), out, title=title, scenes=scenes or None, tone=tone,
                label=f"고냥이 · {LABELS[category]}", title_point=s.get("title_point") or "")

    record = {"date": now.isoformat(timespec="minutes"), "slot": slot, "category": category, "topic": topic,
              "title": title, "file": out.name, "video_id": None, "cta": cta_key}
    if idea:
        record["idea"] = idea["text"][:200]
    if publish_at:
        record["publish_at"] = publish_at.isoformat()
    rec = finish(record, s, out, upload, privacy, publish_at, history, cat_tags)
    if idea and rec["video_id"]:  # 시험 제작(업로드 안 함)에선 ✅ 안 달아서 실제 회차에서 다시 쓰게
        from ideas import mark_used
        when = f"{publish_at:%m/%d %H:%M} 공개 예약" if publish_at else "바로 공개"
        mark_used(idea, f"이 아이디어로 만들었어요 → '{title}' ({when}) https://youtube.com/shorts/{rec['video_id']}")
    return rec


def finish(record: dict, s: dict, out, upload: bool, privacy: str, publish_at, history: list[dict],
           cat_tags: list[str]) -> dict:
    """업로드(선택) + 알림 + history 기록."""
    if upload:
        from alert import send
        from youtube_uploader import upload_video
        tags = [t.replace(" ", "").lstrip("#") for t in s.get("tags", [])][:8]
        # 설명란 해시태그 중 앞 3개가 제목 위에 보임 → 가장 많이 검색되는 것부터
        hashtags = list(dict.fromkeys(["고양이", cat_tags[0], "집사", *cat_tags[1:], "고양이상식", *tags[:3], "Shorts"]))[:12]
        title = f"{s['title']} #{cat_tags[0]} #고양이"
        desc = (f"{s.get('description', '')}\n\n"
                f"🔔 구독하고 매일 고양이 지식 받기 👉 {SUBSCRIBE}\n\n"
                + "\n".join(s["sentences"])
                + "\n\n🐱 고양이에 대한 모든 것 — 매일 아침 7시 · 점심 12시 · 저녁 6시 · 밤 9시, 고양이 지식을 짧게\n"
                "행동 · 건강 · 사료 · 돌봄 · 품종 · 안전 · 잡학까지\n\n"
                + DISCLAIMER + "\n\n" + " ".join("#" + t for t in hashtags))
        all_tags, n = [], 0
        for t in dict.fromkeys(BASE_TAGS + cat_tags + tags + [LABELS[record["category"]].replace("·", " ")]):
            if n + len(t) + 1 > 450:  # 유튜브 태그 합계 500자 제한
                break
            all_tags.append(t)
            n += len(t) + 1
        record["video_id"] = upload_video(out, title, CHANNEL, description=desc, tags=all_tags, privacy=privacy,
                                          publish_at=publish_at)
        when = f"{publish_at:%m/%d %H:%M} 공개 예약" if publish_at else "바로 공개"
        send(f"✅ {when} · [{LABELS.get(record['category'], '')}] {s['title']}\nhttps://youtube.com/shorts/{record['video_id']}")
    import stock_video  # 위에서 import하면 --plan(패키지 설치 전)이 requests 없어서 죽음
    record["clips"] = stock_video.take_picked()  # 다음 영상들이 같은 배경 클립을 안 쓰게
    history.append(record)
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=1), encoding="utf-8")
    return record


def report_error(msg: str):
    """지금 일하던 부서 직원이 문제 보고."""
    from office import current_dept
    report(current_dept(), "앗, 문제가 생겼어요: " + (msg.strip().splitlines() or ["?"])[0][:120], "", kind="error")


def run_with_retry(**kw) -> dict | None:
    """실패 시 새 주제로 1번 더 시도 (Gemini 과부하·영상 검색 실패 등 일시적 오류 대비)."""
    for attempt in (1, 2):
        try:
            rec = run_once(**kw)
            print(f"✅ 완료: {rec}")
            return rec
        except SystemExit as e:
            if "토큰" in str(e) or "채널" in str(e):  # 로그인 문제는 재시도해도 소용없음
                raise
            print(f"⚠ {e}")
            report_error(str(e))
        except Exception as e:
            traceback.print_exc()
            report_error(f"{type(e).__name__}: {e}")
        print("⚠ 실패 → 재시도" if attempt == 1 else "❌ 2회 모두 실패")
        report("plan", "새 주제로 다시 해볼게요!" if attempt == 1 else "두 번 다 실패했어요… 다음 근무 때 다시 채울게요",
               "pd", stage="plan", kind="error" if attempt == 2 else "work")
    return None


def schedule():
    """예약 대기열 채우기. 하나가 실패해도 다음 회차는 계속 만들고, 실패가 있으면 마지막에 실패 처리."""
    todo = pending_slots(datetime.now(KST), load_history())
    if not todo:
        print("예약할 회차 없음 (이미 다 채워짐)")
        return
    print("만들 회차: " + ", ".join(f"{at:%m/%d %H:%M}({slot})" for slot, at in todo))
    failed = []
    for slot, at in todo:
        if at - datetime.now(KST) <= LEAD / 2:
            print(f"⏭ {at:%m/%d %H:%M} 공개 시각이 너무 가까워 건너뜀")
            failed.append(at)
            continue
        print(f"\n===== {at:%m/%d %H:%M} 공개 예약분 ({slot}) =====")
        report("ops", f"{at:%m/%d %H:%M} 공개분 작업 착수합니다!", "pd", stage="ops")
        if not run_with_retry(slot=slot, topic=None, upload=True, privacy="private", publish_at=at):
            failed.append(at)
        os.environ.pop("VOICE", None)  # 목소리 고정은 첫 편에만
    if failed:
        raise SystemExit("❌ 실패한 회차: " + ", ".join(f"{at:%m/%d %H:%M}" for at in failed))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--schedule", action="store_true", help="예약 대기열 채우기")
    p.add_argument("--plan", action="store_true", help="만들 회차 수만 출력")
    p.add_argument("--slot", choices=list(SLOTS))
    p.add_argument("--topic")
    p.add_argument("--category", choices=list(CATEGORIES))
    p.add_argument("--privacy", default="public", choices=["private", "unlisted", "public"])
    p.add_argument("--no-upload", action="store_true")
    a = p.parse_args()
    if a.plan:
        todo = pending_slots(datetime.now(KST), load_history())
        print(len(todo), " ".join(f"{at:%m/%d_%H:%M}" for _, at in todo))
        return
    if a.schedule:
        return schedule()
    slot = a.slot or current_slot(datetime.now(KST))
    if not run_with_retry(slot=slot, topic=a.topic, upload=not a.no_upload, privacy=a.privacy, category=a.category):
        raise SystemExit("❌ 2회 모두 실패")


if __name__ == "__main__":
    main()
