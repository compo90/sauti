"""Depistage oui/non : filet de securite quand l'ASR rate le mot de danger.
Oriente RECALL : seul un 'non' clair ferme un signe."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sauti.dialog.screening import (
    reconnaitre_oui_non, DepistageDanger, depistage_necessaire,
)
from sauti.nlu.danger_detector import ResultatDanger


def test_oui_wolof():
    assert reconnaitre_oui_non("waaw") == "oui"
    assert reconnaitre_oui_non("waaw waay") == "oui"


def test_non_wolof():
    assert reconnaitre_oui_non("déedéet") == "non"
    assert reconnaitre_oui_non("non") == "non"


def test_reponse_confuse_est_incertain():
    assert reconnaitre_oui_non("euh je sais pas") == "incertain"


def test_depistage_escalade_sur_oui():
    dep = DepistageDanger()
    res = dep.evaluer({"hemorragie": "oui"})
    assert res.est_danger and res.action == "urgent"


def test_depistage_incertain_escalade_recall_first():
    # une reponse non comprise ne doit PAS fermer un signe de danger
    dep = DepistageDanger()
    res = dep.evaluer({"hemorragie": "incertain"})
    assert res.est_danger


def test_depistage_tout_non_pas_de_danger():
    dep = DepistageDanger()
    reponses = {q.signe_id: "non" for q in dep.questions()}
    assert not dep.evaluer(reponses).est_danger


def test_filet_se_declenche_si_texte_libre_rien():
    # ASR n'a rien trouve -> on depiste quand meme (le signe a pu etre perdu)
    rien = ResultatDanger(est_danger=False, action="info")
    assert depistage_necessaire(rien) is True


def test_pas_de_depistage_si_danger_deja_confirme():
    danger = ResultatDanger(est_danger=True, action="urgent")
    assert depistage_necessaire(danger) is False
