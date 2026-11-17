{{ config(
    materialized='table',
    partition_by={'field': 'booking_date', 'data_type': 'date', 'granularity': 'month'},
    cluster_by=['customer_id', 'category_group'],
) }}

-- dp_customer_timeline · customer_movements : la vie du client, 1 ligne par mouvement réglé.
--  1. Le Mainframe CFONB fait foi pour tous les comptes du batch J-1 ;
--     les paiements SEPA l'enrichissent (nom / IBAN du bénéficiaire, schéma) via l'end_to_end_id.
--  2. Les paiements SEPA réglés absents du Mainframe sont ajoutés :
--     opérations postérieures au dernier batch (flux temps réel) et comptes ouverts après le batch J-1.
--  Aucun double comptage : chaque paiement SEPA est soit rattaché à un mouvement CFONB, soit ajouté.
WITH accounts AS (
    SELECT account_id, customer_id, account_number_11, account_type, is_in_mainframe
    FROM {{ ref('accounts') }}
),
sepa_settled AS (
    SELECT * FROM {{ ref('stg_sepa_payments') }} WHERE is_settled
),
cfonb AS (
    SELECT m.*, a.account_id, a.customer_id, a.account_type
    FROM {{ ref('stg_cbk_movements') }} AS m
    JOIN accounts AS a USING (account_number_11)
),
cfonb_cutoff AS (
    SELECT MAX(booking_date) AS last_batch_date FROM cfonb
),
from_mainframe AS (
    SELECT
        c.movement_id,
        'MAINFRAME_CFONB'                                   AS source_system,
        c.customer_id,
        c.account_id,
        c.account_type,
        c.booking_date,
        c.value_date,
        c.value_date_was_invalid,
        c.signed_amount_eur,
        c.label,
        c.code_afb,
        c.end_to_end_id,
        COALESCE(s.counterparty_bic, c.counterparty_bic)    AS counterparty_bic,
        s.counterparty_name,
        s.counterparty_iban,
        s.payment_scheme
    FROM cfonb AS c
    LEFT JOIN sepa_settled AS s
        ON s.end_to_end_id = c.end_to_end_id
       AND c.code_op_interne <> '0580'          -- les virements internes 58* ne passent pas par SEPA
),
from_sepa_only AS (
    SELECT
        CONCAT('SEPA-', s.end_to_end_id)                    AS movement_id,
        'SEPA_REALTIME'                                     AS source_system,
        a.customer_id,
        a.account_id,
        a.account_type,
        s.booking_date,
        s.booking_date                                      AS value_date,
        FALSE                                               AS value_date_was_invalid,
        s.signed_amount_eur,
        s.label,
        CAST(NULL AS STRING)                                AS code_afb,
        s.end_to_end_id,
        s.counterparty_bic,
        s.counterparty_name,
        s.counterparty_iban,
        s.payment_scheme
    FROM sepa_settled AS s
    JOIN accounts AS a ON a.account_id = s.account_id
    CROSS JOIN cfonb_cutoff AS k
    WHERE s.booking_date > k.last_batch_date      -- postérieur au dernier batch Mainframe
       OR NOT a.is_in_mainframe                   -- comptes ouverts après le batch J-1
),
unioned AS (
    SELECT * FROM from_mainframe
    UNION ALL
    SELECT * FROM from_sepa_only
),
categorized AS (
    SELECT
        u.*,
        r.category,
        r.category_group
    FROM unioned AS u
    JOIN {{ ref('movement_category_rules') }} AS r
        ON REGEXP_CONTAINS(u.label, r.label_pattern)
    QUALIFY ROW_NUMBER() OVER (PARTITION BY u.movement_id ORDER BY r.priority) = 1
)
SELECT
    movement_id,
    source_system,
    customer_id,
    account_id,
    account_type,
    booking_date,
    value_date,
    value_date_was_invalid,
    IF(signed_amount_eur >= 0, 'CREDIT', 'DEBIT')                               AS direction,
    ABS(signed_amount_eur)                                                     AS amount_eur,
    signed_amount_eur,
    category,
    category_group,
    label,
    counterparty_name,
    counterparty_iban,
    counterparty_bic,
    payment_scheme,
    end_to_end_id,
    counterparty_bic IN ('REVOLT21XXX', 'TRBKDEBBXXX', 'NTSBDEB1XXX', 'BOURFRPPXXX', 'DEGIRO2AXXX')
        AND signed_amount_eur < 0                                              AS is_neobank_outflow,
    category = 'INTERNAL_SAVINGS'                                              AS is_internal_transfer
FROM categorized
