"""
Contrôle croisé inter-silos (lecture seule, seed=2026) appelé en fin de scripts/generate_all_data.sh.

Vérifie que tous les silos générés localement racontent la même histoire :
univers partagé <-> AWS CRM <-> Paiements <-> Finance SAP / ALM <-> PDF avenants.
Les contrôles intra-silo restent dans validate_corebanking.py et validate_payments_coherence.py.
Code retour 1 si au moins un contrôle échoue.
"""
import re
import sys
from pathlib import Path

import duckdb
import polars as pl

G = Path(__file__).resolve().parent
U = G / "data" / "universe"
R = G / "output" / "RAW"
c = duckdb.connect()
results: list[tuple[bool, str]] = []


def check(ok: bool, label: str) -> None:
    results.append((bool(ok), label))
    print(f"[{'OK ' if ok else 'KO '}] {label}")


def q(sql: str):
    return c.execute(sql).fetchall()


cust = pl.read_parquet(U / "customers.parquet")
acc = pl.read_parquet(U / "accounts.parquet")
ag = pl.read_parquet(U / "agencies.parquet")
leak = pl.read_parquet(U / "leak_events_90d.parquet")
c.register("u_cust", cust)
c.register("u_acc", acc)
c.register("u_ag", ag)
c.register("u_leak", leak)

AWS_C = f"read_parquet('{R}/AWS/crm_customers/*.parquet')"
AWS_A = f"read_parquet('{R}/AWS/crm_account_portfolio/*.parquet')"
AWS_B = f"read_parquet('{R}/AWS/crm_branches_ref/*.parquet')"
PAY = f"read_parquet('{R}/PAYMENTS/sepa_payment_events/*.parquet')"
FIN = f"read_parquet('{R}/FINANCE_SAP_ALM/raw_sap_gl_alm.parquet')"
GT = f"read_parquet('{U}/promo_pdfs_ground_truth.parquet')"

print("== Univers <-> AWS CRM ==")
check(q(f"""SELECT COUNT(*) FROM u_cust u FULL JOIN {AWS_C} a USING (customer_id)
          WHERE u.customer_id IS NULL OR a.customer_id IS NULL OR u.agency_code_4 <> a.agency_code_4
             OR u.age <> a.age OR u.region_code <> a.region_code""")[0][0] == 0,
      "80 000 clients AWS identiques à l'univers (id, agence, région, âge)")
check(q(f"""SELECT COUNT(*) FROM u_acc u FULL JOIN {AWS_A} a USING (account_id)
          WHERE u.account_id IS NULL OR a.account_id IS NULL OR u.iban <> a.iban
             OR u.customer_id <> a.customer_id OR u.account_type <> a.account_type""")[0][0] == 0,
      "95 000 comptes AWS identiques à l'univers (id, IBAN, titulaire, type)")
check(q(f"SELECT COUNT(*) FROM u_ag u FULL JOIN {AWS_B} a USING (agency_code_4) "
        "WHERE u.agency_code_4 IS NULL OR a.agency_code_4 IS NULL OR u.region_code <> a.region_code")[0][0] == 0,
      "450 agences AWS identiques à l'univers")

print("== Paiements ==")
NEO = "('REVOLT21XXX','TRBKDEBBXXX','NTSBDEB1XXX','BOURFRPPXXX','DEGIRO2AXXX')"
dedup = f"""(SELECT * FROM {PAY} QUALIFY ROW_NUMBER() OVER (PARTITION BY header.end_to_end_id
             ORDER BY header.execution_ts) = 1)"""
pay_daily = (c.sql(f"""
    SELECT strftime(CAST(header.execution_ts AT TIME ZONE 'Europe/Paris' AS DATE), '%Y%m%d') AS d,
           SUM(instructed_amount.amount_cents) AS cents
    FROM {dedup} WHERE settlement.tx_status = 'ACSC' AND creditor.agent_bic IN {NEO}
      AND CAST(header.execution_ts AT TIME ZONE 'Europe/Paris' AS DATE) BETWEEN DATE '2026-08-15' AND DATE '2026-11-12'
    GROUP BY 1""").pl())
u_daily = leak.group_by("accounting_date").agg(pl.col("amount_cents").sum().alias("u_cents")).rename({"accounting_date": "d"})
cmp_ = u_daily.join(pay_daily, on="d", how="full", coalesce=True).fill_null(0)
check(int(pay_daily["cents"].sum()) == 242_000_000_000, f"Fuite paiements dédoublonnée ACSC 90 j = {pay_daily['cents'].sum() / 100:,.2f} €")
check(cmp_.filter(pl.col("u_cents") != pl.col("cents")).height == 0, "Fuite paiements = univers, jour par jour (90 jours)")
check(q(f"""SELECT COUNT(*) FROM {PAY} p LEFT JOIN u_acc a ON a.account_id = p.debtor.account_id
          WHERE a.account_id IS NULL OR a.iban <> p.debtor.iban OR a.customer_id <> p.debtor.customer_id""")[0][0] == 0,
      "Tous les débiteurs paiements existent dans l'univers (compte, IBAN, client cohérents)")

