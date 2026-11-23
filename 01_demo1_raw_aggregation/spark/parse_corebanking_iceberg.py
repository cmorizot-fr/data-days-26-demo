"""
Paris Data Summit 2026 — Démo #1 (Banque Hexagone)
Job PySpark Dataproc Serverless : Décodage binaire Mainframe z/OS vers BigLake Managed Iceberg.

Responsabilités strictement techniques (couche RAW gouvernée) :
1. Lecture binaire continue RECFM=FB (sans '\\n') des référentiels maîtres :
   - CBK_CUSTOMERS_REF_20261112.ebcdic (LRECL=140, EBCDIC CP500 + COMP-3) -> cbk_customers_ref
   - CBK_ACCOUNTS_MSTR_20261112.ebcdic (LRECL=150, EBCDIC CP500 + COMP-3) -> cbk_accounts_master
2. Contrôle des bannières CFT (00CFT_HDR / 99CFT_TRL) sur les 19 fichiers mensuels CFONB 120
   (.cfonb.gz sur 2025, .cfonb sur 2026) et rejet automatique de tout dump interrompu (RC != 0000,
   notamment CFONB120_MVTS_202610_RUN01.cfonb en ABEND_S0C7 RC=0012).
3. Rattachement par ordre physique des lignes complémentaires SEPA '05' (BIC, EndToEndId, Motif)
   situées immédiatement sous leur mouvement comptable '04' parent :
   - Enregistrements '01' & '07' -> cbk_cfonb_balances
   - Enregistrements '04' (+ '05' rattaché) -> cbk_cfonb_movements
4. Préservation volontaire de 100 % des anomalies de valeurs métier en couche RAW
   (dates '00000000'/'99999999', codes agences/guichets non normalisés '42  '/'     ',
   650 comptes orphelins AWS S3) pour l'audit Auto Data Quality et dbt SILVER (Démo #2).
"""

from __future__ import annotations

import argparse
import gzip
import logging
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterator

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import (
    BooleanType,
    DecimalType,
    LongType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)
from pyspark.storagelevel import StorageLevel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("banque_hexagone.spark_corebanking")

EBCDIC_ENCODING = "cp500"
CFONB_ENCODING = "iso-8859-15"
BQ_NUMERIC = DecimalType(38, 9)

CFONB_LAST_CHAR_MAP: dict[str, tuple[int, int]] = {
    "{": (0, 1),
    "A": (1, 1),
    "B": (2, 1),
    "C": (3, 1),
    "D": (4, 1),
    "E": (5, 1),
    "F": (6, 1),
    "G": (7, 1),
    "H": (8, 1),
    "I": (9, 1),
    "}": (0, -1),
    "J": (1, -1),
    "K": (2, -1),
    "L": (3, -1),
    "M": (4, -1),
    "N": (5, -1),
    "O": (6, -1),
    "P": (7, -1),
    "Q": (8, -1),
    "R": (9, -1),
}

CUSTOMERS_SCHEMA = StructType(
    [
        StructField("customer_id", StringType(), True),
        StructField("code_agence_raw", StringType(), True),
        StructField("code_guichet_raw", StringType(), True),
        StructField("region_code", StringType(), True),
        StructField("birth_date_raw", StringType(), True),
        StructField("age_years", LongType(), True),
        StructField("segment_clientele", StringType(), True),
        StructField("onboarding_date_raw", StringType(), True),
        StructField("closure_date_raw", StringType(), True),
        StructField("dossier_status", StringType(), True),
        StructField("last_name", StringType(), True),
        StructField("first_name", StringType(), True),
        StructField("csp_code", StringType(), True),
        StructField("batch_date_raw", StringType(), True),
        StructField("_source_file", StringType(), True),
        StructField("_ingest_ts", TimestampType(), True),
    ]
)

ACCOUNTS_SCHEMA = StructType(
    [
        StructField("account_id", StringType(), True),
        StructField("num_compte_11", StringType(), True),
        StructField("customer_id", StringType(), True),
        StructField("bank_code", StringType(), True),
        StructField("code_agence_raw", StringType(), True),
        StructField("code_guichet_raw", StringType(), True),
        StructField("cle_rib", StringType(), True),
        StructField("iban", StringType(), True),
        StructField("account_type", StringType(), True),
        StructField("currency_iso", StringType(), True),
        StructField("opening_date_raw", StringType(), True),
        StructField("closure_date_raw", StringType(), True),
        StructField("account_status", StringType(), True),
        StructField("rate_bps", LongType(), True),
        StructField("solde_veille_cents", LongType(), True),
        StructField("solde_veille_eur", BQ_NUMERIC, True),
        StructField("last_movement_date_raw", StringType(), True),
        StructField("product_label", StringType(), True),
        StructField("_source_file", StringType(), True),
        StructField("_ingest_ts", TimestampType(), True),
    ]
)

