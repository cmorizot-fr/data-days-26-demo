"""
Crée et exécute de façon idempotente les scans Dataplex `DATA_DOCUMENTATION`
(Data Insights Gemini) sur les ressources SILVER & GOLD de Banque Hexagone :
  - les 18 tables/vues SILVER & GOLD (`silver_bank` & `gold_bank`)
  - les 2 datasets (`silver_bank`, `gold_bank`)
  - les 7 Data Products Knowledge Catalog (`dp-*`)

Publie également dans Knowledge Catalog (sans aucune bordure colorée en HTML) :
  - sur les 7 Data Products :
      * `655216118709.global.overview` (Documentation riche HTML combinant
        `02_demo2_silver_dbt_dq/kc_products/data_products_catalog.yaml` et la
        synthèse Gemini `dataProductResult.overview` + `assetDescriptions`)
      * `655216118709.global.refresh-cadence` (onglet `Contracts` SLA/fraîcheur)
      * `655216118709.global.queries` (onglet `Insights` requêtes SQL Gemini)
  - sur les 18 Tables/Vues et 2 Datasets :
      * `655216118709.global.overview` (Documentation riche HTML issue du scan
        `DATA_DOCUMENTATION` Gemini pour l'onglet `Overview` de chaque actif).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import html
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

import requests
import yaml

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "data-days-demo")
LOCATION = os.environ.get("GCP_REGION", "europe-west1")
ROOT_DIR = Path(__file__).resolve().parent.parent
CATALOG_YAML_PATH = ROOT_DIR / "02_demo2_silver_dbt_dq" / "kc_products" / "data_products_catalog.yaml"

BQ_TABLE_TARGETS: list[tuple[str, str, str]] = [
    ("doc-silver-customers", "silver_bank.customers", "Insights — SILVER Customers"),
    ("doc-silver-accounts", "silver_bank.accounts", "Insights — SILVER Accounts"),
    ("doc-silver-account-balances", "silver_bank.account_monthly_balances", "Insights — SILVER Account Monthly Balances"),
    ("doc-silver-movements", "silver_bank.customer_movements", "Insights — SILVER Customer Movements"),
    ("doc-silver-beneficiaries", "silver_bank.beneficiaries", "Insights — SILVER Beneficiaries"),
    ("doc-silver-interactions", "silver_bank.interactions", "Insights — SILVER CRM Interactions"),
    ("doc-silver-gl-entries", "silver_bank.gl_entries", "Insights — SILVER SAP GL & ALM Entries"),
    ("doc-silver-promo-contracts", "silver_bank.promo_contracts", "Insights — SILVER Promo Contracts PDF"),
    ("doc-silver-savings-offers", "silver_bank.savings_offers", "Insights — SILVER Savings Offers"),
    ("doc-gold-mobile-insights", "gold_bank.customer_mobile_insights", "Insights — GOLD Customer Mobile Insights"),
    ("doc-gold-tx-enriched", "gold_bank.customer_transactions_enriched", "Insights — GOLD Enriched Transactions"),
    ("doc-gold-monthly-spending", "gold_bank.customer_monthly_spending", "Insights — GOLD Monthly Spending"),
    ("doc-gold-recurring", "gold_bank.customer_recurring_commitments", "Insights — GOLD Recurring Commitments"),
    ("doc-gold-card-forecast", "gold_bank.customer_card_spending_forecast", "Insights — GOLD Card Spending Forecast"),
    ("doc-gold-pnb-regional", "gold_bank.cfo_pnb_regional_bridge", "Insights — GOLD CFO PNB Regional Bridge"),
    ("doc-gold-outflow-reasons", "gold_bank.crm_outflow_reasons_by_segment", "Insights — GOLD Outflow Reasons by Segment"),
    ("doc-gold-pnb-variance", "gold_bank.v_cfo_certified_pnb_variance", "Insights — GOLD Certified PNB Variance"),
    ("doc-gold-witness-cls", "gold_bank.v_witness_lucas_martin_cls_audit", "Insights — GOLD Witness CLS Audit"),
]

BQ_DATASET_TARGETS: list[tuple[str, str, str]] = [
    ("doc-ds-silver-bank", "silver_bank", "Insights — Dataset SILVER Bank"),
    ("doc-ds-gold-bank", "gold_bank", "Insights — Dataset GOLD Bank"),
]

DATA_PRODUCT_IDS: list[str] = [
    "dp-customer-360",
    "dp-customer-timeline",
    "dp-customer-relationship",
    "dp-finance-pnb",
    "dp-commercial-commitments",
    "dp-budget-insight",
    "dp-certified-pnb",
]

DP_FALLBACK_TABLE_SCAN: dict[str, str] = {
    "dp-customer-relationship": "doc-silver-interactions",
    "dp-finance-pnb": "doc-silver-gl-entries",
    "dp-commercial-commitments": "doc-silver-promo-contracts",
}

DP_CADENCE_SPECS: dict[str, dict[str, Any]] = {
    "dp-customer-360": {
        "frequency": "Daily",
        "refreshTime": "06:00 Europe/Paris",
        "thresholdInMinutes": 30,
        "cronSchedule": "0 6 * * *",
    },
    "dp-customer-timeline": {
        "frequency": "Daily",
        "refreshTime": "06:15 Europe/Paris",
        "thresholdInMinutes": 15,
        "cronSchedule": "15 6 * * *",
    },
    "dp-customer-relationship": {
        "frequency": "Daily",
        "refreshTime": "06:30 Europe/Paris",
        "thresholdInMinutes": 45,
        "cronSchedule": "30 6 * * *",
    },
    "dp-finance-pnb": {
        "frequency": "Monthly",
        "refreshTime": "07:00 Europe/Paris",
        "thresholdInMinutes": 60,
        "cronSchedule": "0 7 2 * *",
    },
    "dp-commercial-commitments": {
        "frequency": "Daily",
        "refreshTime": "06:00 Europe/Paris",
        "thresholdInMinutes": 60,
        "cronSchedule": "0 6 * * *",
    },
    "dp-budget-insight": {
        "frequency": "Daily",
        "refreshTime": "06:45 Europe/Paris",
        "thresholdInMinutes": 15,
        "cronSchedule": "45 6 * * *",
    },
    "dp-certified-pnb": {
        "frequency": "Quarterly",
        "refreshTime": "08:00 Europe/Paris",
        "thresholdInMinutes": 60,
        "cronSchedule": "0 8 3 1,4,7,10 *",
    },
}


def load_catalog_metadata() -> dict[str, dict[str, Any]]:
    if not CATALOG_YAML_PATH.exists():
        return {}
    raw = yaml.safe_load(CATALOG_YAML_PATH.read_text(encoding="utf-8")) or {}
    out: dict[str, dict[str, Any]] = {}
    for item in raw.get("data_products", []):
        kebab_id = str(item.get("id", "")).replace("_", "-")
        if kebab_id:
            out[kebab_id] = item
    return out


def get_access_token() -> str:
    env = {
        **os.environ,
        "CLOUDSDK_METRICS_ENVIRONMENT": "datacloud.antigravity",
    }
    out = subprocess.check_output(
        ["gcloud", "auth", "print-access-token"],
        env=env,
        text=True,
    ).strip()
    if not out:
        raise RuntimeError("Impossible d'obtenir un jeton via `gcloud auth print-access-token`.")
    return out


def get_project_number(project_id: str, token: str) -> str:
    r = requests.get(
        f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    r.raise_for_status()
    return str(r.json()["projectNumber"])


def wait_lro(op_name: str, token: str, timeout_s: int = 180) -> dict[str, Any]:
    url = f"https://dataplex.googleapis.com/v1/{op_name}"
    deadline = time.time() + timeout_s
    sleep_s = 4.0
    while time.time() < deadline:
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        if r.status_code == 429:
            time.sleep(sleep_s)
            sleep_s = min(sleep_s * 1.5, 15.0)
            continue
        r.raise_for_status()
        data = r.json()
        if data.get("done"):
            if "error" in data:
                raise RuntimeError(f"LRO error on {op_name}: {data['error']}")
            return data
        time.sleep(sleep_s)
    raise TimeoutError(f"Timeout waiting for operation {op_name}")


def ensure_doc_scan(
    scan_id: str,
    resource: str,
    display_name: str,
    catalog_publishing: bool,
    token: str,
) -> str:
    base = f"https://dataplex.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/dataScans"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    scan_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/dataScans/{scan_id}"

    check = requests.get(f"https://dataplex.googleapis.com/v1/{scan_name}", headers=headers, timeout=20)
    if check.status_code == 200:
        return scan_name

    body: dict[str, Any] = {
        "displayName": display_name,
        "description": f"Scan Gemini Data Documentation généré pour {display_name} (Banque Hexagone).",
        "data": {"resource": resource},
        "dataDocumentationSpec": {"catalogPublishingEnabled": True} if catalog_publishing else {},
        "executionSpec": {"trigger": {"onDemand": {}}},
        "labels": {
            "datacloud": "antigravity",
            "env": "demo2026",
            "scan_kind": "data_documentation",
        },
    }
    for attempt in range(4):
        resp = requests.post(
            base,
            params={"dataScanId": scan_id},
            headers=headers,
            json=body,
            timeout=30,
        )
        if resp.status_code == 429 and attempt < 3:
            time.sleep(5 * (attempt + 1))
            continue
        break
    if resp.status_code == 409:
        return scan_name
    if not resp.ok:
        raise RuntimeError(f"Create scan {scan_id} failed ({resp.status_code}): {resp.text}")
    op = resp.json()
    if not op.get("done"):
        wait_lro(op["name"], token)
    return scan_name


def trigger_or_get_latest_job(scan_name: str, token: str, force_run: bool = False) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    jobs_resp = requests.get(
        f"https://dataplex.googleapis.com/v1/{scan_name}/jobs",
        headers=headers,
        timeout=20,
    )
    if jobs_resp.ok:
        jobs = jobs_resp.json().get("dataScanJobs", [])
        if not force_run:
            for job in jobs:
                if job.get("state") in ("SUCCEEDED", "RUNNING", "PENDING"):
                    return job["name"]

    run_resp = requests.post(
        f"https://dataplex.googleapis.com/v1/{scan_name}:run",
        headers=headers,
        json={},
        timeout=30,
    )
    if not run_resp.ok:
        raise RuntimeError(f"Run scan {scan_name} failed ({run_resp.status_code}): {run_resp.text}")
    return run_resp.json()["job"]["name"]


def fetch_job_full(job_name: str, token: str) -> dict[str, Any]:
    for attempt in range(4):
        r = requests.get(
            f"https://dataplex.googleapis.com/v1/{job_name}",
            params={"view": "FULL"},
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        if r.status_code == 429 and attempt < 3:
            time.sleep(4 * (attempt + 1))
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"Failed to fetch job {job_name}")


def build_data_product_overview_html(
    dp_id: str,
    cat_meta: dict[str, Any],
    job_full: dict[str, Any],
) -> str:
    dpr = (job_full.get("dataDocumentationResult") or {}).get("dataProductResult") or {}
    gemini_overview = str(dpr.get("overview") or "").strip()
    asset_descs = dpr.get("assetDescriptions") or []

    title = html.escape(str(cat_meta.get("title") or dp_id))
    layer = html.escape(str(cat_meta.get("layer") or "silver").upper())
    owner = html.escape(str(cat_meta.get("owner") or "data_governance"))
    freshness = html.escape(str(cat_meta.get("freshness") or "daily"))
    dataset = html.escape(str(cat_meta.get("dataset") or ""))
    contract = html.escape(" ".join(str(cat_meta.get("contract") or "").split()))
    sources = ", ".join(f"<code>{html.escape(str(s))}</code>" for s in (cat_meta.get("sources") or []))
    consumers = ", ".join(f"<code>{html.escape(str(c))}</code>" for c in (cat_meta.get("consumers") or []))
    tables = ", ".join(f"<code>{html.escape(str(t))}</code>" for t in (cat_meta.get("tables") or []))

    parts: list[str] = [
        '<div style="display:flex;flex-direction:column;gap:18px;padding:4px 2px;">',
        # En-tête de gouvernance par luminance de surface uniquement (zéro bordure colorée)
        '<div style="background:#F4F6FA;border-radius:12px;padding:16px 18px;">',
        f'<div style="font-size:12px;font-weight:600;letter-spacing:0.04em;color:#4A5568;text-transform:uppercase;margin-bottom:6px;">Banque Hexagone · Couche {layer} · Dataset {dataset}</div>',
        f'<div style="font-size:16px;font-weight:600;color:#1A202C;margin-bottom:8px;">{title}</div>',
        f'<div style="font-size:14px;color:#2D3748;line-height:1.6;"><strong>Contrat &amp; garanties métier :</strong> {contract}</div>',
        '</div>',
        # Métadonnées opérationnelles (grille en luminance de surface)
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;">',
        f'<div style="background:#F8FAFC;border-radius:10px;padding:12px 14px;"><div style="font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;">Domaine propriétaire</div><div style="font-size:14px;font-weight:500;color:#0F172A;margin-top:4px;">{owner}</div></div>',
        f'<div style="background:#F8FAFC;border-radius:10px;padding:12px 14px;"><div style="font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;">Fraîcheur &amp; SLA</div><div style="font-size:14px;font-weight:500;color:#0F172A;margin-top:4px;">{freshness}</div></div>',
        f'<div style="background:#F8FAFC;border-radius:10px;padding:12px 14px;"><div style="font-size:11px;font-weight:600;color:#64748B;text-transform:uppercase;">Consommateurs cibles</div><div style="font-size:13px;color:#0F172A;margin-top:4px;">{consumers or "-"}</div></div>',
        '</div>',
    ]

    if sources or tables:
        parts.extend([
            '<div style="background:#F8FAFC;border-radius:10px;padding:14px 16px;">',
            f'<div style="font-size:13px;color:#1E293B;margin-bottom:6px;"><strong>Tables exposées dans le catalogue :</strong> {tables}</div>',
            f'<div style="font-size:13px;color:#334155;"><strong>Lignage amont (sources) :</strong> {sources}</div>',
            '</div>',
        ])

    if gemini_overview:
        parts.extend([
            '<div>',
            '<h4 style="margin:0 0 8px 0;font-size:15px;font-weight:600;color:#1A202C;">Synthèse analytique générée (Knowledge Catalog Data Documentation)</h4>',
            f'<p style="margin:0;font-size:14px;color:#334155;line-height:1.65;">{html.escape(gemini_overview)}</p>',
            '</div>',
        ])

    if asset_descs:
        parts.append('<div>')
        parts.append('<h4 style="margin:0 0 10px 0;font-size:15px;font-weight:600;color:#1A202C;">Actifs couverts par le Data Product</h4>')
        parts.append('<div style="display:flex;flex-direction:column;gap:10px;">')
        for asset in asset_descs:
            res = str(asset.get("resource") or "")
            short_tbl = res.split("/datasets/")[-1].replace("/tables/", ".") if "/datasets/" in res else res
            ov = html.escape(str(asset.get("overview") or ""))
            parts.append(
                f'<div style="background:#F4F6FA;border-radius:10px;padding:12px 14px;">'
                f'<div style="font-size:13px;font-weight:600;color:#0F172A;margin-bottom:4px;"><code>{html.escape(short_tbl)}</code></div>'
                f'<div style="font-size:13px;color:#334155;line-height:1.55;">{ov}</div>'
                f'</div>'
            )
        parts.append('</div></div>')

    parts.append('</div>')
    return "".join(parts)


def build_table_or_dataset_overview_html(
    label: str,
    job_full: dict[str, Any],
) -> str:
    doc_res = job_full.get("dataDocumentationResult") or {}
    tbl_res = doc_res.get("tableResult") or {}
    ds_res = doc_res.get("datasetResult") or {}
    overview_text = str(tbl_res.get("overview") or ds_res.get("overview") or "").strip()
    if not overview_text:
        return ""

    fields = (tbl_res.get("schema") or {}).get("fields") or []
    parts = [
        '<div style="display:flex;flex-direction:column;gap:16px;padding:4px 2px;">',
        '<div style="background:#F4F6FA;border-radius:12px;padding:16px 18px;">',
        f'<div style="font-size:12px;font-weight:600;letter-spacing:0.04em;color:#4A5568;text-transform:uppercase;margin-bottom:6px;">Banque Hexagone · Documentation gouvernée Gemini</div>',
        f'<div style="font-size:15px;font-weight:600;color:#1A202C;margin-bottom:8px;"><code>{html.escape(label)}</code></div>',
        f'<p style="margin:0;font-size:14px;color:#2D3748;line-height:1.65;">{html.escape(overview_text)}</p>',
        '</div>',
    ]
    if fields:
        parts.append('<div>')
        parts.append('<h4 style="margin:0 0 10px 0;font-size:14px;font-weight:600;color:#1A202C;">Champs clés documentés</h4>')
        parts.append('<div style="background:#F8FAFC;border-radius:10px;padding:8px 14px;">')
        for idx, f_item in enumerate(fields[:15]):
            fname = html.escape(str(f_item.get("name") or ""))
            fdesc = html.escape(str(f_item.get("description") or ""))
            sep = 'border-bottom:1px solid #ECEEF4;' if idx < min(len(fields), 15) - 1 else ''
            parts.append(
                f'<div style="padding:8px 0;{sep}font-size:13px;line-height:1.5;color:#334155;">'
                f'<strong style="color:#0F172A;"><code>{fname}</code></strong> — {fdesc}'
                f'</div>'
            )
        parts.append('</div></div>')
    parts.append('</div>')
    return "".join(parts)


def publish_dp_aspects(
    dp_id: str,
    project_number: str,
    cat_meta: dict[str, Any],
    job_full: dict[str, Any],
    fallback_job: dict[str, Any] | None,
    token: str,
) -> tuple[int, bool, bool]:
    doc_res = job_full.get("dataDocumentationResult") or {}
    raw_queries: list[dict[str, Any]] = []
    for val in doc_res.values():
        if isinstance(val, dict) and isinstance(val.get("queries"), list):
            raw_queries.extend(val["queries"])

    if not raw_queries and fallback_job:
        fb_res = fallback_job.get("dataDocumentationResult") or {}
        for val in fb_res.values():
            if isinstance(val, dict) and isinstance(val.get("queries"), list):
                raw_queries.extend(val["queries"])

    formatted_queries = [
        {
            "description": q.get("description", ""),
            "sql": q.get("sql", ""),
            "source": "AGENT",
            "sqlDialect": "GOOGLE_SQL",
        }
        for q in raw_queries
        if q.get("sql") and q.get("description")
    ]

    entry_name = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}/entryGroups/@dataplex/"
        f"entries/projects/{project_number}/locations/{LOCATION}/dataProducts/{dp_id}"
    )
    overview_html = build_data_product_overview_html(dp_id, cat_meta, job_full)
    cadence = DP_CADENCE_SPECS.get(dp_id, {
        "frequency": "Daily",
        "refreshTime": "06:00 Europe/Paris",
        "thresholdInMinutes": 30,
        "cronSchedule": "0 6 * * *",
    })

    aspects_payload: dict[str, Any] = {
        "655216118709.global.overview": {
            "aspectType": "projects/655216118709/locations/global/aspectTypes/overview",
            "data": {
                "content": overview_html,
                "contentType": "HTML",
            },
        },
        "655216118709.global.refresh-cadence": {
            "aspectType": "projects/655216118709/locations/global/aspectTypes/refresh-cadence",
            "data": cadence,
        },
    }
    aspect_keys = [
        "655216118709.global.overview",
        "655216118709.global.refresh-cadence",
    ]

    if formatted_queries:
        run_time = job_full.get("startTime") or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")
        aspects_payload["655216118709.global.queries"] = {
            "aspectType": "projects/655216118709/locations/global/aspectTypes/queries",
            "data": {
                "queries": formatted_queries,
                "userManaged": False,
                "job": {
                    "name": job_full.get("name", ""),
                    "runTime": run_time,
                },
            },
        }
        aspect_keys.append("655216118709.global.queries")

    resp = requests.patch(
        f"https://dataplex.googleapis.com/v1/{entry_name}",
        params=[("updateMask", "aspects"), *[("aspectKeys", k) for k in aspect_keys]],
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={"name": entry_name, "aspects": aspects_payload},
        timeout=30,
    )
    if not resp.ok:
        print(f"  [WARN] Patch aspects Data Product {dp_id} ({resp.status_code}): {resp.text[:260]}")
        return (0, False, False)
    return (len(formatted_queries), True, True)


def publish_bq_entry_overview(
    entry_suffix: str,
    label: str,
    job_full: dict[str, Any],
    token: str,
) -> bool:
    overview_html = build_table_or_dataset_overview_html(label, job_full)
    if not overview_html:
        return False

    entry_name = (
        f"projects/{PROJECT_ID}/locations/{LOCATION}/entryGroups/@bigquery/"
        f"entries/bigquery.googleapis.com/{entry_suffix}"
    )
    aspect_key = "655216118709.global.overview"
    resp = requests.patch(
        f"https://dataplex.googleapis.com/v1/{entry_name}",
        params={"updateMask": "aspects", "aspectKeys": aspect_key},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "name": entry_name,
            "aspects": {
                aspect_key: {
                    "aspectType": "projects/655216118709/locations/global/aspectTypes/overview",
                    "data": {
                        "content": overview_html,
                        "contentType": "HTML",
                    },
                }
            },
        },
        timeout=30,
    )
    if not resp.ok:
        print(f"  [WARN] Patch overview sur {label} ({resp.status_code}): {resp.text[:220]}")
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Provisionne et publie les scans Dataplex DATA_DOCUMENTATION & Overview.")
    parser.add_argument("--force-run", action="store_true", help="Relance un job même si un job SUCCEEDED existe déjà.")
    parser.add_argument("--timeout", type=int, default=420, help="Timeout global d'attente des jobs en secondes.")
    args = parser.parse_args()

    catalog_meta = load_catalog_metadata()
    token = get_access_token()
    project_number = get_project_number(PROJECT_ID, token)
    print(f"[1/5] Projet={PROJECT_ID} ({project_number}) | Région={LOCATION} | Catalogue YAML={len(catalog_meta)} Data Products")

    specs: list[tuple[str, str, str, bool, str | None, str | None, str | None]] = []
    # (scan_id, resource, title, catalog_publishing, dp_id, bq_entry_suffix, bq_label)
    for scan_id, ds_tbl, title in BQ_TABLE_TARGETS:
        ds, tbl = ds_tbl.split(".", 1)
        suffix = f"projects/{PROJECT_ID}/datasets/{ds}/tables/{tbl}"
        specs.append((scan_id, f"//bigquery.googleapis.com/{suffix}", title, True, None, suffix, ds_tbl))

    for scan_id, ds, title in BQ_DATASET_TARGETS:
        suffix = f"projects/{PROJECT_ID}/datasets/{ds}"
        specs.append((scan_id, f"//bigquery.googleapis.com/{suffix}", title, True, None, suffix, ds))

    for dp_id in DATA_PRODUCT_IDS:
        scan_id = f"doc-{dp_id}"
        res = f"//dataplex.googleapis.com/projects/{project_number}/locations/{LOCATION}/dataProducts/{dp_id}"
        specs.append((scan_id, res, f"Insights — Data Product {dp_id}", False, dp_id, None, None))

    print(f"[2/5] Vérification / création idempotente de {len(specs)} DataScans DATA_DOCUMENTATION...")
    created_scans: list[tuple[str, str, str | None, str | None, str | None]] = []

    def _create_one(item: tuple[str, str, str, bool, str | None, str | None, str | None]) -> tuple[str, str | None, str | None, str | None, str | None]:
        scan_id, res, title, pub, dp_id, suffix, label = item
        try:
            sname = ensure_doc_scan(scan_id, res, title, pub, token)
            return (scan_id, sname, dp_id, suffix, label)
        except Exception as exc:  # noqa: BLE001
            print(f"  [SKIP] {scan_id}: {exc}")
            return (scan_id, None, dp_id, suffix, label)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for scan_id, sname, dp_id, suffix, label in pool.map(_create_one, specs):
            if sname:
                created_scans.append((scan_id, sname, dp_id, suffix, label))

    print(f"[3/5] Récupération / déclenchement des jobs DATA_DOCUMENTATION ({len(created_scans)} scans)...")
    active_jobs: dict[str, tuple[str, str | None, str | None, str | None]] = {}
    for scan_id, sname, dp_id, suffix, label in created_scans:
        jname = trigger_or_get_latest_job(sname, token, force_run=args.force_run)
        active_jobs[scan_id] = (jname, dp_id, suffix, label)

    print(f"[4/5] Lecture des résultats Gemini DATA_DOCUMENTATION...")
    deadline = time.time() + args.timeout
    completed: dict[str, dict[str, Any]] = {}
    while len(completed) < len(active_jobs) and time.time() < deadline:
        token = get_access_token()
        pending_ids = [sid for sid in active_jobs if sid not in completed]
        for sid in pending_ids:
            jname, _, _, _ = active_jobs[sid]
            job = fetch_job_full(jname, token)
            state = job.get("state", "UNKNOWN")
            if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
                completed[sid] = job
        if len(completed) < len(active_jobs):
            time.sleep(8)

    print(f"[5/5] Publication dans Knowledge Catalog (Overview + Contracts + Queries)...")
    token = get_access_token()
    dp_ok = 0
    bq_ok = 0
    for sid, (_, dp_id, suffix, label) in active_jobs.items():
        job = completed.get(sid)
        if not job or job.get("state") != "SUCCEEDED":
            continue
        if dp_id:
            fb_sid = DP_FALLBACK_TABLE_SCAN.get(dp_id)
            fb_job = completed.get(fb_sid) if fb_sid else None
            q_cnt, ov_ok, rc_ok = publish_dp_aspects(
                dp_id,
                project_number,
                catalog_meta.get(dp_id, {}),
                job,
                fb_job,
                token,
            )
            if ov_ok:
                dp_ok += 1
                print(f"  ✓ Data Product {dp_id}: overview=OK | contracts(refresh-cadence)={rc_ok} | insights={q_cnt} requêtes")
        elif suffix and label:
            if publish_bq_entry_overview(suffix, label, job, token):
                bq_ok += 1

    print("======================================================================")
    print(
        f"Bilan Knowledge Catalog : {dp_ok}/7 Data Products enrichis (Overview + Contracts + Insights) "
        f"| {bq_ok}/20 Tables & Datasets enrichis (Overview)"
    )
    print("======================================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
