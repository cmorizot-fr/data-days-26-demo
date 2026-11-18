{{ config(materialized='view') }}

-- dp_commercial_commitments · promo_contracts_pdf_tracking : suivi d'extraction PDF par PDF.
-- Part de l'Object Table (tous les PDF présents dans GCS, y compris ceux jamais traités) et y rattache
-- le résultat de promo_contracts : statut, tentatives, erreur, montant extrait et contrôles de cohérence.
-- Vue : toujours à jour, sans aucun appel au modèle IA.
SELECT
    p.promo_contract_id,
    p.region_code_hint                                                 AS region_code,
    CASE
        WHEN c.promo_contract_id IS NULL           THEN 'PENDING'      -- PDF arrivé, jamais extrait
        WHEN c.source_md5_hash != p.md5_hash       THEN 'OUTDATED'     -- PDF modifié depuis l'extraction
        WHEN NOT c.is_extraction_complete          THEN 'FAILED'       -- extraction vide ou non conforme
        ELSE 'EXTRACTED'
    END                                                                AS tracking_status,
    c.extraction_attempts,
    c.extracted_at                                                     AS last_extracted_at,
    c.extraction_model,
    c.extraction_status,
    c.extraction_error_detail,
    -- Champs certifiés extraits
    c.agency_code,
    c.promo_type,
    c.pcec_account,
    c.effective_date,
    c.end_date,
    c.committed_promo_cost_eur,
    -- Contrôles de cohérence (aucune règle métier codée en dur : référentiels pcec_accounts et promo_types)
    c.promo_type IS NOT NULL                                           AS is_promo_type_known,
    COALESCE(NOT a.is_in_sap_gl, FALSE)                                AS is_pcec_off_sap_gl,
    c.end_date IS NULL OR c.end_date >= c.effective_date               AS is_period_consistent,
    COALESCE(
        c.is_extraction_complete
        AND c.source_md5_hash = p.md5_hash
        AND c.promo_type IS NOT NULL
        AND NOT a.is_in_sap_gl,
        FALSE
    )                                                                  AS is_certifiable,
    -- PDF source, à rouvrir à la demande : AI.GENERATE((question, OBJ.MAKE_REF(source_uri)), ...) sur cette seule ligne
    p.ref                                                              AS source_pdf,
    p.uri                                                              AS source_uri,
    p.size_bytes                                                       AS source_size_bytes,
    p.md5_hash                                                         AS source_md5_hash,
    p.updated_ts                                                       AS source_updated_at
FROM {{ source('raw_bank', 'raw_promo_contracts_pdf') }} AS p
LEFT JOIN {{ ref('promo_contracts') }} AS c USING (promo_contract_id)
LEFT JOIN {{ ref('pcec_accounts') }} AS a ON a.pcec_account = c.pcec_account