BALANCES_SCHEMA = StructType(
    [
        StructField("period_ym", StringType(), True),
        StructField("record_type", StringType(), True),
        StructField("bank_code", StringType(), True),
        StructField("code_guichet_raw", StringType(), True),
        StructField("currency_iso", StringType(), True),
        StructField("num_compte_11", StringType(), True),
        StructField("code_afb", StringType(), True),
        StructField("balance_date_raw", StringType(), True),
        StructField("libelle", StringType(), True),
        StructField("montant_cfonb_raw", StringType(), True),
        StructField("signed_balance_cents", LongType(), True),
        StructField("signed_balance_eur", BQ_NUMERIC, True),
        StructField("_source_file", StringType(), True),
        StructField("_ingest_ts", TimestampType(), True),
    ]
)

MOVEMENTS_SCHEMA = StructType(
    [
        StructField("period_ym", StringType(), True),
        StructField("bank_code", StringType(), True),
        StructField("code_op_interne", StringType(), True),
        StructField("code_guichet_raw", StringType(), True),
        StructField("currency_iso", StringType(), True),
        StructField("num_compte_11", StringType(), True),
        StructField("code_afb", StringType(), True),
        StructField("date_compta_raw", StringType(), True),
        StructField("code_rejet", StringType(), True),
        StructField("date_valeur_raw", StringType(), True),
        StructField("libelle_court", StringType(), True),
        StructField("num_ecriture", StringType(), True),
        StructField("montant_cfonb_raw", StringType(), True),
        StructField("signed_amount_cents", LongType(), True),
        StructField("signed_amount_eur", BQ_NUMERIC, True),
        StructField("has_complement_05", BooleanType(), True),
        StructField("counterparty_bic", StringType(), True),
        StructField("sepa_end_to_end_id", StringType(), True),
        StructField("sepa_motif", StringType(), True),
        StructField("_source_file", StringType(), True),
        StructField("_line_offset", LongType(), True),
        StructField("_ingest_ts", TimestampType(), True),
    ]
)


def unpack_comp3(raw: bytes) -> int:
    """Décode un champ binaire Mainframe Packed Decimal (COMP-3) signé en entier."""
    hex_str = raw.hex()
    digits = int(hex_str[:-1])
    sign_nibble = hex_str[-1].lower()
    if sign_nibble in ("d", "b"):
        return -digits
    return digits


def decode_cfonb_cents(raw_14: str) -> int:
    """Décode un montant signé CFONB sur 14 caractères en centimes entiers signés."""
    prefix_13 = int(raw_14[:13])
    unit_digit, sign = CFONB_LAST_CHAR_MAP[raw_14[13]]
    return (prefix_13 * 10 + unit_digit) * sign


def cents_to_eur_decimal(cents: int) -> Decimal:
    """Convertit un montant entier en centimes vers un Decimal exact compatible BigQuery NUMERIC."""
    return (Decimal(cents) / Decimal(100)).quantize(Decimal("0.01"))


def decode_customer_partition(
    records: Iterator[bytes],
    source_uri: str,
    ingest_ts: datetime,
) -> Iterator[tuple]:
    """Décode une partition de blocs fixes 140 octets EBCDIC CP500 + COMP-3 (Clients)."""
    for raw_rec in records:
        rec = bytes(raw_rec)
        prefix = rec[:9].decode(EBCDIC_ENCODING, errors="ignore")
        if prefix == "00CFT_HDR":
            continue
        if prefix == "99CFT_TRL":
            trl_text = rec.decode(EBCDIC_ENCODING, errors="replace").strip()
            if "RC=0000" not in trl_text:
                raise RuntimeError(f"Trailer CFT invalide sur {source_uri} : {trl_text}")
            continue

        yield (
            rec[0:12].decode(EBCDIC_ENCODING).strip(),
            rec[12:16].decode(EBCDIC_ENCODING),
            rec[16:21].decode(EBCDIC_ENCODING),
            rec[21:25].decode(EBCDIC_ENCODING).strip(),
            rec[25:33].decode(EBCDIC_ENCODING),
            unpack_comp3(rec[33:35]),
            rec[35:47].decode(EBCDIC_ENCODING).strip(),
            rec[47:55].decode(EBCDIC_ENCODING),
            rec[55:63].decode(EBCDIC_ENCODING),
            rec[63:69].decode(EBCDIC_ENCODING).strip(),
            rec[69:95].decode(EBCDIC_ENCODING).strip(),
            rec[95:115].decode(EBCDIC_ENCODING).strip(),
            rec[115:125].decode(EBCDIC_ENCODING).strip(),
            rec[125:133].decode(EBCDIC_ENCODING),
            source_uri,
            ingest_ts,
        )


