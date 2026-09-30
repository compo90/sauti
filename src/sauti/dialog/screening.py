"""Couche 4 - DIALOGUE : depistage danger par OUI/NON (filet de securite).

Pourquoi ce module existe (mesure du 2026-09-30) :
Le triage sur texte libre a un rappel de ~82 % : deux vrais signes de danger
etaient perdus parce que l'ASR s'est trompe de mot (« ñàkk bu bari » -> « niakoul
bou bar », « dama sibbiru » -> « pharmacie birou »). On ne rattrape PAS ca par une
astuce de chaine. On le rattrape par l'ARCHITECTURE : un **depistage explicite**
ou l'IVR pose des questions fermees, et ou la femme repond **oui / non**.

Reconnaitre « waaw » (oui) vs « déedéet » (non) est BIEN plus robuste que
transcrire une phrase entiere : meme quand l'ASR echoue sur une phrase, il capte un
oui/non court. Ce depistage rend donc le chemin danger quasi independant de la
qualite de transcription — c'est le filet qui ferme le trou du rappel.

Regle RECALL-FIRST : sur une question de danger, seule une reponse clairement
« non » ferme le signe. « oui » **ou** « incertain » -> on escalade (dans le doute,
on protege). Les libelles wolof des questions restent [A VALIDER] par un locuteur
natif ; le MECANISME, lui, est complet et teste.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
import json

from sauti.nlu.danger_detector import _norm, _lev, ResultatDanger

KB_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"

# Marqueurs oui / non (wolof + francais). Formes normalisees (sans diacritiques).
_OUI = ["waaw", "waw", "waayi", "waaw waay", "oui", "ouais", "voui", "yes", "yeah"]
_NON = ["deedeet", "deet", "dedeet", "dedet", "non", "nan", "no", "aca"]


def _proche(mot: str, cle: str) -> bool:
    """Egalite tolerante : exact si <=3 lettres (anti faux positif), sinon 1 faute."""
    if mot == cle:
        return True
    if len(cle) <= 3:
        return False
    return _lev(mot, cle) <= 1


def reconnaitre_oui_non(texte: str, langue: str = "wol") -> str:
    """Renvoie 'oui', 'non' ou 'incertain' a partir d'une reponse vocale transcrite."""
    n = _norm(texte)
    toks = n.split()
    oui = any(_proche(t, c) for t in toks for c in _OUI if " " not in c) \
        or any(c in n for c in _OUI if " " in c)
    non = any(_proche(t, c) for t in toks for c in _NON if " " not in c)
    if oui and not non:
        return "oui"
    if non and not oui:
        return "non"
    return "incertain"          # rien de clair, ou les deux -> incertain


@dataclass
class QuestionDepistage:
    signe_id: str
    action: str                 # urgent | surveillance
    prompt_fr: str
    prompt_wol: str = ""        # [A VALIDER] locuteur natif
    audio: str | None = None    # audio pre-enregistre (serere, ou confort)


class DepistageDanger:
    """Construit un depistage oui/non a partir des signes de danger de la base.

    Utilisation cote IVR :
        dep = DepistageDanger()
        for q in dep.questions():           # poser chaque question (voix)
            rep = reconnaitre_oui_non(asr_du_oui_non, langue)
            reponses[q.signe_id] = rep
        resultat = dep.evaluer(reponses)    # -> ResultatDanger (escalade si besoin)
    """

    def __init__(self, kb_path: Path | None = None, inclure_surveillance: bool = True):
        data = json.loads((kb_path or (KB_DIR / "signes_danger.json")).read_text(encoding="utf-8"))
        self._questions: list[QuestionDepistage] = []
        for s in data["signes"]:
            if s["action"] == "surveillance" and not inclure_surveillance:
                continue
            self._questions.append(QuestionDepistage(
                signe_id=s["id"],
                action=s["action"],
                prompt_fr=f"[A VALIDER] Avez-vous : {s['libelle_fr'].lower()} ? Dites oui ou non.",
                prompt_wol="",          # [A VALIDER] a fournir par un locuteur natif
            ))
        # les signes 'urgent' d'abord (on depiste le plus grave en premier)
        self._questions.sort(key=lambda q: 0 if q.action == "urgent" else 1)

    def questions(self) -> list[QuestionDepistage]:
        return list(self._questions)

    def evaluer(self, reponses: dict[str, str]) -> ResultatDanger:
        """reponses : {signe_id -> 'oui'|'non'|'incertain'}. RECALL-FIRST :
        tout ce qui n'est pas un 'non' clair sur un signe declenche l'escalade."""
        touches = []
        for q in self._questions:
            if q.signe_id not in reponses:
                continue                            # signe non pose -> non evalue
            if reponses[q.signe_id] != "non":       # 'oui' ou 'incertain' -> danger
                touches.append(q)
        if not touches:
            return ResultatDanger(est_danger=False, action="info")
        urgents = [q for q in touches if q.action == "urgent"]
        action = "urgent" if urgents else "surveillance"
        return ResultatDanger(
            est_danger=True,
            signes=[q.signe_id for q in (urgents or touches)],
            action=action,
            message_fr=("[A VALIDER] D'apres vos reponses, rendez-vous sans tarder "
                        "au poste de sante le plus proche. Faites-vous accompagner."),
        )


def depistage_necessaire(resultat_texte_libre: ResultatDanger,
                         confiance_asr: float | None = None,
                         seuil_confiance: float = 0.55,
                         politique_filet: bool = True) -> bool:
    """Faut-il lancer le depistage oui/non apres le tour en texte libre ?

    - Si un danger est deja confirme en texte libre -> pas besoin (on escalade deja).
    - Si la confiance ASR est basse -> OUI (on ne se fie pas a la transcription).
    - politique_filet=True : sur une ligne de sante, on depiste par securite meme
      quand le texte libre n'a rien trouve (car l'ASR a pu perdre le signe).
    """
    if resultat_texte_libre.est_danger:
        return False
    if confiance_asr is not None and confiance_asr < seuil_confiance:
        return True
    return politique_filet
