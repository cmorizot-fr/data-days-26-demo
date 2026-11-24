"""
Crée et exécute de façon idempotente les scans Dataplex `DATA_PROFILE` et `DATA_QUALITY`
(Auto Data Quality avec publication Knowledge Catalog) sur `data-days-demo.raw_bank` (`europe-west1`).
"""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import certifi
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "data-days-demo")
LOCATION = os.environ.get("GCP_REGION", "europe-west1")
BASE_URL = f"https://dataplex.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/dataScans"

PROFILE_TARGETS: list[tuple[str, str, float]] = [
    ("raw-profile-cbk-customers", "cbk_customers_ref", 100.0),
    ("raw-profile-cbk-accounts", "cbk_accounts_master", 100.0),
    ("raw-profile-cbk-movements", "cbk_cfonb_movements", 15.0),
    ("raw-profile-sepa-payments", "raw_sepa_payments_unified", 15.0),
]

DQ_TARGETS: list[tuple[str, str, str, float, list[dict]]] = [
    (
        "raw-dq-cbk-customers",
        "cbk_customers_ref",
        "Auto DQ RAW — Référentiel Clients Mainframe",
        100.0,
        [
            {"column": "customer_id", "dimension": "COMPLETENESS", "nonNullExpectation": {}},
            {"column": "customer_id", "dimension": "UNIQUENESS", "uniquenessExpectation": {}},
            {
                "column": "code_agence_raw",
                "dimension": "VALIDITY",
                "regexExpectation": {"regex": r"^[0-9]{4}$"},
                "threshold": 1.0,
            },
            {
                "column": "age_years",
                "dimension": "VALIDITY",
                "rangeExpectation": {"minValue": "18", "maxValue": "110", "strictMinEnabled": False, "strictMaxEnabled": False},
            },
        ],
    ),
    (
        "raw-dq-cbk-accounts",
        "cbk_accounts_master",
        "Auto DQ RAW — Maître des Comptes Mainframe",
        100.0,
        [
            {"column": "account_id", "dimension": "COMPLETENESS", "nonNullExpectation": {}},
            {"column": "account_id", "dimension": "UNIQUENESS", "uniquenessExpectation": {}},
            {"column": "customer_id", "dimension": "COMPLETENESS", "nonNullExpectation": {}},
            {
                "column": "iban",
                "dimension": "VALIDITY",
                "regexExpectation": {"regex": r"^FR76[0-9A-Z]{23}$"},
            },
        ],
    ),
    (
        "raw-dq-cbk-movements",
        "cbk_cfonb_movements",
        "Auto DQ RAW — Mouvements CFONB 120",
        15.0,
        [
            {"column": "num_compte_11", "dimension": "COMPLETENESS", "nonNullExpectation": {}},
            {"column": "signed_amount_eur", "dimension": "COMPLETENESS", "nonNullExpectation": {}},
            {
                "column": "date_valeur_raw",
                "dimension": "VALIDITY",
                "rowConditionExpectation": {
                    "sqlExpression": "date_valeur_raw NOT IN ('00000000', '99999999')"
                },
                "threshold": 1.0,
            },
        ],
    ),
    (
        "raw-dq-sepa-payments",
        "raw_sepa_payments_unified",
        "Auto DQ RAW — Flux Paiements SEPA (100 % Nested)",
        15.0,
        [
            {
                "column": "header",
                "dimension": "COMPLETENESS",
                "rowConditionExpectation": {"sqlExpression": "header.end_to_end_id IS NOT NULL"},
            },
            {
                "column": "settlement",
                "dimension": "VALIDITY",
                "rowConditionExpectation": {"sqlExpression": "settlement.tx_status = 'ACSC'"},
                "threshold": 1.0,
            },
            {
                "column": "instructed_amount",
                "dimension": "VALIDITY",
                "rowConditionExpectation": {"sqlExpression": "instructed_amount.amount_eur > 0"},
            },
        ],
    ),
]


def get_headers() -> dict[str, str]:
    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    return {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": PROJECT_ID,
        "Content-Type": "application/json",
    }


