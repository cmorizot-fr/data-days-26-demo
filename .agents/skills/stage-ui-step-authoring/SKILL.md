---
name: stage-ui-step-authoring
description: >-
  Ajoute ou met à jour correctement une étape (conversation) ou un échange (turn) de la démo dans
  l'interface scénique stage_ui, à partir de données et de code réellement produits dans le repo.
  À utiliser dès qu'un collègue génère de nouvelles données, de nouveaux modèles dbt, de nouvelles
  tables BigQuery ou de nouveaux Data Products et veut les faire apparaître dans la démo
  (stage_ui/public/demo_config.yaml) : nouvelle étape, nouvelles questions d'arbitrage
  (askQuestions), nouveau code affiché (filesChanged), contrôle visuel, renommage ou renumérotation.
---

# Écrire une étape de démo dans `stage_ui` (`stage-ui-step-authoring`)

Ce skill reprend la méthode suivie pour les Démos 1 et 2 de la Banque Hexagone. Le principe directeur : **l'UI raconte ce qui s'est réellement passé**. Chaque chiffre, chaque fichier et chaque log affiché vient d'une exécution réelle dans le repo ou dans BigQuery.

## 0. Où et quoi modifier (règles non négociables)
- **Source unique** : [`stage_ui/public/demo_config.yaml`](../../../stage_ui/public/demo_config.yaml). Ne jamais coder un scénario en TypeScript (AGENTS.md §4.3).
- **Copie compilée** : répercuter exactement le même contenu dans `stage_ui/dist/demo_config.yaml` (rechargé au `F5`). Recompiler (`npm run build`) **uniquement** si un fichier `stage_ui/src/` change.
- **Schéma** : [`stage_ui/src/types.ts`](../../../stage_ui/src/types.ts) fait foi : `DemoWorkspace` → `DemoScenario` (1 conversation = 1 étape) → `PromptTurn` (1 bouton de prompt).
- **Fins de ligne** : le YAML est en CRLF. Conserver la convention existante.
- **Zéro bordure colorée** dans tout bloc visuel (règle UX globale) : uniquement la luminance de surface et les tons (`tone`).

## 1. Partir du réel (avant d'écrire une ligne de YAML)
1. Exécuter réellement l'étape : générateur, `dbt build`, requêtes `bq`, scripts `scripts/run_*.sh`.
2. Relever les **vrais chiffres** : volumes, tests PASS/FAIL, colonnes documentées (`INFORMATION_SCHEMA.COLUMN_FIELD_PATHS`), invariants d'AGENTS.md §2.
3. Si l'étape crée ou expose quelque chose dans BigQuery, mobiliser le skill [`bq-visual-audit`](../bq-visual-audit/SKILL.md) et `data-agent-kit/render_chart`. Reporter le résultat dans un bloc `visualCheck`.
4. Noter les **décisions réellement prises** pendant le travail (choix de source de vérité, traitement des anomalies, règles métier…). Ce sont elles qui deviennent les `askQuestions`.

> [!IMPORTANT]
> Si un chiffre ne peut pas être vérifié, ne pas l'inventer : laisser la valeur réelle la plus proche et le signaler à l'utilisateur.

## 2. Conventions de nommage et de contenu
| Champ | Convention | Exemple |
|---|---|---|
| `id` conversation | `d<démo>-step<n>` ou suffixe parlant, unique | `d2-step0`, `d1-step-pubsub` |
| `shortName` | **Nom fonctionnel** (bénéfice métier, pas la technologie), numéroté `N. ` en continu dans le workspace | `1. Concevoir les data products` |
| `conversationTitle` | Titre plus complet, peut être technique | `Revue du découpage des Data Products avant la couche SILVER` |
| `id` turn | `d<démo>-t<n>[lettre]`, unique | `d2-t1a` |
| `chipLabel` | Verbe à l'infinitif, numéroté `N. ` en continu dans la conversation | `1. Définir les règles de qualité à mettre en œuvre` |
| `prompt` | Ce que le présentateur demande à l'agent, en français naturel | |
| `askQuestions` | **2 à 3** questions d'arbitrage ; 1re option préfixée `(Recommended) ` ; ≥ 2 options ; options = réponses de l'utilisateur | voir §3 |
| `items` | 2 à 5 blocs « ce qui a été fait / trouvé », bullets factuels avec chiffres réels | |
| `traces` | `analyzed` (skill, doc lue) · `ran` (commande + sortie réelle) · `edited` (fichier + lignes) | |
| `filesChanged` | **Contenu réel** du fichier du repo (voir §4) | |
| `terminalLogs` | 3 à 6 lignes, commandes réellement lancées | |
| `subagents` | Rôle lisible + skill DAK réellement pertinent | `Data Quality Rule Miner` / `data-autocleaning` |

