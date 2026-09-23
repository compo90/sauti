"""Couche 2a - ASR (Kiriku). Enveloppe le modele MULTILINGUE M-Kiriku-ASR.

AIHubSN/M-Kiriku-ASR : fine-tune de whisper-large-v3 couvrant wolof, pulaar et
serere. Modele GATED : il faut accepter les conditions sur huggingface.co et
fournir un HF_TOKEN valide.

En mode 'mock' (defaut si transformers/torch absents), renvoie le texte fourni :
permet de tester tout le pipeline sans GPU ni modele telecharge.

NOTE (a confirmer via la carte du modele, gated) : le mecanisme exact de
selection de langue (token de langue force vs auto-detection) doit etre aligne
sur la documentation de M-Kiriku-ASR avant la Phase 3. Ici on expose `langue`
et on la transmet en `generate_kwargs` ; a defaut, le modele auto-detecte.
"""
from __future__ import annotations
from dataclasses import dataclass

from config.settings import settings, LANGUES

# whisper attend des codes ISO 639-1 ; correspondance depuis nos codes 639-3
_ISO3_TO_WHISPER = {"wol": "wo", "ful": "ff", "srr": "srr", "fr": "fr"}


@dataclass
class Transcription:
    texte: str
    langue: str          # code ISO 639-3
    confiance: float = 0.0


class KirikuASR:
    def __init__(self, model_id: str | None = None, mock: bool = False):
        self.model_id = model_id or settings.kiriku_asr_model
        self.mock = mock
        self._pipe = None

    def _lazy_load(self):
        if self._pipe is not None or self.mock:
            return
        from transformers import pipeline  # import tardif (Phase 2)
        self._pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model_id,
            token=settings.hf_token or None,
        )

    def transcrire(self, audio, langue_forcee: str | None = None,
                   texte_mock: str | None = None) -> Transcription:
        """audio : chemin .wav ou tableau numpy. En mock, passer texte_mock."""
        langue = langue_forcee or settings.default_lang
        if langue not in LANGUES and langue != "fr":  # fr = langue de repli/test
            raise ValueError(f"Langue non supportee : {langue!r} (attendu {list(LANGUES)} + fr)")

        if self.mock:
            return Transcription(texte=texte_mock or "", langue=langue)

        self._lazy_load()
        gen_kwargs = {}
        code = _ISO3_TO_WHISPER.get(langue)
        if code:
            # a confirmer avec la carte du modele ; sinon retirer pour auto-detection
            gen_kwargs["language"] = code
        out = self._pipe(audio, generate_kwargs=gen_kwargs or None)
        return Transcription(texte=out.get("text", "").strip(), langue=langue)
