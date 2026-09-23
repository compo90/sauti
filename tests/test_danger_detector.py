"""Le detecteur de danger doit privilegier le RECALL : ne rien laisser passer."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sauti.nlu.danger_detector import DangerDetector


def test_detecte_hemorragie_fr():
    d = DangerDetector().analyser("j'ai un saignement abondant", langue="fr")
    assert d.est_danger and d.action == "urgent"


def test_detecte_convulsions_fr():
    d = DangerDetector().analyser("ma soeur a fait une crise et tremble", langue="fr")
    assert d.est_danger


def test_question_benigne_non_danger():
    d = DangerDetector().analyser("que dois-je manger pendant la grossesse", langue="fr")
    assert not d.est_danger
