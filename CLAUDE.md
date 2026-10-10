# Sauti — contexte projet pour Claude Code

> Lu automatiquement à chaque session. Contexte, état du code, décisions
> d'ingénierie, pièges connus, reste à faire. À mettre à jour au fil du projet.

---

## 1. Ce qu'est Sauti

**Sauti** (« la voix » en swahili) est une **ligne téléphonique (IVR) de santé
maternelle en langues nationales** du Sénégal : wolof, pulaar, sérère. Une femme
enceinte appelle depuis un **téléphone simple** (pas d'app, pas d'internet), parle
dans sa langue, et le système comprend, **détecte les urgences obstétricales**, et
répond par la voix — ou l'oriente vers un soignant.

- **Challenge :** Kiriku Voice Inclusive & Creative Challenge (KVICC), organisé par
  **AI Hub Senegal × Vie Publique Sénégal**. Secteur : **Santé**.
- **Équipe :** « **Echo Sahel** » — Aboubacar Compo (lead, data/IA), Abdoul Karim
  Diallo (dev web), Kadi Ndiaye (dev web & IA).
- **Dépôt :** `github.com/compo90/sauti` (public). Dev en **local Windows / Git Bash**.
- **Deadline de soumission :** **10 octobre 2026, 20h00** (cérémonie finale 16 oct.,
  Hôtel Noom Dakar, à partir de 08h30, pitch 5 min + Q/R).
- **Vision :** ce n'est PAS qu'un projet de challenge — il est destiné à être
  **déployé réellement au Sénégal** à l'échelle nationale. Garder cette exigence.

**Inspirations :** Kilkari (Inde, IVR maternel national), Jacaranda/PROMPTS (Kenya,
triage IA + escalade humaine), Viamo 3-2-1 (Afrique de l'Ouest, IVR en langues
locales), FarmerChat (NLU vocal en langues locales).

---

## 2. Modèles Kiriku (couche voix) — source de vérité : `docs/modeles_kiriku.md`

### 2a. API d'inférence du challenge (backend par défaut si clé présente)

- Base : `https://14hyb7tjwzuh9q-8000.proxy.runpod.net/v1` — doc : `/docs`.
  Compatible SDK OpenAI. RunPod RTX 4090. **Disponible jusqu'au 16 oct. 2026.**
- Clé d'équipe `sk-kiriku-...` → `.env` : `KIRIKU_API_KEY=...`. **Jamais commitée.**
- `POST /audio/transcriptions` : `model=m-kiriku-asr`, `language=wolof|pulaar|serer`, ≤ 60 s, ≤ 25 Mo.
- `POST /audio/speech` : `model=kiriku-tts`, `voice=wolof|pulaar` (**pas de sérère**), ≤ 512 car., WAV 22,05 kHz.
  Vitesse par défaut : wolof 1.2, pulaar 1.0.
- Limites : 30 req/min, 15 concurrentes par clé → 429 + `Retry-After` ; 503 si serveur saturé.
- **Pièges TTS** : tout caractère hors alphabet est **ignoré en silence** ; seuls les
  nombres 0–10 sont lus (en français) → **écrire les nombres > 10 en toutes lettres**.
  Pulaar : utiliser les vraies lettres `ɓ ɗ ƴ ŋ`.
- Les TTS de l'API viennent de `mlroot/ww2` (pas forcément le même checkpoint que
  `AIHubSN/Kiriku-*-TTS`) → le MOS annoncé n'est pas garanti sur cette voix.
- `User-Agent` obligatoire (fourni par `requests`/SDK, pas par `urllib`).
- Journal d'usage : métadonnées seulement (code public : github.com/abdouaziz/Sbckend).
  Un partage volontaire des audios est à l'étude, **opt-in** → ne pas l'activer sans
  accord explicite (données de santé, CDP).
- Code : `src/sauti/voice/kiriku_api.py`. Sélection via `VOICE_BACKEND=auto|api|local`
  (`auto` = api si `KIRIKU_API_KEY` renseignée). Découpage > 512 car. par phrase +
  concaténation WAV ; retries sur 429/503 ; panne TTS API → `TTSIndisponible`
  (dégradation gérée par le pipeline).

