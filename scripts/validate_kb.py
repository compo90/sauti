"""Valide toutes les entrees de la base de connaissances contre le schema JSON."""
import json, sys
from pathlib import Path
from jsonschema import Draft7Validator

KB = Path(__file__).resolve().parents[1] / "data" / "knowledge_base"


def main() -> int:
    schema = json.loads((KB / "schema.json").read_text(encoding="utf-8"))
    validator = Draft7Validator(schema)
    faq = json.loads((KB / "faq_maternelle.json").read_text(encoding="utf-8"))

    erreurs = 0
    for e in faq:
        for err in validator.iter_errors(e):
            erreurs += 1
            print(f"[X] {e.get('id','?')}: {err.message}")

    # Rapport de completude des traductions
    total = len(faq)
    a_traduire = sum(1 for e in faq for lg in ("wol", "ful", "srr")
                     if e["reponses"].get(lg, {}).get("statut") == "a_traduire")
    non_valide = sum(1 for e in faq if e["validation"]["statut"] != "valide_clinique")

    print(f"\n{total} entrees FAQ valides contre le schema. {erreurs} erreur(s).")
    print(f"Traductions locales a produire : {a_traduire}")
    print(f"Entrees non encore validees cliniquement : {non_valide}/{total}")
    print("\nRappel : aucun contenu ne doit partir en production avant validation clinique.")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
