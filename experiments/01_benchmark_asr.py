"""Phase 2 - Banc d'essai rigoureux de M-Kiriku-ASR sur NOTRE corpus terrain.

Mesure WER et CER, ventiles par langue et par condition (calme / bruit / code-
switching), et produit un rapport JSON. Ne jamais se fier au WER annonce du
modele : mesurer sur nos propres donnees.

Corpus attendu : data/corpus_test/transcriptions.csv
  colonnes : fichier, langue, condition, texte
  (langue in {wol, ful, srr} ; condition in {calme, bruit, code_switch})

Prerequis : transformers + torch + acces HF (modele gated) + HF_TOKEN.
Usage : python experiments/01_benchmark_asr.py
"""
from __future__ import annotations
import csv, json, unicodedata
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data" / "corpus_test"
RAPPORT = ROOT / "experiments" / "rapport_asr.json"


def _norm(t: str) -> str:
    return unicodedata.normalize("NFC", t.strip().lower())


def _levenshtein(a: list, b: list) -> int:
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev, d[0] = d[0], i
        for j, cb in enumerate(b, 1):
            prev, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, prev + (ca != cb))
    return d[-1]


def wer(ref: str, hyp: str) -> float:
    r, h = _norm(ref).split(), _norm(hyp).split()
    return _levenshtein(r, h) / max(1, len(r))


def cer(ref: str, hyp: str) -> float:
    r, h = list(_norm(ref)), list(_norm(hyp))
    return _levenshtein(r, h) / max(1, len(r))


def main() -> int:
    import sys
    sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT))
    from sauti.voice.asr import KirikuASR

    csv_path = CORPUS / "transcriptions.csv"
    if not csv_path.exists():
        print("Ajoutez data/corpus_test/transcriptions.csv (voir data/corpus_test/README.md).")
        return 1

    asr = KirikuASR(mock=False)
    lignes, par_groupe = [], defaultdict(lambda: {"wer": [], "cer": []})

    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            audio = CORPUS / row["fichier"]
            tr = asr.transcrire(str(audio), langue_forcee=row["langue"])
            w, c = wer(row["texte"], tr.texte), cer(row["texte"], tr.texte)
            cond = row.get("condition", "n/a")
            for cle in (("global", "global"), (row["langue"], "langue"), (cond, "condition")):
                par_groupe[cle[0]]["wer"].append(w)
                par_groupe[cle[0]]["cer"].append(c)
            lignes.append({"fichier": row["fichier"], "langue": row["langue"],
                           "condition": cond, "wer": round(w, 4), "cer": round(c, 4),
                           "hyp": tr.texte})
            print(f"{row['fichier']:18} {row['langue']} {cond:11} WER={w:6.2%} CER={c:6.2%}")

    resume = {g: {"n": len(v["wer"]), "wer_moyen": round(mean(v["wer"]), 4),
                  "cer_moyen": round(mean(v["cer"]), 4)}
              for g, v in par_groupe.items() if v["wer"]}
    RAPPORT.write_text(json.dumps({"resume": resume, "details": lignes},
                                  ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n--- Resume (WER/CER moyens) ---")
    for g, s in sorted(resume.items()):
        print(f"{g:14} n={s['n']:3}  WER={s['wer_moyen']:.2%}  CER={s['cer_moyen']:.2%}")
    print(f"\nRapport ecrit : {RAPPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
