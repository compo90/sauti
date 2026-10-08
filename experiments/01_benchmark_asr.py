#!/usr/bin/env python3
"""experiments/01_benchmark_asr.py — Banc d'essai ASR de Sauti.

On ne mesure pas le WER "du modele" : on mesure ce que M-Kiriku-ASR vaut sur
NOTRE terrain — questions de sante maternelle, voix feminines, telephone, bruit,
code-switching wolof/francais. On ne peut pas ameliorer ce qu'on n'a pas mesure.

Ce que ce script produit (bonne pratique metier) :
  1. WER et CER par LANGUE et par CONDITION, sur *notre* corpus (micro-moyenne
     au niveau du corpus, pas une moyenne de WER par phrase — plus honnete).
  2. Un intervalle de confiance a 95 % (bootstrap) : sur un petit jeu de test,
     annoncer "16 %" sans IC n'a aucune valeur defendable.
  3. Une variante "assouplie" (diacritiques repliees) pour voir combien d'erreurs
     ne sont que des accents — utile pour decider de la normalisation en prod.
  4. Le RAPPEL sur mots-cles de DANGER : metrique de SECURITE. Rater "dëret"
     (sang) coute plus cher qu'une erreur de mot quelconque. Cette metrique
     prime sur le WER global pour une ligne de sante.

Modes :
  --check-only : valide le manifeste (fichiers presents, refs non vides) SANS
                 modele ni jiwer. A lancer AVANT la collecte pour cadrer le format.
  --mock       : auto-test du banc (l'ASR renvoie la reference -> WER ~0),
                 pour verifier la tuyauterie de scoring sans GPU.
  (defaut)     : vrai run avec M-Kiriku-ASR (gated : HF_TOKEN + acces accepte).

Usage :
  python experiments/01_benchmark_asr.py --check-only
  python experiments/01_benchmark_asr.py --mock
  python experiments/01_benchmark_asr.py --manifest experiments/testset/manifest.csv \
         --audio-dir experiments/testset/audio

Format du manifeste (CSV, en-tetes exactes) :
  fichier,langue,condition,locuteur,sexe,texte_ref
    - fichier   : nom du .wav (resolu dans --audio-dir)
    - langue    : wol | ful | srr   (ISO 639-3, comme le reste du code)
    - condition : calme | bruit | telephone | debit_rapide | code_switch
    - locuteur  : identifiant anonyme (spk01...) — pour la diversite des voix
    - sexe      : f | m           — le public cible est feminin : suivre le WER voix f
    - texte_ref : transcription humaine EXACTE de ce qui est dit
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
KB_DANGER = REPO / "data" / "knowledge_base" / "signes_danger.json"
CONDITIONS = {"calme", "bruit", "telephone", "debit_rapide", "code_switch"}
LANGUES_OK = {"wol", "ful", "srr"}


# --------------------------------------------------------------------------- #
# Normalisation du texte : etape CRITIQUE. Un WER calcule sur des textes non
# normalises (casse, ponctuation, espaces) ne veut rien dire.
# --------------------------------------------------------------------------- #
def normaliser(texte: str, replier_diacritiques: bool = False) -> str:
    """minuscule + suppression ponctuation + espaces normalises.

    On conserve lettres (accentuees comprises : ë, ñ, ŋ...) et chiffres, on
    remplace tout le reste par une espace. `replier_diacritiques` fait tomber
    les accents (variante assouplie) pour mesurer leur poids dans le WER.
    """
    texte = unicodedata.normalize("NFC", texte).lower().strip()
    out = []
    for ch in texte:
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "N"):        # Lettre ou Nombre
            out.append(ch)
        elif ch.isspace():
            out.append(" ")
        else:
            out.append(" ")             # ponctuation -> espace
    texte = "".join(out)
    if replier_diacritiques:
        texte = "".join(
            c for c in unicodedata.normalize("NFD", texte)
            if unicodedata.category(c) != "Mn"
        )
    return " ".join(texte.split())


# --------------------------------------------------------------------------- #
# Comptage d'erreurs par enonce (S, D, I, N) via jiwer, pour agreger au niveau
# corpus ET pour le bootstrap.
# --------------------------------------------------------------------------- #
def compter_mots(ref: str, hyp: str):
    import jiwer
    out = jiwer.process_words([ref], [hyp])
    S, D, I, H = out.substitutions, out.deletions, out.insertions, out.hits
    N = S + D + H                       # longueur de la reference en mots
    return S, D, I, N


def compter_caracteres(ref: str, hyp: str):
    import jiwer
    try:
        out = jiwer.process_characters([ref], [hyp])
        S, D, I, H = out.substitutions, out.deletions, out.insertions, out.hits
        return S, D, I, S + D + H
    except Exception:
        # jiwer ancien : repli sur cer() (donne un taux, pas les comptes)
        import jiwer as _j
        n = max(len(ref.replace(" ", "")), 1)
        return round(_j.cer(ref, hyp) * n), 0, 0, n


def wer_depuis_comptes(items) -> float:
    sdi = sum(s + d + i for s, d, i, n in items)
    N = sum(n for s, d, i, n in items)
    return sdi / N if N else 0.0


def bootstrap_ic(items, n_iter: int = 2000, seed: int = 13):
    """IC 95 % du WER par re-echantillonnage des enonces (avec remise)."""
    if len(items) < 2:
        return (None, None)
    rng = random.Random(seed)
    k = len(items)
    vals = []
    for _ in range(n_iter):
        ech = [items[rng.randrange(k)] for _ in range(k)]
        vals.append(wer_depuis_comptes(ech))
    vals.sort()
    lo = vals[int(0.025 * len(vals))]
    hi = vals[int(0.975 * len(vals))]
    return (lo, hi)


# --------------------------------------------------------------------------- #
# Metrique securite : rappel sur les mots-cles de danger.
# --------------------------------------------------------------------------- #
def charger_mots_danger() -> dict[str, list[str]]:
    """langue -> liste de mots-cles danger (normalises, diacritiques repliees)."""
    par_langue: dict[str, set[str]] = defaultdict(set)
    if not KB_DANGER.exists():
        return {}
    data = json.loads(KB_DANGER.read_text(encoding="utf-8"))
    for signe in data.get("signes", []):
        for langue, mots in signe.get("mots_cles", {}).items():
            for m in mots:
                par_langue[langue].add(normaliser(m, replier_diacritiques=True))
    return {k: sorted(v) for k, v in par_langue.items()}


def rappel_danger(paires, mots_danger):
    """Sur les enonces dont la REF contient un mot-cle danger, combien
    l'HYP le contient aussi ? (present = attendu, detecte = retrouve)."""
    res = {}
    for langue in sorted({p["langue"] for p in paires}):
        cles = mots_danger.get(langue, []) + mots_danger.get("fr", [])
        if not cles:
            continue
        present = detecte = 0
        for p in paires:
            if p["langue"] != langue:
                continue
            ref = normaliser(p["ref"], replier_diacritiques=True)
            hyp = normaliser(p["hyp"], replier_diacritiques=True)
            touche = [c for c in cles if c and c in ref]
            if touche:
                present += 1
                if any(c in hyp for c in touche):
                    detecte += 1
        if present:
            res[langue] = {"present": present, "detecte": detecte,
                           "rappel": detecte / present}
    return res


