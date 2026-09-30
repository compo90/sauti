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

**Lecture honnête du run du 30/09** (11 vraies voix féminines, locutrices natives) :
- L'intervalle de confiance à 95 % (bootstrap) est **[13,7 % – 57,1 %]** : très large.
  Sur 11 phrases **courtes**, un seul mot raté fait bondir le WER du clip — le point
  estimé n'est donc **pas défendable seul**. On l'annonce avec son IC, jamais nu.
- 6 clips sur 11 sont transcrits à la perfection ; 2 catastrophes tirent la moyenne
  (« dama sibbiru » → « pharmacie birou », « ñàkk bu bari » → « niakoul bou bar »).
- Prochaine mesure : **corpus élargi** (≥ 20 wolof, conditions bruit/téléphone) pour
  un WER stable. Le repère AI Hub est ~16,3 % (studio) ; notre terrain est plus dur.

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
