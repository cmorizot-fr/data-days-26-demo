"""
Déploie de façon idempotente la taxonomie Policy Tags & les Data Policies de masquage
BigQuery Column-Level Security (CLS) directement sur les 10 sous-champs `STRUCT` sensibles
des 2 tables streaming Pub/Sub (`raw_sepa_payments_pubsub_stream` & `raw_iban_events_pubsub_stream`).

Trois niveaux de protection appliqués aux feuilles des `STRUCT` :
  1. `PII_IBAN_PARTIAL_MASK`         -> `LAST_FOUR_CHARACTERS` (ex: ***********************2623)
  2. `PII_IDENTITY_IP_HASH`          -> `SHA256` (pseudonymisation déterministe noms & IP)
  3. `PII_SENSITIVE_FREETEXT_REDACT` -> `ALWAYS_NULL` (occultation motifs santé CPAM / libellés)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from typing import Any

import google.auth
import requests
from google.auth.transport.requests import Request

TAXONOMY_DISPLAY_NAME = "hexagone-cls-payments-pii"

POLICY_SPECS = [
    {
        "tag_key": "PII_IBAN_PARTIAL_MASK",
        "description": "Masquage dynamique partiel des IBAN (4 derniers caractères conservés).",
        "data_policy_id": "hexagone_dp_iban_last4",
        "predefined_expression": "LAST_FOUR_CHARACTERS",
    },
    {
        "tag_key": "PII_IDENTITY_IP_HASH",
        "description": "Hachage SHA-256 déterministe des identités civiles et adresses IPv4.",
        "data_policy_id": "hexagone_dp_identity_sha256",
        "predefined_expression": "SHA256",
    },
    {
        "tag_key": "PII_SENSITIVE_FREETEXT_REDACT",
        "description": "Occultation intégrale (NULL) des champs texte libres sensibles (santé RGPD Art.9, loyer).",
        "data_policy_id": "hexagone_dp_freetext_redact",
        "predefined_expression": "ALWAYS_NULL",
    },
]

# Mapping exact : table -> (struct_parent, leaf_field) -> tag_key
TABLE_NESTED_TAG_MAP: dict[str, dict[tuple[str, str], str]] = {
    "raw_sepa_payments_pubsub_stream": {
        ("debtor", "iban"): "PII_IBAN_PARTIAL_MASK",
        ("creditor", "iban"): "PII_IBAN_PARTIAL_MASK",
        ("debtor", "full_name"): "PII_IDENTITY_IP_HASH",
        ("creditor", "name"): "PII_IDENTITY_IP_HASH",
        ("remittance", "unstructured_info"): "PII_SENSITIVE_FREETEXT_REDACT",
    },
    "raw_iban_events_pubsub_stream": {
        ("account_holder", "debtor_iban"): "PII_IBAN_PARTIAL_MASK",
        ("beneficiary", "iban"): "PII_IBAN_PARTIAL_MASK",
        ("account_holder", "full_name"): "PII_IDENTITY_IP_HASH",
        ("security_context", "device_ip"): "PII_IDENTITY_IP_HASH",
        ("beneficiary", "custom_label"): "PII_SENSITIVE_FREETEXT_REDACT",
    },
}


def get_access_token_and_principal() -> tuple[str, str]:
    res_acc = subprocess.run(
        ["gcloud", "config", "get-value", "account", "--quiet"],
        capture_output=True,
        text=True,
        check=True,
    )
    principal_email = res_acc.stdout.strip()

    try:
        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(Request())
        if creds.token:
            return creds.token, principal_email
    except Exception:
        pass

    for cmd in (
        ["gcloud", "auth", "application-default", "print-access-token", "--quiet"],
        ["gcloud", "auth", "print-access-token", "--quiet"],
    ):
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip(), principal_email
    raise RuntimeError("Impossible d'obtenir un jeton OAuth GCP actif.")


def api_request(
    session: requests.Session,
    method: str,
    url: str,
    token: str,
    project_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": project_id,
        "Content-Type": "application/json",
    }
    resp = session.request(method, url, headers=headers, json=payload, timeout=30)
    if resp.status_code >= 400:
        raise RuntimeError(f"HTTP {resp.status_code} on {method} {url}: {resp.text}")
    return resp.json() if resp.text.strip() else {}


def ensure_taxonomy(
    session: requests.Session, token: str, project_id: str, location: str
) -> str:
    base_url = f"https://datacatalog.googleapis.com/v1/projects/{project_id}/locations/{location}/taxonomies"
    existing = api_request(session, "GET", base_url, token, project_id).get("taxonomies", [])
    for tax in existing:
        if tax.get("displayName") == TAXONOMY_DISPLAY_NAME:
            print(f"[cls] Taxonomie existante trouvée : {tax['name']}")
            return tax["name"]

    created = api_request(
        session,
        "POST",
        base_url,
        token,
        project_id,
        payload={
            "displayName": TAXONOMY_DISPLAY_NAME,
            "description": "Taxonomie CLS Banque Hexagone — Protection granulaire des sous-champs STRUCT Paiements SEPA & IBAN.",
            "activatedPolicyTypes": ["FINE_GRAINED_ACCESS_CONTROL"],
        },
    )
    print(f"[cls] Taxonomie créée : {created['name']}")
    return created["name"]


def ensure_policy_tags(
    session: requests.Session, token: str, project_id: str, taxonomy_name: str
) -> dict[str, str]:
    pt_url = f"https://datacatalog.googleapis.com/v1/{taxonomy_name}/policyTags"
    existing = api_request(session, "GET", pt_url, token, project_id).get("policyTags", [])
    by_name = {pt["displayName"]: pt["name"] for pt in existing}

    result: dict[str, str] = {}
    for spec in POLICY_SPECS:
        key = spec["tag_key"]
        if key in by_name:
            result[key] = by_name[key]
            print(f"[cls] Policy Tag déjà présent : {key} -> {by_name[key]}")
        else:
            created = api_request(
                session,
                "POST",
                pt_url,
                token,
                project_id,
                payload={"displayName": key, "description": spec["description"]},
            )
            result[key] = created["name"]
            print(f"[cls] Policy Tag créé : {key} -> {created['name']}")
    return result


def ensure_data_policies_and_masked_reader(
    session: requests.Session,
    token: str,
    project_id: str,
    location: str,
    tag_map: dict[str, str],
    masked_reader_member: str,
) -> None:
    dp_base = f"https://bigquerydatapolicy.googleapis.com/v1/projects/{project_id}/locations/{location}/dataPolicies"
    existing = api_request(session, "GET", dp_base, token, project_id).get("dataPolicies", [])
    by_id = {dp["name"].split("/")[-1]: dp for dp in existing}

    for spec in POLICY_SPECS:
        dp_id = spec["data_policy_id"]
        pt_resource = tag_map[spec["tag_key"]]
        body = {
            "dataPolicyId": dp_id,
            "dataPolicyType": "DATA_MASKING_POLICY",
            "policyTag": pt_resource,
            "dataMaskingPolicy": {
                "predefinedExpression": spec["predefined_expression"],
            },
        }
        if dp_id in by_id:
            dp_name = by_id[dp_id]["name"]
            api_request(
                session,
                "PATCH",
                f"https://bigquerydatapolicy.googleapis.com/v1/{dp_name}?updateMask=policyTag,dataMaskingPolicy",
                token,
                project_id,
                payload={"name": dp_name, **body},
            )
            print(f"[cls] Data Policy mise à jour : {dp_id} ({spec['predefined_expression']})")
        else:
            created = api_request(session, "POST", dp_base, token, project_id, payload=body)
            dp_name = created["name"]
            print(f"[cls] Data Policy créée : {dp_id} ({spec['predefined_expression']})")

        # Accorde `roles/bigquerydatapolicy.maskedReader` à l'opérateur pour lire les valeurs masquées en direct
        iam_url = f"https://bigquerydatapolicy.googleapis.com/v1/{dp_name}:setIamPolicy"
        api_request(
            session,
            "POST",
            iam_url,
            token,
            project_id,
            payload={
                "policy": {
                    "bindings": [
                        {
                            "role": "roles/bigquerydatapolicy.maskedReader",
                            "members": [masked_reader_member],
                        }
                    ]
                }
            },
        )
        print(f"[cls] Rôle maskedReader attribué sur {dp_id} à {masked_reader_member}")


def patch_bq_nested_table_policy_tags(
    session: requests.Session,
    token: str,
    project_id: str,
    dataset: str,
    table_name: str,
    nested_rules: dict[tuple[str, str], str],
    tag_map: dict[str, str],
) -> int:
    tbl_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{dataset}/tables/{table_name}"
    tbl_meta = api_request(session, "GET", tbl_url, token, project_id)
    fields = tbl_meta["schema"]["fields"]

    patched_count = 0
    for top_col in fields:
        if top_col.get("type") in ("RECORD", "STRUCT") and "fields" in top_col:
            parent_name = top_col["name"]
            for sub_col in top_col["fields"]:
                key_pair = (parent_name, sub_col["name"])
                if key_pair in nested_rules:
                    tag_key = nested_rules[key_pair]
                    sub_col["policyTags"] = {"names": [tag_map[tag_key]]}
                    patched_count += 1

    api_request(
        session,
        "PATCH",
        tbl_url,
        token,
        project_id,
        payload={"schema": {"fields": fields}},
    )
    print(f"[cls] Table {dataset}.{table_name} patchée : {patched_count} sous-champs STRUCT protégés par CLS.")
    return patched_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Applique la taxonomie CLS sur les sous-champs STRUCT Pub/Sub.")
    parser.add_argument("--project-id", default=os.getenv("GCP_PROJECT_ID", "data-days-demo"))
    parser.add_argument("--location", default=os.getenv("GCP_REGION", "europe-west1"))
    parser.add_argument("--dataset", default=os.getenv("BQ_DATASET_RAW", "raw_bank"))
    args = parser.parse_args()

    token, email = get_access_token_and_principal()
    member_type = "serviceAccount" if email.endswith(".gserviceaccount.com") else "user"
    masked_member = f"{member_type}:{email}"

    session = requests.Session()
    tax_name = ensure_taxonomy(session, token, args.project_id, args.location)
    tag_map = ensure_policy_tags(session, token, args.project_id, tax_name)
    ensure_data_policies_and_masked_reader(
        session, token, args.project_id, args.location, tag_map, masked_member
    )

    total_tagged = 0
    for tbl, rules in TABLE_NESTED_TAG_MAP.items():
        total_tagged += patch_bq_nested_table_policy_tags(
            session, token, args.project_id, args.dataset, tbl, rules, tag_map
        )

    print(
        json.dumps(
            {
                "status": "OK",
                "taxonomy": tax_name,
                "masked_reader": masked_member,
                "protected_nested_struct_fields": total_tagged,
                "policy_tags": tag_map,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    sys.exit(main())
