# Inventaire des modèles Kiriku (vérifié sur Hugging Face)

> Source de vérité technique pour la couche voix. À revérifier à chaque mise à
> jour des modèles par IA Hub Senegal (`AIHubSN`).

## Modèles disponibles

| Modèle | Tâche | Langues | Base | Licence | Accès |
|--------|-------|---------|------|---------|-------|
| `AIHubSN/M-Kiriku-ASR` | ASR | wolof · pulaar · sérère | whisper-large-v3 | apache-2.0 | 🔒 gated |
| `AIHubSN/Kiriku-Wolof-ASR` | ASR | wolof (seul) | whisper-large-v2 | apache-2.0 | 🔒 gated |
| `AIHubSN/Kiriku-Wolof-TTS` | TTS | wolof | VITS | — | 🔒 gated |
| `AIHubSN/Kiriku-Pulaar-TTS` | TTS | pulaar | VITS | — | 🔒 gated |

**Choix retenu pour l'ASR** : `M-Kiriku-ASR` (multilingue) plutôt que le wolof-seul,
car il couvre les trois langues nationales d'un seul modèle.

## Matrice de couverture par langue

| Langue (ISO 639-3) | ASR | TTS | Conséquence |
|--------------------|-----|-----|-------------|
| wolof `wol` | ✅ | ✅ | Chaîne vocale complète. Langue de démarrage. |
| pulaar `ful` | ✅ | ✅ | Chaîne vocale complète. |
| sérère `srr` | ✅ | ❌ | **On écoute mais on ne synthétise pas.** Réponses par audio humain pré-enregistré (champ `audio` de la base de connaissances) jusqu'à l'arrivée d'un TTS sérère. |

## Décisions d'architecture qui en découlent

1. **ASR** : un seul point d'entrée multilingue. La détection/forçage de langue
   exact de `M-Kiriku-ASR` (token forcé vs auto-détection) est **à confirmer via
   la carte du modèle** (gated) avant la Phase 3 — voir le `TODO` dans `voice/asr.py`.
2. **TTS sérère** : le pipeline exige un `audio_pre_enregistre` pour le sérère et
   lève `TTSIndisponible` s'il manque, plutôt que de produire du son dans une
   mauvaise langue. Prévoir l'enregistrement humain des réponses + des messages de
   danger en sérère.
3. **Modèles gated** : accepter les conditions de chaque dépôt sur huggingface.co,
   puis renseigner `HF_TOKEN` (lecture) dans `.env`.
4. **Poids lourds** (~1,5 Md paramètres, whisper-large-v3) : GPU recommandé pour
   l'inférence en temps réel. À intégrer dans le dimensionnement infra (Phase 4).

## Résultats mesurés sur notre corpus (Sauti)

| Date | Modèle | Langue | Condition | Échantillon | WER | CER |
|------|--------|--------|-----------|-------------|-----|-----|
| 2026-09-23 | M-Kiriku-ASR | wolof | clair (1 phrase) | 1 clip | **0,0 %** | **0,0 %** |
| 2026-09-30 | M-Kiriku-ASR | wolof | voix féminines, phrases courtes de danger | 11 clips | **30,4 %** (assoupli 26,1 %) | — |
| 2026-10-08 | M-Kiriku-ASR **via API Kiriku** (fp16, RTX 4090) | wolof | mêmes 11 clips, manifeste **v1** `1e9130c9ab83…` (références incomplètes) | 11 clips | 39,0 % (assoupli 34,1 %), IC95 [15,4 – 74,2 %] — *remplacé* | 19,5 % |
| 2026-10-08 | M-Kiriku-ASR **via API Kiriku** | wolof | mêmes 11 clips, manifeste **v2** `a2eb3c2cb7eb…` (références corrigées) | 11 clips | **26,1 %** (assoupli 21,7 %), **IC95 [11,8 – 48,5 %]** | **9,1 %** |

