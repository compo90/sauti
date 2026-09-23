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

## Étape Phase 2 associée
`experiments/01_benchmark_asr.py` mesure le **WER et le CER réels** de
`M-Kiriku-ASR` sur *notre* corpus terrain (bruité, code-switching), par langue.
Ne jamais se fier au WER annoncé du modèle : mesurer sur nos propres données.
