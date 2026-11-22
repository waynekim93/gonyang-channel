# 고냥이 유튜브 로그인 (한 번만): 브라우저에서 waynekim93 → 채널 "고냥이" 선택 → token_gonyang.json 저장
# 비밀 파일은 저장소 밖 ~/.gonyang/channel 에만 둔다
import json
import sys
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

KEYS = Path.home() / ".gonyang" / "channel"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]

flow = InstalledAppFlow.from_client_secrets_file(str(KEYS / "client_secret.json"), SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline", open_browser=True)

yt = build("youtube", "v3", credentials=creds)
items = yt.channels().list(part="snippet", mine=True).execute().get("items", [])
title = items[0]["snippet"]["title"] if items else "(채널 없음)"
print("로그인한 채널:", title, "| 채널 ID:", items[0]["id"] if items else "-")
if "고냥이" not in title:
    print("⚠️ 고냥이 채널이 아니에요. 저장하지 않아요. 다시 실행해서 '고냥이'를 골라 주세요.")
    sys.exit(1)
if not creds.refresh_token:
    print("⚠️ 갱신 토큰이 없어요. 저장하지 않아요.")
    sys.exit(1)
(KEYS / "token_gonyang.json").write_text(creds.to_json(), encoding="utf-8")
(KEYS / "channel.json").write_text(json.dumps({"title": title, "id": items[0]["id"]}, ensure_ascii=False), encoding="utf-8")
print("저장 완료:", KEYS / "token_gonyang.json")
