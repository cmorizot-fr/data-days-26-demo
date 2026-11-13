"""
Validation de bout en bout des fichiers Core Banking « Dirty Mainframe »
générés dans `00_data_generator/output/corebanking/`.

Reproduit exactement la logique que le job Managed Spark exécutera en Démo #1 :
1. Lecture binaire `RECFM=FB` (sans '\\n') + transcodage `EBCDIC CP500` + décodage `COMP-3`
2. Contrôle des bannières CFT (`00CFT_HDR` / `99CFT_TRL`) et rejet automatique du dump
   en erreur `CFONB120_MVTS_202610_RUN01.cfonb` (`STATUS=ABEND_S0C7`, `RC=0012`)
3. Lecture mixte `.cfonb.gz` (2025) et `.cfonb` (2026) avec rattachement par ordre physique
   (`LEAD` sur le numéro de ligne) des enregistrements complémentaires `05` (BIC & EndToEndId)
   sur leur mouvement `04` parent
4. Vérification au centime près de 100 % des invariants de `AGENTS.md`.
"""

from __future__ import annotations

import gzip
import re
from pathlib import Path

import duckdb
import polars as pl

BASE_DIR: Path = Path(__file__).resolve().parent
COREBANKING_DIR: Path = BASE_DIR / "output" / "corebanking"
UNIVERSE_DIR: Path = BASE_DIR / "data" / "universe"
EBCDIC_ENCODING: str = "cp500"


def unpack_comp3(raw: bytes) -> int:
    """Décode un champ binaire Mainframe Packed Decimal (COMP-3) signé."""
    hex_str = raw.hex()
    digits = int(hex_str[:-1])
    sign_nibble = hex_str[-1].lower()
    if sign_nibble in ("d", "b"):
        return -digits
    return digits


def decode_ebcdic_customers(path: Path) -> pl.DataFrame:
    data = path.read_bytes()
    assert b"\n" not in data[:140], "Le flux RECFM=FB ne doit pas être délimité par LF"
    assert len(data) % 140 == 0, f"Taille non multiple de LRECL=140 : {len(data)}"
    n_blocks = len(data) // 140

    hdr = data[:140].decode(EBCDIC_ENCODING)
    trl = data[-140:].decode(EBCDIC_ENCODING)
    assert hdr.startswith("00CFT_HDR") and "RC=0000" in trl

    rows = []
    for idx in range(1, n_blocks - 1):
        rec = data[idx * 140 : (idx + 1) * 140]
        rows.append(
            (
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
            )
        )
    return pl.DataFrame(
        rows,
        schema=[
            "customer_id",
            "code_agence_raw",
            "code_guichet_raw",
            "region_code",
            "birth_date",
            "age",
            "segment",
            "onboarding_date",
            "closure_date",
            "status",
            "last_name",
            "first_name",
        ],
        orient="row",
    )


def decode_ebcdic_accounts(path: Path) -> pl.DataFrame:
    data = path.read_bytes()
    assert len(data) % 150 == 0, f"Taille non multiple de LRECL=150 : {len(data)}"
    n_blocks = len(data) // 150

    hdr = data[:150].decode(EBCDIC_ENCODING)
    trl = data[-150:].decode(EBCDIC_ENCODING)
    assert hdr.startswith("00CFT_HDR") and "RC=0000" in trl

    rows = []
    for idx in range(1, n_blocks - 1):
        rec = data[idx * 150 : (idx + 1) * 150]
        rows.append(
            (
                rec[0:11].decode(EBCDIC_ENCODING).strip(),
                rec[11:22].decode(EBCDIC_ENCODING),
                rec[22:34].decode(EBCDIC_ENCODING).strip(),
                rec[34:39].decode(EBCDIC_ENCODING),
                rec[39:43].decode(EBCDIC_ENCODING),
                rec[43:48].decode(EBCDIC_ENCODING),
                rec[48:50].decode(EBCDIC_ENCODING),
                rec[50:77].decode(EBCDIC_ENCODING),
                rec[77:87].decode(EBCDIC_ENCODING).strip(),
                rec[90:98].decode(EBCDIC_ENCODING),
                rec[98:106].decode(EBCDIC_ENCODING),
                rec[106:112].decode(EBCDIC_ENCODING).strip(),
                unpack_comp3(rec[112:115]),
                unpack_comp3(rec[115:123]),
            )
        )
    return pl.DataFrame(
        rows,
        schema=[
            "account_id",
            "num_compte_11",
            "customer_id",
            "bank_code",
            "code_agence_raw",
            "code_guichet_raw",
            "cle_rib",
            "iban",
            "account_type",
            "opening_date",
            "closure_date",
            "status",
            "rate_bps",
            "solde_veille_cents",
        ],
        orient="row",
    )


