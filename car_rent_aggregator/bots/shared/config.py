from pydantic import BaseModel
from dotenv import load_dotenv, find_dotenv
from pathlib import Path
import os

# Ищем .env вверх по дереву (работает, даже если запускаешь скрипт из другой папки)
env_path = find_dotenv(usecwd=True)
if not env_path:
    # fallback: рядом с репозиторием/управляющим скриптом
    here = Path(__file__).resolve()
    for up in [here.parent, here.parent.parent, here.parent.parent.parent]:
        cand = up / ".env"
        if cand.exists():
            env_path = str(cand)
            break
load_dotenv(env_path or None)

class Settings(BaseModel):
    api_base_url: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")
    api_key: str = os.getenv("BOTS_API_KEY", "")
    tz: str = os.getenv("TZ", "Asia/Tashkent")
    token_client: str = os.getenv("BOT_TOKEN_CLIENT", "")
    token_partner: str = os.getenv("BOT_TOKEN_PARTNER", "")
    debug_bots: bool = os.getenv("DEBUG_BOTS", "0") in ("1", "true", "True")
    media_root: str = os.getenv("BOTS_MEDIA_ROOT", "")

settings = Settings()

# Небольшой дебаг-лог (видно в консоли бота)
if settings.debug_bots:
    print("[BOT SETTINGS] API_BASE_URL=", settings.api_base_url)
    print("[BOT SETTINGS] API_KEY set? ", bool(settings.api_key))

