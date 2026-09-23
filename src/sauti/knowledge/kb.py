"""Couche 5 - Chargement et acces a la base de connaissances validee."""
from __future__ import annotations
import json
from pathlib import Path

KB_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"


class KnowledgeBase:
    def __init__(self, kb_dir: Path | None = None):
        d = kb_dir or KB_DIR
        self.faq = json.loads((d / "faq_maternelle.json").read_text(encoding="utf-8"))
        self._by_id = {e["id"]: e for e in self.faq}

    def entree(self, kb_id: str, langue: str = "fr") -> dict | None:
        """Renvoie {'texte', 'audio', 'langue_servie'} avec repli FR si besoin."""
        e = self._by_id.get(kb_id)
        if not e:
            return None
        rl = e["reponses"].get(langue)
        texte = rl.get("texte", "") if rl else ""
        audio = rl.get("audio") if rl else None
        langue_servie = langue
        if not texte and langue != "fr":  # repli sur le francais si traduction absente
            texte = e["reponses"]["fr"]["texte"]
            audio = e["reponses"]["fr"].get("audio")
            langue_servie = "fr"
        return {"texte": texte or None, "audio": audio, "langue_servie": langue_servie}

    def reponse(self, kb_id: str, langue: str = "fr") -> str | None:
        e = self.entree(kb_id, langue)
        return e["texte"] if e else None