- **Data Products, tables, colonnes, modèles dbt : en anglais** (AGENTS.md §3), conformes au catalogue [`data_products_catalog.yaml`](../../../02_demo2_silver_dbt_dq/kc_products/data_products_catalog.yaml). Textes destinés au public : en français.
- Valeurs autorisées (sinon l'UI casse) :
  - `traces[].icon` et `analyzed/edited` : `sql`, `yml`, `py`, `dak`, `cpy`, `csv`, `mp4`, `md` ;
  - `items[].chips[].kind` : `sql`, `yml`, `py`, `bq`, `kc`, `mp4` ;
  - `filesChanged[].language` : `sql`, `yaml`, `python`, `markdown` ;
  - `tone` : `neutral`, `positive`, `warning`, `ruby`, `blue` ;
  - `subagents[].status` : `completed`, `running`.

## 3. Écrire les questions d'arbitrage (règle d'or AGENTS.md §4.2)
L'agent ne décide jamais en silence face à un piège de données, un choix de schéma ou un risque PII.
- Une question = un vrai dilemme rencontré, formulé avec le **constat chiffré** (« 650 comptes… ne sont pas encore dans le batch J-1. Que fait-on ? »).
- L'option `(Recommended)` est celle qui a réellement été retenue ; les alternatives sont crédibles (elles montrent que l'agent a comparé).
- Les `items` et `leadConfirmation` doivent ensuite refléter l'option recommandée.
- Exemples réalisés : découpage des Data Products, langue des noms, fraîcheur (Démo 2 · étape 1) ; où appliquer les règles DQ, traitement des anomalies, seuils (étape 2) ; double comptage Mainframe ↔ SEPA, comptes orphelins, catégorisation (étape 3).

## 4. Afficher le vrai code (`filesChanged`)
Ne jamais réécrire à la main un code « illustratif ». Générer le bloc depuis le fichier réel :
```bash
uv run --frozen python .agents/skills/stage-ui-step-authoring/scripts/render_file_block.py \
  02_demo2_silver_dbt_dq/models/silver/customer_timeline/customer_movements.sql
```
Le script imprime le bloc `content: |-` correctement indenté (18 espaces) et le nombre de lignes à reporter dans `added`. Pour un extrait (ex. seulement les tests d'un `schema.yml`), utiliser `--until "    columns:"`.

## 5. Modifier le YAML de façon sûre
Procéder par un **script Python ponctuel** (dans le dossier `scratch/` de l'agent), jamais par édition manuelle de gros blocs :
1. Lire le fichier, normaliser `\r\n` → `\n`, mémoriser la fin de ligne d'origine.
2. Repérer un **ancre unique** (`      - id: d2-step1\n` pour insérer une conversation avant une autre, `          - id: d2-t1\n` pour un turn) et `assert s.count(anchor) == 1`.
3. Insérer ou remplacer le bloc, faire les renommages exacts avec `assert s.count(old) == 1`.
4. Appliquer le même script à `public/` **et** `dist/`, puis réécrire avec la fin de ligne d'origine.
5. Ajouter une garde d'idempotence (`assert "id: <nouvel id>" not in s`).

Pièges YAML déjà rencontrés :
- Une valeur non guillemetée contenant `": "` casse le parse (`règles : scan` → mettre entre guillemets ou reformuler).
- Une valeur qui commence par `` ` ``, `"`, `{`, `[`, `*`, `&`, `!`, `%`, `@` ou `?` doit être guillemetée.
- Dans une chaîne entre guillemets doubles, éviter les guillemets doubles internes.
- Insérer une conversation en tête d'un workspace décale la numérotation : renuméroter tous les `shortName` suivants.

## 6. Valider (obligatoire avant de rendre la main)
```bash
node .agents/skills/stage-ui-step-authoring/scripts/check_demo_config.mjs
```
Le validateur vérifie :
- que le YAML est lisible (`public/` et `dist/`) et que les deux copies sont identiques ;
- l'unicité des identifiants et la présence des champs obligatoires ;
- les valeurs autorisées ;
- la numérotation continue des `shortName` et des `chipLabel` ;
- le format des `askQuestions` (2 à 3 questions, `(Recommended)` en tête) ;
- que chaque `filesChanged` pointant vers un fichier du repo affiche bien son contenu réel (sinon `WARN`).

Corriger toute erreur (`ERROR`) ; expliquer ou corriger chaque `WARN`.

## 7. Mettre à jour la documentation
- [`docs/DEMO_QUESTIONS_AND_FLOW.md`](../../../docs/DEMO_QUESTIONS_AND_FLOW.md) : liste des conversations du workspace (nom, questions d'arbitrage, résultat).
- [`DESIGN_AND_CONTEXT.md`](../../../DESIGN_AND_CONTEXT.md) : actions de la démo concernée si le récit change.
- [`AGENTS.md`](../../../AGENTS.md) et le catalogue des Data Products si une convention ou un invariant change.

## Checklist de fin
- [ ] Étape réellement exécutée, chiffres relevés (et `bq-visual-audit` si BigQuery a été touché).
- [ ] `shortName` fonctionnel et numérotation continue ; `chipLabel` numérotés.
- [ ] 2 à 3 `askQuestions` issues de vraies décisions, `(Recommended)` en tête.
- [ ] `filesChanged` générés depuis les vrais fichiers ; traces et logs réels.
- [ ] `public/` et `dist/` identiques ; validateur sans `ERROR`.
- [ ] Docs mises à jour ; aucune bordure colorée ; noms techniques en anglais.
