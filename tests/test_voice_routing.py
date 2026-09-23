"""Verrouille les decisions d'architecture de la couche voix (mode mock)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sauti.voice.asr import KirikuASR
from sauti.voice.tts import KirikuTTS


def test_asr_rejette_langue_inconnue():
    with pytest.raises(ValueError):
        KirikuASR(mock=True).transcrire(None, langue_forcee="eng", texte_mock="x")


def test_tts_wolof_synthetise():
    a = KirikuTTS(mock=True).synthetiser("test", "wol")
    assert a.source == "mock" and a.langue == "wol"


def test_tts_serere_utilise_audio_pre_enregistre():
    a = KirikuTTS(mock=True).synthetiser("test", "srr", audio_pre_enregistre="rep_srr.wav")
    assert a.source == "pre-enregistre" and a.contenu == "rep_srr.wav"


def test_tts_serere_sans_audio_reste_mock_en_mode_mock():
    # En mode reel, l'absence d'audio pour le serere leverait TTSIndisponible.
    a = KirikuTTS(mock=True).synthetiser("test", "srr")
    assert a.source == "mock"
