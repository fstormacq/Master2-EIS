# Roadmap — Projet INFOM218 : reverse engineering d'ADempiere

**Groupe 4** : Louca Mathieu (porte-parole), Nathan Lambrechts, Florian Stormacq

| | |
|---|---|
| Application | [ADempiere](https://github.com/adempiere/adempiere), branche `develop` |
| Commit analysé | `4ae098fd18065f1a658ff56de3b90e63aabfecb2` |
| Sous-ensemble | Gestion des immobilisations : 22 tables, validé le 2 novembre 2026 |
| Exigence du prof | Pour chaque table retenue, indiquer d'où elle provient (code source, migrations…) et décrire une démarche **reproductible** |

---

## Sommaire

- [Jalons](#jalons)
- [Phase 0 : mise en place](#phase-0--mise-en-place)
- [Étape 1 : schémas PS, LS, CS et clés étrangères](#étape-1--schémas-ps-ls-cs-et-clés-étrangères)
- [Étape 2 : localiser et analyser les accès à la base](#étape-2--localiser-et-analyser-les-accès-à-la-base)
- [Étape 3 : analyse what-if](#étape-3--analyse-what-if)
- [Étape 4 : évaluation de la qualité](#étape-4--évaluation-de-la-qualité)
- [Bonus](#bonus)
- [Livrables finaux](#livrables-finaux)
- [Répartition proposée](#répartition-proposée)
- [Pièges connus](#pièges-connus)

---

## Jalons

| Date | Jalon | Objectif du groupe |
|---|---|---|
| 24 novembre 2026 | **Checkpoint** | Étape 1 bien avancée, SQLInspect opérationnel, blocages identifiés |
| Fin novembre | — | Étape 1 terminée, étape 2 entamée |
| Mi-décembre | — | Étapes 2 et 3 terminées |
| Fin décembre | — | Étape 4, bonus, rédaction du rapport |
| Janvier 2027 (date à confirmer) | **Oral et remise** | Rapport PDF et lien de la repo envoyés à `maxime.derycke@unamur.be`, objet `INFOM218 project report - group 4` |

> La note du cours compte pour 40 % le projet et 60 % l'oral individuel, avec un minimum de 10/20 à l'oral. Chaque membre doit maîtriser **toutes** les étapes.

---

## Phase 0 : mise en place

- [x] Créer la repo et figer ADempiere comme submodule sur `4ae098f`
- [x] Mettre en place l'arborescence :

```
database-scope/
  studied-tables.txt         # les 22 tables, regroupées par sous-domaine

tools/                       # scripts d'extraction, d'inférence, de statistiques…

01-schema-reconstruction/
  physical-schema/           # schéma physique
  foreign-key-inference/     # inférence des FK, precision/recall
  logical-schema/            # schéma logique
  conceptual-schema/         # schéma conceptuel

02-access-analysis/
  sqlinspect-results/
    raw/                     # sorties brutes de SQLInspect
    filtered/                # sorties restreintes aux 22 tables
  other-accesses/            # accès non vus par SQLInspect (ORM PO, API Query, helpers JDBC…)
  statistics/                # statistiques et graphiques
  logical-subschema/         # schéma logique utilisé (LSS)

03-what-if-analysis/         # un fichier par scénario

04-quality-assessment/       # mérites, défauts et recommandations (schéma et code d'accès)

bonus-version-evolution/     # bonus A : comparaison entre trois versions d'ADempiere

report/                      # sources du rapport PDF et des slides

target/                      # code source d'ADempiere (submodule, lecture seule)
workspace/                   # workspace Eclipse pour SQLInspect (ignoré par Git)
```

- [ ] Un `README.md` par dossier : ce qu'il contient, et la commande pour le régénérer
- [ ] Convenir des conventions : noms de tables en MAJUSCULES, CSV séparés par `,`, encodage UTF-8
- [ ] Installer les outils : Python 3, `cloc`, Docker (pour SQLInspect), DB-Main ou un outil de diagramme, éventuellement PostgreSQL via Docker

---

## Étape 1 : schémas PS, LS, CS et clés étrangères

> Cours de référence : 1 (*Introduction to DBRE*) et 5 (*Foreign Key Conceptualization*)

### 1.1 Présenter l'application

- [ ] Décrire ADempiere en un paragraphe : un ERP open source, issu d'un fork de Compiere
- [ ] Mesurer la taille du code : `cloc target/`, avec un tableau par langage
- [ ] Décrire la structure : modules `base/`, `org.adempiere.asset/`, `client/`, `zkwebui/`, `migration/`, `db/`, `data/`…
- [ ] Expliquer le fonctionnement du **dictionnaire applicatif** :
  - `AD_Table` et `AD_Column` décrivent le schéma ;
  - les classes `X_*` et `I_*` sont générées à partir de ce dictionnaire, dans `base/src/org/adempiere/core/domains/models/` ;
  - les classes `M*` contiennent la logique métier.
- [ ] Situer le domaine des immobilisations : quels modules et quels packages le concernent ?

### 1.2 Identifier la source du schéma physique

- [ ] Inventorier les sources candidates :
  - `db/ddlutils/model/*.xml`, avec un fichier par table ;
  - `db/database/Create/Adempiere.sql` ;
  - `data/seed/Adempiere_pg.jar`, qui contient un dump `pg_dump` ;
  - les scripts de `migration/` ;
  - les interfaces `I_A_*.java`.
- [ ] Pour chacune des 22 tables, vérifier si chaque source la contient
- [ ] Comparer le nombre de colonnes entre les sources et les interfaces Java
- [ ] Choisir une source de référence et **justifier** ce choix
- [ ] Documenter l'origine de chaque table : définition initiale, migrations qui la créent ou la modifient
- [ ] Documenter les écarts entre sources : c'est une observation précieuse pour l'étape 4

**Livrable :** un tableau `table → source(s) → migrations` dans `01-schema-reconstruction/physical-schema/README.md`

### 1.3 Extraire le schéma physique (PS)

- [ ] Écrire un script `tools/…` qui extrait, pour les 22 tables :
  - tables et colonnes (type, nullabilité, valeur par défaut) ;
  - clés primaires et contraintes `UNIQUE` ;
  - contraintes `CHECK` ;
  - index ;
  - FK déclarées.
- [ ] Produire les fichiers `columns.csv`, `primary_keys.csv`, `foreign_keys.csv`, `indexes.csv` et `ps.sql`
- [ ] Rédiger une brève description du PS : nombre de tables, de colonnes et de FK (internes et externes au sous-ensemble), types utilisés, conventions de nommage
- [ ] Mettre de côté `foreign_keys.csv` : c'est la **vérité terrain** pour la section 1.4

### 1.4 Inférer les clés étrangères

Le schéma déclare des FK explicites. Il faut donc :
1. évaluer dans quelle mesure on peut les **retrouver** en faisant comme si elles n'existaient pas ;
2. découvrir les FK **implicites**.

- [ ] **Heuristique H1, par le nom** : une colonne `X_ID` est candidate vers la PK de la table `X`
  - [ ] Gérer les cas particuliers : préfixes, alias comme `A_Parent_Asset_ID`, colonnes `*_Acct`, auto-références
- [ ] **Heuristique H2, par le type** : la colonne doit avoir le même type que la PK cible
- [ ] **Heuristique H3, par les requêtes** : extraire les conditions de jointure (`a.col = b.col`) du SQL trouvé à l'étape 2
- [ ] **Heuristique H4, par le dictionnaire** : `AD_Column.AD_Reference_ID` ∈ {Table, TableDir, Search} combiné à `AD_Reference_Value_ID`. Ces données sont dans le dump seed.
- [ ] Pour chaque heuristique, puis pour leurs combinaisons, calculer :
  - **Precision** = FK correctement inférées / FK inférées
  - **Recall** = FK correctement inférées / FK déclarées
- [ ] Analyser les faux positifs et faux négatifs : pourquoi l'heuristique se trompe-t-elle ?
- [ ] Lister les **FK implicites**, c'est-à-dire inférées avec confiance mais non déclarées. Pistes à examiner :
  - [ ] les tables `A_ASSET_INFO_*` → `A_ASSET` ;
  - [ ] `AD_CLIENT_ID` et `AD_ORG_ID`, présentes dans toutes les tables ;
  - [ ] les colonnes `*_ID` sans contrainte.
- [ ] Ajouter les FK implicites au schéma enrichi

**Livrables :** `01-schema-reconstruction/foreign-key-inference/` (script, candidats, matrice de confusion, tableau precision/recall, liste des FK implicites)

### 1.5 Schéma logique (LS)

- [ ] Partir du PS, ajouter les FK implicites et les identifiants secondaires
- [ ] Repérer les colonnes « techniques » communes à toutes les tables (`AD_Client_ID`, `AD_Org_ID`, `IsActive`, `Created`, `CreatedBy`, `Updated`, `UpdatedBy`, `UUID`) et décider comment les représenter
- [ ] Enrichir avec ce que révèle le code : domaines de valeurs (listes de référence), contraintes métier dans les classes `M*`
- [ ] Dessiner le LS en notation GER (DB-Main) ou à défaut avec un outil équivalent, et exporter en PNG/SVG

### 1.6 Schéma conceptuel (CS)

- [ ] Abstraire le LS en entités, relations et attributs :
  - remplacer les FK par des types de relations ;
  - identifier les relations 1-1, par exemple entre `ASSET` et chaque fiche `INFO_*` ;
  - repérer les sous-types possibles ;
  - traiter les tables `_ACCT` (une ligne par schéma comptable) ;
  - séparer ce qui relève de la classification, des mouvements et de l'amortissement.
- [ ] Documenter chaque décision d'abstraction (transformation appliquée et justification)
- [ ] Dessiner le CS

**Livrables de l'étape 1 :** description de l'application, PS, analyse des FK, LS, CS

> **Pour le checkpoint :** sections 1.1 à 1.4 terminées, brouillons du LS et du CS.

---

## Étape 2 : localiser et analyser les accès à la base

> Cours de référence : 2 (*Dynamic Analysis for DBRE*) et la présentation de SQLInspect

### 2.1 SQLInspect

- [ ] **À commencer immédiatement** : c'est le poste le plus susceptible de bloquer
- [x] Installer SQLInspect en ligne de commande : image Docker `linux/amd64` (`docker/sqlinspect/`, wrapper `tools/sqlinspect/sqlinspect.sh`), portable Linux / macOS (ARM émulé) / Windows
- [ ] Le lancer sur `target/`, en commençant par les modules pertinents : `base/`, `org.adempiere.asset/`
- [ ] Filtrer les résultats sur les requêtes qui touchent les 22 tables
- [ ] Sauvegarder les sorties brutes dans `02-access-analysis/sqlinspect-results/raw/`
- [ ] Documenter la commande exacte, la version de l'outil et les éventuels problèmes rencontrés (fait pour `org.adempiere.asset` : `tools/sqlinspect/run_sqlinspect_*.sh`, README de `raw/`)

### 2.2 Accès non détectés par SQLInspect

ADempiere passe majoritairement par des mécanismes que SQLInspect ne voit pas ou voit mal. Les recenser un par un :

- [ ] **ORM `PO`** : constructeurs `new MAsset(ctx, id, trxName)`, `save()`, `saveEx()`, `delete()`, setters et getters des classes `X_A_*`
- [ ] **API `Query`** : `new Query(ctx, I_A_Asset.Table_Name, whereClause, trxName)`. Seule la clause WHERE est du SQL ; la table est passée en paramètre.
- [ ] **Helpers JDBC** : `DB.getSQLValue*`, `DB.executeUpdate*`, `DB.prepareStatement`, `DB.getKeyNamePairs`…
- [ ] **SQL dynamique** : construit par concaténation ou `StringBuilder` dans le code Java
- [ ] **Hors Java** : vues SQL (`db/database/Create/Views.sql`), rapports Jasper, processus définis dans le dictionnaire

Pour chaque mécanisme :
- [ ] écrire un script de détection (regex, ou parseur comme JavaParser) qui produit le fichier, la ligne de début, la ligne de fin, les tables et les colonnes ;
- [ ] vérifier un échantillon à la main pour estimer la fiabilité du script.

### 2.3 Inventaire structuré des accès

- [ ] Définir un format commun, CSV ou JSON, par exemple :

| Champ | Exemple |
|---|---|
| `file` | `base/src/org/compiere/model/MAsset.java` |
| `start_line` / `end_line` | `412` / `418` |
| `mechanism` | `SQL` / `QUERY_API` / `PO` / `JDBC_HELPER` |
| `operation` | `SELECT` / `INSERT` / `UPDATE` / `DELETE` |
| `tables` | `A_ASSET;A_ASSET_GROUP` |
| `columns` | `A_ASSET.A_ASSET_ID;…` |
| `detected_by` | `SQLInspect` / `script:<nom>` / `manual` / `LLM` |

- [ ] Créer **deux fichiers séparés**, comme exigé par l'énoncé :
  - `accesses_sqlinspect.csv`
  - `accesses_other.csv`
- [ ] Dédupliquer les accès communs aux deux sources et documenter la règle appliquée

### 2.4 Statistiques commentées

- [ ] Répartition par type d'opération (SELECT, INSERT, UPDATE, DELETE…)
- [ ] Répartition par mécanisme (SQL brut vs ORM vs API Query)
- [ ] Répartition dans le code : par module, par package, par classe
- [ ] Tables et colonnes les plus accédées
- [ ] Complexité des requêtes : nombre de jointures, sous-requêtes, agrégats, requêtes dynamiques
- [ ] Graphiques, avec un **commentaire pour chacun** : que révèle-t-il du système ?
- [ ] Comparer SQLInspect aux autres méthodes : qu'est-ce que chacune détecte ou rate ?

### 2.5 Schéma logique utilisé (LSS)

- [ ] Fixer la règle « une colonne est utilisée si… » (un getter ou setter de `X_A_*` appelé suffit-il ?) et la justifier
- [ ] Retirer du LS les tables et colonnes jamais accédées
- [ ] Produire le LSS sous forme de diagramme, avec la liste des éléments retirés
- [ ] Chiffrer la proportion du LS réellement utilisée

### 2.6 Usage d'un LLM (facultatif)

- [ ] Documenter le modèle, les prompts et les dates d'exécution
- [ ] Vérifier **chaque** résultat dans le code source
- [ ] Comparer plusieurs exécutions et noter les divergences

**Livrables de l'étape 2 :** processus et outils documentés, deux inventaires structurés, statistiques commentées, LSS

---

## Étape 3 : analyse what-if

> Cours de référence : 6 (*Data-Intensive System Evolution using Transformation*) pour les co-transformations et la classification S+ / S- / S=

### 3.1 Préparation

- [ ] Écrire un outil d'**analyse d'impact** : à partir d'une table ou d'une colonne, il retrouve tous les accès dans l'inventaire de l'étape 2
- [ ] Définir un gabarit commun, `03-what-if-analysis/TEMPLATE.md`

### 3.2 Scénarios (au moins 10, variés)

- [ ] S01 : renommer une table
- [ ] S02 : renommer une colonne très utilisée (par exemple `A_ASSET.A_ASSET_GROUP_ID`)
- [ ] S03 : supprimer une colonne
- [ ] S04 : ajouter une colonne `NOT NULL`
- [ ] S05 : changer le type d'une colonne (précision numérique, longueur de `varchar`)
- [ ] S06 : fusionner les tables `A_ASSET_INFO_*`, entre elles ou dans `A_ASSET`
- [ ] S07 : découper une table (par exemple séparer la localisation de `A_ASSET`)
- [ ] S08 : transformer une relation 1-N en N-N (table de liaison)
- [ ] S09 : supprimer une table (par exemple `A_ASSET_TYPE`)
- [ ] S10 : déclarer une FK implicite, ou rendre une colonne obligatoire
- [ ] (optionnel) S11 et suivants : déplacer une colonne, modifier une PK…

### 3.3 Contenu de chaque scénario

- [ ] Description précise de la modification (DDL avant et après)
- [ ] Classe sémantique : S+, S- ou S=
- [ ] Impact sur les données : migration nécessaire, perte d'information éventuelle
- [ ] **Impact sur le code** : liste des fichiers, classes, méthodes et lignes concernés, issue de l'inventaire
- [ ] Impact sur les artefacts générés et le dictionnaire : `X_*`, `I_*`, `AD_Column`, migrations, vues
- [ ] Adaptations nécessaires pour garder la cohérence, si c'est possible
- [ ] Possibilité d'automatiser la propagation (co-transformation)

**Livrable de l'étape 3 :** un fichier par scénario, plus un tableau récapitulatif (scénario, classe, nombre de fichiers et de lignes impactés, difficulté)

---

## Étape 4 : évaluation de la qualité

Chaque constat doit s'appuyer sur une **preuve** tirée des étapes 1 à 3 (chiffre, exemple de code, scénario).

### 4.1 Schéma de la base

- [ ] Mérites : conventions de nommage, PK systématiques, FK en grande partie déclarées…
- [ ] Inconvénients, pistes à vérifier :
  - FK manquantes ;
  - colonnes techniques dupliquées dans toutes les tables ;
  - redondances (par exemple entre `A_ASSET_ACCT` et `A_ASSET_GROUP_ACCT`) ;
  - types peu précis ;
  - colonnes jamais utilisées (d'après le LSS) ;
  - incohérences entre les sources du schéma.

### 4.2 Code d'accès à la base

- [ ] Mérites : ORM générée, API Query…
- [ ] Inconvénients, pistes à vérifier :
  - mélange de mécanismes d'accès ;
  - SQL concaténé (maintenance, risque d'injection) ;
  - dispersion des accès ;
  - couplage fort avec les noms de colonnes ;
  - coût d'évolution révélé par l'étape 3.

### 4.3 Recommandations

- [ ] Au moins une recommandation **concrète** par type d'inconvénient
- [ ] Les classer par priorité, selon l'effort et le gain

**Livrable de l'étape 4 :** liste documentée des mérites, des inconvénients et des recommandations

---

## Bonus

### Bonus A : évolution entre versions

> Cours de référence : 3 (*Analyzing Data-Intensive System Evolution*)

- [ ] Choisir 3 versions : une ancienne (3.5.x), une intermédiaire (3.8 LTS), et la version actuelle (`4ae098f`)
- [ ] Extraire le schéma des 22 tables pour chaque version (les dossiers `migration/` donnent les deltas)
- [ ] Comparer les tables et colonnes ajoutées, supprimées ou modifiées, et l'évolution des FK
- [ ] Comparer éventuellement les requêtes (étape 2 relancée sur les anciennes versions)
- [ ] Commenter l'évolution de la qualité, avec des illustrations (graphiques, diagrammes avant/après)

### Bonus B : autre périmètre

- [ ] Uniquement si l'équipe enseignante le demande : refaire l'étape 2 sur un autre projet ou un périmètre plus large

---

## Livrables finaux

### Repo GitHub (publique, documentée)

- [ ] `README.md` principal : présentation, version analysée, plan de la repo, comment tout régénérer
- [ ] Tous les artefacts des étapes 1 à 4 (et des bonus)
- [ ] Documentation des outils et de l'usage des LLM
- [ ] Repo **publique** et accessible à l'équipe enseignante

### Rapport PDF (concis)

- [ ] Méthodologie détaillée pour chaque étape
- [ ] Synthèse des résultats, avec **renvoi systématique** vers les fichiers de la repo
- [ ] Origine de chaque table et démarche reproductible (exigence du prof)
- [ ] Commit analysé indiqué clairement

### Présentation orale

- [ ] Slides pour 15 minutes, questions comprises
- [ ] Chaque membre prépare son oral individuel de 15 minutes sur **l'ensemble** du projet

---

## Répartition proposée

| Période | Personne A | Personne B | Personne C |
|---|---|---|---|
| → 24/11 | 1.1, 1.2, 1.3 | 2.1 (SQLInspect) | 1.4 (H1, H2, H4) |
| Fin novembre | 1.5, 1.6 | 2.2 | 1.4 (H3), précision et recall |
| Début décembre | 2.4 | 2.3, 2.5 | 3.1, scénarios S01 à S05 |
| Mi-décembre | Bonus A | Scénarios S06 à S10 | Étape 4 |
| Fin décembre | Rapport | README et relecture | Slides |
| Janvier | Révision commune de toutes les étapes pour l'oral | | |

---

## Pièges connus

- **Le schéma n'a pas de source unique fiable** : vérifiez toujours en recoupant avec les interfaces `I_*.java`.
- **SQLInspect ne verra qu'une partie des accès**, à cause de l'ORM et de l'API Query. C'est attendu : le travail de l'étape 2.2 consiste justement à compléter.
- **Le SQL dynamique** rend la détection des tables et colonnes approximative. Documentez les limites.
- **Les tables `_ACCT`** et les colonnes `*_Acct` référencent des combinaisons comptables (`C_ValidCombination`), pas une table du même nom : attention à l'heuristique H1.
- **Une table hors sous-ensemble** peut être la cible d'une FK : distinguez les FK internes et externes dans les chiffres.
- **Reproductibilité** : chaque fichier généré doit pouvoir être reproduit par une commande documentée.
