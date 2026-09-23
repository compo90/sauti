# Sauti — ligne vocale de santé maternelle

> Service téléphonique (IVR) qui **écoute et parle** les langues nationales du Sénégal
> (wolof · pulaar · sérère) pour informer les femmes enceintes et jeunes mères,
> détecter les signes de danger et les orienter vers un soignant.
> Inspiré de **Kilkari** (Inde), **PROMPTS / Jacaranda** (Kenya) et **Viamo 3-2-1** (Burkina Faso).

## ⚠️ Avertissement clinique
Ce dépôt est un **prototype technique**. Aucun contenu médical ici n'est validé.
Chaque réponse et chaque signe de danger **doit être revu et signé par un
professionnel de santé** et calé sur les protocoles nationaux (PNDS, PEV) avant
tout usage réel. Le service **ne remplace pas** une consultation.

## Langues & modèles Kiriku (réalité vérifiée sur Hugging Face)
ASR multilingue unique `AIHubSN/M-Kiriku-ASR` (whisper-large-v3) + TTS par langue.
Détail et décisions dans [`docs/modeles_kiriku.md`](docs/modeles_kiriku.md).

| Langue | ASR | TTS | Chaîne vocale |
|--------|-----|-----|---------------|
| Wolof (`wol`) | ✅ | ✅ | complète — langue de démarrage |
| Pulaar (`ful`) | ✅ | ✅ | complète |
| Sérère (`srr`) | ✅ | ❌ | **écoute oui, synthèse non** → réponses par audio pré-enregistré |

> Tous les modèles Kiriku sont **gated** : accepter les conditions sur huggingface.co
> et renseigner `HF_TOKEN`. Le gate de validation clinique est décrit dans
> [`docs/validation_clinique.md`](docs/validation_clinique.md).

## Architecture (8 couches)
| # | Couche | Dossier |
|---|--------|---------|
| 1 | Téléphonie / IVR (Asterisk) | `src/sauti/telephony/` |
| 2 | Voix — ASR & TTS (Kiriku)   | `src/sauti/voice/` |
| 3 | NLU + **triage danger** (cœur) | `src/sauti/nlu/` |
| 4 | Dialogue (machine à états)  | `src/sauti/dialog/` |
| 5 | Base de connaissances médicale | `src/sauti/knowledge/` + `data/knowledge_base/` |
| 6 | Escalade humaine            | `src/sauti/escalation/` |
| 7 | Données & supervision       | `src/sauti/` (logs) |
| 8 | Sécurité & conformité (CDP) | transversal |

Orchestration de bout en bout : `src/sauti/pipeline.py`
```
audio → ASR → [triage danger] → (escalade | intention → réponse KB) → TTS → audio
```

## Démarrage rapide
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # renseigner HF_TOKEN, contacts escalade...

python scripts/validate_kb.py   # valider la base de connaissances
pytest -q                       # lancer les tests
python -m sauti.pipeline --demo "..."   # démo en mode mock (sans modèles)
```

## Feuille de route (voir dossier d'architecture)
- **Phase 1** — Données & contenu : compléter `data/knowledge_base/` + corpus audio de test.
- **Phase 2** — Voix : brancher Kiriku ASR/TTS, mesurer le WER sur notre échantillon.
- **Phase 3** — NLU & danger : entraîner l'intention, régler le détecteur de danger (recall élevé).
- **Phase 4** — Dialogue & IVR : assembler dans Asterisk.
- **Phase 5+** — Pilote district, évaluation d'impact, passage à l'échelle.

## Structure
```
sauti/
├── data/knowledge_base/   # contenu validé (FAQ, signes de danger, calendrier)
├── src/sauti/            # code, une couche = un sous-paquet
├── scripts/               # utilitaires (validation KB...)
├── experiments/           # bancs d'essai (WER/CER Kiriku ASR)
├── docs/                  # inventaire modèles, gate de validation clinique
├── .github/workflows/     # CI (validation KB + tests à chaque push)
└── tests/                 # intégrité KB + recall danger + routage voix
```

## Licence & données
Données de santé = catégorie **sensible** (loi sénégalaise 2008-12, CDP).
Consentement, chiffrement, anonymisation dès la conception. Ne jamais committer
de données personnelles réelles ni de fichiers `.env`.