# --------------------------------------------------------------------------- #
# Chargement / validation du manifeste
# --------------------------------------------------------------------------- #
def charger_manifeste(manifest: Path, audio_dir: Path, limit: int | None):
    if not manifest.exists():
        sys.exit(f"[ERREUR] Manifeste introuvable : {manifest}\n"
                 f"         Copie experiments/testset/manifest.example.csv "
                 f"vers {manifest.name} et remplis-le.")
    lignes, manquants, invalides = [], [], []
    with manifest.open(encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f), start=2):
            langue = (row.get("langue") or "").strip()
            ref = (row.get("texte_ref") or "").strip()
            cond = (row.get("condition") or "").strip()
            nom = (row.get("fichier") or "").strip()
            if langue not in LANGUES_OK or not ref or not nom:
                invalides.append((i, nom or "?", "langue/texte_ref/fichier manquant ou invalide"))
                continue
            if cond and cond not in CONDITIONS:
                invalides.append((i, nom, f"condition inconnue : {cond!r}"))
                continue
            chemin = audio_dir / nom
            row["_chemin"] = chemin
            row["_present"] = chemin.exists()
            if not chemin.exists():
                manquants.append(str(chemin))
            lignes.append(row)
            if limit and len(lignes) >= limit:
                break
    return lignes, manquants, invalides


