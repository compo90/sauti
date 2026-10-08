"""Backend API Kiriku : contrat HTTP, decoupage 512 car., degradation (sans reseau)."""
import io
import wave

import pytest
from sauti.voice.asr import KirikuASR
from sauti.voice.kiriku_api import KirikuAPI, decouper_texte, concatener_wav
from sauti.voice.tts import KirikuTTS, TTSIndisponible


def _wav(n_frames=100):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(b"\x00\x00" * n_frames)
    return b.getvalue()


class _Rep:
    def __init__(self, status=200, json_=None, content=b"", headers=None):
        self.status_code, self._json, self.content = status, json_, content
        self.headers, self.text = headers or {}, ""

    def json(self):
        return self._json


class _Session:
    def __init__(self, reponses):
        self.reponses, self.appels = list(reponses), []

    def post(self, url, **kw):
        self.appels.append((url, kw))
        return self.reponses.pop(0)


def test_asr_api_envoie_langue_et_modele(tmp_path):
    f = tmp_path / "a.wav"; f.write_bytes(_wav())
    s = _Session([_Rep(json_={"text": " dama di xeeñ \n"})])
    api = KirikuAPI(api_key="k", base_url="http://x/v1", session=s)
    tr = KirikuASR(api=api, utiliser_api=True).transcrire(str(f), langue_forcee="wol")
    url, kw = s.appels[0]
    assert url == "http://x/v1/audio/transcriptions"
    assert kw["data"] == {"model": "m-kiriku-asr", "response_format": "json", "language": "wolof"}
    assert kw["headers"]["Authorization"] == "Bearer k"
    assert tr.texte == "dama di xeeñ"


def test_asr_api_reessaie_sur_429(monkeypatch, tmp_path):
    monkeypatch.setattr("sauti.voice.kiriku_api.time.sleep", lambda s: None)
    s = _Session([_Rep(429, headers={"Retry-After": "1"}), _Rep(json_={"text": "ok"})])
    api = KirikuAPI(api_key="k", base_url="http://x/v1", session=s)
    assert api.transcrire(b"RIFF", "ful") == "ok"
    assert len(s.appels) == 2


def test_decoupage_respecte_512_caracteres():
    texte = ("Phrase de test numero un. " * 60).strip()
    morceaux = decouper_texte(texte)
    assert len(morceaux) > 1 and all(len(m) <= 512 for m in morceaux)
    assert " ".join(morceaux) == texte


def test_concatenation_wav():
    w = concatener_wav([_wav(100), _wav(50)])
    with wave.open(io.BytesIO(w), "rb") as r:
        assert r.getnframes() == 150


def test_tts_api_pulaar_ecrit_un_wav(tmp_path):
    s = _Session([_Rep(content=_wav())])
    api = KirikuAPI(api_key="k", base_url="http://x/v1", session=s)
    a = KirikuTTS(sortie_dir=str(tmp_path), api=api, utiliser_api=True).synthetiser("jam", "ful")
    assert a.source == "tts" and s.appels[0][1]["json"]["voice"] == "pulaar"


def test_tts_api_en_panne_devient_tts_indisponible(tmp_path):
    s = _Session([_Rep(500)])
    api = KirikuAPI(api_key="k", base_url="http://x/v1", session=s, max_essais=1)
    with pytest.raises(TTSIndisponible):
        KirikuTTS(sortie_dir=str(tmp_path), api=api, utiliser_api=True).synthetiser("x", "wol")


def test_serere_ne_passe_jamais_par_le_tts_api(tmp_path):
    s = _Session([])
    api = KirikuAPI(api_key="k", base_url="http://x/v1", session=s)
    a = KirikuTTS(sortie_dir=str(tmp_path), api=api, utiliser_api=True).synthetiser(
        "x", "srr", audio_pre_enregistre="srr.wav")
    assert a.source == "pre-enregistre" and not s.appels
