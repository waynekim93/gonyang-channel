"""디스코드 '고냥이-아이디어' 채널 → 영상 주제 대기열.

대표님이 채널에 글을 쓰면, 봇(고냥이)이 아직 ✅ 를 안 단 글 중 가장 오래된 것부터 하나씩 씀.
쓴 글엔 ✅ 반응 + 어떤 영상이 됐는지 답글.
"""
import os
import urllib.parse

from alert import call
from settings import load_env

DONE = "✅"


def _ready() -> bool:
    load_env()
    return bool(os.environ.get("DISCORD_BOT_TOKEN") and os.environ.get("DISCORD_IDEA_CHANNEL"))


def next_idea() -> dict | None:
    """처리 안 된 가장 오래된 아이디어 {id, text} — 없거나 디스코드 오류면 None (영상 제작은 계속)."""
    if not _ready():
        return None
    try:
        me = call("/users/@me")["id"]
        msgs = call(f"/channels/{os.environ['DISCORD_IDEA_CHANNEL']}/messages?limit=50")
    except Exception as e:
        print(f"  (아이디어 확인 실패: {str(e)[:100]})")
        return None
    for m in reversed(msgs):  # 오래된 것부터
        if m["author"]["id"] == me or m["author"].get("bot") or not m.get("content", "").strip():
            continue
        if any(r["emoji"]["name"] == DONE and r.get("me") for r in m.get("reactions", [])):
            continue
        return {"id": m["id"], "text": m["content"].strip()}
    return None


def mark_used(idea: dict, note: str):
    """✅ 달고 답글 (실패해도 무시)."""
    ch = os.environ.get("DISCORD_IDEA_CHANNEL")
    try:
        call(f"/channels/{ch}/messages/{idea['id']}/reactions/{urllib.parse.quote(DONE)}/@me", None, "PUT")
        call(f"/channels/{ch}/messages", {"content": note[:1900], "message_reference": {"message_id": idea["id"]}}, "POST")
    except Exception as e:
        print(f"  (아이디어 표시 실패: {str(e)[:100]})")