# --------------------------------------------------------------------------- #
# Sorties
# --------------------------------------------------------------------------- #
def pct(x):
    return "—" if x is None else f"{x*100:.1f}%"


def afficher_et_ecrire(agg, rappel, meta, mots_danger):
    print("\n" + "=" * 62)
    print("  BANC D'ESSAI ASR — SAUTI   ·  M-Kiriku-ASR")
    print("=" * 62)
    print(f"  Date        : {meta['date']}")
    print(f"  Modele      : {meta['modele']}   (mode : {meta['mode']}, backend : {meta['backend']})")
    print(f"  Manifeste   : sha256 {meta['manifest_sha256'][:12]}…  ·  {meta['n_locuteurs']} locuteur(s)")
    print(f"  Enonces     : {meta['n_scores']} scores / {meta['n_total']} lignes")
    if meta["n_manquants"]:
        print(f"  Audio absent: {meta['n_manquants']} (non scores)")
    print("-" * 62)

    print("\n  WER par langue (micro-moyenne corpus, IC 95 %)")
    print("  {:<8} {:>8} {:>8} {:>18} {:>6}".format(
        "langue", "WER", "WER≈", "IC95 (WER)", "n"))
    for langue in sorted(agg["par_langue"]):
        d = agg["par_langue"][langue]
        ic = f"[{pct(d['ic'][0])}, {pct(d['ic'][1])}]" if d["ic"][0] is not None else "—"
        print("  {:<8} {:>8} {:>8} {:>18} {:>6}".format(
            langue, pct(d["wer"]), pct(d["wer_relax"]), ic, d["n"]))
    g = agg["global"]
    icg = f"[{pct(g['ic'][0])}, {pct(g['ic'][1])}]" if g["ic"][0] is not None else "—"
    print("  {:<8} {:>8} {:>8} {:>18} {:>6}".format(
        "GLOBAL", pct(g["wer"]), pct(g["wer_relax"]), icg, g["n"]))
    print("  (WER≈ = variante avec diacritiques repliees)")

    if agg["par_condition"]:
        print("\n  WER par langue × condition")
        print("  {:<8} {:<14} {:>8} {:>6}".format("langue", "condition", "WER", "n"))
        for (langue, cond) in sorted(agg["par_condition"]):
            d = agg["par_condition"][(langue, cond)]
            print("  {:<8} {:<14} {:>8} {:>6}".format(langue, cond, pct(d["wer"]), d["n"]))

    print("\n  Rappel DANGER (metrique de securite — vise 100 %)")
    if rappel:
        print("  {:<8} {:>8} {:>10} {:>9}".format("langue", "rappel", "detectes", "presents"))
        for langue, r in sorted(rappel.items()):
            flag = "" if r["rappel"] >= 0.999 else "  <-- A SURVEILLER"
            print("  {:<8} {:>8} {:>10} {:>9}{}".format(
                langue, pct(r["rappel"]), r["detecte"], r["present"], flag))
    else:
        print("  (aucun enonce de reference ne contient de mot-cle danger —")
        print("   ajoute des phrases 'signe de danger' au jeu de test.)")

    print("\n  CER par langue")
    for langue in sorted(agg["par_langue"]):
        print("  {:<8} {:>8}".format(langue, pct(agg["par_langue"][langue]["cer"])))
    print("=" * 62)

    # JSON reproductible
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    prefixe = "mock" if meta["mode"] == "mock" else "asr"  # mock_* non versionnes
    out_json = REPO / "experiments" / "results" / f"{prefixe}_{stamp}.json"
    payload = {
        "meta": meta,
        "global": _clean(agg["global"]),
        "par_langue": {k: _clean(v) for k, v in agg["par_langue"].items()},
        "par_condition": {f"{k[0]}/{k[1]}": _clean(v) for k, v in agg["par_condition"].items()},
        "rappel_danger": rappel,
    }
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  -> Resultats JSON : {out_json.relative_to(REPO)}")
    print("  -> A reporter dans docs/modeles_kiriku.md (section Resultats mesures).\n")


