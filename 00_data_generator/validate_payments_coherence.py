"""
Contrôle local de cohérence Historique (Parquet 18 mois) ↔ Temps réel (Pub/Sub) du silo Paiements.

Génère un lot temps réel en mémoire (sans appel Pub/Sub) et vérifie qu'il est décrit exactement
comme l'archive historique :
  1. Schéma : mêmes blocs STRUCT et mêmes sous-champs, dans le même ordre.
  2. Contreparties : chaque (nom, BIC, IBAN, schéma, libellé) du temps réel existe dans l'historique.
  3. Néobanques : l'IBAN externe d'un client vers une néobanque est identique dans les deux sources.
  4. Identité : le nom du débiteur correspond au `customer_id` (référentiel partagé).
  5. Enrôlements IBAN : mêmes canal / statut SCA / IP / libellé pour un même client ; aucun ré-enrôlement.
  6. Identifiants : aucune collision d'`end_to_end_id` entre historique et temps réel.

Usage :
  uv run python 00_data_generator/validate_payments_coherence.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import polars as pl

from shared_universe import DEMO_SEED, build_or_load_universe
from stream_payments_pubsub import _enrolled_pairs, build_witness_live_events, generate_live_event_batch

PAYMENTS_DIR = Path(__file__).resolve().parent / "output" / "RAW" / "PAYMENTS"


def _struct_layout(df: pl.DataFrame) -> list[tuple[str, list[str]]]:
    return [(name, [f.name for f in dtype.fields]) for name, dtype in df.schema.items()]


def main() -> int:
    universe = build_or_load_universe()
    hist = pl.read_parquet(PAYMENTS_DIR / "sepa_payment_events" / "*.parquet")
    hist_iban = pl.read_parquet(PAYMENTS_DIR / "iban_beneficiary_events" / "*.parquet")

    rng = np.random.default_rng(DEMO_SEED + 777)
    p_msgs, i_msgs = generate_live_event_batch(rng, universe, 3_000, 0, _enrolled_pairs(universe))
    w_msgs, _ = build_witness_live_events(universe)
    live = pl.DataFrame(p_msgs + w_msgs)
    live_iban = pl.DataFrame(i_msgs) if i_msgs else None

    checks: list[tuple[str, bool, str]] = []

    # 1. Schéma STRUCT identique
    live_layout = _struct_layout(live)
    checks.append(("Schéma STRUCT paiements identique", live_layout == _struct_layout(hist), str(live_layout)))
    if live_iban is not None:
        checks.append(("Schéma STRUCT enrôlements identique", _struct_layout(live_iban) == _struct_layout(hist_iban), ""))

    def flat(df: pl.DataFrame) -> pl.DataFrame:
        return df.select([
            pl.col("header").struct.field("end_to_end_id"),
            pl.col("settlement").struct.field("payment_scheme"),
            pl.col("debtor").struct.field("customer_id"),
            pl.col("debtor").struct.field("full_name"),
            pl.col("creditor").struct.field("name").alias("cr_name"),
            pl.col("creditor").struct.field("iban").alias("cr_iban"),
            pl.col("creditor").struct.field("agent_bic").alias("cr_bic"),
            pl.col("remittance").struct.field("unstructured_info").alias("label"),
        ])

    h, lv = flat(hist), flat(live)
    neo_bics = ["REVOLT21XXX", "TRBKDEBBXXX", "NTSBDEB1XXX", "BOURFRPPXXX", "DEGIRO2AXXX"]

    # 2. Contreparties non-néobanques
    cp_cols = ["cr_name", "cr_bic", "cr_iban", "payment_scheme", "label"]
    hist_cps = h.filter(~pl.col("cr_bic").is_in(neo_bics)).select(cp_cols).unique()
    live_cps = lv.filter(~pl.col("cr_bic").is_in(neo_bics)).select(cp_cols).unique()
    unknown_cps = live_cps.join(hist_cps, on=cp_cols, how="anti")
    checks.append(("Contreparties temps réel présentes dans l'historique", unknown_cps.height == 0, str(unknown_cps.head(5))))

    # 3. IBAN néobanque par (client, BIC)
    hist_neo = h.filter(pl.col("cr_bic").is_in(neo_bics)).select(["customer_id", "cr_bic", "cr_iban"]).unique()
    live_neo = lv.filter(pl.col("cr_bic").is_in(neo_bics)).select(["customer_id", "cr_bic", "cr_iban"]).unique()
    joined = live_neo.join(hist_neo, on=["customer_id", "cr_bic"], how="inner", suffix="_hist")
    mismatch = joined.filter(pl.col("cr_iban") != pl.col("cr_iban_hist"))
    checks.append((
        f"IBAN néobanque identique ({joined.height} couples communs)",
        joined.height > 0 and mismatch.height == 0,
        str(mismatch.head(5)),
    ))
    ambiguous = hist_neo.group_by(["customer_id", "cr_bic"]).len().filter(pl.col("len") > 1)
    checks.append(("Un seul IBAN néobanque par (client, BIC) dans l'historique", ambiguous.height == 0, str(ambiguous.head(5))))

    # 4. Nom du débiteur conforme au référentiel
    ref_names = universe["customers"].select([
        "customer_id",
        (pl.col("first_name") + " " + pl.col("last_name")).alias("ref_name"),
    ])
    bad_names = lv.join(ref_names, on="customer_id").filter(pl.col("full_name") != pl.col("ref_name"))
    checks.append(("Nom du débiteur conforme au customer_id", bad_names.height == 0, str(bad_names.head(5))))

    # 5. Enrôlements : attributs digitaux identiques + aucun ré-enrôlement
    if live_iban is not None:
        def iflat(df: pl.DataFrame) -> pl.DataFrame:
            return df.select([
                pl.col("account_holder").struct.field("customer_id"),
                pl.col("beneficiary").struct.field("agent_bic").alias("bic"),
                pl.col("security_context").struct.field("channel"),
                pl.col("security_context").struct.field("sca_strong_auth_status"),
                pl.col("security_context").struct.field("device_ip"),
            ])
        hi, li = iflat(hist_iban).unique(), iflat(live_iban).unique()
        attrs = ["channel", "sca_strong_auth_status", "device_ip"]
        common = li.join(hi.select(["customer_id"] + attrs).unique(), on="customer_id", how="inner", suffix="_hist")
        bad_attrs = common.filter(
            (pl.col("channel") != pl.col("channel_hist"))
            | (pl.col("sca_strong_auth_status") != pl.col("sca_strong_auth_status_hist"))
            | (pl.col("device_ip") != pl.col("device_ip_hist"))
        )
        checks.append((f"Attributs digitaux identiques ({common.height} clients communs)", bad_attrs.height == 0, ""))
        re_enrolled = li.join(hi, on=["customer_id", "bic"], how="semi")
        checks.append(("Aucun ré-enrôlement d'un bénéficiaire déjà connu", re_enrolled.height == 0, str(re_enrolled.head(5))))

    # 6. Collisions d'identifiants
    collisions = lv.select("end_to_end_id").unique().join(h.select("end_to_end_id").unique(), on="end_to_end_id", how="semi")
    checks.append(("Aucune collision end_to_end_id historique / temps réel", collisions.height == 0, str(collisions.head(5))))

    ok_all = True
    for name, ok, detail in checks:
        ok_all &= ok
        print(f"[{'OK ' if ok else 'KO '}] {name}")
        if not ok and detail:
            print(f"      {detail}")
    print(f"\nRésultat : {sum(c[1] for c in checks)}/{len(checks)} contrôles OK")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
