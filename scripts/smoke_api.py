"""Test de fumee de l'API Kiriku : connexion, TTS wolof + pulaar, ASR, pipeline.

N'envoie AUCUN audio de locutrice (donnees sous consentement) : l'ASR est verifie
sur l'audio produit par le TTS. C'est un test de CONNEXION, pas une mesure :
ne JAMAIS en tirer un WER (circulaire). Pour mesurer : experiments/01_benchmark_asr.py.

Usage (KIRIKU_API_KEY dans .env) :
  export PYTHONPATH="src;." && python scripts/smoke_api.py
Les WAV sont ecrits dans experiments/smoke/ (non versionne) pour ecoute.
"""
from __future__ import annotations
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO))

from config.settings import settings  # noqa: E402

PHRASES = {
    "wol": "jàmm nga fanaane? sama biir dafa metti.",
    "ful": "a jaaraama. no mbaɗ-ɗaa?",
}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not settings.kiriku_api_key:
        print("[ERREUR] KIRIKU_API_KEY absente : l'ajouter dans .env (jamais commitee).")
        return 1

    from sauti.voice.kiriku_api import KirikuAPI
    import requests

    api = KirikuAPI()
    sortie = REPO / "experiments" / "smoke"
    sortie.mkdir(parents=True, exist_ok=True)
    echecs = 0

    ping = requests.get(api.base_url.removesuffix("/v1") + "/ping",
                        headers={"User-Agent": "sauti/0.1"}, timeout=20)
    print(f"[ping] HTTP {ping.status_code} {ping.text[:80]}")

    for langue, phrase in PHRASES.items():
        try:
            t0 = time.perf_counter()
            wav = api.synthetiser(phrase, langue)
            dt = time.perf_counter() - t0
            f = sortie / f"tts_{langue}.wav"
            f.write_bytes(wav)
            print(f"[tts {langue}] OK {len(wav) / 1024:.0f} Ko en {dt:.1f}s -> {f.relative_to(REPO)}")

            t0 = time.perf_counter()
            texte = api.transcrire(f, langue)
            print(f"[asr {langue}] OK en {time.perf_counter() - t0:.1f}s : {texte!r}"
                  f"  (attendu ~ {phrase!r} — controle de connexion, pas un WER)")
        except Exception as e:
            echecs += 1
            print(f"[{langue}] ECHEC : {e}")

    # Bout en bout : le pipeline reel route bien vers l'API (danger -> escalade + voix)
    try:
        from sauti.pipeline import Pipeline
        pipe = Pipeline(mock=False)
        res = pipe.traiter(chemin_audio=str(sortie / "tts_wol.wav"), langue="wol")
        print(f"[pipeline] danger={res['danger']} texte={res['texte_entrant']!r} "
              f"audio={getattr(res['audio_reponse'], 'contenu', None)}")
    except Exception as e:
        echecs += 1
        print(f"[pipeline] ECHEC : {e}")

    print("\nRESULTAT :", "OK" if not echecs else f"{echecs} echec(s)")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
