# Documentation des Données Mainframe Core Banking dans BigQuery (`raw_bank`)

Ce document décrit le **dataset**, les **4 tables BigLake Iceberg** et l'ensemble des **colonnes** produites dans BigQuery par le job **Managed Spark Serverless (`gcp-spark`)** à partir des fichiers Mainframe z/OS (`EBCDIC CP500 + COMP-3` et relevés multi-lignes `CFONB 120`).

---

## 1. Vue d'ensemble du Dataset & des 4 Tables Iceberg

* **Projet GCP** : `data-days-demo`
* **Région / Location** : `europe-west1`
* **Dataset cible** : `data-days-demo.raw_bank`
  * *Description* : Couche `RAW` multi-silos sans copie inutile de Banque Hexagone (tables BigLake Iceberg Mainframe décodées par Managed Spark, fédération AWS S3 BigQuery Omni, flux temps réel Pub/Sub ISO 20022 et Object Tables PDF).
* **Stockage Iceberg sous-jacent** : `gs://data-days-demo-landing/iceberg/raw_bank/` *(format `PARQUET`, table format `ICEBERG`)*

| Table BigQuery (`raw_bank`) | Fichier(s) Mainframe source & Copybook | Volumétrie (`seed=2026`) | Rôle fonctionnel & Particularités `RAW` |
| :--- | :--- | :--- | :--- |
| **`cbk_customers_ref`** | `CBK_CUSTOMERS_REF_20261112.ebcdic`<br>[`CBK_CUSTOMERS_REF.cpy`](../00_data_generator/copybooks/CBK_CUSTOMERS_REF.cpy) (`LRECL=140`) | **`79 350` lignes** | Signalétique clients Mainframe J-1 (`80 000` clients au total moins les **`650` clients récents AWS S3** pas encore réconciliés). Âge décodé depuis `COMP-3`. |
| **`cbk_accounts_master`** | `CBK_ACCOUNTS_MSTR_20261112.ebcdic`<br>[`CBK_ACCOUNTS_MSTR.cpy`](../00_data_generator/copybooks/CBK_ACCOUNTS_MSTR.cpy) (`LRECL=150`) | **`94 350` lignes** | Référentiel des comptes courants & livrets Mainframe (`95 000 - 650` orphelins AWS). Taux et solde veille J-1 décodés depuis `COMP-3` binaire (8 octets). `0` clôture sur le trimestre. |
| **`cbk_cfonb_balances`** | `CFONB120_MVTS_*.cfonb[.gz]` (`ENR '01'` & `'07'`)<br>[`CFONB120_BAL_OPS.cpy`](../00_data_generator/copybooks/CFONB120_BAL_OPS.cpy) (`LRECL=120`) | **`2 875 062` lignes** | Arrêtés mensuels de soldes CFONB : `'01'` (Ancien solde début de mois) et `'07'` (Nouveau solde fin de mois), signés CFONB, hors fichier `202610_RUN01` rejeté (`ABEND_S0C7`). |
| **`cbk_cfonb_movements`** | `CFONB120_MVTS_*.cfonb[.gz]` (`ENR '04'` + `'05'`)<br>[`CFONB120_BAL_OPS.cpy`](../00_data_generator/copybooks/CFONB120_BAL_OPS.cpy) (`LRECL=120`) | **`5 500 000` lignes** | Écritures comptables valorisées J+1 (`04`) enrichies par fenêtre physique Spark de leur ligne complémentaire SEPA `05` (`counterparty_bic`, `sepa_end_to_end_id`). Conserve les anomalies métier brutes (`1,20 %` de dates `00000000`/`99999999`, `12,10 %` de guichets décalés/blancs). |

> [!NOTE]
> Les mouvements `cbk_cfonb_movements` proviennent du journal partagé [`customer_ledger.py`](../00_data_generator/customer_ledger.py) : chaque mouvement SEPA (`code_op_interne` ≠ `0310` carte, ≠ `0580` virement interne) existe à l'identique dans le flux paiements `raw_sepa_payments_unified` (même `sepa_end_to_end_id`, date et montant). La couche SILVER (`silver_bank.customer_movements`) s'appuie sur ce rapprochement pour éviter tout double comptage.

---

## 2. Dictionnaire détaillé des colonnes par table

