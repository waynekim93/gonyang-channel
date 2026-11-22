"""빈 회차 감시 (health.yml 이 하루 3번 실행) — 표준 라이브러리만.

1) 유튜브 로그인(토큰 갱신)이 살아 있는지 확인 → 풀렸으면 디스코드 알림 (사람 손 필요)
2) 앞으로 WINDOW 안에 공개될 회차 중 예약 안 된 칸이 있으면 → 제작 워크플로를 다시 돌리고 디스코드 알림
   (다시 돌리는 건 health.yml 이 이 스크립트의 출력 'REFILL' 을 보고 함)

  python healthcheck.py
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from alert import send
from autopilot import KST, PUBLISH_TIMES, load_history

WINDOW = timedelta(hours=14)


def youtube_login_ok() -> str:
    """'' = 정상, 아니면 문제 설명."""
    raw = os.environ.get("YT_TOKEN")
    if not raw:
        return ""  # 로컬 등 토큰 없는 환경에선 건너뜀
    try:
        t = json.loads(raw.lstrip("﻿"))
        body = urllib.parse.urlencode({"client_id": t["client_id"], "client_secret": t["client_secret"],
                                       "refresh_token": t["refresh_token"], "grant_type": "refresh_token"}).encode()
        with urllib.request.urlopen(t.get("token_uri", "https://oauth2.googleapis.com/token"), body, timeout=15) as r:
            json.loads(r.read())["access_token"]
        return ""
    except Exception as e:
        return f"{type(e).__name__}: {str(e)[:120]}"


def empty_slots(now: datetime) -> list[datetime]:
    done = {h["publish_at"] for h in load_history() if h.get("publish_at") and h.get("video_id")}
    out = []
    for day in range(2):
        d = (now + timedelta(days=day)).date()
        for hh, mm in PUBLISH_TIMES.values():
            at = datetime(d.year, d.month, d.day, hh, mm, tzinfo=KST)
            if now < at <= now + WINDOW and at.isoformat() not in done:
                out.append(at)
    return sorted(out)


def main():
    now = datetime.now(KST)
    problems = []
    login = youtube_login_ok()
    if login:
        problems.append("login")
        send("🚨 [고냥이] 유튜브 로그인이 풀렸어요 — 이대로면 업로드가 멈춰요. "
             f"Claude에게 '고냥이 불러와, 유튜브 로그인 다시' 하고 알려주세요. ({login})")
    empty = empty_slots(now)
    if empty:
        when = ", ".join(f"{at:%m/%d %H:%M}" for at in empty)
        print(f"빈 회차: {when}")
        if not login:
            print("REFILL")  # health.yml 이 제작 워크플로를 다시 돌림
            send(f"⚠️ [고냥이] 예약 안 된 회차 발견: {when} → 지금 다시 만들고 있어요. "
                 "또 실패하면 다음 알림이 와요.")
    else:
        print(f"이상 없음: 앞으로 {WINDOW.seconds // 3600}시간 안 회차 모두 예약됨")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