### 2b. Modèles Hugging Face (backend `local`, post-challenge / souveraineté)

Tous **gated** (accepter les conditions + `HF_TOKEN` en lecture).

| Modèle | Tâche | Langues | Base | Format |
|--------|-------|---------|------|--------|
| `AIHubSN/M-Kiriku-ASR` | ASR | wol·ful·srr | whisper-large-v3 | transformers pipeline |
| `AIHubSN/Kiriku-Wolof-TTS` | TTS | wolof | VITS | **Coqui-TTS** (`model.pth`+`config.json`) |
| `AIHubSN/Kiriku-Pulaar-TTS` | TTS | pulaar | VITS | Coqui-TTS — accès HF pas encore accordé (**l'API le fournit**) |
| — | TTS sérère | — | — | **inexistant** → audio humain pré-enregistré |

**WER annoncé AI Hub (studio) :** wolof ~16,3 % · pulaar ~45,3 % · sérère ~43,0 %.
**MOS TTS :** wolof 3,34 · pulaar 4,32 (annoncé).

**Tiering par langue (décision d'archi) :**
- **wolof** : question libre (ASR) + réponse TTS — chaîne complète.
- **pulaar** : menu guidé + TTS (ASR trop faible pour question libre).
- **sérère** : menu + **audio humain pré-enregistré** (ni ASR fiable, ni TTS).

**TTS Coqui local — pièges résolus :** charger via `TTS.utils.synthesizer.Synthesizer`
(PAS `transformers`). Appliquer `.lower()` au texte. Installer `coqui-tts` avec
`transformers<5`.

---

## 3. Architecture — 8 couches

Flux : `audio → ASR → TRIAGE DANGER → (escalade | dialogue → KB → TTS) → audio`.
La **sécurité prime sur la pertinence** : le triage danger passe avant tout.

1. **Téléphonie / IVR** — Asterisk + AGI, DTMF, numéro court. *(squelette)*
2. **Voix — ASR & TTS** — M-Kiriku-ASR + Kiriku-TTS, backend API ou local. *(intégré, WER mesuré)*
3. **NLU & Triage danger (barrière 1)** — détecteur tolérant recall-first. *(fait)*
4. **Dialogue & Dépistage (barrière 2)** — filet oui/non, tiering. *(fait)*
5. **Base de connaissances** — FAQ + signes danger, portail `[A VALIDER]`. *(validation clinique en cours)*
6. **Escalade humaine** — poste de santé / sage-femme, webhook + appel. *(squelette)*
7. **Données & monitoring** *(transversale)* — WER, rappel danger, corpus terrain. *(banc d'essai fait)*
8. **Sécurité & consentement / CDP** *(transversale)* — consentement, chiffrement, souveraineté. *(principes posés)*

---

## 4. Structure du dépôt

```
sauti/
├── config/settings.py            # pydantic-settings, lit .env (HF_TOKEN, KIRIKU_API_KEY, VOICE_BACKEND…)
├── src/sauti/
│   ├── voice/asr.py              # KirikuASR : mock | api | local (transformers)
│   ├── voice/tts.py              # KirikuTTS : mock | api | local (Coqui VITS), routage par langue
│   ├── voice/kiriku_api.py       # client HTTP API Kiriku (retries, découpage 512 car.)
│   ├── nlu/danger_detector.py    # DangerDetector FUZZY recall-first (_lev, _tok_close, _STOP)
│   ├── nlu/intent_classifier.py  # classification d'intention
│   ├── dialog/screening.py       # DepistageDanger + reconnaitre_oui_non (filet oui/non)
│   ├── knowledge/kb.py           # accès base de connaissances
│   ├── escalation/escalation.py  # escalade vers humain
│   ├── telephony/agi_sauti.py    # AGI Asterisk + ivr_handler.py + dialplan/extensions.conf
│   └── pipeline.py               # orchestration bout-en-bout, mode mock (--demo)
├── data/knowledge_base/
│   ├── faq_maternelle.json       # 30 questions [A VALIDER], trad wol/ful/srr à compléter
│   └── signes_danger.json        # 6 signes, mots-clés fr + wolof (validés par locuteur)
├── experiments/
│   ├── 01_benchmark_asr.py       # banc WER/CER + rappel danger + IC bootstrap
│   ├── README.md                 # protocole de collecte du jeu de test
│   ├── results/                  # asr_*.json versionnés (agrégats + manifest_sha256)
│   └── testset/                  # manifest.example.csv versionné ; manifest.csv + audio/ privés
├── tests/                        # pytest (24 tests) — aucun réseau ni modèle
├── docs/modeles_kiriku.md        # inventaire modèles + RÉSULTATS MESURÉS
└── .github/workflows/            # CI GitHub Actions (pytest, deps légères)
```

**6 signes de danger** (`signes_danger.json`) : hémorragie, convulsions,
céphalées/vision, fièvre forte, mouvements fœtaux, œdème.

---

## 5. Résultats mesurés (à jour au 10 oct. 2026)

Manifeste **v3** `aba0ea05854b…` : **19 clips wolof, 3 locutrices** (`spk01` : 11 signes
de danger ; `spk02`, `spk03` : 8 questions bénignes partie B), colonnes `type`
(danger|benin) et `kb_attendu`. Variante `manifest_telephone.csv` (ffmpeg 8 kHz).
Évaluation sécurité : `experiments/02_eval_securite.py` (agrégats + IC de Wilson).

**Chiffres à citer (10 oct., API Kiriku)** :
- Rappel danger : **82 % (9/11) au calme, 64 % (7/11) au téléphone simulé** → justifie
  le filet oui/non.
- Fausses alertes : **0/8** au calme et au téléphone (IC jusqu'à 32 % : petit effectif).
- WER 19 clips : 37,6 % [26,5–48,9] au calme, 42,7 % au téléphone ; surestimé sur la
  partie B (références en orthographe « à la française »). WER partie A seule (v2) :
  26,1 % [11,8–48,5].
- Bonne fiche KB : 1/4 → le classifieur ne comprend pas le wolof (FAQ en français).

Historique (v2, 11 clips, `spk01`) :
- **Rappel danger** (métrique de sécurité principale), détecteur tolérant, via API :
  **9/11 = 82 %**, 0 faux positif (exact : 8/11 = 73 %).
- **Ratés via API** : « dama sibbiru » → « damaski biru » ; « dama miir » → « dama mire ».
  (Sous Colab les ratés étaient #2 et #4 : ils varient selon le backend.) Fermés par
  l'ARCHITECTURE (filet oui/non + escalade). Ne PAS régler le détecteur sur ces clips.
- **À soumettre au soignant** : la douleur abdominale (« sama biir dafa metti ») n'est
  pas dans les 6 signes ; une douleur abdominale sévère est un signe d'alerte reconnu.

**Détecteur tolérant** : `fuzzy=True` (défaut). Distance d'édition sur les mots de
sens, souple sur `_STOP`, exact sur les mots ≤ 3 lettres. `fuzzy=False` = exact.

**Filet oui/non** : `reconnaitre_oui_non()` (« waaw »/« déedéet » + fr).
`DepistageDanger.evaluer()` recall-first : seul un « non » clair ferme un signe.
Le clip #4 raté par l'ASR est rattrapé par le dépistage.

---

## 6. Corpus / données (le vrai goulot)

- **11 clips wolof** collectés (signes de danger, 1 locutrice, calme).
- **Fiche de collecte** : A (12 phrases de danger), B (questions banales — **4 vocaux reçus sur WhatsApp,
  à exporter et transcrire**), C (mises en situation + une longue bénigne).
- **Condition téléphone** simulée :
  `ffmpeg -i in.wav -ar 8000 -af "highpass=f=300,lowpass=f=3400" out.wav`.
- **Objectif WER défendable :** 30–50 clips wolof, 5–10 locutrices, plusieurs conditions.
- **RÈGLE DONNÉES (tranchée le 8 oct. 2026)** — cf. `experiments/README.md` :
  - audios **et** `manifest.csv` = données sous consentement → **hors dépôt**
    (Drive équipe, accès restreint). Seul `manifest.example.csv` est versionné.
  - `results/asr_*.json` (agrégats, aucun texte) = **versionnés** ; chacun porte
    `manifest_sha256` + `backend`. Tout chiffre annoncé renvoie à l'un d'eux.
  - `--mock` écrit `results/mock_*.json` (ignorés).
  - Historique : `manifest.csv` (11 phrases scriptées partie A, `spk01`) a été
    public jusqu'au 8 oct. Risque jugé faible (phrases scriptées, pseudonyme) →
    pas de réécriture d'historique. Ne JAMAIS y mettre de parties B/C.
- **Envoi des audios de test à l'API** (tiers : RunPod, UE) : couvert par le
  consentement (confirmé le 8 oct. 2026). À re-vérifier pour toute nouvelle locutrice.

**Format** `experiments/testset/manifest.csv` (UTF-8) :
`fichier,langue,condition,locuteur,sexe,texte_ref`. Conditions :
`calme|bruit|telephone|debit_rapide|code_switch`. Nommage : `wol_<condition>_<spkNN>_<num>.wav`.

---

## 7. Décisions d'ingénierie & bonnes pratiques (à respecter)

- **Recall-first sur le danger** : dans le doute, on escalade.
- **Deux barrières** : triage texte libre PUIS dépistage oui/non.
- **Portail `[A VALIDER]`** : aucun contenu médical diffusé sans validation soignant.
- **Mesurer sur NOS données**, toujours avec intervalle de confiance.
- **Ne pas surapprendre sur 11 clips.** Élargir le corpus d'abord.
- **Données avant modèle** : fine-tuning = roadmap post-challenge.
- **Ne JAMAIS tester l'ASR avec de l'audio généré par TTS** (circulaire).
- **Dégradation gracieuse** : ASR peu fiable → menu guidé ; pas de TTS → audio
  pré-enregistré ; doute danger → escalade ; API en panne → repli. Jamais de silence.
- **Dépendance API = risque de démo** : l'API s'arrête le 16 oct. et n'est pas un
  déploiement. Garder le backend `local` fonctionnel ; pré-générer les audios de démo.
- **Mode mock** partout (sans modèle, GPU ni réseau) pour la logique + CI.
- **Changements de code** : blocs avant/après exacts, tests verts avant commit.

---

## 8. Environnement de dev & pièges connus

- **OS :** Windows + Git Bash, `.venv`. `export PYTHONPATH="src;."` (séparateur `;`).
- **ffmpeg** requis. `winget install ffmpeg`.
- **HF :** chaque modèle gated s'autorise séparément. `HF_TOKEN` dans `.env`. `hf auth login`.
- **Conflit `huggingface_hub` :** `transformers<5` exige `huggingface_hub<1.0`.
- **CSV :** `manifest.csv` en **UTF-8**, **jamais via Excel**. Vérifier avec `cat`.
- **ASR local lent** sur CPU → API Kiriku ou Colab GPU.
- **CI** : deps légères (`jsonschema pydantic-settings pytest`) ; `requests` importé
  tardivement, les tests API utilisent une session factice.

---

## 9. Ressources externes — Google Drive du projet

Dossier : https://drive.google.com/drive/folders/14Xws10ZZ1CglzHqKSlLVIVCkHB7Cs5cI
(accès restreint : c'est ici que vivent les DONNÉES — audios, manifeste réel).

| Fichier | ID Drive | Rôle |
|---|---|---|
| `Sauti_Benchmark_Colab.ipynb` | `1w_PRZnpJOBmtNhgrxO3Sg2m-2mm-771c` | banc WER + rappel danger (GPU) — run du 30 sept. (30,4 %) |
| `Sauti_Kiriku_Colab.ipynb` | `1aabavx9lKQ0KK5nGSLBfV8rHDAAeINEn` | ASR+WER (A) + TTS Coqui (B) |
| `Sauti_Demo_E2E.ipynb` | `1QqVRasZrmjEBhVwywcqCchxufOoyd6tP` | démo bout-en-bout ASR → danger → TTS |
| `Sauti_validation_contenu.xlsx` | `1H4k0s5Gk0mGDiIYLoLPErobRrkZNM0zR` | validation clinique du contenu |
| `Matosbi 10/12/13/14.m4a` | — | vocaux wolof d'Aboubacar (voix masculine), hors jeu de test cible |
| `HUG.png`, `TTS.png` | — | captures (HF / TTS) |

Consentement : l'envoi des audios de test à l'API Kiriku (RunPod, UE) est
couvert (confirmé par Aboubacar le 8 oct. 2026).

## 10. Reste à faire (priorisé — deadline 10 oct. 20h)

**Livrables :** prototype · **pitch deck PDF** · **démo vidéo MP4** · documentation ·
code (dépôt Git) · équipe (rôles). Nommage type `EchoSahel_Sauti_Pitch.pdf`.

**Grille :** Impact & pertinence **25 %** · Inclusion & accessibilité **20 %** ·
Qualité technique **20 %** · Langues nationales **15 %** · Viabilité & déploiement
**15 %** · Pitch & démo **10 %**.

### État au 9 oct. 2026 (reprise après redémarrage)
- [x] API Kiriku branchée + test de connexion OK (clé dans `.env`, ignoré par Git).
- [x] WER via API, refs v2 : 26,1 % [11,8–48,5] ; rappel danger 82 %.
- [x] **Partie B** intégrée (10 oct.) : 8 vocaux, 2 locutrices (Femme 1 du fichier =
      `spk02`, Femme 2 = `spk03` ; la 3ᵉ a été écartée par Aboubacar, réponses non conformes).
      Aucune n'est `spk01`. Manifeste v3 + téléphone + évaluation sécurité faits.
- [x] `Matosbi*.m4a` (Drive) = vocaux d'Aboubacar lui-même (voix masculine) → hors du
      jeu de test cible (public féminin) ; utilisables plus tard en test de robustesse.
- [ ] Fiche FAQ « médicament » [A VALIDER] (n'existe pas : sujet à risque).

### Priorité 1 — AVANT le 10 oct.
- [x] Backend API Kiriku (ASR + TTS wolof/pulaar) intégré et testé (mock HTTP).
- [ ] Mettre la clé dans `.env`, tester un appel réel (1 clip wolof, 1 phrase TTS wolof + pulaar).
- [ ] **Pitch deck PDF** (5 min) : architecture 8 couches, récit mesuré (rappel 73→82 % + filet).
- [ ] **Démo vidéo MP4** : boucle wolof, question bénigne vs signe de danger ; montrer
      aussi une réponse TTS **pulaar** (nouveau grâce à l'API).
- [ ] Vérifier les 6 livrables (dépôt public, vidéo lisible, liens OK).

### Priorité 2 — contenu & robustesse
- [ ] Validation clinique du contenu `[A VALIDER]` par un soignant.
- [ ] Libellés wolof des questions oui/non du dépistage (locuteur natif).
- [ ] Normaliser les références partie B en orthographe CLAD (locuteur natif, sans copier l'ASR).
- [ ] Traductions wol/ful/srr de la FAQ (nombres > 10 en toutes lettres pour le TTS).
- [ ] Repli ASR si l'API échoue (aujourd'hui l'exception remonte) → menu guidé / escalade.

### Priorité 3 — mesure & modèle (post-challenge pour l'essentiel)
- [ ] Re-mesurer le WER via l'API (vérifier l'égalité avec le run local) et élargir à 30–50 clips.
- [ ] Simuler la condition téléphone (ffmpeg) sur les clips calmes.
- [ ] Biais de domaine ASR (`initial_prompt`) + n-best (pas exposés par l'API → local).
- [ ] Implémenter les couches 1 (Asterisk) et 6 (escalade).
- [ ] Roadmap fine-tuning (programme de collecte annotée).

---

## 11. Comment travailler avec Aboubacar

- Répondre en **français**, direct, orienté livrable, sans blabla introductif.
- **Rigueur et bonnes pratiques du métier** — projet d'envergure.
- **Challenger, proposer, dire ce qui ne va pas**, pas seulement valider.
- Honnêteté sur les limites (petits échantillons, mesuré vs supposé).
- Changements de code : **blocs avant/après exacts**, tests verts avant commit.
- Ancrer dans le contexte réel (Sénégal, santé maternelle, téléphone simple).
