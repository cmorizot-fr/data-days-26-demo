{{ config(materialized='view') }}

-- Grand livre SAP FI / BPC / ALM, sans aucune transformation de montant.
-- gross_amount_eur et sens_dc sont conservés tels quels : la règle de calcul du PNB vit dans Knowledge Catalog.
SELECT
    gl_line_id,
    company_code,
    fiscal_year,
    fiscal_period,
    ledger,
    source_system,
    doc_type,
    doc_number,
    line_item,
    posting_date,
    agency_code,
    region_code,
    pcec_account,
    pcec_account_label,
    sens_dc,
    gross_amount_eur,
    item_text
FROM {{ source('raw_bank', 'raw_sap_gl_alm') }}
