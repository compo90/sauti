"""Messages vocaux du serveur vocal (accueil, incomprehension, escalade), par langue.

Repli sur le francais si la traduction manque. Le marqueur editorial
`[A VALIDER]` est une metadonnee : il ne doit jamais etre prononce.
"""
from __future__ import annotations
import json
import re
from functools import lru_cache
from pathlib import Path

KB_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"
_MARQUEUR = re.compile(r"\[\s*A\s+VALIDER\s*\]\s*", re.IGNORECASE)


def texte_parle(texte: str | None) -> str:
    """Retire les marqueurs editoriaux avant la synthese vocale."""
    return _MARQUEUR.sub("", texte or "").strip()


def choisir(par_langue: dict, langue: str) -> tuple[str, str]:
    """(texte, langue_servie) : la langue demandee si traduite, sinon le francais."""
    t = (par_langue or {}).get(langue) or ""
    if t.strip():
        return t, langue
    return (par_langue or {}).get("fr", ""), "fr"


@lru_cache(maxsize=1)
def _messages() -> dict:
    return json.loads((KB_DIR / "messages_systeme.json").read_text(encoding="utf-8"))["messages"]


def message_systeme(cle: str, langue: str) -> tuple[str, str]:
    return choisir(_messages()[cle], langue)
