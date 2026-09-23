"""Couche 2b - TTS (Kiriku). Texte -> audio, routage PAR LANGUE.

Format reel des modeles (verifie sur la fiche HF) : ce sont des modeles
**Coqui-TTS (VITS)** publies sous forme de `model.pth` + `config.json` — et NON
des modeles `transformers`. On les charge donc via `TTS.utils.synthesizer`.

  - wolof  : AIHubSN/Kiriku-Wolof-TTS  (Coqui VITS, 22 050 Hz)
  - pulaar : AIHubSN/Kiriku-Pulaar-TTS (Coqui VITS)
  - serere : AUCUN modele -> repli sur audio humain pre-enregistre.

Dependances (Phase 2, hors CI) : `pip install coqui-tts huggingface_hub`.
Modeles GATED : accepter les conditions + HF_TOKEN.
En mode 'mock', renvoie une chaine texte (aucune dependance).
"""
from __future__ import annotations
import tempfile
from dataclasses import dataclass
from pathlib import Path

from config.settings import settings, LANGUES


class TTSIndisponible(RuntimeError):
    """Levee quand aucune voix (modele ni audio pre-enregistre) n'est disponible."""


@dataclass
class Audio:
    """Resultat TTS : octets/chemin synthetise, ou chemin audio pre-enregistre."""
    langue: str
    source: str            # "tts" | "pre-enregistre" | "mock"
    contenu: object        # chemin .wav (str), texte (mock), ou octets


class KirikuTTS:
    def __init__(self, mock: bool = False, sortie_dir: str | None = None):
        self.mock = mock
        self.sortie_dir = Path(sortie_dir or tempfile.gettempdir()) / "sauti_tts"
        self._synth: dict[str, object] = {}   # cache par langue

    def _lazy_load(self, langue: str):
        """Telecharge le checkpoint Coqui et instancie le Synthesizer (une fois)."""
        if langue in self._synth:
            return self._synth[langue]
        model_id = settings.tts_par_langue.get(langue)
        if not model_id:
            raise TTSIndisponible(f"Aucun modele TTS configure pour {langue!r}.")

        from huggingface_hub import snapshot_download  # imports tardifs (Phase 2)
        from TTS.utils.synthesizer import Synthesizer
        import torch

        local = self.sortie_dir / f"model_{langue}"
        snapshot_download(repo_id=model_id, local_dir=str(local),
                          token=settings.hf_token or None)
        synth = Synthesizer(
            tts_checkpoint=str(local / "model.pth"),
            tts_config_path=str(local / "config.json"),
            use_cuda=torch.cuda.is_available(),
        )
        self._synth[langue] = synth
        return synth

    def synthetiser(self, texte: str, langue: str, audio_pre_enregistre: str | None = None) -> Audio:
        if langue not in LANGUES and langue != "fr":
            raise ValueError(f"Langue non supportee : {langue!r}")
        a_un_tts = LANGUES.get(langue, {"tts": True})["tts"]

        if self.mock:
            src = "pre-enregistre" if (not a_un_tts and audio_pre_enregistre) else "mock"
            contenu = audio_pre_enregistre if src == "pre-enregistre" else f"[TTS:{langue}] {texte}"
            return Audio(langue=langue, source=src, contenu=contenu)

        # Langue sans TTS (serere) -> exiger un audio pre-enregistre
        if not a_un_tts:
            if audio_pre_enregistre:
                return Audio(langue=langue, source="pre-enregistre", contenu=audio_pre_enregistre)
            raise TTSIndisponible(
                f"Pas de TTS pour {langue!r} et aucun audio pre-enregistre fourni.")

        # Synthese Coqui VITS
        synth = self._lazy_load(langue)
        self.sortie_dir.mkdir(parents=True, exist_ok=True)
        import uuid
        out = self.sortie_dir / f"{langue}_{uuid.uuid4().hex[:8]}.wav"
        wav = synth.tts(texte)
        synth.save_wav(wav, str(out))
        return Audio(langue=langue, source="tts", contenu=str(out))
