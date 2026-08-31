"""Optional AI helpers for the panel, via Groq's OpenAI-compatible API.

Text only — no vision on the free model tier, so captions are written from a short
brief you type, not from the image. Key resolution: GROQ_API_KEY env, else
panel/state.json ("groq_api_key"). Everything degrades gracefully when unset.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

from panel.account import STATE_PATH

_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

BRAND = (
    "Sen Bitronix'in sosyal medya editörüsün. Bitronix; kritik altyapılar, "
    "endüstriyel otomasyon ve özel elektronik kartlar için uçtan uca güvenli "
    "donanım + yazılım sistemleri geliştiren bir Türk teknoloji şirketi "
    "(gömülü sistemler, PCB tasarım, IoT edge, Edge AI, RTOS). "
    "Ton: kurumsal, net, teknik ama anlaşılır. Abartı ve emoji yağmuru yok; "
    "en fazla 1-2 anlamlı emoji. Türkçe yaz. "
    "İletişim gerektiğinde site bitronixdev.com, e-posta info@bitronixdev.com — "
    "başka adres/e-posta uydurma."
)


def _key() -> str | None:
    if os.environ.get("GROQ_API_KEY"):
        return os.environ["GROQ_API_KEY"]
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8")).get("groq_api_key")
    except Exception:  # noqa: BLE001
        return None


def configured() -> bool:
    return bool(_key())


def set_key(key: str) -> dict[str, Any]:
    key = key.strip()
    if not key.startswith("gsk_"):
        return {"ok": False, "error": "Groq anahtarı 'gsk_' ile başlamalı"}
    try:
        st = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        st = {}
    st["groq_api_key"] = key
    STATE_PATH.write_text(json.dumps(st, indent=2), encoding="utf-8")
    return {"ok": True}


def _chat(system: str, user: str, *, max_tokens: int = 500, temperature: float = 0.7) -> dict[str, Any]:
    key = _key()
    if not key:
        return {"ok": False, "error": "AI anahtarı ayarlı değil (Ayarlar sekmesi)"}
    try:
        r = httpx.post(
            _URL,
            headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
            json={
                "model": _MODEL,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=45,
        ).json()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    if "error" in r:
        return {"ok": False, "error": r["error"].get("message", "AI hatası")}
    try:
        return {"ok": True, "text": r["choices"][0]["message"]["content"].strip()}
    except Exception:  # noqa: BLE001
        return {"ok": False, "error": "beklenmeyen yanıt"}


def caption(brief: str, tone: str = "kurumsal") -> dict[str, Any]:
    return _chat(
        BRAND,
        f"Bir Instagram feed gönderisi için caption yaz.\nKonu: {brief}\nİstenen ton: {tone}\n"
        "1 kısa paragraf + boş satır + 6-10 alakalı hashtag. Sadece caption'ı ver, başka açıklama yok.",
        max_tokens=600,
    )


def polish(text: str) -> dict[str, Any]:
    return _chat(
        BRAND,
        "Aşağıdaki taslak Instagram caption'ını marka tonuna göre düzelt: akıcılaştır, "
        "gereksiz kelimeleri at, sonuna 6-10 alakalı hashtag ekle (yoksa). Sadece "
        f"düzeltilmiş caption'ı ver.\n\n---\n{text}",
        max_tokens=600, temperature=0.5,
    )


def hashtags(text: str) -> dict[str, Any]:
    return _chat(
        BRAND,
        "Bu caption için 10-15 alakalı Instagram hashtag'i üret, boşlukla ayrılmış tek "
        f"satır, sadece hashtag'ler:\n\n{text}",
        max_tokens=200, temperature=0.4,
    )


def reply(comment_text: str, post_caption: str = "") -> dict[str, Any]:
    return _chat(
        BRAND,
        "Bir takipçi yorumuna Bitronix adına kısa, kibar, marka tonunda bir yanıt taslağı yaz "
        "(1-2 cümle, gerekiyorsa 1 emoji). Yalnızca yanıt metnini ver.\n"
        f"Gönderi: {post_caption[:200]}\nYorum: {comment_text}",
        max_tokens=200, temperature=0.6,
    )
