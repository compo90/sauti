#!/usr/bin/env python3
"""experiments/02_eval_securite.py — Evaluation SECURITE du pipeline sur voix reelles.

Le WER (01_benchmark_asr.py) dit si l'ASR transcrit bien. Ici on mesure ce qui
compte pour une ligne de sante, a partir de la SORTIE ASR (pas de la reference) :
  - RAPPEL danger      : enonces `type=danger` detectes par DangerDetector (vise 100 %)
  - FAUSSES ALERTES    : enonces `type=benin` escalades a tort (vise 0)
  - BONNE REPONSE      : enonces `kb_attendu` renseigne -> IntentClassifier tombe-t-il
                         sur la bonne fiche ? (les questions sans fiche sont comptees a part)
Intervalles de Wilson a 95 % (petits effectifs).

Le JSON ecrit ne contient que des agregats (aucun texte) + manifest_sha256 :
versionnable selon la politique de donnees (experiments/README.md).

Usage :
  python experiments/02_eval_securite.py                       # manifeste calme
  python experiments/02_eval_securite.py --manifest experiments/testset/manifest_telephone.csv
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, c - h), 4), round(min(1.0, c + h), 4)


def taux(k, n):
    return {"k": k, "n": n, "taux": round(k / n, 4) if n else None, "ic95": wilson(k, n)}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Evaluation securite (danger / fausses alertes / KB).")
    ap.add_argument("--manifest", type=Path, default=REPO / "experiments" / "testset" / "manifest.csv")
    ap.add_argument("--audio-dir", type=Path, default=REPO / "experiments" / "testset" / "audio")
    ap.add_argument("--details", action="store_true",
                    help="afficher ref/hyp par enonce (terminal seulement, jamais ecrit)")
    args = ap.parse_args()

    from sauti.voice.asr import KirikuASR
    from sauti.nlu.danger_detector import DangerDetector
    from sauti.nlu.intent_classifier import IntentClassifier

    asr, dd, ic = KirikuASR(), DangerDetector(), IntentClassifier()
    lignes = list(csv.DictReader(args.manifest.open(encoding="utf-8")))
    if not lignes or "type" not in lignes[0]:
        sys.exit("[ERREUR] Le manifeste doit avoir une colonne `type` (danger|benin).")

    rd = nd = fa = nb = kb_ok = kb_n = sans_fiche = 0
    for r in lignes:
        hyp = asr.transcrire(str(args.audio_dir / r["fichier"]), langue_forcee=r["langue"]).texte
        alerte = dd.analyser(hyp, langue=r["langue"]).est_danger
        if r["type"] == "danger":
            nd += 1; rd += alerte
        else:
            nb += 1; fa += alerte
            if r.get("kb_attendu"):
                kb_n += 1
                _, kb_id, _ = ic.predire(hyp)
                kb_ok += (kb_id == r["kb_attendu"])
            else:
                sans_fiche += 1
        if args.details:
            print(f"  [{r['type']:<6}] alerte={alerte!s:<5} ref={r['texte_ref']!r}\n{'':11}hyp={hyp!r}")

    res = {
        "meta": {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "backend": "api Kiriku" if asr.utiliser_api else "local (transformers)",
            "manifest": args.manifest.name,
            "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
            "n_locuteurs": len({r["locuteur"] for r in lignes}),
            "conditions": sorted({r["condition"] for r in lignes}),
        },
        "rappel_danger": taux(rd, nd),
        "fausses_alertes": taux(fa, nb),
        "bonne_fiche_kb": taux(kb_ok, kb_n),
        "questions_sans_fiche_kb": sans_fiche,
    }
    print(json.dumps({k: v for k, v in res.items() if k != "meta"}, ensure_ascii=False, indent=1))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out = REPO / "experiments" / "results" / f"securite_{stamp}.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"-> {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
