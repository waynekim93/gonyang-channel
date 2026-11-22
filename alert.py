"""디스코드 '고냥이-알림' 채널로 알림 (봇 '고냥이', 표준 라이브러리).

  python alert.py "보낼 내용"
DISCORD_BOT_TOKEN · DISCORD_ALERT_CHANNEL 필요 (노트북은 settings.load_env 가 ~/.gonyang/channel 에서 읽음).
"""
import json
import os
import sys
import urllib.request

from settings import load_env

API = "https://discord.com/api/v10"


def call(path: str, body: dict | None = None, method: str = "GET"):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": "Bot " + os.environ["DISCORD_BOT_TOKEN"],
                                          "Content-Type": "application/json",
                                          "User-Agent": "gonyang-channel (https://gonyang.vercel.app, 1)"})
    return json.loads(urllib.request.urlopen(req, timeout=15).read() or b"null")


def send(text: str) -> bool:
    load_env()
    if not (os.environ.get("DISCORD_BOT_TOKEN") and os.environ.get("DISCORD_ALERT_CHANNEL")):
        print("(디스코드 설정 없음 — 알림 생략)\n" + text)
        return False
    try:
        call(f"/channels/{os.environ['DISCORD_ALERT_CHANNEL']}/messages", {"content": text[:1900]}, "POST")
        return True
    except Exception as e:
        print(f"  (알림 실패: {str(e)[:120]})")
    return False


if __name__ == "__main__":
    print("보냄" if send(" ".join(sys.argv[1:])) else "못 보냄")