**Lecture honnête du run du 30/09** (11 vraies voix féminines, locutrices natives) :
- L'intervalle de confiance à 95 % (bootstrap) est **[13,7 % – 57,1 %]** : très large.
  Sur 11 phrases **courtes**, un seul mot raté fait bondir le WER du clip — le point
  estimé n'est donc **pas défendable seul**. On l'annonce avec son IC, jamais nu.
- 6 clips sur 11 sont transcrits à la perfection ; 2 catastrophes tirent la moyenne
  (« dama sibbiru » → « pharmacie birou », « ñàkk bu bari » → « niakoul bou bar »).
- Prochaine mesure : **corpus élargi** (≥ 20 wolof, conditions bruit/téléphone) pour
  un WER stable. Le repère AI Hub est ~16,3 % (studio) ; notre terrain est plus dur.

**Runs du 08/10 via l'API Kiriku** (`experiments/results/asr_20261008_162803.json` = v1,
`asr_20261008_163830.json` = v2) :
- Même modèle annoncé, servi en fp16 ; l'API est **déterministe** (2 passes identiques).
- **Manifeste v2 : références corrigées par écoute humaine** (transcription des vocaux
  WhatsApp par l'équipe) :
  - clip 2 : « ñàkk bu bari » → « ñàkk bu **bar** » (ce qui a été réellement prononcé) ;
  - clip 6 : la référence omettait la 2ᵉ moitié → « sama bët dey lëndem, **sama gis-gis
    dafa leerul** ».
  - « tàng » est conservé (orthographe standard CLAD) ; les variantes d'accent sont
    mesurées par le WER assoupli, pas corrigées dans la référence.
- **WER v2 = 26,1 % [11,8 – 48,5 %]**, CER 9,1 %. Les hypothèses ASR sont identiques à v1 :
  tout l'écart (39,0 → 26,1 %) vient de la **qualité des références**. Leçon : la référence
  compte autant que le modèle ; toute référence doit être *ce qui est dit*, pas le script.
- **Limite à déclarer** : ces corrections ont été faites *après* avoir vu la sortie ASR
  (risque de biais vers l'ASR). Bonne pratique pour la suite : transcription par un
  locuteur natif **sans voir la sortie ASR**, double transcription sur un échantillon.
- Écart avec le run Colab du 30/09 (30,4 %, refs v1) : non interprétable (refs différentes,
  IC qui se recouvrent). On cite **26,1 % [11,8 – 48,5 %], API, refs v2**.
- **Rappel danger** (détecteur tolérant, sorties ASR inchangées) : **9/11 = 82 %**, 8/11 en
  exact, 0 faux positif. Ratés : « dama sibbiru » → « damaski biru » et « dama miir » →
  « dama mire » ; « ñàkk bu bar » → « ñak bou bar » est rattrapé. Les ratés varient d'un
  backend à l'autre → argument du **filet oui/non**. Détecteur **non réglé** sur ces clips.

### Run du 10/10 — manifeste v3 : 19 clips, 3 locutrices, + condition téléphone

Ajout de la **partie B** : 8 questions bénignes en voix réelle (2 nouvelles locutrices
`spk02`, `spk03` ; 4 questions chacune : alimentation, prochaine visite, médicament,
salutation). Une 3ᵉ locutrice a été écartée (réponses non conformes aux consignes).
Condition **téléphone** simulée par ffmpeg (8 kHz, bande 300–3400 Hz) sur les 19 clips.

| Mesure (API Kiriku) | Calme | Téléphone simulé | Fichier |
|---|---|---|---|
| WER (19 clips) | 37,6 % [26,5 – 48,9] | 42,7 % [30,2 – 56,2] | `asr_20261010_070437` / `_070520` |
| **Rappel danger** (11 signes) | **9/11 = 82 %** [52 – 95] | **7/11 = 64 %** [35 – 85] | `securite_20261010_070354` / `_070552` |
| **Fausses alertes** (8 questions bénignes) | **0/8** [0 – 32] | **0/8** [0 – 32] | idem |
| Bonne fiche KB trouvée (4 questions avec fiche) | 1/4 | 1/4 | idem |

IC 95 % : bootstrap (WER), Wilson (proportions).

**Lecture :**
- **Le téléphone dégrade la sécurité du texte libre** (82 % → 64 %). C'est la mesure
  qui justifie l'architecture : sur un vrai appel, la barrière 1 ne suffit pas, le
  **filet oui/non** (barrière 2) est indispensable.
- **0 fausse alerte** sur des questions bénignes réelles, mais seulement 8 énoncés :
  l'IC monte à 32 %. À élargir avant d'annoncer une spécificité.
- **Le WER des clips B est surestimé par l'orthographe des références** : elles sont écrites
  « à la française » (kan, done, khale, docteur, as salam alaykoum), alors que l'ASR sort
  l'orthographe wolof standard (kañ, doon, xale, doktoor, asalaamaalekum). Normaliser les
  références en orthographe CLAD, **par un locuteur natif, sans copier l'ASR**, avant de
  comparer ce WER aux runs précédents.
- **Le classifieur d'intention ne comprend pas encore le wolof** (1/4) : la FAQ n'a que des
  formulations françaises. Repli actuel = « rendez-vous au poste de santé » (sûr mais
  pauvre). Priorité post-challenge : formulations wolof de la FAQ.
- **2 questions sur 8 portent sur un médicament : aucune fiche n'existe.** C'est un sujet à
  risque ; la seule réponse sûre est d'orienter vers l'agent de santé.

## Détection de danger : mesure et architecture de sécurité

Le WER seul ne dit rien du risque **médical**. La vraie question : *un signe de danger
prononcé est-il capté ?* Mesure sur les mêmes 11 clips (le champ qui compte) :

| Barrière | Rappel danger | Faux positifs (jeu bénin) |
|----------|---------------|---------------------------|
| Correspondance **exacte** (v1) | 8/11 = **73 %** | 0 |
| Correspondance **tolérante** (distance d'édition, mots de sens) | 9/11 = **82 %** | 0 |
| **+ dépistage oui/non** (filet, `dialog/screening.py`) | **ferme le résidu** | — |

**Les 3 signes ratés par l'ASR brut** et ce qu'on en fait :

| Dit par la locutrice | Entendu par l'ASR | Récupéré par |
|----------------------|-------------------|--------------|
| damay miir (vertige) | « damar mbir » | correspondance **tolérante** (orthographe proche) |
| ñàkk bu bari (saignement) | « niakoul bou bar » | **dépistage oui/non** (mot perdu par l'ASR) |
| dama sibbiru (fièvre) | « pharmacie birou » | **dépistage oui/non** (mot perdu par l'ASR) |

**Architecture à deux barrières** (décision fondée sur la mesure, pas sur une intuition) :
1. **Texte libre** : la femme parle → ASR → détecteur *tolérant* (rappel 82 %, 0 faux
   positif). Rattrape les erreurs d'orthographe de l'ASR sans escalader à tort.
2. **Filet oui/non** (`dialog/screening.py`) : quand le texte libre ne confirme rien,
   l'IVR pose des questions fermées (« avez-vous de la fièvre ? »). Reconnaître un
   « waaw »/« déedéet » court est **bien plus robuste** que transcrire une phrase :
   même quand l'ASR perd le mot, le oui/non passe. Preuve sur le cas réel #4 : danger
   perdu en texte libre → **rattrapé** par le dépistage.

Règle **recall-first** gravée dans le code : sur une question de danger, seule une
réponse **« non » claire** ferme un signe ; « oui » ou « incertain » → escalade.
On ne joue jamais une vie sur une seule transcription libre.

> Reste [A VALIDER] : les libellés **wolof** des questions oui/non (locuteur natif).
> Le mécanisme est complet et testé (17 tests) ; le texte wolof relève de la
> validation de contenu, pas de l'ingénierie.

## Étape Phase 2 associée
`experiments/01_benchmark_asr.py` mesure le **WER, le CER et le rappel danger réels**
de `M-Kiriku-ASR` sur *notre* corpus terrain (bruité, code-switching), par langue et
condition, avec intervalle de confiance bootstrap. Ne jamais se fier au WER annoncé
du modèle : mesurer sur nos propres données.