def cfonb_sql_cents_expr(raw_col: str) -> str:
    return f"""
    (
        CAST(SUBSTR({raw_col}, 1, 13) AS BIGINT) * 10
        + CASE SUBSTR({raw_col}, 14, 1)
            WHEN '{{' THEN 0 WHEN 'A' THEN 1 WHEN 'B' THEN 2 WHEN 'C' THEN 3 WHEN 'D' THEN 4
            WHEN 'E' THEN 5 WHEN 'F' THEN 6 WHEN 'G' THEN 7 WHEN 'H' THEN 8 WHEN 'I' THEN 9
            WHEN '}}' THEN 0 WHEN 'J' THEN 1 WHEN 'K' THEN 2 WHEN 'L' THEN 3 WHEN 'M' THEN 4
            WHEN 'N' THEN 5 WHEN 'O' THEN 6 WHEN 'P' THEN 7 WHEN 'Q' THEN 8 WHEN 'R' THEN 9
          END
    ) * CASE
        WHEN SUBSTR({raw_col}, 14, 1) IN ('{{','A','B','C','D','E','F','G','H','I') THEN 1
        ELSE -1
    END
    """


def load_valid_cfonb_files() -> tuple[pl.DataFrame, list[str]]:
    """Lit les fichiers .cfonb.gz et .cfonb en validant le trailer 99CFT_TRL RC=0000."""
    all_files = sorted(
        list(COREBANKING_DIR.glob("*.cfonb.gz")) + list(COREBANKING_DIR.glob("*.cfonb"))
    )
    rejected_files: list[str] = []
    frames: list[pl.DataFrame] = []

    trl_re = re.compile(r"RC=(\d{4})\s+DATA_RECORDS=(\d{9})\s+CHECKSUM_MVTS_04=(\d{9})")

    for fpath in all_files:
        raw_bytes = gzip.decompress(fpath.read_bytes()) if fpath.name.endswith(".gz") else fpath.read_bytes()
        lines = raw_bytes.decode("iso-8859-15").splitlines()
        hdr, trl = lines[0], lines[-1]
        assert hdr.startswith("00CFT_HDR") and trl.startswith("99CFT_TRL")

        m = trl_re.search(trl)
        assert m is not None, f"Trailer illisible sur {fpath.name}: {trl}"
        rc, exp_records, exp_04 = m.group(1), int(m.group(2)), int(m.group(3))

        if rc != "0000":
            rejected_files.append(f"{fpath.name} (RC={rc})")
            continue

        body_lines = lines[1:-1]
        assert len(body_lines) == exp_records, f"Écart DATA_RECORDS sur {fpath.name}"

        df_f = pl.DataFrame(
            {
                "source_file": [fpath.name] * len(body_lines),
                "line_no": list(range(1, len(body_lines) + 1)),
                "raw_line": body_lines,
            }
        )
        obs_04 = df_f.filter(pl.col("raw_line").str.starts_with("04")).height
        assert obs_04 == exp_04, f"Écart CHECKSUM_MVTS_04 sur {fpath.name}"
        frames.append(df_f)

    return pl.concat(frames), rejected_files


