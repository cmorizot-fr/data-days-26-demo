{{ config(
    materialized='table',
    partition_by={'field': 'posting_date', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['ledger', 'pcec_account'],
) }}

-- dp_finance_pnb · gl_entries : grand livre SAP FI (réel), budget BPC et coût de refinancement ALM (TCI), 1 ligne par écriture.
-- Montants conservés tels quels (gross_amount_eur non signé + sens_dc) : aucune formule de PNB n'est codée ici.
-- La règle certifiée (signe D/C, exclusion des comptes de liaison, ajout des primes PDF) est portée par Knowledge Catalog.
-- Les attributs ajoutés sont descriptifs et viennent du référentiel pcec_accounts (nature du compte, compte de liaison).
SELECT
    g.gl_line_id,
    g.company_code,
    g.fiscal_year,
    g.fiscal_period,
    g.ledger,
    g.source_system,
    g.doc_type,
    g.doc_number,
    g.line_item,
    g.posting_date,
    g.agency_code,
    g.region_code,
    g.pcec_account,
    g.pcec_account_label,
    p.pcec_class,
    p.account_nature,
    p.is_liaison_account,
    g.sens_dc,
    g.gross_amount_eur,
    g.item_text
FROM {{ ref('stg_sap_gl') }} AS g
LEFT JOIN {{ ref('pcec_accounts') }} AS p USING (pcec_account)