print("== Finance SAP / ALM ==")
fin_alm = (c.sql(f"SELECT strftime(posting_date, '%Y%m%d') d, item_text FROM {FIN} "
                                  "WHERE source_system = 'ALM_TCI_DROP'").pl())
fin_alm = fin_alm.with_columns(
    pl.col("item_text").map_elements(
        lambda t: int(round(float(re.search(r"assiette ([\d ]+\.\d{2})", t).group(1).replace(" ", "")) * 100)),
        return_dtype=pl.Int64).alias("draw_cents"))
cmp2 = fin_alm.join(pay_daily, on="d", how="full", coalesce=True).fill_null(0)
check(cmp2.filter(pl.col("draw_cents") != pl.col("cents")).height == 0,
      "Assiette ALM quotidienne (Finance) = fuite paiements du jour (90 jours)")
check(q(f"SELECT COUNT(*) FROM {FIN} f LEFT JOIN u_ag a ON a.agency_code_4 = f.agency_code "
        "WHERE a.agency_code_4 IS NULL AND f.agency_code <> '0000'")[0][0] == 0,
      "Agences Finance toutes présentes dans l'univers (+ 0000 Trésorerie)")
check(q(f"SELECT COUNT(*) FROM {FIN} f JOIN u_ag a ON a.agency_code_4 = f.agency_code WHERE a.region_code <> f.region_code")[0][0] == 0,
      "Régions Finance cohérentes avec l'univers")
check(q(f"""SELECT COUNT(*) FROM {FIN} WHERE source_system = 'SAP_FI_LIAISON' AND regexp_extract(item_text, 'VIR INT (ACC\\d+)', 1)
          NOT IN (SELECT account_id FROM u_acc WHERE account_type = 'CC_CHQ')""")[0][0] == 0,
      "Virements internes 58* : comptes courants sources existants")
check(q(f"SELECT MIN(posting_date) >= DATE '2026-08-15' AND MAX(posting_date) <= DATE '2026-11-12' FROM {FIN}")[0][0],
      "Finance dans la fenêtre 90 j [2026-08-15 .. 2026-11-12]")

print("== PDF avenants ==")
check(q(f"SELECT SUM(committed_cents) FROM {GT}")[0][0] == 1_430_000_000, "250 PDF = 14 300 000,00 €")
check(q(f"SELECT COUNT(*) FROM {GT} g LEFT JOIN u_ag a ON a.agency_code_4 = g.primary_branch_code "
        "WHERE a.agency_code_4 IS NULL OR a.region_code <> g.region_code")[0][0] == 0,
      "Agences / régions des PDF cohérentes avec l'univers")
check(q(f"""SELECT COUNT(*) FROM (SELECT DISTINCT promo_contract_id FROM {AWS_A} WHERE promo_contract_id IS NOT NULL) a
          FULL JOIN {GT} g USING (promo_contract_id) WHERE a.promo_contract_id IS NULL OR g.promo_contract_id IS NULL""")[0][0] == 0,
      "Contrats PDF référencés par le CRM AWS = 250 PDF générés")

print("== Client témoin CUST00002026 ==")
check(q(f"""SELECT (SELECT COUNT(*) FROM {AWS_C} WHERE customer_id='CUST00002026')
             + (SELECT COUNT(*) > 0 FROM {PAY} WHERE debtor.customer_id='CUST00002026')::INT""")[0][0] == 2,
      "Témoin présent dans AWS et dans les paiements")
AWS_I = f"read_parquet('{R}/AWS/crm_interactions/*.parquet')"
check(q(f"""SELECT COUNT(*) = 1 AND MIN(account_type) = 'CC_CHQ' FROM {AWS_A}
            WHERE customer_id='CUST00002026'""")[0][0],
      "Témoin : un seul compte, le compte courant (l'agent Démo #4 ouvre le livret)")
check(q(f"""SELECT COUNT(*) FROM {AWS_I} WHERE customer_id='CUST00002026'
            AND topic_code = 'OFFRE_PROMO_TAUX_BOOSTE_AGENCE'""")[0][0] == 0,
      "Témoin : aucun RDV d'avenant promotionnel / livret boosté dans le CRM")
check(q(f"SELECT COUNT(*) FROM {AWS_A} WHERE account_type='LIV_MAISON' AND rate_bps <> 150")[0][0] == 0
      and acc.filter((pl.col("account_type") == "LIV_MAISON") & (pl.col("rate_bps") != 150)).height == 0,
      "Livret Maison servi à 1,50 % (= PDF REG_06 ACPR et avenants agence)")

ko = [l for ok, l in results if not ok]
print(f"\nRésultat : {len(results) - len(ko)}/{len(results)} contrôles OK")
if ko:
    sys.exit(1)