def decode_account_partition(
    records: Iterator[bytes],
    source_uri: str,
    ingest_ts: datetime,
) -> Iterator[tuple]:
    """Décode une partition de blocs fixes 150 octets EBCDIC CP500 + COMP-3 (Comptes)."""
    for raw_rec in records:
        rec = bytes(raw_rec)
        prefix = rec[:9].decode(EBCDIC_ENCODING, errors="ignore")
        if prefix == "00CFT_HDR":
            continue
        if prefix == "99CFT_TRL":
            trl_text = rec.decode(EBCDIC_ENCODING, errors="replace").strip()
            if "RC=0000" not in trl_text:
                raise RuntimeError(f"Trailer CFT invalide sur {source_uri} : {trl_text}")
            continue

        solde_cents = unpack_comp3(rec[115:123])
        yield (
            rec[0:11].decode(EBCDIC_ENCODING).strip(),
            rec[11:22].decode(EBCDIC_ENCODING),
            rec[22:34].decode(EBCDIC_ENCODING).strip(),
            rec[34:39].decode(EBCDIC_ENCODING),
            rec[39:43].decode(EBCDIC_ENCODING),
            rec[43:48].decode(EBCDIC_ENCODING),
            rec[48:50].decode(EBCDIC_ENCODING),
            rec[50:77].decode(EBCDIC_ENCODING),
            rec[77:87].decode(EBCDIC_ENCODING).strip(),
            rec[87:90].decode(EBCDIC_ENCODING),
            rec[90:98].decode(EBCDIC_ENCODING),
            rec[98:106].decode(EBCDIC_ENCODING),
            rec[106:112].decode(EBCDIC_ENCODING).strip(),
            unpack_comp3(rec[112:115]),
            solde_cents,
            cents_to_eur_decimal(solde_cents),
            rec[123:131].decode(EBCDIC_ENCODING),
            rec[131:150].decode(EBCDIC_ENCODING).strip(),
            source_uri,
            ingest_ts,
        )


