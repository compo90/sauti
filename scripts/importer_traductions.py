"""Verse les traductions de data/knowledge_base/a_traduire_wol.txt dans la base.

Routage des ids :
  accueil | pas_compris | escalade     -> messages_systeme.json
  <signe>                              -> signes_danger.json  (message.wol)
  q_<signe>                            -> signes_danger.json  (question.wol)
  <fiche FAQ> (medicament -> medicament_grossesse) -> faq_maternelle.json (reponses.wol)

Idempotent : un bloc dont la ligne "wol :" est vide ne touche rien. Le statut
clinique ne change pas (tout reste [A VALIDER] tant qu'un soignant n'a pas valide).

Usage : python scripts/importer_traductions.py [--verifier]
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

KB = Path(__file__).resolve().parents[1] / "data" / "knowledge_base"
SOURCE = KB / "a_traduire_wol.txt"
ALIAS = {"medicament": "medicament_grossesse"}


def lire_blocs(texte: str) -> dict[str, str]:
    blocs, courant = {}, None
    for ligne in texte.splitlines():
        if ligne.lstrip().startswith("#") or ":" not in ligne:
            continue
        cle, _, val = ligne.partition(":")
        cle, val = cle.strip().lower(), val.strip()
        if cle == "id":
            courant = val.replace("★", "").strip()
        elif cle == "wol" and courant:
            blocs[courant] = val
    return blocs


def importer(blocs: dict[str, str], ecrire: bool = True) -> tuple[list[str], list[str]]:
    msgs_p, signes_p, faq_p = (KB / "messages_systeme.json", KB / "signes_danger.json",
                               KB / "faq_maternelle.json")
    msgs = json.loads(msgs_p.read_text(encoding="utf-8"))
    signes = json.loads(signes_p.read_text(encoding="utf-8"))
    faq = json.loads(faq_p.read_text(encoding="utf-8"))
    par_signe = {s["id"]: s for s in signes["signes"]}
    par_fiche = {e["id"]: e for e in faq}

    faits, inconnus = [], []
    for id_, wol in blocs.items():
        if not wol:
            continue
        id_ = ALIAS.get(id_, id_)
        if id_ in msgs["messages"]:
            msgs["messages"][id_]["wol"] = wol
        elif id_ in par_signe:
            par_signe[id_].setdefault("message", {})["wol"] = wol
        elif id_.startswith("q_") and id_[2:] in par_signe:
            par_signe[id_[2:]].setdefault("question", {})["wol"] = wol
        elif id_ in par_fiche:
            par_fiche[id_]["reponses"]["wol"].update({"texte": wol, "statut": "traduit"})
        else:
            inconnus.append(id_)
            continue
        faits.append(id_)

    if ecrire:
        for p, o in ((msgs_p, msgs), (signes_p, signes), (faq_p, faq)):
            p.write_text(json.dumps(o, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return faits, inconnus


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    blocs = lire_blocs(SOURCE.read_text(encoding="utf-8"))
    vides = [k for k, v in blocs.items() if not v]
    faits, inconnus = importer(blocs, ecrire="--verifier" not in sys.argv)
    print(f"Traduits importes : {len(faits)}/{len(blocs)}")
    if vides:
        print("Encore vides     :", ", ".join(vides))
    if inconnus:
        print("[!] ids inconnus :", ", ".join(inconnus))
    return 1 if inconnus else 0


if __name__ == "__main__":
    sys.exit(main())
