-- =============================================================================
-- Démo #4 · AlloyDB `hexagone` · socle (base shell)
-- Paiements du jour J reçus depuis Pub/Sub (sepa-payments-alloydb-ops-sub).
-- Le batch Mainframe J-1 et le GOLD restent dans BigQuery ; ici on ne garde que
-- ce qui arrive après le snapshot, pour que l'app le voie en millisecondes.
-- Idempotent : peut être rejoué sans erreur.
-- =============================================================================

CREATE TABLE IF NOT EXISTS live_movements (
    end_to_end_id       TEXT PRIMARY KEY,               -- clé ISO 20022, dédoublonne les retries
    event_id            TEXT        NOT NULL,
    customer_id         TEXT        NOT NULL,
    account_id          TEXT        NOT NULL,
    execution_ts        TIMESTAMPTZ NOT NULL,
    booking_date        DATE        NOT NULL,
    payment_scheme      TEXT        NOT NULL,
    tx_status           TEXT        NOT NULL CHECK (tx_status IN ('ACSC', 'PDNG', 'RJCT')),
    status_reason_code  TEXT,
    amount_eur          NUMERIC(14, 2) NOT NULL CHECK (amount_eur >= 0),
    signed_amount_eur   NUMERIC(14, 2) NOT NULL,        -- *_INBOUND = crédit, sinon débit (même règle que dbt)
    counterparty_name   TEXT,
    counterparty_bic    TEXT,
    label               TEXT,
    pubsub_message_id   TEXT        NOT NULL,
    publish_time        TIMESTAMPTZ,
    duplicate_count     INTEGER     NOT NULL DEFAULT 0, -- nb de retries reçus et ignorés
    received_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Pas d'IBAN ni de nom du titulaire : l'app n'en a pas besoin (minimisation RGPD).

CREATE INDEX IF NOT EXISTS live_movements_customer_ts
    ON live_movements (customer_id, execution_ts DESC);

-- Vue lue par l'app : uniquement les paiements réglés.
CREATE OR REPLACE VIEW v_live_movements_settled AS
SELECT end_to_end_id, customer_id, account_id, execution_ts, booking_date,
       payment_scheme, signed_amount_eur, counterparty_name, label
FROM live_movements
WHERE tx_status = 'ACSC';

-- -----------------------------------------------------------------------------
-- Droits du service d'ingestion (moindre privilège) : insérer et mettre à jour
-- live_movements, rien d'autre. L'utilisateur IAM est créé par infra/ (MCP).
-- -----------------------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'hexagone-d4-ingest@data-days-demo.iam') THEN
    EXECUTE 'GRANT CONNECT ON DATABASE hexagone TO "hexagone-d4-ingest@data-days-demo.iam"';
    EXECUTE 'GRANT USAGE ON SCHEMA public TO "hexagone-d4-ingest@data-days-demo.iam"';
    EXECUTE 'GRANT SELECT, INSERT, UPDATE ON live_movements TO "hexagone-d4-ingest@data-days-demo.iam"';
  END IF;
END
$$;