def parse_cfonb_file_entry(
    file_entry: tuple[str, bytes],
    ingest_ts: datetime,
) -> Iterator[tuple[str, tuple]]:
    """
    Valide un fichier mensuel CFONB (.cfonb ou .cfonb.gz) via ses bannières CFT,
    rejette automatiquement les dumps interrompus (RC != 0000), et émet en un seul
    passage ordonné :
      - ('B', tuple_solde) pour les lignes '01' et '07'
      - ('M', tuple_mouvement) pour les lignes '04' enrichies de leur '05' adjacent.
    """
    file_uri, payload = file_entry
    fname = file_uri.rsplit("/", 1)[-1]
    raw_bytes = bytes(payload)
    if fname.endswith(".gz"):
        raw_bytes = gzip.decompress(raw_bytes)

    lines = raw_bytes.decode(CFONB_ENCODING).splitlines()
    if len(lines) < 2:
        raise RuntimeError(f"Fichier CFONB tronqué ou vide : {fname}")

    hdr, trl = lines[0], lines[-1]
    if not hdr.startswith("00CFT_HDR") or not trl.startswith("99CFT_TRL"):
        raise RuntimeError(f"Enveloppe CFT 00/99 absente sur {fname}")

    trl_match = re.search(
        r"RC=(\d{4})\s+DATA_RECORDS=(\d{9})\s+CHECKSUM_MVTS_04=(\d{9})",
        trl,
    )
    if trl_match is None:
        raise RuntimeError(f"Trailer 99CFT_TRL non conforme sur {fname} : {trl}")

    rc_code = trl_match.group(1)
    expected_records = int(trl_match.group(2))
    expected_mvts_04 = int(trl_match.group(3))

    if rc_code != "0000":
        logging.warning(
            "CFT ABEND DETECTE — Rejet automatique du fichier %s (RC=%s | trailer=%s)",
            fname,
            rc_code,
            trl.strip(),
        )
        return

    ym_match = re.search(r"CFONB120_MVTS_(\d{6})", fname)
    period_ym = ym_match.group(1) if ym_match else "UNKNOWN"

    body = lines[1:-1]
    if len(body) != expected_records:
        raise RuntimeError(
            f"Contrôle DATA_RECORDS en échec sur {fname} : observé={len(body)} vs attendu={expected_records}"
        )

    n_body = len(body)
    observed_04 = 0

    for idx in range(n_body):
        line = body[idx]
        rec_type = line[0:2]

        if rec_type in ("01", "07"):
            raw_amt = line[94:108]
            bal_cents = decode_cfonb_cents(raw_amt)
            yield (
                "B",
                (
                    period_ym,
                    rec_type,
                    line[2:7],
                    line[11:16],
                    line[16:19],
                    line[21:32],
                    line[32:34],
                    line[34:42],
                    line[52:83].strip(),
                    raw_amt,
                    bal_cents,
                    cents_to_eur_decimal(bal_cents),
                    fname,
                    ingest_ts,
                ),
            )
        elif rec_type == "04":
            observed_04 += 1
            raw_amt = line[94:108]
            mvt_cents = decode_cfonb_cents(raw_amt)

            has_05 = (idx + 1 < n_body) and (body[idx + 1][0:2] == "05")
            if has_05:
                line_05 = body[idx + 1]
                bic = line_05[47:59].strip() or None
                e2e_id = line_05[59:95].strip() or None
                motif = line_05[95:120].strip() or None
            else:
                bic = None
                e2e_id = None
                motif = None

            yield (
                "M",
                (
                    period_ym,
                    line[2:7],
                    line[7:11],
                    line[11:16],
                    line[16:19],
                    line[21:32],
                    line[32:34],
                    line[34:42],
                    line[42:44],
                    line[44:52],
                    line[52:83].strip(),
                    line[85:92],
                    raw_amt,
                    mvt_cents,
                    cents_to_eur_decimal(mvt_cents),
                    has_05,
                    bic,
                    e2e_id,
                    motif,
                    fname,
                    idx + 2,  # Numéro de ligne physique 1-indexé dans le fichier (après 00CFT_HDR)
                    ingest_ts,
                ),
            )

    if observed_04 != expected_mvts_04:
        raise RuntimeError(
            f"Contrôle CHECKSUM_MVTS_04 en échec sur {fname} : observé={observed_04} vs attendu={expected_mvts_04}"
        )


