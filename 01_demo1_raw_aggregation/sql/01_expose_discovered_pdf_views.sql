-- ==============================================================================
-- Paris Data Summit 2026 — Démo #1 (Banque Hexagone)
-- Exposition gouvernée dans `raw_bank` des deux corpus PDF découverts
-- automatiquement par Dataplex Cloud Storage Discovery (`__DISCOVERED_DATASET__.raw`).
--
-- Pourquoi ces 2 vues gouvernées ?
--   1. Dataplex Cloud Storage Discovery crée automatiquement l'Object Table BigLake
--      managée `__PROJECT_ID__.__DISCOVERED_DATASET__.raw` (`metadataCacheMode=AUTOMATIC`,
--      colonne `ref` ObjectRef native) sur le préfixe commun `gs://__BUCKET_LANDING__/RAW/*`.
--   2. Le wildcard `*` d'une Object Table BigQuery remontant tous les objets sous `RAW/`
--      (y compris les binaires `.ebcdic`, `.cfonb` et `.parquet`), ces deux vues filtrent
--      strictement `content_type = 'application/pdf'` par sous-dossier métier afin
--      d'isoler les 250 avenants agences (-14,30 M€) et les 6 normes CFO/ACPR pour
--      `dbt` (`AI.GENERATE_TABLE`) et `Knowledge Catalog`.
-- ==============================================================================

CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET_RAW__.raw_promo_contracts_pdf`
OPTIONS (
  description = "Vue gouvernée zéro-copie sur les 250 contrats et avenants promotionnels PDF d'agences (-14,30 M€ impact PNB), découverte automatiquement par Dataplex Cloud Storage Discovery (__DISCOVERED_DATASET__.raw) avec colonne ObjectRef `ref` prête pour AI.GENERATE_TABLE."
) AS
SELECT
  REGEXP_EXTRACT(uri, r'/(PROMO-2026-[0-9]{3})_') AS promo_contract_id,
  REGEXP_EXTRACT(uri, r'/PROMO-2026-[0-9]{3}_(REG[1-8])_') AS region_code_hint,
  uri,
  content_type,
  size AS size_bytes,
  md5_hash,
  updated AS updated_ts,
  ref
FROM `__PROJECT_ID__.__DISCOVERED_DATASET__.raw`
WHERE content_type = 'application/pdf'
  AND STARTS_WITH(uri, 'gs://__BUCKET_LANDING__/RAW/PROMO_CONTRACTS_PDF/');

CREATE OR REPLACE VIEW `__PROJECT_ID__.__DATASET_RAW__.raw_cfo_regulatory_pdf`
OPTIONS (
  description = "Vue gouvernée zéro-copie sur les 6 documents réglementaires, comptables et prudentiels CFO (ANC PCEC 2014-07, Charte ALM TCI, ILAAP LCR ACPR, PV Comité des Risques, SEPA Instant UE 2024/886, Recommandation ACPR 2024-R-01) découverts par Dataplex."
) AS
SELECT
  REGEXP_EXTRACT(uri, r'/(REG_[0-9]{2}_[^/]+)\.pdf$') AS doc_code,
  uri,
  content_type,
  size AS size_bytes,
  md5_hash,
  updated AS updated_ts,
  ref
FROM `__PROJECT_ID__.__DISCOVERED_DATASET__.raw`
WHERE content_type = 'application/pdf'
  AND STARTS_WITH(uri, 'gs://__BUCKET_LANDING__/RAW/REGULATORY_CFO_PDF/');
