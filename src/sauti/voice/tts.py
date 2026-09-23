"""Couche 2b - TTS (Kiriku). Texte -> audio, routage PAR LANGUE.

Realite des modeles (aout 2026) :
  - wolof  : AIHubSN/Kiriku-Wolof-TTS  (VITS)
  - pulaar : AIHubSN/Kiriku-Pulaar-TTS (VITS)
  - serere : AUCUN modele TTS -> repli sur audio humain pre-enregistre.

Consequence d'architecture : pour le serere, la reponse doit exister sous forme
d'un fichier audio pre-enregistre (champ `audio` de la base de connaissances).
S'il n'existe pas, on remonte une erreur explicite plutot que de produire du son
dans une langue erronee.

Tous les modeles sont GATED (accepter les conditions + HF_TOKEN).
En mode 'mock', renvoie une chaine texte : permet de tester la logique de routage.
"""
from __future__ import annotations
from dataclasses import dataclass

from config.settings import settings, LANGUES


class TTSIndisponible(RuntimeError):
    """Levee quand aucune voix (modele ni audio pre-enregistre) n'est disponible."""


@dataclass
class Audio:
    """Resultat TTS : soit des octets synthetises, soit un chemin audio pre-enregistre."""
    langue: str
    source: str            # "tts" | "pre-enregistre" | "mock"
    contenu: object        # bytes, chemin (str) ou texte (mock)


class KirikuTTS:
    def __init__(self, mock: bool = False):
        self.mock = mock
        self._modeles: dict[str, object] = {}

    def _lazy_load(self, model_id: str):
        if model_id in self._modeles:
            return self._modeles[model_id]
        # VITS (arxiv 2106.06103). Chargement reel a brancher en Phase 2 selon le
        # format publie ; laisse volontairement en TODO pour ne pas coder a l'aveugle.
        raise NotImplementedError(
            f"Chargement du modele TTS {model_id!r} a brancher (Phase 2, format VITS a confirmer)."
        )

    def synthetiser(self, texte: str, langue: str, audio_pre_enregistre: str | None = None) -> Audio:
        if langue not in LANGUES and langue != "fr":  # fr = langue de repli/test
            raise ValueError(f"Langue non supportee : {langue!r}")
        a_un_tts = LANGUES.get(langue, {"tts": True})["tts"]  # fr traite comme dispo (repli/test)

        if self.mock:
            src = "pre-enregistre" if (not a_un_tts and audio_pre_enregistre) else "mock"
            contenu = audio_pre_enregistre if src == "pre-enregistre" else f"[TTS:{langue}] {texte}"
            return Audio(langue=langue, source=src, contenu=contenu)

        # Langue sans TTS (serere) -> exiger un audio pre-enregistre
        if not a_un_tts:
            if audio_pre_enregistre:
                return Audio(langue=langue, source="pre-enregistre", contenu=audio_pre_enregistre)
            raise TTSIndisponible(
                f"Pas de TTS pour {langue!r} et aucun audio pre-enregistre fourni."
            )

        model_id = settings.tts_par_langue[langue]
        model = self._lazy_load(model_id)  # noqa: F841 (branchement Phase 2)
        raise NotImplementedError("Generation VITS a brancher (Phase 2).")
