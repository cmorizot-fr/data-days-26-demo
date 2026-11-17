-- ==============================================================================
-- Paris Data Summit 2026 — Démo #1 : Certification de la cohérence Historique ↔ Temps réel
-- du SI Paiements (vue raw_sepa_payments_unified) et du rapprochement avec le Mainframe CFONB.
--
-- Variables : __PROJECT_ID__, __DATASET_RAW__
-- Retourne une ligne par contrôle : check_name, observed, expected, status (PASS / FAIL).
-- ==============================================================================

WITH
u AS (
  SELECT * FROM `__PROJECT_ID__.__DATASET_RAW__.raw_sepa_payments_unified`
),
src AS (
  SELECT
    ingestion_source,
    COUNT(*) AS n,
    MIN(header.execution_ts) AS min_ts,
    MAX(header.execution_ts) AS max_ts
  FROM u
  GROUP BY ingestion_source
),
leak AS (
  -- Fuite 90j : virements ACSC dédoublonnés vers néobanques, fenêtre FIXE 2026-08-15 → 2026-11-12
  SELECT
    p.debtor.customer_id AS customer_id,
    p.header.execution_ts AS ts,
    p.instructed_amount.amount_cents AS cents
  FROM u AS p
  WHERE p.settlement.tx_status = 'ACSC'
    AND p.creditor.agent_bic IN ('REVOLT21XXX', 'TRBKDEBBXXX', 'NTSBDEB1XXX', 'BOURFRPPXXX', 'DEGIRO2AXXX')
    AND DATE(p.header.execution_ts) BETWEEN '2026-08-15' AND '2026-11-12'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY p.header.end_to_end_id ORDER BY p.header.execution_ts DESC) = 1
),
leak_kpi AS (
  SELECT
    SUM(l.cents) AS total_cents,
    SUM(IF(c.age_years BETWEEN 18 AND 32 AND EXTRACT(DAY FROM l.ts) BETWEEN 1 AND 5, l.cents, 0)) AS young_cents
  FROM leak AS l
  LEFT JOIN `__PROJECT_ID__.__DATASET_RAW__.cbk_customers_ref` AS c USING (customer_id)
),
e2e_collisions AS (
  SELECT COUNT(DISTINCT l.header.end_to_end_id) AS n
  FROM u AS l
  JOIN u AS h
    ON h.header.end_to_end_id = l.header.end_to_end_id
   AND h.ingestion_source = 'HISTORY_ARCHIVE'
  WHERE l.ingestion_source = 'PUBSUB_LIVE'
),
mainframe_leak_match AS (
  -- Rapprochement ligne à ligne des 200 000 virements de fuite 90j avec les lignes CFONB 04+05
  SELECT
    COUNT(*) AS n_matched,
    COUNTIF(-m.signed_amount_cents != p.instructed_amount.amount_cents) AS n_amount_mismatch
  FROM (
    SELECT * FROM u
    WHERE ingestion_source = 'HISTORY_ARCHIVE'
      AND settlement.retry_attempt = 0
      AND STARTS_WITH(header.end_to_end_id, 'E2E2026Q4LEAK')
  ) AS p
  JOIN `__PROJECT_ID__.__DATASET_RAW__.cbk_cfonb_movements` AS m
    ON m.sepa_end_to_end_id = p.header.end_to_end_id
),
iban_orphans AS (
  -- Les seuls IBAN débiteurs absents du Mainframe doivent être les 650 comptes récents créés sur AWS
  SELECT COUNT(*) AS n
  FROM (SELECT DISTINCT debtor.iban AS iban FROM u) AS d
  LEFT JOIN `__PROJECT_ID__.__DATASET_RAW__.cbk_accounts_master` AS a USING (iban)
  WHERE a.iban IS NULL
),
neo_iban_consistency AS (
  -- Un client vers une même néobanque : un seul IBAN externe, historique et temps réel confondus
  SELECT COUNT(*) AS n_conflicts
  FROM (
    SELECT debtor.customer_id, creditor.agent_bic, COUNT(DISTINCT creditor.iban) AS n_iban
    FROM u
    WHERE creditor.agent_bic IN ('REVOLT21XXX', 'TRBKDEBBXXX', 'NTSBDEB1XXX', 'BOURFRPPXXX', 'DEGIRO2AXXX')
    GROUP BY 1, 2
    HAVING n_iban > 1
  )
),
counterparty_consistency AS (
  -- Une contrepartie (BIC + libellé) garde le même nom et le même IBAN dans les deux couches
  SELECT COUNT(*) AS n_conflicts
  FROM (
    SELECT creditor.agent_bic, remittance.unstructured_info, COUNT(DISTINCT CONCAT(creditor.name, '|', creditor.iban)) AS n_variants
    FROM u
    WHERE creditor.agent_bic NOT IN ('REVOLT21XXX', 'TRBKDEBBXXX', 'NTSBDEB1XXX', 'BOURFRPPXXX', 'DEGIRO2AXXX')
    GROUP BY 1, 2
    HAVING n_variants > 1
  )
),
iban_events_reenrolled AS (
  SELECT COUNT(*) AS n
  FROM `__PROJECT_ID__.__DATASET_RAW__.raw_iban_events_unified` AS l
  JOIN `__PROJECT_ID__.__DATASET_RAW__.raw_iban_events_unified` AS h
    ON h.account_holder.customer_id = l.account_holder.customer_id
   AND h.beneficiary.agent_bic = l.beneficiary.agent_bic
   AND h.ingestion_source = 'HISTORY_ARCHIVE'
  WHERE l.ingestion_source = 'PUBSUB_LIVE'
)
SELECT check_name, observed, expected, IF(ok, 'PASS', 'FAIL') AS status
FROM (
  SELECT 1 AS ord, 'Volume historique (BigLake)' AS check_name,
         CAST((SELECT n FROM src WHERE ingestion_source = 'HISTORY_ARCHIVE') AS STRING) AS observed,
         '6200000' AS expected,
         (SELECT n FROM src WHERE ingestion_source = 'HISTORY_ARCHIVE') = 6200000 AS ok
  UNION ALL
  SELECT 2, 'Volume temps réel (Pub/Sub)',
         CAST(IFNULL((SELECT n FROM src WHERE ingestion_source = 'PUBSUB_LIVE'), 0) AS STRING),
         '> 0',
         IFNULL((SELECT n FROM src WHERE ingestion_source = 'PUBSUB_LIVE'), 0) > 0
  UNION ALL
  SELECT 3, 'Continuité : fin historique < début temps réel',
         CONCAT(CAST((SELECT max_ts FROM src WHERE ingestion_source = 'HISTORY_ARCHIVE') AS STRING), ' < ',
                CAST((SELECT min_ts FROM src WHERE ingestion_source = 'PUBSUB_LIVE') AS STRING)),
         'aucun chevauchement',
         (SELECT max_ts FROM src WHERE ingestion_source = 'HISTORY_ARCHIVE')
           < (SELECT min_ts FROM src WHERE ingestion_source = 'PUBSUB_LIVE')
  UNION ALL
  SELECT 4, 'Collisions end_to_end_id historique / temps réel',
         CAST((SELECT n FROM e2e_collisions) AS STRING), '0', (SELECT n FROM e2e_collisions) = 0
  UNION ALL
  SELECT 5, 'Fuite 90j fenêtre fixe (EUR, ACSC dédoublonné)',
         FORMAT('%.2f', (SELECT total_cents FROM leak_kpi) / 100), '2420000000.00',
         (SELECT total_cents FROM leak_kpi) = 242000000000
  UNION ALL
  SELECT 6, 'Part 18-32 ans jours 1..5 (%)',
         FORMAT('%.2f', 100 * (SELECT young_cents FROM leak_kpi) / (SELECT total_cents FROM leak_kpi)), '68.00',
         ROUND(100 * (SELECT young_cents FROM leak_kpi) / (SELECT total_cents FROM leak_kpi), 2) = 68.00
  UNION ALL
  SELECT 7, 'Rapprochement fuite 90j avec Mainframe CFONB 05 (lignes)',
         CAST((SELECT n_matched FROM mainframe_leak_match) AS STRING), '200000',
         (SELECT n_matched FROM mainframe_leak_match) = 200000
  UNION ALL
  SELECT 8, 'Écarts de montant Paiements vs Mainframe',
         CAST((SELECT n_amount_mismatch FROM mainframe_leak_match) AS STRING), '0',
         (SELECT n_amount_mismatch FROM mainframe_leak_match) = 0
  UNION ALL
  SELECT 9, 'IBAN débiteurs absents du Mainframe (= 650 comptes AWS J0)',
         CAST((SELECT n FROM iban_orphans) AS STRING), '650',
         (SELECT n FROM iban_orphans) = 650
  UNION ALL
  SELECT 10, 'Clients avec plusieurs IBAN pour une même néobanque',
         CAST((SELECT n_conflicts FROM neo_iban_consistency) AS STRING), '0',
         (SELECT n_conflicts FROM neo_iban_consistency) = 0
  UNION ALL
  SELECT 11, 'Contreparties décrites différemment entre couches',
         CAST((SELECT n_conflicts FROM counterparty_consistency) AS STRING), '0',
         (SELECT n_conflicts FROM counterparty_consistency) = 0
  UNION ALL
  SELECT 12, 'Bénéficiaires ré-enrôlés en temps réel',
         CAST((SELECT n FROM iban_events_reenrolled) AS STRING), '0',
         (SELECT n FROM iban_events_reenrolled) = 0
)
ORDER BY ord;
