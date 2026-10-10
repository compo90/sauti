# Sauti — réponses au formulaire de soumission KVICC (10 oct. 2026)

Équipe **Echo Sahel** · Secteur **Santé** · Code : https://github.com/compo90/sauti (public)

## 1. Présentation courte (problème et solution)

**Problème.** Au Sénégal, beaucoup de femmes enceintes ne reconnaissent pas à temps les signes
de danger obstétrical (saignement, convulsions, fièvre forte, maux de tête avec troubles de la
vue, bébé qui ne bouge plus, gonflements). Les services d'information existants supposent de
lire le français ou d'avoir un smartphone et Internet.

**Solution.** Sauti (« la voix » en swahili) est une ligne téléphonique vocale de santé
maternelle en langues nationales. La femme appelle depuis un téléphone simple et parle wolof.
Sauti comprend sa question, **détecte d'abord les signes de danger**, et répond à voix haute en
wolof. En cas de danger, il l'oriente vers le poste de santé et prévient une sage-femme.
La sécurité passe avant la pertinence : dans le doute, Sauti escalade.

## 2. Intégration de Kiriku ASR et TTS

- **M-Kiriku-ASR** (API du challenge, `m-kiriku-asr`, `language=wolof`) transcrit la voix de
  l'appelante. Le texte passe ensuite dans le **triage danger** (détecteur tolérant aux erreurs
  de l'ASR, par distance d'édition), puis dans la base de connaissances.
- **Kiriku-TTS** (`kiriku-tts`, voix `wolof` et `pulaar`) lit la réponse. Textes de plus de
  512 caractères découpés par phrase, puis WAV concaténés. Nombres de plus de 10 écrits en toutes lettres.
- **Filet de sécurité oui/non**, car l'ASR peut mal entendre : après chaque échange, Sauti pose une
  question fermée sur un signe de danger (« ndax dangay ñàkk bu bari ? »). Un « waaw » déclenche
  l'alerte. Exemple réel de la démo : « amna dëret » (je saigne) a été transcrit
  « am na direct » ; le filet l'a rattrapé.
- **Choix par langue** selon la qualité mesurée et annoncée des modèles : en wolof, question libre et TTS ;
  en pulaar, menu guidé et TTS ; en sérère, menu et audio humain enregistré (pas de TTS sérère).
- **Backends** : API Kiriku (par défaut), modèles Hugging Face `AIHubSN/*` en local (souveraineté
  et déploiement après le 16 oct.), mock pour les tests et la CI.

**Résultats mesurés sur nos propres voix** (19 clips wolof, 3 locutrices, API Kiriku) :
- rappel des signes de danger : **82 % (9/11) au calme**, **64 % (7/11) en qualité téléphone
  simulée**, sans compter le filet oui/non ;
- **0 fausse alerte sur 8** questions courantes (petit effectif : intervalle de confiance jusqu'à 32 %) ;
- WER 26 % [12–48 %] sur les phrases de danger.

## 3. Découvrir le prototype

- **Vidéo de démonstration** (3 appels réels en wolof, environ 3 min) : [LIEN VIDÉO]
- **Pitch deck** : EchoSahel_Sauti_Pitch.pdf (joint)
- **Test sans clé, sans GPU, sans réseau** (mode mock) :

```bash
git clone https://github.com/compo90/sauti && cd sauti
python -m venv .venv && source .venv/bin/activate   # Windows : .venv\Scripts\activate
pip install jsonschema pydantic-settings pytest     # dépendances légères du mode mock
export PYTHONPATH="src:."                            # Windows : set PYTHONPATH=src;.
python -m sauti.pipeline --demo "amna dëret" --langue wol         # signe de danger → alerte
python -m sauti.pipeline --demo "lan laa wara lekk" --langue wol  # question courante → conseil en wolof
pytest -q                                                          # 34 tests
```

## 4. Instructions et identifiants

Aucun identifiant n'est nécessaire pour le mode mock. Pour la vraie chaîne vocale, copiez
`.env.example` en `.env`, mettez-y votre clé `KIRIKU_API_KEY` (clé d'équipe du challenge, non
publiée), puis lancez `python scripts/smoke_api.py`.

## 5. Architecture et méthodologie

Flux : `audio → ASR → triage danger → (escalade | dialogue → base de connaissances → TTS) → audio`.

Huit couches :
1. téléphonie (Asterisk et AGI, squelette) ;
2. voix (Kiriku ASR et TTS) ;
3. triage danger (première barrière) ;
4. dépistage oui/non (deuxième barrière) ;
5. base de connaissances (contenu `[A VALIDER]` : rien n'est diffusé sans validation par un soignant) ;
6. escalade vers la sage-femme (squelette) ;
7. mesure : WER et rappel danger avec intervalles de confiance, sur nos propres voix, jamais sur de l'audio TTS ;
8. consentement et protection des données : audios hors dépôt, agrégats seulement, loi 2008-12.

**Limites, dites honnêtement** :
- petit corpus (19 clips) ;
- contenu médical en attente de validation clinique ;
- téléphonie et escalade au stade de squelette.

**Feuille de route** :
- élargir le corpus (5 à 10 locutrices) ;
- valider le contenu avec des sages-femmes ;
- pilote sur un numéro court ;
- héberger les modèles au Sénégal.
