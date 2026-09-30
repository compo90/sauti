"""Couche 3 - DETECTION DE DANGER (composant critique, oriente RECALL).

Principe de securite : deux barrieres en OU logique.
  1) Barriere a base de REGLES : mots-cles critiques par langue -> si match, DANGER.
  2) Barriere ML (a entrainer en Phase 3) : classifieur binaire danger/non-danger.
Si l'une OU l'autre se declenche, on escalade. En cas de doute, on escalade.
Ne jamais regler ce composant pour la precision au detriment du recall.

CORRESPONDANCE TOLERANTE (mesure du 2026-09-30) :
L'ASR ne renvoie pas toujours l'orthographe exacte du mot-cle. Sur 11 vraies voix
feminines, la correspondance *exacte* attrapait 8/11 signes de danger (73 %) : elle
ratait « damay miir » -> « damar mbir » (l'ASR entend juste, l'orthographe differe).
La correspondance *floue* (distance d'edition, mots de sens uniquement) porte le
rappel a 9/11 (82 %) SANS faux positif sur un jeu de phrases benignes.

Deux cas restent hors de portee au niveau texte (« ñàkk bu bari » -> « niakoul bou
bar », « dama sibbiru » -> « pharmacie birou ») : ce sont de vraies erreurs ASR ou
le mot a disparu. On ne les rattrape PAS par une astuce de chaine (ce serait
inventer du signal et creer des faux positifs). Le rappel residuel se ferme par
l'ARCHITECTURE : repli sur menu guide si la confiance ASR est basse, et
CONFIRMATION explicite dans l'IVR sur le chemin danger. On ne joue jamais une vie
sur une seule transcription libre.
"""
from __future__ import annotations
import json
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

KB_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"

# Mots-outils wolof/fr : frequents, non discriminants. Ils peuvent varier un peu
# (sama/dama/dafa) sans porter le sens ; on ne relache la tolerance QUE sur eux.
_STOP = {
    "sama", "dafa", "dey", "bi", "bu", "na", "ci", "ak", "la", "li", "ma", "wi",
    "de", "du", "le", "les", "je", "mon", "ma", "a", "au", "the",
}


def _norm(t: str) -> str:
    """minuscule + suppression des diacritiques + ne garde que lettres/chiffres."""
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    out = [ch if unicodedata.category(ch)[0] in ("L", "N") else " " for ch in t]
    return " ".join("".join(out).split())


def _lev(a: str, b: str) -> int:
    """Distance de Levenshtein (petites chaines : implementation directe)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _tok_close(mot: str, cle: str, sens: bool) -> bool:
    """Le mot d'hypothese `mot` est-il assez proche du token de mot-cle `cle` ?

    `sens` = True pour un mot porteur de sens (tolerance serree, exact si <=3
    lettres pour eviter les faux positifs), False pour un mot-outil (plus souple).
    """
    if mot == cle:
        return True
    if sens:
        if len(cle) <= 3:            # mot de sens court -> exact obligatoire
            return False
        tol = 1 if len(cle) <= 6 else 2
        return _lev(mot, cle) <= tol
    tol = 1 if len(cle) <= 4 else 2
    if _lev(mot, cle) <= tol:
        return True
    return SequenceMatcher(None, mot, cle).ratio() >= 0.85


def _match_flou(hyp_norm: str, cle_norm: str) -> bool:
    """Cherche le mot-cle (normalise) dans l'hypothese, en tolerant de petites
    erreurs sur les mots de sens et un peu plus sur les mots-outils."""
    H = hyp_norm.split()
    K = cle_norm.split()
    if not K:
        return False
    if len(K) == 1:
        # mono-mot : exact (les mots de danger isoles sont souvent courts/ambigus)
        return K[0] in H
    n = len(K)
    for i in range(len(H) - n + 1):
        if all(_tok_close(H[i + j], K[j], sens=(K[j] not in _STOP)) for j in range(n)):
            return True
    return False


@dataclass
class ResultatDanger:
    est_danger: bool
    signes: list = field(default_factory=list)   # ids des signes detectes
    action: str = "info"                          # info | surveillance | urgent
    message_fr: str = ""


class DangerDetector:
    def __init__(self, kb_path: Path | None = None, ml_model=None, fuzzy: bool = True):
        data = json.loads((kb_path or (KB_DIR / "signes_danger.json")).read_text(encoding="utf-8"))
        self.signes = data["signes"]
        self.ml_model = ml_model    # optionnel (Phase 3)
        self.fuzzy = fuzzy          # correspondance tolerante (defaut) vs exacte

    def _match(self, hyp_norm: str, cle: str) -> bool:
        c = _norm(cle)
        if not c:
            return False
        if self.fuzzy:
            return _match_flou(hyp_norm, c)
        return c in hyp_norm        # correspondance exacte (retro-compatibilite)

    def _regles(self, texte: str, langue: str):
        n = _norm(texte)
        touches = []
        for s in self.signes:
            cles = s["mots_cles"].get(langue, []) + s["mots_cles"].get("fr", [])
            if any(self._match(n, c) for c in cles if c):
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
                ml_danger = False   # ne jamais planter le triage a cause du ML

        if not touches and not ml_danger:
            return ResultatDanger(est_danger=False, action="info")

        # Priorite a l'action la plus grave detectee
        urgent = [s for s in touches if s["action"] == "urgent"]
        choisi = (urgent or touches or [None])[0]
        if choisi is None:          # danger ML sans signe identifie -> escalade prudente
            return ResultatDanger(est_danger=True, signes=["ml_indetermine"], action="urgent",
                                  message_fr="[A VALIDER] Par prudence, rendez-vous au poste de sante.")
        return ResultatDanger(est_danger=True,
                              signes=[s["id"] for s in (urgent or touches)],
                              action=choisi["action"],
                              message_fr=choisi["message_fr"])
