"""Couche 3 - DETECTION DE DANGER (composant critique, oriente RECALL).

Principe de securite : deux barrieres en OU logique.
  1) Barriere a base de REGLES : mots-cles critiques par langue -> si match, DANGER.
  2) Barriere ML (a entrainer en Phase 3) : classifieur binaire danger/non-danger.
Si l'une OU l'autre se declenche, on escalade. En cas de doute, on escalade.
Ne jamais regler ce composant pour la precision au detriment du recall.
"""
from __future__ import annotations
import json
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

KB_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


@dataclass
class ResultatDanger:
    est_danger: bool
    signes: list = field(default_factory=list)   # ids des signes detectes
    action: str = "info"                          # info | surveillance | urgent
    message_fr: str = ""


class DangerDetector:
    def __init__(self, kb_path: Path | None = None, ml_model=None):
        data = json.loads((kb_path or (KB_DIR / "signes_danger.json")).read_text(encoding="utf-8"))
        self.signes = data["signes"]
        self.ml_model = ml_model  # optionnel (Phase 3)

    def _regles(self, texte: str, langue: str):
        n = _norm(texte)
        touches = []
        for s in self.signes:
            cles = s["mots_cles"].get(langue, []) + s["mots_cles"].get("fr", [])
            if any(_norm(c) in n for c in cles if c):
                touches.append(s)
        return touches

    def analyser(self, texte: str, langue: str = "fr") -> ResultatDanger:
        touches = self._regles(texte, langue)

        # Barriere ML (si un modele est fourni) — declenche aussi l'escalade.
        ml_danger = False
        if self.ml_model is not None:
            try:
                ml_danger = bool(self.ml_model.predict([texte])[0])
            except Exception:
                ml_danger = False  # ne jamais planter le triage a cause du ML

        if not touches and not ml_danger:
            return ResultatDanger(est_danger=False, action="info")

        # Priorite a l'action la plus grave detectee
        urgent = [s for s in touches if s["action"] == "urgent"]
        choisi = (urgent or touches or [None])[0]
        if choisi is None:  # danger ML sans signe identifie -> escalade prudente
            return ResultatDanger(est_danger=True, signes=["ml_indetermine"], action="urgent",
                                  message_fr="[A VALIDER] Par prudence, rendez-vous au poste de sante.")
        return ResultatDanger(est_danger=True,
                              signes=[s["id"] for s in (urgent or touches)],
                              action=choisi["action"],
                              message_fr=choisi["message_fr"])