def write_to_biglake_iceberg_table(
    df: DataFrame,
    full_table_id: str,
    write_method: str,
    temp_gcs_bucket: str,
) -> None:
    """Écrit un DataFrame Spark en mode append dans une table BigLake Managed Iceberg pré-documentée."""
    logger.info("Schéma Spark validé avant écriture vers %s :", full_table_id)
    df.printSchema()

    writer = (
        df.write.format("bigquery")
        .option("table", full_table_id)
        .option("writeMethod", write_method)
    )
    if temp_gcs_bucket:
        writer = writer.option("temporaryGcsBucket", temp_gcs_bucket)

    writer.mode("append").save()
    logger.info("Table BigLake Managed Iceberg %s chargée avec succès.", full_table_id)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Décodage PySpark Mainframe z/OS (EBCDIC/COMP-3 & CFONB 120) vers BigLake Iceberg"
    )
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GCP_PROJECT_ID", ""),
        required=not bool(os.environ.get("GCP_PROJECT_ID")),
        help="ID du projet Google Cloud cible",
    )
    parser.add_argument(
        "--dataset",
        default=os.environ.get("BQ_DATASET_RAW", "raw_bank"),
        help="Dataset BigQuery contenant les tables BigLake Managed Iceberg pré-créées",
    )
    parser.add_argument(
        "--raw-gcs-uri",
        default=os.environ.get("RAW_COREBANKING_GCS_URI", ""),
        required=not bool(os.environ.get("RAW_COREBANKING_GCS_URI")),
        help="URI GCS racine du drop Mainframe (ex: gs://data-days-demo-landing/RAW/corebanking)",
    )
    parser.add_argument(
        "--temp-gcs-bucket",
        default=os.environ.get("GCS_BUCKET_LANDING", ""),
        help="Bucket GCS de staging temporaire pour le connecteur BigQuery",
    )
    parser.add_argument(
        "--write-method",
        choices=["direct", "indirect"],
        default="direct",
        help="Méthode d'écriture du connecteur Spark BigQuery (défaut: direct = Storage Write API)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Exécute le décodage PySpark distribué complet et valide les volumes sans écrire dans BigQuery/Iceberg",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_base_uri = args.raw_gcs_uri.rstrip("/")
    ingest_ts = datetime.now(timezone.utc)

    logger.info(
        "Démarrage du job Dataproc Serverless : source=%s -> cible=%s.%s.* (writeMethod=%s, dryRun=%s)",
        raw_base_uri,
        args.project_id,
        args.dataset,
        args.write_method,
        args.dry_run,
    )

    spark = (
        SparkSession.builder.appName("banque-hexagone-parse-corebanking-iceberg")
        .getOrCreate()
    )
    sc = spark.sparkContext
    # Force 1 tâche parallèle par fichier mensuel CFONB (~10 à 114 Mo) au lieu de les grouper
    sc._jsc.hadoopConfiguration().set(
        "mapreduce.input.fileinputformat.split.maxsize", "33554432"
    )

    def emit_or_validate(df: DataFrame, table_name: str) -> None:
        full_table_id = f"{args.project_id}.{args.dataset}.{table_name}"
        if args.dry_run:
            row_count = df.count()
            logger.info(
                "[DRY-RUN] Décodage validé sans écriture pour %s : %d lignes (0 mutation BigQuery/Iceberg).",
                full_table_id,
                row_count,
            )
            return
        write_to_biglake_iceberg_table(
            df=df,
            full_table_id=full_table_id,
            write_method=args.write_method,
            temp_gcs_bucket=args.temp_gcs_bucket,
        )

    # 1. Référentiel Clients EBCDIC CP500 + COMP-3 (RECFM=FB, LRECL=140)
    customers_uri = f"{raw_base_uri}/CBK_CUSTOMERS_REF_20261112.ebcdic"
    logger.info("[1/4] Décodage binaire RECFM=FB (LRECL=140) : %s", customers_uri)
    customers_rdd = sc.binaryRecords(customers_uri, 140).mapPartitions(
        lambda part: decode_customer_partition(part, customers_uri, ingest_ts)
    )
    customers_df = spark.createDataFrame(customers_rdd, schema=CUSTOMERS_SCHEMA)
    emit_or_validate(customers_df, "cbk_customers_ref")

    # 2. Référentiel Comptes EBCDIC CP500 + COMP-3 (RECFM=FB, LRECL=150)
    accounts_uri = f"{raw_base_uri}/CBK_ACCOUNTS_MSTR_20261112.ebcdic"
    logger.info("[2/4] Décodage binaire RECFM=FB (LRECL=150) : %s", accounts_uri)
    accounts_rdd = sc.binaryRecords(accounts_uri, 150).mapPartitions(
        lambda part: decode_account_partition(part, accounts_uri, ingest_ts)
    )
    accounts_df = spark.createDataFrame(accounts_rdd, schema=ACCOUNTS_SCHEMA)
    emit_or_validate(accounts_df, "cbk_accounts_master")

    # 3 & 4. Relevés multi-lignes CFONB 120 (.cfonb.gz 2025 + .cfonb 2026)
    cfonb_glob = f"{raw_base_uri}/CFONB120_MVTS_*"
    logger.info(
        "[3/4] Lecture distribuée CFONB 120 + filtrage CFT RC=0000 + rattachement 04/05 : %s",
        cfonb_glob,
    )
    cfonb_tagged_rdd = (
        sc.binaryFiles(cfonb_glob, minPartitions=19)
        .flatMap(lambda entry: parse_cfonb_file_entry(entry, ingest_ts))
        .persist(StorageLevel.MEMORY_AND_DISK)
    )

    balances_rdd = cfonb_tagged_rdd.filter(lambda item: item[0] == "B").map(
        lambda item: item[1]
    )
    balances_df = spark.createDataFrame(balances_rdd, schema=BALANCES_SCHEMA)
    emit_or_validate(balances_df, "cbk_cfonb_balances")

    logger.info("[4/4] Traitement des mouvements CFONB '04' enrichis des compléments SEPA '05'...")
    movements_rdd = cfonb_tagged_rdd.filter(lambda item: item[0] == "M").map(
        lambda item: item[1]
    )
    movements_df = spark.createDataFrame(movements_rdd, schema=MOVEMENTS_SCHEMA)
    emit_or_validate(movements_df, "cbk_cfonb_movements")

    cfonb_tagged_rdd.unpersist()
    logger.info(
        "Job PySpark Mainframe -> BigLake Managed Iceberg terminé avec succès (dryRun=%s).",
        args.dry_run,
    )
    spark.stop()


if __name__ == "__main__":
    main()
