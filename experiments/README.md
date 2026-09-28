# Banc d'essai ASR — Sauti

> **Principe :** on n'améliore pas ce qu'on n'a pas mesuré. Ce dossier mesure ce
> que `M-Kiriku-ASR` vaut **sur notre terrain** (santé maternelle, voix
> féminines, téléphone, bruit), pas sur un corpus de labo. C'est la première
> brique d'ingénierie du projet — et la source de vérité de la section
> « Résultats mesurés » de `docs/modeles_kiriku.md`.

## Pourquoi ce banc avant tout fine-tuning

Le WER annoncé par AI Hub (wolof 16,3 % · pulaar 45,3 % · sérère 43,0 %) est un
**repère**, pas notre réalité. Nos conditions sont plus dures (téléphone bas
débit, bruit, code-switching). On mesure d'abord, on décide ensuite. Toucher aux
poids du modèle sans banc de test, c'est optimiser à l'aveugle.

## Ce qu'il mesure

| Métrique | Ce qu'elle dit | Pourquoi elle compte |
|----------|----------------|----------------------|
| **WER** par langue × condition | taux d'erreur mot, micro-moyenne corpus | qualité brute de transcription |
| **IC 95 % (bootstrap)** | incertitude sur le WER | un petit jeu de test sans IC n'est pas défendable |
| **WER assoupli** | WER avec diacritiques repliées | combien d'erreurs ne sont que des accents |
| **CER** | taux d'erreur caractère | plus stable que le WER sur petits échantillons |
| **Rappel danger** | % des signes de danger retrouvés dans l'hypothèse | **sécurité** : rater « dëret » (sang) est une faute grave |

Le **rappel danger prime sur le WER global** : pour une ligne de santé, mieux vaut
un WER moyen mais 100 % des mots de danger captés, que l'inverse.

## Protocole de collecte du jeu de test

Le jeu de test doit **ressembler à la vraie ligne**, pas à un studio.

1. **Taille cible (v1)** : ≥ 20 énoncés wolof, ≥ 15 pulaar, ≥ 15 sérère.
   Monter à 50/langue pour un WER vraiment stable.
2. **Voix** : majorité **féminine** (le public cible), plusieurs locutrices
   (≥ 3 par langue) pour ne pas mesurer une seule voix.
3. **Conditions** (colonne `condition`) — couvrir les 5 :
   - `calme` : pièce silencieuse (référence haute).
   - `bruit` : marché, rue, ventilateur en fond.
   - `telephone` : enregistré via un vrai appel (bande passante réduite) — **le plus important**, c'est le canal réel.
   - `debit_rapide` : parole naturelle rapide.
   - `code_switch` : mélange langue nationale + français (« sama rendez-vous »).
4. **Contenu** : la moitié = **vraies questions** de santé maternelle ; l'autre
   moitié = **signes de danger** formulés naturellement (pour tester le rappel
   danger). Réutiliser les tournures de `data/knowledge_base/`.
5. **Transcription de référence** : faite par un **locuteur natif**, exactement
   ce qui est dit (hésitations comprises), orthographe cohérente.
6. **Consentement** : chaque locutrice consent à l'usage (règle « Données » du
   challenge). Garder une trace. Pas de données sans droits.
7. **Anonymat** : `locuteur` = identifiant neutre (`spk01`), jamais de nom.

### Nommage des fichiers audio
```
<langue>_<condition>_<locuteur>_<num>.wav
ex : wol_telephone_spk02_004.wav
```
Format : WAV mono 16 kHz de préférence (whisper ré-échantillonne, mais autant
partir propre).

## Utilisation

```bash
# 0) depuis la racine du dépôt, avec l'environnement du projet
export PYTHONPATH="src;."          # Windows Git Bash (; et non :)

# 1) AVANT de collecter : valider le format du manifeste (aucun modèle requis)
python experiments/01_benchmark_asr.py --check-only

# 2) Auto-test de la tuyauterie de scoring (WER doit ressortir ~0)
python experiments/01_benchmark_asr.py --mock

# 3) Vrai run (modèle gated : HF_TOKEN + accès accepté sur huggingface.co)
python experiments/01_benchmark_asr.py \
    --manifest experiments/testset/manifest.csv \
    --audio-dir experiments/testset/audio
```

Pour démarrer : copier `manifest.example.csv` en `manifest.csv`, y mettre tes
vraies lignes, déposer les `.wav` dans `experiments/testset/audio/`.

Les résultats sont écrits dans `experiments/results/asr_<horodatage>.json`
(reproductibles, à commiter) et résumés dans le terminal. Reporter le tableau
final dans `docs/modeles_kiriku.md`.

## Après la mesure — l'ordre des décisions

1. **Mesurer** (ce banc) → WER honnête par langue/condition + rappel danger.
2. **Adapter le système sans réentraîner** : lexique domaine, seuils de
   confiance, repli sur menu guidé si l'ASR n'est pas sûr. Re-mesurer.
3. **Seulement ensuite, et post-challenge** : fine-tuning sur données terrain
   annotées — quand le programme de collecte existe. Les données d'abord.
