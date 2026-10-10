"""Orchestration de bout en bout (relie les couches 2->3->5/6->2).

Flux :  audio --ASR--> texte --[triage danger]--> soit ESCALADE, soit
        intention -> reponse KB --TTS--> audio.

Le triage danger passe AVANT tout le reste : la securite prime sur la pertinence.
Le TTS est route par langue ; le serere (sans TTS) exige un audio pre-enregistre.
Utilisable en mode 'mock' (sans modeles) pour tester la logique.
"""
from __future__ import annotations
import argparse, logging

from config.settings import settings
from sauti.voice.asr import KirikuASR
from sauti.voice.tts import KirikuTTS, TTSIndisponible
from sauti.nlu.danger_detector import DangerDetector
from sauti.nlu.intent_classifier import IntentClassifier
from sauti.knowledge.kb import KnowledgeBase
from sauti.escalation.escalation import escalader
from sauti.knowledge.messages import message_systeme, texte_parle

log = logging.getLogger("pipeline")


class Pipeline:
    def __init__(self, mock: bool = False):
        self.mock = mock
        self.asr = KirikuASR(mock=mock)
        self.tts = KirikuTTS(mock=mock)
        self.danger = DangerDetector()
        self.intent = IntentClassifier()
        self.kb = KnowledgeBase()

    def _dire(self, texte: str, langue: str, audio_pre_enregistre=None):
        texte = texte_parle(texte)   # jamais prononcer "[A VALIDER]"
        try:
            return self.tts.synthetiser(texte, langue, audio_pre_enregistre=audio_pre_enregistre)
        except TTSIndisponible as e:
            log.error("TTS indisponible: %s", e)
            return None

    def traiter(self, chemin_audio=None, langue=None, texte_mock=None) -> dict:
        langue = langue or settings.default_lang

        # 1) ASR
        tr = self.asr.transcrire(chemin_audio, langue_forcee=langue, texte_mock=texte_mock)
        texte = tr.texte

        # 2) TRIAGE DANGER (avant tout) — couche 3, oriente recall
        d = self.danger.analyser(texte, langue=langue)
        if d.est_danger:
            escalader(signes=d.signes, action=d.action, langue=langue, contexte=texte)
            msg, servie = d.message(langue)
            if d.action == "urgent":
                esc, esc_langue = message_systeme("escalade", servie)
                if esc_langue == servie:   # jamais deux langues dans un meme message
                    msg = f"{msg} {esc}"
            if servie != langue:
                log.warning("Message danger non traduit en %s : repli %s", langue, servie)
            audio = self._dire(msg, langue)  # TODO: audio danger pre-enregistre (srr)
            return {"texte_entrant": texte, "danger": True, "signes": d.signes,
                    "action": d.action, "reponse": texte_parle(msg),
                    "langue_servie": servie, "audio_reponse": audio}

        # 3) Intention -> reponse validee (couche 5)
        intent, kb_id, score = self.intent.predire(texte)
        entree = self.kb.entree(kb_id, langue=langue) if kb_id else None
        if entree and entree["texte"]:
            reponse, audio_pre, servie = entree["texte"], entree["audio"], entree["langue_servie"]
        else:
            (reponse, servie), audio_pre = message_systeme("pas_compris", langue), None
        if servie != langue:
            log.warning("Reponse non traduite en %s : repli %s", langue, servie)

        # 4) TTS (route par langue ; repli audio pour le serere)
        audio = self._dire(reponse, langue, audio_pre_enregistre=audio_pre)
        return {"texte_entrant": texte, "danger": False, "intent": intent,
                "score": score, "reponse": texte_parle(reponse),
                "langue_servie": servie, "audio_reponse": audio}


def _cli():
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description="Demo pipeline Sauti (mode mock)")
    p.add_argument("--demo", help="texte simule (ce que dirait l'utilisatrice)", default="")
    p.add_argument("--langue", default=settings.default_lang, choices=["wol", "ful", "srr", "fr"])
    a = p.parse_args()
    pipe = Pipeline(mock=True)
    res = pipe.traiter(texte_mock=a.demo, langue=a.langue)
    print("\n--- Resultat ---")
    for k, v in res.items():
        print(f"{k:14}: {v}")


if __name__ == "__main__":
    _cli()
