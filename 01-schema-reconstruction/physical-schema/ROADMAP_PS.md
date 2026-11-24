# Roadmap : extraction du schéma physique (étape 1.3)

Plan de travail détaillé pour la section [1.3 du ROADMAP général](../../ROADMAP.md#13-extraire-le-schéma-physique-ps). Le code est écrit par Florian. Claude a servi de guide et de relecteur (voir [`AI_USAGE.md`](../../AI_USAGE.md)).

Prérequis, déjà fait (étape 1.2) : la source du PS est le dump `target/data/seed/Adempiere_pg.jar`, et aucune migration n'est à appliquer. Voir la section *Source of the physical schema* du [README](README.md) et la section 1.2 de [`REPRODUCE.md`](../../REPRODUCE.md#12-source-of-the-physical-schema).

---

## Livrables

| Fichier | Contenu |
|---|---|
| `tools/physical_schema/restore_dump.sh` | Étape A : conteneur PostgreSQL 15 + restauration du dump |
| `tools/physical_schema/extract_ps.py` | Étapes B à D : catalogue → CSV + DDL |
| `columns.csv` | Une ligne par colonne |
| `primary_keys.csv` | PK, contraintes `UNIQUE` et unique index (colonne `kind`) |
| `foreign_keys.csv` | Les 96 FK, colonne `internal` (vérité terrain pour l'étape 1.4) |
| `indexes.csv` | Index |
| `check_constraints.csv` | Contraintes `CHECK` |
| `ps_dbmain.sql` | DDL en SQL standard, importable dans DB-Main (*File → Extract → SQL*) |
| `ps_dbmain_nofk.sql` | Même DDL sans FK, pour l'inférence de FK « à l'aveugle » (precision/recall) |
| `ps_dbmain_test_a_asset.sql` | Fichier de test d'une table, à faire valider par Nathan avant de tout générer |

Ces livrables remplacent le `ps.sql` prévu dans le ROADMAP général : à mettre à jour là-bas une fois terminé.

## Décisions à prendre

- [ ] **Dossier de sortie** : `01-schema-reconstruction/physical-schema/` (dossier existant, recommandé) ou `step1-schemas/ps/` (nom utilisé dans le prompt d'origine).
- [ ] **Accès à PostgreSQL depuis Python** : `psql --csv` via `subprocess` (recommandé, le repo n'utilise que la bibliothèque standard) ou `psycopg` ajouté avec `uv add` (il faut alors exposer un port).
- [ ] **Nom du conteneur** : garder `ps-check` (cohérent avec REPRODUCE 1.2) ou un nom dédié, et aligner les deux documents.
- [ ] **`indexes.csv`** : avec les 22 index des PK (23 lignes) ou sans (1 ligne).
- [ ] **CHECK dans le DDL** : réécrits en `IN ('Y','N')` ou supprimés, selon le retour de Nathan sur le fichier de test.
- [ ] **FK externes (étape D)** : tables stub ou CSV séparé. À décider **avec Nathan**, car ça change sa métrique.

## Valeurs attendues (oracle)

Relevées dans le DDL du dump le 24.11.2026. Le script doit les retrouver **à partir du catalogue**.

| Élément | Attendu |
|---|---|
| Tables | 22 sur 1 177 dans le schéma `adempiere` |
| Colonnes | 704 (710 constantes `COLUMNNAME_*` moins 6 colonnes virtuelles) |
| PK | 22, toutes sur une seule colonne `<TABLE>_ID` |
| Contraintes `UNIQUE` | 0 |
| Unique index | 1 : `a_asset_value` sur `A_ASSET(AD_CLIENT_ID, VALUE)` |
| Autres index | 0 |
| FK | 96 : 36 internes, 60 externes vers 32 tables distinctes |
| Détail des FK | 0 multi-colonnes, 1 auto-référence (`A_ASSET.A_PARENT_ASSET_ID → A_ASSET`), toutes `DEFERRABLE INITIALLY DEFERRED`, 3 en `ON DELETE CASCADE` |
| CHECK | 57, toutes de la forme `col = ANY (ARRAY['Y'::bpchar, 'N'::bpchar])` |
| Types | `numeric(10,0)` ×300, `character varying(n)` ×160, `character(n)` ×85, `numeric` sans précision ×81, `timestamp without time zone` ×78 |
| DEFAULT | Avec des casts : `NULL::numeric`, `(0)::numeric`, `'N'::bpchar`… et `now()` |

---

## A. Restaurer le dump

**À écrire** : `restore_dump.sh`, idempotent (s'il trouve le conteneur avec le schéma restauré, il ne refait rien, ce qui évite 5 min à chaque relance).

- [ ] Extraire le dump : `unzip -p target/data/seed/Adempiere_pg.jar Adempiere_pg.dmp > workspace/ps/dump.sql`
- [ ] `docker run -d --name <nom> -e POSTGRES_PASSWORD=… -e POSTGRES_DB=adempiere -v …/dump.sql:/dump.sql:ro postgres:15`
- [ ] Attendre que le **vrai** serveur soit prêt
- [ ] `CREATE ROLE adempiere`
- [ ] `psql -v ON_ERROR_STOP=1 -f /dump.sql`
- [ ] Si le schéma existe déjà, ne rien refaire

**Pièges**

- Sans nom d'entrée, `unzip -p` écrit `META-INF/MANIFEST.MF` devant le dump (`syntax error at or near "Manifest"`).
- `pg_isready` peut répondre OK pendant le serveur temporaire d'initialisation de l'image. Attendre la ligne `PostgreSQL init process complete` dans `docker logs`, puis `pg_isready`.
- Sans `ON_ERROR_STOP=1`, `psql` continue après une erreur et renvoie 0.
- Le dump fait des `GRANT … TO adempiere` : le rôle doit exister avant.
- `postgres:15` est un tag mobile : noter le digest dans REPRODUCE.

**Test**

- [ ] Code retour 0, et 0 `ERROR` dans le log
- [ ] Une seconde exécution ne refait pas la restauration
- [ ] `SELECT count(*) FROM information_schema.tables WHERE table_schema='adempiere'` renvoie 1177

## B. Extraire depuis le catalogue

**À écrire** : dans `extract_ps.py`, une fonction par CSV. Chaque requête a un `ORDER BY` explicite, et l'écriture se fait avec `csv.writer(lineterminator="\n")` pour avoir des fichiers identiques d'une exécution à l'autre.

**Règle absolue** : jamais de regex sur le dump. Les blocs COPY contiennent des chaînes DDL qui donneraient des faux positifs.

- [ ] Lire `database-scope/studied-tables.txt`, en ignorant les commentaires (même logique que `read_table_names` dans `scan_migrations.py`)
- [ ] Vérifier que les 22 tables existent. Si une manque, **arrêter le script** en la nommant (attention, les noms sont en minuscules dans le catalogue)
- [ ] `columns.csv` depuis `information_schema.columns` : `ordinal_position`, `data_type`, `character_maximum_length`, `numeric_precision`, `numeric_scale`, `is_nullable`, `column_default`
- [ ] `primary_keys.csv` depuis `pg_constraint` (`contype` `p` et `u`) **plus** les unique index de `pg_index`, avec une colonne `kind`
- [ ] `foreign_keys.csv` depuis `pg_constraint` (`contype='f'`), avec `conkey`/`confkey` dépliés en gardant leur position, et les colonnes `internal`, `on_delete` (`confdeltype`) et `deferrable` (`condeferrable`)
- [ ] `check_constraints.csv` avec `pg_get_constraintdef(oid)`
- [ ] `indexes.csv` depuis `pg_index` (`indkey`, `indisunique`, `indisprimary`)

Principe pour garder l'ordre des colonnes d'une contrainte :

```sql
CROSS JOIN LATERAL unnest(c.conkey, c.confkey) WITH ORDINALITY AS k(attnum, ref_attnum, pos)
JOIN pg_attribute a  ON a.attrelid  = c.conrelid  AND a.attnum  = k.attnum
JOIN pg_attribute fa ON fa.attrelid = c.confrelid AND fa.attnum = k.ref_attnum
-- ORDER BY …, k.pos
```

Pour les PK, `confkey` vaut NULL : déplier seulement `conkey`.

**Pièges**

- Pour un `numeric` sans précision (81 colonnes), `numeric_precision` vaut NULL.
- Il n'y a aucune contrainte `UNIQUE`, mais il y a 1 unique index. En ne lisant que `pg_constraint`, l'identifiant `(AD_CLIENT_ID, VALUE)` de `A_ASSET` disparaît. C'est aussi une observation pour l'étape 4.
- Ne pas filtrer les FK externes : on les marque avec la colonne `internal`, c'est ce dont l'étape D a besoin.
- Les CHECK peuvent être réécrits par regex sur la sortie de `pg_get_constraintdef` : c'est un texte normalisé par PostgreSQL, pas le dump.

**Test**

- [ ] `columns.csv` : 704 lignes
- [ ] `primary_keys.csv` : 22 PK et 1 unique index
- [ ] `foreign_keys.csv` : 96 FK, dont 36 avec `internal=true`
- [ ] `check_constraints.csv` : 57 lignes
- [ ] Deux exécutions de suite donnent des fichiers identiques (`git diff` vide)
- [ ] Colonnes = constantes Java moins les colonnes virtuelles (voir les contrôles finaux, point 2)

## C. Générer le DDL pour DB-Main

**À écrire** : une fonction `ddl(tables, with_fk)` qui part des CSV (ou des mêmes structures en mémoire), et non du catalogue. Les deux fichiers SQL sortent ainsi de la même fonction.

- [ ] Pas de préfixe `adempiere.`, noms en MAJUSCULES
- [ ] Correspondance des types. Lever une erreur sur un type inconnu au lieu de le laisser passer.
  - `numeric(p,0)` → `NUMERIC(p)`
  - `numeric(p,s)` → `NUMERIC(p,s)` (absent ici, mais à prévoir)
  - `numeric` → `NUMERIC`
  - `character varying(n)` → `VARCHAR(n)`
  - `character(n)` → `CHAR(n)`
  - `timestamp without time zone` → `TIMESTAMP`
- [ ] Colonnes dans l'ordre de `ordinal_position`, avec `NOT NULL`
- [ ] `CONSTRAINT <NOM> PRIMARY KEY (…)` dans le `CREATE TABLE`
- [ ] Unique index → `CONSTRAINT … UNIQUE (AD_CLIENT_ID, VALUE)` dans le `CREATE TABLE`, pour que DB-Main en fasse un identifiant secondaire. Expliquer ce choix dans le README.
- [ ] FK en `ALTER TABLE … ADD CONSTRAINT … FOREIGN KEY … REFERENCES …` à la fin, sans `DEFERRABLE` ni `ON DELETE CASCADE` (ils restent dans le CSV)
- [ ] CHECK réécrits en `CHECK (X IN ('Y','N'))`, ou supprimés (décision après le test de Nathan)
- [ ] DEFAULT retirés du DDL (casts, `now()`) : ils restent dans `columns.csv`
- [ ] Tables triées par nom, pour un fichier identique à chaque exécution
- [ ] `ps_dbmain_nofk.sql` = même fonction avec `with_fk=False`

**Pièges**

- Aucun `::` ne doit atteindre le DDL : le faire vérifier par le script.
- Des noms de colonnes sont peut-être des mots réservés pour DB-Main (`VALUE`, `NAME`, `TEXT`, `LINE`, `SCRIPT`, `HELP`…). Le fichier de test le dira.
- Certains outils limitent les noms de contraintes à 30 caractères : vérifier le plus long.

**Fichier de test pour Nathan : `A_ASSET`.** Cette table contient les 5 types, 5 CHECK, un `now()`, les colonnes `VALUE`, `NAME` et `HELP`, l'unique index, et l'auto-référence `A_PARENT_ASSET_ID → A_ASSET` (la seule FK testable avec une seule table).

- [ ] Générer `ps_dbmain_test_a_asset.sql`
- [ ] Le charger dans un PostgreSQL vide (`psql -v ON_ERROR_STOP=1 -f`) avant de l'envoyer
- [ ] L'envoyer à Nathan avec ces critères :
  1. l'import passe sans erreur ;
  2. 70 colonnes, avec les bons types et la bonne nullabilité ;
  3. identifiant primaire `A_ASSET_ID` ;
  4. `(AD_CLIENT_ID, VALUE)` apparaît comme identifiant secondaire ;
  5. la FK réflexive est présente ;
  6. noter ce que DB-Main a fait des CHECK.
- [ ] Attendre son retour et ajuster les règles **avant** de générer les 22 tables

**Test**

- [ ] `ps_dbmain.sql` : 22 `CREATE TABLE`, 22 `PRIMARY KEY`, et autant de `FOREIGN KEY` que la décision D le prévoit
- [ ] `ps_dbmain_nofk.sql` : 0 `FOREIGN KEY`
- [ ] `diff` entre les deux fichiers : uniquement des lignes de FK
- [ ] Ni `::`, ni `ANY (`, ni `adempiere.` dans les fichiers
- [ ] Les deux fichiers se chargent sans erreur dans un PostgreSQL vide

## D. FK externes : tables stub ou CSV séparé

60 FK sur 96 pointent vers 32 tables hors du sous-ensemble.

| | Tables stub (`CREATE TABLE C_BPARTNER (C_BPARTNER_ID NUMERIC(10) PRIMARY KEY)`) | CSV séparé (le DDL garde les 36 FK internes) |
|---|---|---|
| Pour | Les 96 FK sont visibles dans DB-Main : on voit les dépendances du module vers le reste d'ADempiere (utile pour les étapes 2 et 3). Le DDL se charge tel quel. | Schéma lisible : seulement les 22 tables. Vérité terrain nette : 36 FK. Pas de tables « fausses ». |
| Contre | 32 tables vides encombrent le schéma, il faut les marquer et les expliquer. Il faut décider si les FK vers des stubs comptent dans le rappel. | Les dépendances externes ne sont visibles que dans `foreign_keys.csv`. Les 60 colonnes `*_ID` concernées ressemblent à des colonnes ordinaires. |
| Métrique de Nathan | Deux mesures nécessaires (FK internes et externes) | Une seule mesure : 36 FK à retrouver |

Compromis possible : DDL avec les FK internes, plus une version annexe `ps_dbmain_with_stubs.sql` générée par une option de la même fonction.

- [ ] Décider avec Nathan, et noter la décision et sa raison dans le README
- [ ] Test : `foreign_keys.csv` contient toujours les 96 FK, et le DDL en contient 36 ou 96 (plus 32 stubs)

---

## Contrôles finaux (dans le script, avec des `assert` et des messages explicites)

- [ ] 22 tables ; arrêt du script en nommant la table si une table de la liste manque
- [ ] Pour chaque table : colonnes du PS = constantes `COLUMNNAME_*` de `I_<Table>.java` moins les colonnes virtuelles (lues dans `ad_column` avec `columnsql IS NOT NULL`, plutôt que codées en dur)
- [ ] 22 PK, 96 FK dont 36 internes
- [ ] Le DDL généré se recharge sans erreur dans une base vide

## Ordre de travail

1. [ ] A, puis le test A
2. [ ] B : liste des tables et `columns.csv`, avec le contrôle Java
3. [ ] B : contraintes et index
4. [ ] C pour `A_ASSET` seule, chargée dans un PostgreSQL vide, puis envoi à Nathan. **Attendre son retour.**
5. [ ] D : décision avec Nathan (pendant qu'il teste)
6. [ ] C pour les 22 tables, les deux versions du DDL, puis les contrôles finaux
7. [ ] Documentation :
   - `REPRODUCE.md` section 1.3 (commandes et résultats attendus de ce document)
   - README : description du PS (nombre de tables, de colonnes et de FK internes/externes, types, conventions de nommage, décisions prises)
   - `AI_USAGE.md` : séance de guidage
   - `ROADMAP.md` : cocher 1.3 et remplacer `ps.sql` par les vrais livrables
