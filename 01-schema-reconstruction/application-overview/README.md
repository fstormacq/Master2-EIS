# Application overview

## 1. What is ADempiere ?
ADempiere is an enterprise resource planning software that covers Customer Relationship Management, Supply Chain Management, accounting or even finance to avoid listing everything.
It is a fully open source software built in Java, running usually on a PostgreSQL database. Its strength is the Application Dictionary allowing administrators to add fields, create new windows, customize reports, and build workflows without modifying the underlying Java source code. 

The project ADempiere is actually a fork from the ERP software Compiere. It comes from the italian language and means to "fulfil (a duty)", "to accomplish" symbolizing their commitment to upholding the promises of free software in the face of the increasing commercialization of Compiere. 

## 2. Size
We measured with `cloc` excluding blank lines and comments.

| Scope | Java files | Java LoC | Total LoC (all languages) |
|---|---|---|---|
| Whole ADempiere | 5 424 | 895 302 | 6 012 838 |
| Module `org.adempiere.asset/` | 77 | 9 313 | 9 612 |

Most of the total comes from XML (4.38 M lines) and SQL (578 k lines):
schema definitions and migration scripts, not hand-written code.

## 3. Project structure

The repository contains about 60 folders. Java lines of code per folder
are listed in [`structure-folder.txt`](structure_folder.txt).

- `base/`: core of the ERP (61 % of the Java code): data model, business logic,
  classes generated from the Application Dictionary;
- `client/`, `zkwebui/`: desktop and web user interfaces;
- `org.adempiere.asset/`: assets module;
- `org.eevolution.*`, `org.spin.*`, `org.adempiere.*`: other functional modules
  (manufacturing, payroll, point of sale, …);
- `db/`, `data/`, `migration/`: schema definitions, seed data and migration scripts.


Two parts of the repository matter most for this project:
- `org.adempiere.asset/` and the asset-related classes of `base/`,
- `db/`, `data/` and `migration/`, from which the physical schema is
  reconstructed.

## 4. Application dictionary

ADempiere does not describe its tables only in SQL: each table is also described in
the **Application Dictionary**, a set of tables stored in the database itself
(`AD_Table`, `AD_Column`, …). Java classes are generated from this description.
We illustrate the mechanism on A_ASSET.

| Class | Location | Evidence |
|---|---|---|
| `I_A_Asset` | `base/src/org/adempiere/core/domains/models/` | Declares the table name (`Table_Name = "A_Asset"`, l. 33), its identifier in the dictionary (`AD_Table_ID=539`, l. 35) and one constant per column (70 columns) |
| `X_A_Asset` | `base/src/org/adempiere/core/domains/models/` | Header comment `Generated Model - DO NOT CHANGE` (l. 18) and `Generated Model for A_Asset` (l. 31) |
| `MAsset` | `org.adempiere.asset/src/main/java/base/org/compiere/asset/model/` | `public class MAsset extends X_A_Asset` (l. 63) |

The table is thus described by row 539 of `AD_Table`. Two classes are generated from this description: an interface listing the table and its columns and a class implementing them. The business logic is then added by hand in a third class which extends the generated one. The generated classes live in the (`base/`) while the business class lives in the asset module.

As a consequence, a lot of database accesses go through these classes rather than through SQL written in the code which SQLInspect cannot detect

The commands used to obtain these observations are listed in [How to reproduce](#how-to-reproduce).

## 5. Scope of fixed assets
We searched for Java files that mention one of the 22 tables.
It shows that 138 are related to them mainly coming from `base` and `org.adempiere.asset`([`asset_related_files.txt`](asset_related_files.txt)).
The files are either directly from the generated classes, generated classes that refer to our tables or code that uses theses tables. 

## How to reproduce
Run from the repository root (cloc 2.12, ADempiere commit `4ae098f`):

    cloc target/ --exclude-dir=.git --quiet                 # section 2, whole ADempiere
    cloc target/org.adempiere.asset/ --quiet                # section 2, asset module
    for d in target/*/; do
  n=$(cloc "$d" --quiet --include-lang=Java --csv 2>/dev/null | awk -F, '$2=="Java"{print $5}')
  printf "%-45s %s\n" "$d" "${n:-0}"
done | sort -k2 -rn | tee 01-schema-reconstruction/application-overview/structure_folder.txt    # section 3, Java lines of code per folder

To know the classes:
`grep -n "Table_Name\|Table_ID" target/base/src/org/adempiere/core/domains/models/I_A_Asset.java`
`grep -c "String COLUMNNAME_" target/base/src/org/adempiere/core/domains/models/I_A_Asset.java`
`grep -n "Generated Model" target/base/src/org/adempiere/core/domains/models/X_A_Asset.java`
`grep -n "class MAsset" target/org.adempiere.asset/src/main/java/base/org/compiere/asset/model/MAsset.java`

To know the number of classes related to the 22 tables of the scope: 
grep -oE '^A_[A-Z_]+' database-scope/studied-tables.txt | sort -u > /tmp/tables.txt
pattern=$(sed -E 's/.*/(^|[^A-Za-z0-9_])(I_|X_)?&([^A-Za-z0-9_]|$)/' /tmp/tables.txt | paste -sd'|' -)
grep -rliE "$pattern" target --include='*.java' | sort > 01-schema-reconstruction/application-overview/asset_related_files.txt
wc -l < 01-schema-reconstruction/application-overview/asset_related_files.txt