def _clean(d):
    return {k: v for k, v in d.items() if k != "items"}


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    # Console Windows (cp1252) : evite un crash sur les diacritiques wolof si la
    # sortie est redirigee vers un fichier ou un pipe.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Banc d'essai ASR de Sauti (WER/CER + securite).")
    ap.add_argument("--manifest", type=Path,
                    default=REPO / "experiments" / "testset" / "manifest.csv")
    ap.add_argument("--audio-dir", type=Path,
                    default=REPO / "experiments" / "testset" / "audio")
    ap.add_argument("--limit", type=int, default=None, help="limiter le nombre d'enonces")
    ap.add_argument("--check-only", action="store_true",
                    help="valider le manifeste sans modele ni scoring")
    ap.add_argument("--mock", action="store_true",
                    help="auto-test : l'ASR renvoie la reference (WER ~0)")
    args = ap.parse_args()

    lignes, manquants, invalides = charger_manifeste(args.manifest, args.audio_dir, args.limit)

    if invalides:
        print(f"[MANIFESTE] {len(invalides)} ligne(s) invalide(s) :")
        for i, nom, motif in invalides[:20]:
            print(f"  L{i}: {nom} — {motif}")

    # --- mode validation seule ---
    if args.check_only:
        par_l = defaultdict(int)
        par_c = defaultdict(int)
        par_s = defaultdict(int)
        for r in lignes:
            par_l[r["langue"]] += 1
            par_c[(r["langue"], r.get("condition", "?"))] += 1
            par_s[r.get("sexe", "?")] += 1
        print("\n[CHECK] Manifeste :", args.manifest.name)
        print(f"  Lignes valides   : {len(lignes)}")
        print(f"  Audio present    : {sum(r['_present'] for r in lignes)} / {len(lignes)}")
        print(f"  Par langue       : {dict(par_l)}")
        print(f"  Par sexe (voix)  : {dict(par_s)}")
        print("  Par langue×cond  :")
        for k in sorted(par_c):
            print(f"    {k[0]:<5} {k[1]:<14} {par_c[k]}")
        if manquants:
            print(f"  [!] {len(manquants)} audio absent(s), ex :")
            for m in manquants[:8]:
                print("      -", m)
        # Garde-fous de representativite (recommandations, pas des erreurs)
        print("\n  Rappels de representativite :")
        for langue, seuil in (("wol", 20), ("ful", 15), ("srr", 15)):
            n = par_l.get(langue, 0)
            etat = "ok" if n >= seuil else f"faible (vise >= {seuil})"
            print(f"    {langue} : {n} enonces — {etat}")
        if par_s.get("f", 0) < par_s.get("m", 0):
            print("    [!] Moins de voix feminines que masculines — public cible = femmes.")
        return

    # --- ASR ---
    sys.path.insert(0, str(REPO / "src"))
    sys.path.insert(0, str(REPO))
    try:
        import jiwer  # noqa: F401
    except ImportError:
        sys.exit("[ERREUR] jiwer manquant : pip install jiwer")
    from sauti.voice.asr import KirikuASR

    asr = KirikuASR(mock=args.mock)
    # En mock (auto-test), on n'ouvre aucun audio : on score toutes les lignes
    # valides via texte_ref. En reel, on ne score que les audios presents.
    a_scorer = lignes if args.mock else [r for r in lignes if r["_present"]]
    if not a_scorer:
        sys.exit("[ERREUR] Aucun audio present a scorer. Verifie --audio-dir "
                 "ou lance --check-only.")

    paires = []
    print(f"\nTranscription de {len(a_scorer)} enonce(s)...")
    for i, r in enumerate(a_scorer, 1):
        try:
            if args.mock:
                hyp = asr.transcrire("", langue_forcee=r["langue"],
                                     texte_mock=r["texte_ref"]).texte
            else:
                hyp = asr.transcrire(str(r["_chemin"]), langue_forcee=r["langue"]).texte
        except Exception as e:
            print(f"  [!] {r['fichier']} : echec ASR ({e}) — ignore")
            continue
        paires.append({"langue": r["langue"], "condition": r.get("condition", "?"),
                       "locuteur": r.get("locuteur", "?"),
                       "ref": r["texte_ref"], "hyp": hyp})
        if i % 10 == 0:
            print(f"  {i}/{len(a_scorer)}")

    if not paires:
        sys.exit("[ERREUR] Aucun enonce transcrit (toutes les transcriptions ont echoue) "
                 "— aucun resultat ecrit.")

    # --- agregation ---
    def bloc(sous_ensemble):
        mots = [compter_mots(normaliser(p["ref"]), normaliser(p["hyp"])) for p in sous_ensemble]
        mots_relax = [compter_mots(normaliser(p["ref"], True), normaliser(p["hyp"], True))
                      for p in sous_ensemble]
        cars = [compter_caracteres(normaliser(p["ref"]), normaliser(p["hyp"])) for p in sous_ensemble]
        return {
            "n": len(sous_ensemble),
            "wer": wer_depuis_comptes(mots),
            "wer_relax": wer_depuis_comptes(mots_relax),
            "cer": wer_depuis_comptes(cars),
            "ic": bootstrap_ic(mots),
            "items": mots,
        }

    agg = {"global": bloc(paires), "par_langue": {}, "par_condition": {}}
    for langue in sorted({p["langue"] for p in paires}):
        agg["par_langue"][langue] = bloc([p for p in paires if p["langue"] == langue])
    for key in sorted({(p["langue"], p["condition"]) for p in paires}):
        sub = [p for p in paires if (p["langue"], p["condition"]) == key]
        if sub:
            agg["par_condition"][key] = bloc(sub)

    rappel = rappel_danger(paires, charger_mots_danger())
    if args.mock:
        backend = "mock"
    else:
        backend = "api Kiriku" if asr.utiliser_api else "local (transformers)"
    meta = {
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "modele": "AIHubSN/M-Kiriku-ASR" if not args.mock else "MOCK (auto-test)",
        "mode": "mock" if args.mock else "reel",
        "backend": backend,
        # Le manifeste reste prive (donnees) : son empreinte relie ce resultat
        # a une version exacte du jeu de test sans le publier.
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "n_locuteurs": len({p.get("locuteur") for p in paires}),
        "n_total": len(lignes), "n_scores": len(paires),
        "n_manquants": len(manquants),
    }
    afficher_et_ecrire(agg, rappel, meta, charger_mots_danger())

    if args.mock and agg["global"]["wer"] > 0.001:
        print("[AUTO-TEST] Attendu WER~0 en mock : verifie la normalisation.")


if __name__ == "__main__":
    main()
