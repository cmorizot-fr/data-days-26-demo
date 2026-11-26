-- =============================================================================
-- Benchmark Cross-Cloud Lakehouse (100 000 000 de lignes sur AWS S3 eu-west-1)
-- Table hors flux SILVER/dbt : aws_crm_catalog.crm_callcenter_db.crm_digital_clickstream_events
-- Exécuter en région europe-west1 dans BigQuery Studio
-- =============================================================================

-- 1) Scan & agrégation sur 100 M d'événements stockés sur AWS S3 (eu-west-1)
--    Astuce démo : lancer 2 fois de suite pour montrer l'accélération du Cross-Cloud Cache !
SELECT
  target_competitor,
  channel,
  COUNT(*) AS nb_events,
  COUNT(DISTINCT customer_id) AS distinct_customers,
  ROUND(SUM(simulated_amount_eur), 2) AS total_simulated_eur,
  ROUND(AVG(latency_ms), 1) AS avg_api_latency_ms
FROM `data-days-demo.aws_crm_catalog.crm_callcenter_db.crm_digital_clickstream_events`
WHERE target_competitor != 'NONE'
GROUP BY target_competitor, channel
ORDER BY nb_events DESC;

-- 2) Jointure Cross-Cloud en direct :
--    100 M de lignes AWS S3 (eu-west-1) ⋈ Référentiel Mainframe Iceberg sur GCP (europe-west1)
SELECT
  c.segment_clientele AS mainframe_segment,
  e.target_competitor,
  COUNT(*) AS digital_intent_events,
  COUNT(DISTINCT e.customer_id) AS impacted_customers,
  ROUND(SUM(e.simulated_amount_eur), 2) AS simulated_outflow_eur
FROM `data-days-demo.aws_crm_catalog.crm_callcenter_db.crm_digital_clickstream_events` AS e
INNER JOIN `data-days-demo.raw_bank.cbk_customers_ref` AS c
  ON e.customer_id = c.customer_id
WHERE e.event_type IN ('ADD_EXTERNAL_NEOBANK_IBAN', 'INITIATE_SEPA_TRANSFER')
  AND e.target_competitor != 'NONE'
GROUP BY mainframe_segment, e.target_competitor
ORDER BY simulated_outflow_eur DESC
LIMIT 15;
