"""공통 경로 / 비밀값 로더.
GitHub Actions: 환경변수(Secrets). 노트북: .env 또는 ~/.gonyang/channel 의 파일들 (저장소 밖)."""
import json
import os
from pathlib import Path

BASE = Path(__file__).resolve().parent
KEYS = Path.home() / ".gonyang" / "channel"
KEY_FILES = {"GEMINI_API_KEY": "gemini.txt", "PIXABAY_API_KEY": "pixabay.txt", "DISCORD_BOT_TOKEN": "discord_bot_token.txt"}


def load_env():
    env = BASE / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if v.strip():
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    for k, name in KEY_FILES.items():
        f = KEYS / name
        if not os.environ.get(k) and f.exists() and f.read_text(encoding="utf-8-sig").strip():
            os.environ[k] = f.read_text(encoding="utf-8-sig").strip()
    d = KEYS / "discord.json"
    if d.exists():
        ids = json.loads(d.read_text(encoding="utf-8"))
        os.environ.setdefault("DISCORD_ALERT_CHANNEL", ids.get("alert_channel", ""))
        os.environ.setdefault("DISCORD_IDEA_CHANNEL", ids.get("idea_channel", ""))
