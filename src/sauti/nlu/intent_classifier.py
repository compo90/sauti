"""Couche 3 - Classification d'intention (non critique).

Baseline v0 : appariement lexical sur les intentions de la FAQ.
A remplacer en Phase 3 par un classifieur entraine (LightGBM sur embeddings, ou
un modele SLU) une fois le corpus annote disponible.
"""
from __future__ import annotations
import json, unicodedata
from pathlib import Path

KB_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


class IntentClassifier:
    def __init__(self, faq_path: Path | None = None):
        faq = json.loads((faq_path or (KB_DIR / "faq_maternelle.json")).read_text(encoding="utf-8"))
        # index simple mot-cle -> intent, derive des questions source FR
        self.index = []
        for e in faq:
            mots = set(_norm(e.get("question_source_fr", "")).split())
            self.index.append((e["intent"], mots, e["id"]))

    def predire(self, texte: str):
        """Renvoie (intent, kb_id, score) — baseline par recouvrement de mots."""
        toks = set(_norm(texte).split())
        best, score = None, 0.0
        for intent, mots, kb_id in self.index:
            if not mots:
                continue
            s = len(toks & mots) / len(mots)
            if s > score:
                best, score = (intent, kb_id), s
        if best is None:
            return None, None, 0.0
        return best[0], best[1], round(score, 3)
