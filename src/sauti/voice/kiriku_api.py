"""Client de l'API d'inference Kiriku (fournie par AI Hub Senegal pour le challenge).

API compatible OpenAI (RunPod RTX 4090) : evite de charger whisper-large-v3 et
les VITS en local. Contrat (cf. /docs de l'API) :
  - POST /v1/audio/transcriptions  model=m-kiriku-asr, language=wolof|pulaar|serer, <= 60 s
  - POST /v1/audio/speech          model=kiriku-tts, voice=wolof|pulaar, <= 512 car., WAV 22,05 kHz
  - 30 req/min par cle -> 429 + Retry-After ; 503 si serveur sature.

La cle (sk-kiriku-...) se met dans .env (KIRIKU_API_KEY) : ne jamais la commiter.
`requests` est importe tardivement : la CI legere n'en a pas besoin.
"""
from __future__ import annotations
import io
import re
import time
import wave
from pathlib import Path

from config.settings import settings

# Nos codes ISO 639-3 -> noms attendus par l'API
_LANGUE_API = {"wol": "wolof", "ful": "pulaar", "srr": "serer"}
_VOIX_API = {"wol": "wolof", "ful": "pulaar"}  # pas de voix serere

MAX_CARACTERES_TTS = 512


class KirikuAPIErreur(RuntimeError):
    pass


def decouper_texte(texte: str, limite: int = MAX_CARACTERES_TTS) -> list[str]:
    """Decoupe par phrase (puis par mot si une phrase depasse) sous `limite` caracteres."""
    texte = " ".join(texte.split())
    if len(texte) <= limite:
        return [texte] if texte else []
    morceaux, courant = [], ""
    for phrase in re.split(r"(?<=[.!?;])\s+", texte):
        mots = phrase.split(" ") if len(phrase) > limite else [phrase]
        for m in mots:
            candidat = f"{courant} {m}".strip()
            if len(candidat) <= limite:
                courant = candidat
            else:
                if courant:
                    morceaux.append(courant)
                courant = m[:limite]
    if courant:
        morceaux.append(courant)
    return morceaux


def concatener_wav(blocs: list[bytes]) -> bytes:
    """Concatene des WAV de meme format (sortie TTS homogene)."""
    if len(blocs) == 1:
        return blocs[0]
    sortie = io.BytesIO()
    with wave.open(sortie, "wb") as w:
        for i, b in enumerate(blocs):
            with wave.open(io.BytesIO(b), "rb") as r:
                if i == 0:
                    w.setparams(r.getparams())
                w.writeframes(r.readframes(r.getnframes()))
    return sortie.getvalue()


class KirikuAPI:
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 session=None, max_essais: int = 3, timeout: float = 90.0):
        self.api_key = api_key or settings.kiriku_api_key
        self.base_url = (base_url or settings.kiriku_api_base).rstrip("/")
        if not self.api_key:
            raise KirikuAPIErreur("KIRIKU_API_KEY absente (.env).")
        self._session = session
        self.max_essais = max_essais
        self.timeout = timeout

    @property
    def session(self):
        if self._session is None:
            import requests  # import tardif
            self._session = requests.Session()
            # User-Agent obligatoire : le proxy RunPod bloque les requetes sans.
            self._session.headers["User-Agent"] = "sauti/0.1"
        return self._session

    def _post(self, chemin: str, **kwargs):
        url = f"{self.base_url}{chemin}"
        entetes = {"Authorization": f"Bearer {self.api_key}"}
        for essai in range(1, self.max_essais + 1):
            r = self.session.post(url, headers=entetes, timeout=self.timeout, **kwargs)
            if r.status_code in (429, 503) and essai < self.max_essais:
                attente = float(r.headers.get("Retry-After", 2 * essai))
                time.sleep(min(attente, 30))
                continue
            if r.status_code != 200:
                raise KirikuAPIErreur(f"{chemin} -> HTTP {r.status_code} : {r.text[:300]}")
            return r
        raise KirikuAPIErreur(f"{chemin} : echec apres {self.max_essais} essais")

    def transcrire(self, audio, langue: str | None) -> str:
        """audio : chemin de fichier ou octets. langue : code ISO 639-3 (None/fr = auto)."""
        if isinstance(audio, (str, Path)):
            nom, contenu = Path(audio).name, Path(audio).read_bytes()
        else:
            nom, contenu = "audio.wav", bytes(audio)
        data = {"model": "m-kiriku-asr", "response_format": "json"}
        if langue in _LANGUE_API:
            data["language"] = _LANGUE_API[langue]
        r = self._post("/audio/transcriptions", data=data, files={"file": (nom, contenu)})
        return r.json().get("text", "").strip()

    def synthetiser(self, texte: str, langue: str, speed: float | None = None) -> bytes:
        """Renvoie un WAV (octets). Decoupe au-dela de 512 caracteres."""
        voix = _VOIX_API.get(langue)
        if not voix:
            raise KirikuAPIErreur(f"Pas de voix API pour {langue!r}.")
        blocs = []
        for morceau in decouper_texte(texte):
            corps = {"model": "kiriku-tts", "voice": voix, "input": morceau}
            if speed is not None:
                corps["speed"] = speed
            blocs.append(self._post("/audio/speech", json=corps).content)
        if not blocs:
            raise KirikuAPIErreur("Texte vide.")
        return concatener_wav(blocs)
