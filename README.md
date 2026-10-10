# Sauti — ligne vocale de santé maternelle en langues nationales

> **Sauti** (« la voix ») est une ligne téléphonique (IVR) pour les femmes enceintes du
> Sénégal. Elle appelle depuis **n'importe quel téléphone**, parle **wolof, pulaar ou
> sérère**, et Sauti l'aide à **reconnaître un signe de danger** et à agir à temps :
> réponse vocale validée, ou alerte et sage-femme prévenue.
>
> Équipe **Echo Sahel** · Kiriku Voice Inclusive & Creative Challenge 2026 · secteur Santé.

## ⚠️ Avertissement clinique
Prototype technique. **Aucun contenu médical n'est encore validé** : tout est marqué
`[A VALIDER]` et doit être revu par un professionnel de santé, selon les protocoles
nationaux, avant tout usage réel. Sauti ne remplace pas une consultation.

## 1. Le problème
Les décès maternels s'expliquent souvent par **trois retards** (Thaddeus & Maine, 1994) :
reconnaître le danger et décider, atteindre le soin, recevoir le soin. Sauti agit sur le
**premier**, un problème d'information. Notre utilisatrice vit loin du poste de santé, a un
téléphone simple sans internet, et ne lit pas forcément le français : les applications et
les SMS l'excluent, la voix non.

## 2. La solution
```
appel → ASR Kiriku → TRIAGE DANGER (barrière 1) ─┬─ danger → message d'urgence + escalade
                                                 └─ sinon → réponse validée (TTS Kiriku)
                                                           → FILET OUI/NON (barrière 2) → escalade si « oui » ou doute
```
- **La sécurité passe avant la pertinence** : le danger est vérifié avant toute réponse.
- **Deux barrières** : détecteur tolérant sur la parole libre, puis questions fermées
  (« waaw » / « déedéet »), beaucoup plus robustes à reconnaître qu'une phrase.
- **Recall-first** : seul un « non » clair rassure ; « oui » ou incertain → sage-femme prévenue.
- **Dégradation gracieuse, jamais de silence** : ASR peu fiable → menu guidé ; pas de voix
  de synthèse → voix humaine enregistrée ; API en panne → repli.

| Langue | Elle s'exprime par | Sauti répond par |
|---|---|---|
| Wolof | question libre (ASR) | synthèse vocale Kiriku — **18 messages traduits par l'équipe** |
| Pulaar | menu guidé | synthèse vocale Kiriku (traductions à produire) |
| Sérère | menu guidé | voix humaine enregistrée (pas de TTS sérère) |

## 3. Architecture (8 couches)
| # | Couche | Code | État |
|---|---|---|---|
| 1 | Téléphonie / IVR (Asterisk, numéro court) | `src/sauti/telephony/` | squelette |
| 2 | Voix : ASR & TTS Kiriku (API du challenge ou local) | `src/sauti/voice/` | fait, mesuré |
| 3 | Triage danger, barrière 1 (détecteur tolérant) | `src/sauti/nlu/danger_detector.py` | fait |
| 4 | Dépistage oui/non, barrière 2 | `src/sauti/dialog/screening.py` | fait |
| 5 | Base de connaissances (31 fiches, 6 signes de danger) | `data/knowledge_base/` | validation clinique en cours |
| 6 | Escalade humaine (sage-femme de garde) | `src/sauti/escalation/` | squelette |
| 7 | Données & mesure (WER, rappel danger, IC) | `experiments/` | fait |
| 8 | Consentement & protection des données (CDP) | transversal | principes appliqués |

Messages par langue avec repli tracé (`langue_servie`), marqueur `[A VALIDER]` jamais
prononcé, mode mock partout (CI sans modèle ni réseau), 34 tests automatisés.

## 4. Résultats mesurés (sur nos voix, pas en studio)
19 enregistrements wolof, 3 locutrices natives, API Kiriku (M-Kiriku-ASR). Protocole et
fichiers de résultats : [`experiments/`](experiments/) et
[`docs/modeles_kiriku.md`](docs/modeles_kiriku.md).