def api_call(method: str, url: str, body: dict | None = None) -> dict:
    ctx = ssl.create_default_context(cafile=certifi.where())
    data = json.dumps(body).encode("utf-8") if body is not None else (b"" if method == "POST" else None)
    req = urllib.request.Request(url, data=data, method=method, headers=get_headers())
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def ensure_and_run_scan(scan_id: str, payload: dict) -> str:
    scan_url = f"{BASE_URL}/{scan_id}"
    try:
        api_call("GET", scan_url)
        # Met à jour si existant pour garantir catalogPublishingEnabled=True
        api_call("PATCH", f"{scan_url}?updateMask=dataQualitySpec,dataProfileSpec", payload)
        print(f"[scan] {scan_id:<28} mis à jour")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        op = api_call("POST", f"{BASE_URL}?dataScanId={scan_id}", payload)
        # Attend la fin de la LRO de création
        op_name = op.get("name", "")
        if op_name:
            for _ in range(30):
                st = api_call("GET", f"https://dataplex.googleapis.com/v1/{op_name}")
                if st.get("done"):
                    break
                time.sleep(2)
        print(f"[scan] {scan_id:<28} créé")

    run_resp = api_call("POST", f"{scan_url}:run", {})
    return run_resp["job"]["name"]


def wait_for_jobs(jobs: dict[str, str], timeout_sec: int = 360) -> dict[str, dict]:
    deadline = time.time() + timeout_sec
    done: dict[str, dict] = {}
    while len(done) < len(jobs) and time.time() < deadline:
        for sid, jname in jobs.items():
            if sid in done:
                continue
            j = api_call("GET", f"https://dataplex.googleapis.com/v1/{jname}?view=FULL")
            if j.get("state") in ("SUCCEEDED", "FAILED", "CANCELLED"):
                done[sid] = j
                if j["state"] == "SUCCEEDED":
                    res = j.get("dataQualityResult") or j.get("dataProfileResult") or {}
                    extra = f"passed={res.get('passed')}" if "passed" in res else f"rows={res.get('rowCount')}"
                    print(f"[job]  {sid:<28} SUCCEEDED ({extra})")
                else:
                    print(f"[job]  {sid:<28} {j.get('state')}: {j.get('message', '')}")
        if len(done) < len(jobs):
            time.sleep(6)
    return done


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    jobs: dict[str, str] = {}

    print("=== 1/2 Création & lancement des 4 scans DATA_PROFILE (raw_bank) ===")
    for scan_id, table_name, pct in PROFILE_TARGETS:
        payload = {
            "displayName": f"Profil RAW — {table_name}",
            "data": {"resource": f"//bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/raw_bank/tables/{table_name}"},
            "executionSpec": {"trigger": {"onDemand": {}}},
            "dataProfileSpec": {
                "samplingPercent": pct,
                "catalogPublishingEnabled": True,
            },
        }
        jobs[scan_id] = ensure_and_run_scan(scan_id, payload)

    print("=== 2/2 Création & lancement des 4 scans DATA_QUALITY (raw_bank) ===")
    for scan_id, table_name, title, pct, rules in DQ_TARGETS:
        payload = {
            "displayName": title,
            "data": {"resource": f"//bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/raw_bank/tables/{table_name}"},
            "executionSpec": {"trigger": {"onDemand": {}}},
            "dataQualitySpec": {
                "samplingPercent": pct,
                "catalogPublishingEnabled": True,
                "rules": rules,
            },
        }
        jobs[scan_id] = ensure_and_run_scan(scan_id, payload)

    results = wait_for_jobs(jobs)
    # Test generateDataQualityRules sur le profil clients
    try:
        rec = api_call("POST", f"{BASE_URL}/raw-profile-cbk-customers:generateDataQualityRules", {})
        print(f"[generateDataQualityRules] {len(rec.get('rule', []))} règles recommandées depuis raw-profile-cbk-customers")
    except Exception as exc:
        print(f"[generateDataQualityRules] info: {exc}")

    print(f"Terminé : {len(results)}/{len(jobs)} jobs terminés.")


if __name__ == "__main__":
    main()
