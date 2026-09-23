"""Tests d'integrite de la base de connaissances."""
import json
from pathlib import Path
from jsonschema import Draft7Validator

KB = Path(__file__).resolve().parents[1] / "data" / "knowledge_base"


def test_faq_conforme_au_schema():
    schema = json.loads((KB / "schema.json").read_text(encoding="utf-8"))
    v = Draft7Validator(schema)
    faq = json.loads((KB / "faq_maternelle.json").read_text(encoding="utf-8"))
    for e in faq:
        assert not list(v.iter_errors(e)), f"{e['id']} non conforme"


def test_ids_uniques():
    faq = json.loads((KB / "faq_maternelle.json").read_text(encoding="utf-8"))
    ids = [e["id"] for e in faq]
    assert len(ids) == len(set(ids))