| Mesure | Calme | Téléphone simulé (8 kHz) |
|---|---|---|
| **Signes de danger captés** (barrière 1 seule) | **82 %** (9/11) | **64 %** (7/11) |
| **Fausses alertes** sur des questions courantes | **0/8** | **0/8** |
| WER, phrases de danger | 26 % [IC 95 % : 12–48] | — |

**Lecture** : au téléphone, la reconnaissance vocale laisse passer 4 signes de danger sur 11.
C'est la mesure qui justifie la barrière 2. Démontré en conditions réelles : « amna dëret »
(je saigne) a été transcrit « am na direct » ; le filet oui/non l'a rattrapé.

## 5. Limites (transparence)
- **Petit échantillon** (19 enregistrements, 3 voix) : intervalles de confiance larges.
- **Questions en wolof encore mal comprises** (1 sur 4 trouve la bonne fiche) : classifieur
  lexical ; repli sûr vers le poste de santé.
- **Contenu médical non validé** ; traductions wolof à faire relire par un soignant.
- **Téléphonie et escalade** au stade de squelette (journal d'escalade, pas d'appel réel).
- **Voix de synthèse non vérifiée lettre par lettre** : le TTS ignore sans prévenir les
  caractères hors de son alphabet ; écoute de contrôle par un locuteur natif.
- **API du challenge** disponible jusqu'au 16 octobre 2026 ; les modèles Kiriku sont ouverts
  et peuvent être hébergés au Sénégal (backend `local`).

## 6. Lancer le projet
```bash
python -m venv .venv && source .venv/Scripts/activate     # Windows Git Bash
pip install -r requirements.txt
cp .env.example .env              # KIRIKU_API_KEY (clé d'équipe), jamais commitée
export PYTHONPATH="src;."         # Windows ; "src:." sous Linux/macOS

pytest -q                                          # 34 tests, sans réseau
python scripts/validate_kb.py                      # schéma de la base
python -m sauti.pipeline --demo "amna dëret" --langue wol   # logique en mode mock
python scripts/smoke_api.py                        # connexion à l'API Kiriku
python scripts/demo_appel.py --nom essai --question q.ogg --oui-non oui.ogg --jouer
python experiments/01_benchmark_asr.py             # WER + IC (jeu de test privé)
python experiments/02_eval_securite.py             # rappel danger, fausses alertes
```

## 7. Sources, modèles et licences
| Ressource | Usage | Licence / conditions |
|---|---|---|
| `AIHubSN/M-Kiriku-ASR` (Whisper large-v3 fine-tuné, AI Hub Senegal) | ASR wolof, pulaar, sérère | Apache-2.0, accès conditionnel (gated) |
| Kiriku TTS (VITS, via l'API du challenge ; checkpoints `AIHubSN/Kiriku-*-TTS`) | synthèse wolof, pulaar | selon la carte de chaque modèle |
| API d'inférence Kiriku (AI Hub Senegal, RunPod) | ASR/TTS pendant le challenge | conditions du challenge |
| Coqui TTS, transformers, pydantic, requests, jiwer | code | licences open source respectives |
| Jeu de test : enregistrements de locutrices volontaires | évaluation | **sous consentement, jamais publié** |

Licence du code Sauti : à définir selon le règlement final du challenge.

## 8. Données personnelles
Données de santé = catégorie sensible (loi sénégalaise 2008-12, CDP). Les audios et
transcriptions du jeu de test restent **hors du dépôt** (stockage d'équipe à accès
restreint) ; seuls des agrégats chiffrés sont publiés, chacun relié à la version exacte
du jeu de test par son empreinte (`manifest_sha256`). Politique complète :
[`experiments/README.md`](experiments/README.md).

## 9. Équipe Echo Sahel
| Membre | Rôle | Contributions |
|---|---|---|
| **Aboubacar Compo** | Chef de projet · Data & IA | architecture, couche voix et API Kiriku, triage et filet de sécurité, protocole d'évaluation et collecte des voix, traductions wolof |
| **Abdoul Karim Diallo** | Développement web | [à préciser] |
| **Kadi Ndiaye** | Développement web & IA | [à préciser] |

Merci aux femmes qui ont prêté leur voix, et à AI Hub Senegal pour les modèles Kiriku.
Inspirations : Kilkari (Inde), PROMPTS / Jacaranda (Kenya), Viamo 3-2-1 (Afrique de l'Ouest).
