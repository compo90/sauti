# Corpus de test audio

Enregistrez ici 30 à 80 phrases réelles (wolof, pulaar, sérère) posées par de
vraies utilisatrices, **en conditions terrain** (bruit de marché, vent, radio),
sur un téléphone basique. Ce jeu sert à mesurer le **WER/CER réel** de
`M-Kiriku-ASR` (voir `experiments/01_benchmark_asr.py`).

- Format : `.wav` 16 kHz mono de préférence.
- Nommage : `wol_001.wav`, `ful_001.wav`, `srr_001.wav`…
- Fichier de référence : `transcriptions.csv`, colonnes :
  `fichier, langue, condition, texte`
  - `langue` ∈ {`wol`, `ful`, `srr`}
  - `condition` ∈ {`calme`, `bruit`, `code_switch`} (pour ventiler les scores)
- ⚠️ Ces audios peuvent contenir des données personnelles : **ne jamais committer**
  (voir `.gitignore`). Obtenir le **consentement** des locutrices.

Exemple de `transcriptions.csv` :

```csv
fichier,langue,condition,texte
wol_001.wav,wol,calme,naka la jangoro ji
wol_002.wav,wol,bruit,sama doom dafa tang
ful_001.wav,ful,calme,...
srr_001.wav,srr,code_switch,...
```
