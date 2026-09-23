# Gate de validation clinique (processus obligatoire)

> Projet destiné à l'échelle nationale, sur des données de santé. Aucun contenu
> ne parle à une utilisatrice réelle sans avoir franchi ce gate. Une réponse
> fausse peut coûter une vie.

## Cycle de vie d'une entrée de la base de connaissances

```
brouillon ──► revue_linguistique ──► valide_clinique ──► (production autorisée)
```

Le champ `validation.statut` de chaque entrée (`data/knowledge_base/`) porte cet état.

| Statut | Qui | Ce qui est vérifié |
|--------|-----|--------------------|
| `brouillon` | rédacteur / data | contenu FR rédigé, structuré, référencé à un protocole. |
| `revue_linguistique` | locuteur natif (wol/ful/srr) | traduction fidèle, registre respectueux, compréhensible à l'oral. |
| `valide_clinique` | sage-femme / médecin | exactitude médicale, cohérence avec PNDS / PEV, absence de risque. |

Chaque passage renseigne `valide_par`, `protocole_ref` et `date`.

## Règles non négociables

1. **Aucune entrée `!= valide_clinique` ne part en production.** La CI le vérifie
   (`scripts/validate_kb.py` compte les entrées non validées).
2. **Base fermée** : le service ne répond que depuis la base validée. Pas de
   génération libre non bornée en production.
3. **Triage danger orienté recall** : en cas de doute, on escalade. Le seuil du
   détecteur de danger est revu avec le référent médical (matrice de confusion).
4. **Red-teaming** (inspiré de Digital Green) : avant chaque montée de version,
   des cas adverses sont soumis au système pour débusquer biais de genre, angles
   morts et réponses dangereuses.
5. **Traçabilité** : toute réponse servie est journalisée (anonymisée) avec l'`id`
   de l'entrée et sa version, pour audit clinique a posteriori.

## Disclaimer utilisateur
Chaque parcours rappelle : « ce service ne remplace pas une consultation ; en cas
de doute, rendez-vous au poste de santé ».
