"""La ligne repond dans la langue de l'appelante (repli FR trace), sans lire les marqueurs."""
from sauti.knowledge.messages import texte_parle, choisir, message_systeme
from sauti.nlu.danger_detector import DangerDetector, ResultatDanger
from sauti.nlu.intent_classifier import IntentClassifier
from sauti.dialog.screening import QuestionDepistage
from sauti.pipeline import Pipeline
import importlib.util, pathlib

_spec = importlib.util.spec_from_file_location(
    "imp", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "importer_traductions.py")
imp = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(imp)


def test_marqueur_jamais_prononce():
    assert texte_parle("[A VALIDER] Allez au poste de sante.") == "Allez au poste de sante."


def test_choisir_wolof_sinon_francais():
    assert choisir({"fr": "bonjour", "wol": "salaam"}, "wol") == ("salaam", "wol")
    assert choisir({"fr": "bonjour", "wol": ""}, "wol") == ("bonjour", "fr")


def test_message_danger_par_langue():
    r = ResultatDanger(est_danger=True, message_fr="urgence", messages={"wol": "jamono"})
    assert r.message("wol") == ("jamono", "wol")
    assert r.message("ful") == ("urgence", "fr")


def test_detecteur_transmet_messages_par_langue():
    d = DangerDetector().analyser("amna dëret", langue="wol")
    assert d.est_danger and "fr" not in d.messages


def test_question_oui_non_wolof():
    q = QuestionDepistage("hemorragie", "urgent", prompt_fr="saignez-vous ?", prompt_wol="am nga dëret ?")
    assert q.prompt("wol") == ("am nga dëret ?", "wol")


def test_intention_mot_cle_wolof():
    intent, kb_id, score = IntentClassifier().predire("garab bi ndax baax na")
    assert kb_id == "medicament_grossesse" and score == 1.0


def test_pipeline_signale_la_langue_servie():
    res = Pipeline(mock=True).traiter(texte_mock="lan laa wara lekk", langue="wol")
    assert res["intent"] == "nutrition_grossesse"
    assert "[A VALIDER]" not in res["reponse"] and res["langue_servie"] in ("wol", "fr")


def test_pipeline_danger_ajoute_escalade_dans_la_meme_langue():
    res = Pipeline(mock=True).traiter(texte_mock="amna dëret", langue="wol")
    assert res["danger"] and "[A VALIDER]" not in res["reponse"]
    esc, esc_langue = message_systeme("escalade", res["langue_servie"])
    if esc_langue == res["langue_servie"]:
        assert texte_parle(esc) in res["reponse"]
    else:  # escalade non traduite : pas de francais colle au message wolof
        assert texte_parle(esc) not in res["reponse"]


def test_importeur_lit_les_blocs():
    b = imp.lire_blocs("id  : hemorragie ★\nfr  : x\nwol : jamono\n\nid : accueil\nwol :\n")
    assert b == {"hemorragie": "jamono", "accueil": ""}


def test_importeur_route_sans_ecrire():
    faits, inconnus = imp.importer({"q_fievre_forte": "a", "medicament": "b", "zzz": "c",
                                    "accueil": "d"}, ecrire=False)
    assert set(faits) == {"q_fievre_forte", "medicament_grossesse", "accueil"} and inconnus == ["zzz"]
