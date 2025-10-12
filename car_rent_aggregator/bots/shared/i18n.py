from __future__ import annotations
import functools
from pathlib import Path
from typing import Any, Optional
from fluent.runtime import FluentLocalization, FluentResourceLoader

# --- Поиск папки с локалями ---
def _candidate_roots() -> list[Path]:
    here = Path(__file__).resolve()
    return [
        here.parent.parent / "locales",                            # bots/locales
        here.parent.parent / "client_bot" / "locales",             # bots/client_bot/locales
        here.parent.parent.parent / "bots" / "locales",            # car_rent_aggregator/bots/locales
        here.parent.parent.parent / "bots" / "client_bot" / "locales",
        Path.cwd() / "bots" / "locales",                           # запуск из корня
        Path.cwd() / "bots" / "client_bot" / "locales",
    ]

def _find_locales_root() -> Path:
    for root in _candidate_roots():
        if (root / "ru" / "bot.ftl").exists() and (root / "uz" / "bot.ftl").exists() and (root / "en" / "bot.ftl").exists():
            return root
    return Path(__file__).resolve().parent.parent / "locales"

LOCALES_ROOT = _find_locales_root()
DEFAULT_LANG = "ru"
SUPPORTED = {"uz", "ru", "en"}

@functools.lru_cache(maxsize=16)
def _get_l10n(lang: str) -> FluentLocalization:
    lang = (lang or DEFAULT_LANG).lower()
    if lang not in SUPPORTED:
        lang = DEFAULT_LANG
    loader = FluentResourceLoader(str(LOCALES_ROOT / "{locale}"))
    return FluentLocalization([lang, DEFAULT_LANG], ["bot.ftl"], resource_loader=loader)

def t(lang: str, key: str, **params: Any) -> str:
    """
    Поддерживаем ключи с точками/дефисами и конвертируем '\n' в реальные переводы строк.
    """
    l10n = _get_l10n(lang)
    candidates = [key, key.replace(".", "-"), key.replace("-", ".")]
    for k in dict.fromkeys(candidates):
        try:
            txt = l10n.format_value(k, params)  # type: ignore
            if txt:
                # ВАЖНО: превращаем текстовый '\n' в настоящую новую строку
                return txt.replace("\\n", "\n")
        except Exception:
            continue
    return key

async def resolve_user_lang(api_client, tg_user_id: int, fsm_data: Optional[dict] = None) -> str:
    if fsm_data and fsm_data.get("selected_lang"):
        return fsm_data["selected_lang"]
    try:
        resp = await api_client.get("/users/check/", params={"tg_user_id": tg_user_id})
        lang = (resp or {}).get("language")
        if lang and lang.lower() in SUPPORTED:
            return lang.lower()
    except Exception:
        pass
    return DEFAULT_LANG