### 2.1. Table `raw_bank.cbk_customers_ref`
*Description de la table :* Extraction quotidienne J-1 du référentiel tiers Mainframe z/OS (`RECFM=FB`, `EBCDIC CP500` + `COMP-3`). N'inclut pas les 650 entrées en relation saisies en agence dans AWS CRM après le cut-off batch.

| Colonne BigQuery | Type | Champ Copybook & Octets | Règle de décodage Spark & Description métier |
| :--- | :--- | :--- | :--- |
| `customer_id` | `STRING` | `CBK-CUST-ID` (`001–012`) | Identifiant unique client Mainframe (`CUST00000001` à `CUST00079350` ; témoin Démo #4 = `CUST00002026`). Décodé `CP500` + `TRIM`. |
| `code_agence_raw` | `STRING` | `CBK-CODE-AGENCE` (`013–016`) | Code agence sur 4 caractères **conservé brut sans normalisation** : contient `'0042'` mais aussi `'42  '` (~11,5 %) et `'    '` (~0,6 %) pour l'audit Data Quality Démo #2. |
| `code_guichet_raw` | `STRING` | `CBK-CODE-GUICHET` (`017–021`) | Code guichet interbancaire sur 5 caractères **conservé brut** (`'00042'` vs `'42   '` / `'     '`). |
| `region_code` | `STRING` | `CBK-CODE-REGION` (`022–025`) | Code direction régionale (`REG1` à `REG8`). |
| `birth_date_raw` | `STRING` | `CBK-DATE-NAISSANCE` (`026–033`) | Date de naissance au format Mainframe `AAAAMMJJ` (ex. `'19990415'`). |
| `age_years` | `INT64` | `CBK-AGE-COMP3` (`034–035`) | Âge révolu au batch J-1 décodé depuis **2 octets binaires `PIC S9(03) COMP-3`** (permet d'isoler la cohorte `18–32 ans`). |
| `segment_clientele` | `STRING` | `CBK-SEG-CLIENTELE` (`036–047`) | Segment commercial (`JEUNE_ACTIF`, `MASS_MARKET`, `AFFLUENT`, `PATRIMONIAL`). |
| `onboarding_date_raw` | `STRING` | `CBK-DATE-ENTREE-REL` (`048–055`) | Date d'entrée en relation `AAAAMMJJ`. |
| `closure_date_raw` | `STRING` | `CBK-DATE-CLOTURE-REL` (`056–063`) | Date de fin de relation (`'00000000'` si dossier actif). |
| `dossier_status` | `STRING` | `CBK-STATUT-DOSSIER` (`064–069`) | Statut administratif du tiers (`ACTIF`). |
| `last_name` | `STRING` | `CBK-NOM-PATRONYMIQUE` (`070–095`) | Nom patronymique du client (ex. `MARTIN`). |
| `first_name` | `STRING` | `CBK-PRENOM-USUEL` (`096–115`) | Prénom usuel du client (ex. `LUCAS`). |
| `csp_code` | `STRING` | `CBK-CSP-CODE` (`116–125`) | Catégorie socio-professionnelle (`CADRE_TECH`, `INGENIEUR`, `ETUDIANT`, `EMPLOYE`, `LIBERAL`, `RETRAITE`, etc.). |
| `batch_date_raw` | `STRING` | `CBK-DATE-MAJ-BATCH` (`126–133`) | Date d'arrêté du traitement batch z/OS (`'20261112'`). |
| `_source_file` | `STRING` | *(Métadonnée Spark)* | URI GCS complète du fichier binaire `.ebcdic` source. |
| `_ingest_ts` | `TIMESTAMP` | *(Métadonnée Spark)* | Horodatage UTC d'écriture dans la table BigLake Iceberg. |

---

### 2.2. Table `raw_bank.cbk_accounts_master`
*Description de la table :* Référentiel maître des comptes courants (`CC_CHQ`) et livrets d'épargne (`LIVRET_A`, `LDDS`, `LIV_MAISON`) Mainframe (`LRECL=150`, `EBCDIC CP500` + `COMP-3`). Le solde veille comptable est strictement égal au dernier solde `07` de novembre 2026.

| Colonne BigQuery | Type | Champ Copybook & Octets | Règle de décodage Spark & Description métier |
| :--- | :--- | :--- | :--- |
| `account_id` | `STRING` | `CBK-ACC-ID` (`001–011`) | Identifiant interne du compte (`ACC00000001` à `ACC00095000`, hors `650` comptes AWS récents ; témoin = `ACC00002026`). |
| `num_compte_11` | `STRING` | `CBK-NUM-COMPTE-11` (`012–022`) | Numéro de compte RIB sur 11 chiffres (clé de jointure directe avec les relevés CFONB 120). |
| `customer_id` | `STRING` | `CBK-CUST-ID` (`023–034`) | Identifiant du client titulaire (`cbk_customers_ref.customer_id`). |
| `bank_code` | `STRING` | `CBK-CODE-BANQUE` (`035–039`) | Code établissement Banque Hexagone (`'30002'`). |
| `code_agence_raw` | `STRING` | `CBK-CODE-AGENCE` (`040–043`) | Code agence brut non normalisé (`'0042'` vs `'42  '` / `'    '`). |
| `code_guichet_raw` | `STRING` | `CBK-CODE-GUICHET` (`044–048`) | Code guichet RIB brut non normalisé (`'00042'` vs `'42   '` / `'     '`). |
| `cle_rib` | `STRING` | `CBK-CLE-RIB` (`049–050`) | Clé de contrôle RIB française modulo 97 (`01` à `97`). |
| `iban` | `STRING` | `CBK-IBAN-FR27` (`051–077`) | IBAN complet ISO 13616 sur 27 caractères (`FRkk30002...`). |
| `account_type` | `STRING` | `CBK-TYPE-COMPTE` (`078–087`) | Type de produit : `CC_CHQ` (dépôt à vue), `LIVRET_A`, `LDDS`, `LIV_MAISON`. |
| `currency_iso` | `STRING` | `CBK-DEVISE-ISO` (`088–090`) | Devise de tenue de compte (`EUR`). |
| `opening_date_raw` | `STRING` | `CBK-DATE-OUVERTURE` (`091–098`) | Date d'ouverture `AAAAMMJJ` (`14 350` ouvertures sur le trimestre côté Mainframe + `650` côté AWS = `15 000`). |
| `closure_date_raw` | `STRING` | `CBK-DATE-CLOTURE` (`099–106`) | Date de clôture (`'00000000'` sur 100 % des comptes -> `0` clôture sur le trimestre). |
| `account_status` | `STRING` | `CBK-STATUT-COMPTE` (`107–112`) | Statut du compte (`OUVERT`). |
| `rate_bps` | `INT64` | `CBK-TAUX-REMUN-BPS` (`113–115`) | Taux nominal en points de base décodé depuis **3 octets binaires `COMP-3`** (`0` sur `CC_CHQ`, `300` sur `LIVRET_A`/`LDDS`, `250` sur `LIV_MAISON`). |
| `solde_veille_cents` | `INT64` | `CBK-SOLDE-VEILLE-COMP3` (`116–123`) | Solde comptable veille J-1 en **centimes signés**, décodé depuis **8 octets binaires `PIC S9(13)V99 COMP-3`** (nibble `'C'` = `+`, `'D'` = `-`). |
| `solde_veille_eur` | `NUMERIC(15,2)` | *(Dérivé `COMP-3 / 100`)* | Solde comptable veille J-1 en euros avec 2 décimales exactes. |
| `last_movement_date_raw` | `STRING` | `CBK-DATE-DERNIER-MVT` (`124–131`) | Date de dernière écriture comptable `AAAAMMJJ`. |
| `product_label` | `STRING` | `CBK-LIBELLE-PRODUIT` (`132–150`) | Libellé commercial du produit. |
| `_source_file` | `STRING` | *(Métadonnée Spark)* | URI GCS du fichier `.ebcdic` source. |
| `_ingest_ts` | `TIMESTAMP` | *(Métadonnée Spark)* | Horodatage UTC d'ingestion Spark. |

---

### 2.3. Table `raw_bank.cbk_cfonb_balances`
*Description de la table :* Enregistrements d'arrêtés de soldes CFONB 120 (`record_type = '01'` Ancien solde début de mois et `'07'` Nouveau solde fin de mois) sur 18 mois (`202506` à `202611`), issus des fichiers validés `RC=0000`. Partitionnée par `period_ym`.

| Colonne BigQuery | Type | Champ Copybook & Positions | Règle de décodage Spark & Description métier |
| :--- | :--- | :--- | :--- |
| `period_ym` | `STRING` | *(Extrait `DATE-COMPTA 1..6`)* | Mois comptable `AAAAMM` (`'202506'` à `'202611'`). Clé de partitionnement. |
| `record_type` | `STRING` | `CFONB-CODE-ENR` (`001–002`) | `'01'` = Ancien solde début de période ; `'07'` = Nouveau solde fin de période. |
| `bank_code` | `STRING` | `CFONB-CODE-BANQUE` (`003–007`) | Code banque (`'30002'`). |
| `code_guichet_raw` | `STRING` | `CFONB-CODE-GUICHET` (`012–016`) | Code guichet agence sur 5 caractères. |
| `currency_iso` | `STRING` | `CFONB-CODE-DEVISE` (`017–019`) | Devise (`'EUR'`). |
| `num_compte_11` | `STRING` | `CFONB-NUM-COMPTE` (`022–032`) | Numéro de compte RIB sur 11 chiffres (`cbk_accounts_master.num_compte_11`). |
| `code_afb` | `STRING` | `CFONB-CODE-AFB` (`033–034`) | `'60'` (ancien solde) ou `'62'` (nouveau solde). |
| `balance_date_raw` | `STRING` | `CFONB-DATE-COMPTA` (`035–042`) | Date de l'arrêté de solde `AAAAMMJJ`. |
| `libelle` | `STRING` | `CFONB-LIBELLE` (`053–083`) | Libellé CFONB (`ANCIEN SOLDE DEBUT PERIODE` / `NOUVEAU SOLDE FIN PERIODE`). |
| `montant_cfonb_raw` | `STRING` | `CFONB-MONTANT-SIGNE` (`095–108`) | Montant brut CFONB sur 14 caractères (13 chiffres + caractère signé ASCII `{`/`A..I` positif, `}`/`J..R` négatif). |
| `signed_balance_cents` | `INT64` | *(Décodé pos `095–108`)* | Solde signé décodé en centimes (`s01 + Σ(m04) = s07` exact au centime sur 100 % des comptes). |
| `signed_balance_eur` | `NUMERIC(15,2)` | *(Décodé `/ 100`)* | Solde signé décodé en euros. |
| `_source_file` | `STRING` | *(Métadonnée Spark)* | Fichier `.cfonb` / `.cfonb.gz` d'origine (hors `202610_RUN01` rejeté). |
| `_ingest_ts` | `TIMESTAMP` | *(Métadonnée Spark)* | Horodatage UTC d'ingestion Spark. |

---

### 2.4. Table `raw_bank.cbk_cfonb_movements`
*Description de la table :* Mouvements comptables valorisés J+1 (`record_type = '04'`, `5 500 000` lignes) enrichis par jointure positionnelle Spark (`Window.orderBy(_line_offset)`) avec leur ligne complémentaire SEPA `05` immédiatement adjacente (`3 080 073` compléments). **Conserve volontairement les anomalies de contenu `RAW`** pour le scan Auto Data Quality et la couche `dbt` `SILVER` en Démo #2.

| Colonne BigQuery | Type | Champ Copybook & Positions | Règle de décodage Spark & Description métier |
| :--- | :--- | :--- | :--- |
| `period_ym` | `STRING` | *(Extrait `DATE-COMPTA 1..6`)* | Mois comptable `AAAAMM` (`'202506'` à `'202611'`). |
| `bank_code` | `STRING` | `CFONB-CODE-BANQUE` (`003–007`) | Code établissement (`'30002'`). |
| `code_op_interne` | `STRING` | `CFONB-CODE-OP-INTERNE` (`008–011`) | Nature interne de l'écriture : `'0420'` salaire/revenu, `'0430'` remboursement santé/divers, `'0580'` **virement interne compte-à-livret (`58*`)**, `'0810'` **virement SEPA Instant sortant**, `'0650'` prélèvement SEPA, `'0310'` paiement CB. |
| `code_guichet_raw` | `STRING` | `CFONB-CODE-GUICHET` (`012–016`) | **Anomalie `RAW` conservée** : `12,10 %` des lignes (`664 637`) ont un code guichet non padé (`'42   '`) ou blanc (`'     '`). |
| `currency_iso` | `STRING` | `CFONB-CODE-DEVISE` (`017–019`) | Devise (`'EUR'`). |
| `num_compte_11` | `STRING` | `CFONB-NUM-COMPTE` (`022–032`) | Numéro de compte RIB sur 11 caractères (`cbk_accounts_master.num_compte_11`). |
| `code_afb` | `STRING` | `CFONB-CODE-AFB` (`033–034`) | Code interbancaire CFONB : `'05'` virement reçu, `'16'` virement émis, `'08'` prélèvement, `'28'` paiement carte. |
| `date_compta_raw` | `STRING` | `CFONB-DATE-COMPTA` (`035–042`) | Date de comptabilisation `AAAAMMJJ` (toujours valide). |
| `code_rejet` | `STRING` | `CFONB-CODE-REJET` (`043–044`) | Code motif rejet (`'00'` = opération compensée `ACSC`). |
| `date_valeur_raw` | `STRING` | `CFONB-DATE-VALEUR` (`045–052`) | **Anomalie `RAW` conservée** : exactement **`1,20 %` (`66 000` lignes)** valent `'00000000'` (`41 250`) ou `'99999999'` (`24 750`) au lieu de `AAAAMMJJ`. |
| `libelle_court` | `STRING` | `CFONB-LIBELLE` (`053–083`) | Libellé court CFONB sur 31 caractères (`VIR SEPA INST REVOLT21`, `PRLV SEPA STRMFLIX ABO`, etc.). |
| `num_ecriture` | `STRING` | `CFONB-NUM-ECRITURE` (`086–092`) | Numéro séquentiel d'écriture dans le lot mensuel (7 chiffres). |
| `montant_cfonb_raw` | `STRING` | `CFONB-MONTANT-SIGNE` (`095–108`) | Chaîne brute signée CFONB de 14 caractères (ex. `'0000000210760O'`). |
| `signed_amount_cents` | `INT64` | *(Décodé pos `095–108`)* | Montant signé en centimes (`> 0` crédit, `< 0` débit). Sur `[20260815..20261112]`, les débits `0810` vers BIC néobanques totalisent exactement **`-242 000 000 000` centimes (`-2 420 000 000,00 €`)**. |
| `signed_amount_eur` | `NUMERIC(15,2)` | *(Décodé `/ 100`)* | Montant signé en euros. |
| `has_complement_05` | `BOOLEAN` | *(Issu ligne `05` adjacente)* | `TRUE` lorsque le mouvement `04` était suivi d'une ligne complémentaire `05` (`FALSE` sur les paiements CB `'0310'`). |
| `counterparty_bic` | `STRING` | `CF05-CONTREPARTIE-BIC` (`048–059`) | Code BIC de la banque contrepartie extrait de la ligne `05` (`REVOLT21XXX`, `TRBKDEBBXXX`, `NTSBDEB1XXX`, `BOURFRPPXXX`, `DEGIRO2AXXX`, `HEXAFRLPXXX`, etc.). `NULL` sur CB. |
| `sepa_end_to_end_id` | `STRING` | `CF05-END-TO-END-ID` (`060–095`) | Identifiant bout-en-bout ISO 20022 extrait de la ligne `05` (`E2E2026Q4LEAK...`), permettant la réconciliation exacte avec le flux temps réel `raw_sepa_payments_pubsub_stream`. |
| `sepa_motif` | `STRING` | `CF05-MOTIF-SEPA` (`096–120`) | Motif complémentaire SEPA extrait de la ligne `05` (`TRANSFERT SEPA INSTANTANE`, `VIREMENT EPARGNE INTERNE`, etc.). |
| `_source_file` | `STRING` | *(Métadonnée Spark)* | Fichier `.cfonb` / `.cfonb.gz` source. |
| `_line_offset` | `INT64` | *(Métadonnée Spark)* | Position physique de la ligne `04` dans le fichier source (garantit la traçabilité du recollage `04+05`). |
| `_ingest_ts` | `TIMESTAMP` | *(Métadonnée Spark)* | Horodatage UTC d'ingestion Spark. |