def run_validation() -> None:
    print("=== VERIFICATION DES FICHIERS 'DIRTY MAINFRAME' & INVARIANTS (AGENTS.md) ===\n")

    # 1. Décodage binaire EBCDIC CP500 + COMP-3 des référentiels maîtres
    parsed_customers_df = decode_ebcdic_customers(COREBANKING_DIR / "CBK_CUSTOMERS_REF_20261112.ebcdic")
    parsed_accounts_df = decode_ebcdic_accounts(COREBANKING_DIR / "CBK_ACCOUNTS_MSTR_20261112.ebcdic")

    # 2. Filtrage CFT (détection ABEND) + lecture .cfonb.gz / .cfonb avec ordre physique des lignes
    valid_cfonb_df, rejected = load_valid_cfonb_files()
    print(f"[OK] Fichier(s) CFT en ABEND écarté(s) : {rejected}")
    assert len(rejected) == 1 and "CFONB120_MVTS_202610_RUN01.cfonb" in rejected[0]

    con = duckdb.connect(":memory:")
    con.register("parsed_customers", parsed_customers_df)
    con.register("parsed_accounts", parsed_accounts_df)
    con.register("raw_cfonb_ordered", valid_cfonb_df)

    # 3. Simulation exacte du Windowing Spark : rattachement de la ligne '05' (BIC + EndToEndId)
    #    située physiquement juste sous sa ligne '04' parente !
    con.execute(
        f"""
        CREATE VIEW stitched_cfonb AS
        WITH with_next AS (
            SELECT
                source_file,
                line_no,
                raw_line,
                SUBSTR(raw_line, 1, 2) AS record_type,
                LEAD(raw_line) OVER (PARTITION BY source_file ORDER BY line_no) AS next_line
            FROM raw_cfonb_ordered
        )
        SELECT
            record_type,
            SUBSTR(raw_line, 3, 5)          AS bank_code,
            SUBSTR(raw_line, 8, 4)          AS code_op_interne,
            SUBSTR(raw_line, 12, 5)         AS code_guichet_raw,
            SUBSTR(raw_line, 22, 11)        AS num_compte_11,
            SUBSTR(raw_line, 33, 2)         AS code_afb,
            SUBSTR(raw_line, 35, 8)         AS date_compta,
            SUBSTR(raw_line, 45, 8)         AS date_valeur,
            TRIM(SUBSTR(raw_line, 53, 31))  AS libelle,
            {cfonb_sql_cents_expr("SUBSTR(raw_line, 95, 14)")} AS signed_cents,
            CASE
                WHEN record_type = '04' AND SUBSTR(next_line, 1, 2) = '05'
                THEN TRIM(SUBSTR(next_line, 48, 12))
                ELSE NULL
            END AS counterparty_bic,
            CASE
                WHEN record_type = '04' AND SUBSTR(next_line, 1, 2) = '05'
                THEN TRIM(SUBSTR(next_line, 60, 36))
                ELSE NULL
            END AS sepa_end_to_end_id,
            LENGTH(raw_line) AS line_len
        FROM with_next
        WHERE record_type IN ('01', '04', '07');
        """
    )

    # A. Volumétries & Orphelins AWS S3
    c_cnt, n_reg = con.execute("SELECT COUNT(*), COUNT(DISTINCT region_code) FROM parsed_customers").fetchone()
    a_cnt, a_closed, a_recent_mf = con.execute(
        """
        SELECT
            COUNT(*),
            COUNT(*) FILTER (WHERE closure_date <> '00000000' OR status <> 'OUVERT'),
            COUNT(*) FILTER (WHERE opening_date >= '20260815')
        FROM parsed_accounts
        """
    ).fetchone()
    aws_cust_total, aws_acc_total, aws_orphans, total_recent_open = con.execute(
        f"""
        SELECT
            (SELECT COUNT(*) FROM '{UNIVERSE_DIR}/customers.parquet'),
            (SELECT COUNT(*) FROM '{UNIVERSE_DIR}/accounts.parquet'),
            (SELECT COUNT(*) FROM '{UNIVERSE_DIR}/accounts.parquet' a
             LEFT JOIN parsed_accounts m ON a.account_id = m.account_id
             WHERE m.account_id IS NULL),
            (SELECT COUNT(*) FROM '{UNIVERSE_DIR}/accounts.parquet' WHERE opening_date >= '20260815')
        """
    ).fetchone()

    print(f"[OK] Clients EBCDIC+COMP3        : {c_cnt:,} / {aws_cust_total:,} ({n_reg} régions)")
    print(f"[OK] Comptes EBCDIC+COMP3        : {a_cnt:,} / {aws_acc_total:,} (orphelins AWS={aws_orphans:,}, clôtures={a_closed})")
    print(f"[OK] Ouvertures récentes 90j     : {total_recent_open:,} ({a_recent_mf:,} MF + {aws_orphans:,} AWS)")
    assert (c_cnt, n_reg, a_cnt, a_closed, aws_orphans, total_recent_open) == (
        79_350,
        8,
        94_350,
        0,
        650,
        15_000,
    )

    # B. Mouvements 04 + Compléments 05 + Anomalies RAW préservées
    mvt_cnt, stitched_05_cnt, bad_dates_cnt, noisy_guichet_cnt, min_cf, max_cf = con.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE record_type = '04'),
            COUNT(*) FILTER (WHERE record_type = '04' AND counterparty_bic IS NOT NULL),
            COUNT(*) FILTER (WHERE record_type = '04' AND date_valeur IN ('00000000', '99999999')),
            COUNT(*) FILTER (WHERE record_type = '04' AND (RIGHT(code_guichet_raw, 1) = ' ' OR TRIM(code_guichet_raw) = '')),
            MIN(line_len),
            MAX(line_len)
        FROM stitched_cfonb
        """
    ).fetchone()
    bad_date_pct = 100.0 * bad_dates_cnt / mvt_cnt
    print(
        f"[OK] Mouvements '04' + '05'      : {mvt_cnt:,} '04' (dont {stitched_05_cnt:,} enrichis par ligne '05' adjacente, LRECL={min_cf}..{max_cf})"
    )
    print(
        f"[OK] Anomalies RAW préservées    : {bad_dates_cnt:,} dates 00000000/99999999 ({bad_date_pct:.2f}%), "
        f"{noisy_guichet_cnt:,} guichets décalés/blancs"
    )
    assert (mvt_cnt, min_cf, max_cf) == (5_500_000, 120, 120)
    assert stitched_05_cnt > 3_000_000
    assert abs(bad_date_pct - 1.20) < 0.01

    # C. Fuite exacte des dépôts à vue sur 90j (récupérée grâce au BIC porté par la ligne '05' !)
    total_leak_cents, young_1_5_cents = con.execute(
        """
        SELECT
            SUM(-m.signed_cents) AS total_leak_cents,
            SUM(-m.signed_cents) FILTER (
                WHERE c.age BETWEEN 18 AND 32
                  AND CAST(SUBSTR(m.date_compta, 7, 2) AS INTEGER) BETWEEN 1 AND 5
            ) AS young_1_5_cents
        FROM stitched_cfonb m
        JOIN parsed_accounts a ON m.num_compte_11 = a.num_compte_11
        JOIN parsed_customers c ON a.customer_id = c.customer_id
        WHERE m.record_type = '04'
          AND m.code_op_interne = '0810'
          AND m.counterparty_bic IN ('REVOLT21XXX', 'TRBKDEBBXXX', 'NTSBDEB1XXX', 'BOURFRPPXXX', 'DEGIRO2AXXX')
          AND m.date_compta BETWEEN '20260815' AND '20261112'
        """
    ).fetchone()
    print(
        f"[OK] Fuite 90j via BIC ligne '05': {total_leak_cents / 100:,.2f} € | "
        f"Part 18-32 ans j1..5 = {young_1_5_cents / 100:,.2f} € ({100.0 * young_1_5_cents / total_leak_cents:.2f}%)"
    )
    assert total_leak_cents == 242_000_000_000
    assert young_1_5_cents == 164_560_000_000

    # D. Réconciliation 01 + 04 = 07 = Master Solde COMP-3
    unbalanced_202611 = con.execute(
        """
        WITH nov AS (
            SELECT
                num_compte_11,
                SUM(signed_cents) FILTER (WHERE record_type = '01') AS s01,
                COALESCE(SUM(signed_cents) FILTER (WHERE record_type = '04'), 0) AS m04,
                SUM(signed_cents) FILTER (WHERE record_type = '07') AS s07
            FROM stitched_cfonb
            WHERE SUBSTR(date_compta, 1, 6) = '202611'
            GROUP BY num_compte_11
        )
        SELECT COUNT(*)
        FROM nov n
        JOIN parsed_accounts a ON n.num_compte_11 = a.num_compte_11
        WHERE (n.s01 + n.m04 <> n.s07) OR (n.s07 <> a.solde_veille_cents)
        """
    ).fetchone()[0]
    print(f"[OK] Réconciliation COMP-3 Master: {unbalanced_202611} écart sur 94 350 comptes")
    assert unbalanced_202611 == 0

    # E. Client témoin Démo #4 (Lucas Martin)
    nov_net_cents, strm_oct, strm_nov, sante_nov, leak_sep_oct = con.execute(
        """
        SELECT
            SUM(signed_cents) FILTER (WHERE record_type = '04' AND SUBSTR(date_compta, 1, 6) = '202611'),
            SUM(-signed_cents) FILTER (WHERE record_type = '04' AND date_compta = '20261008' AND counterparty_bic = 'STRMFLIXEUR'),
            SUM(-signed_cents) FILTER (WHERE record_type = '04' AND date_compta = '20261108' AND counterparty_bic = 'STRMFLIXEUR'),
            SUM(signed_cents) FILTER (WHERE record_type = '04' AND date_compta = '20261110' AND counterparty_bic = 'CPAMIDF7500'),
            SUM(-signed_cents) FILTER (WHERE record_type = '04' AND date_compta IN ('20260903', '20261003') AND counterparty_bic = 'REVOLT21XXX')
        FROM stitched_cfonb
        WHERE num_compte_11 = '00000002026'
        """
    ).fetchone()
    projected_eom_surplus_cents = nov_net_cents - 63_800
    print(
        f"[OK] Témoin Démo #4 (Lucas Martin): Streaming {strm_oct/100:.2f}€ -> {strm_nov/100:.2f}€ (+{(strm_nov-strm_oct)/100:.2f}€), "
        f"Santé +{sante_nov/100:.2f}€, Excédent fin de mois = +{projected_eom_surplus_cents/100:.2f}€"
    )
    assert (strm_oct, strm_nov, sante_nov, leak_sep_oct, projected_eom_surplus_cents) == (
        1_599,
        1_999,
        4_200,
        90_000,
        30_000,
    )

    print("\nSUCCÈS TOTAL : Les fichiers 'Dirty Mainframe' (EBCDIC+COMP3, CFONB 04+05, ABEND CFT, GZIP) sont prêts pour Spark !")


if __name__ == "__main__":
    run_validation()
