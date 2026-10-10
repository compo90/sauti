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
        self.index_wol = []   # mots-cles wolof du domaine : 1 seul suffit
        for e in faq:
            mots = set(_norm(e.get("question_source_fr", "")).split())
            self.index.append((e["intent"], mots, e["id"]))
            cles = {_norm(m) for m in e.get("mots_cles_wol", []) if m}
            if cles:
                self.index_wol.append((e["intent"], cles, e["id"]))

    def predire(self, texte: str):
        """Renvoie (intent, kb_id, score) — baseline par recouvrement de mots."""
        toks = set(_norm(texte).split())
        # Un mot-cle wolof du domaine (garab, lekk...) est un indice fort et precis.
        for intent, cles, kb_id in self.index_wol:
            if toks & cles:
                return intent, kb_id, 1.0
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
