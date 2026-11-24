"""
Documente les 4 tables Iceberg AWS Glue (`crm_callcenter_db`, 49 colonnes) côté AWS (Glue + S3 Iceberg)
puis synchronise et enrichit les entrées `@biglake` dans Google Cloud Knowledge Catalog (`europe-west1`).
"""

from __future__ import annotations

import html
import json
import os
import ssl
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

import boto3
import certifi
from dotenv import load_dotenv
from pyiceberg.catalog.glue import GlueCatalog

REPO_ROOT = Path(__file__).resolve().parent.parent

TABLE_SPECS: dict[str, dict] = {
    "crm_customers": {
        "description": (
            "Référentiel clients particuliers du SaaS CRM (temps réel agence & digital). "
            "Inclut dès J0 les ouvertures réalisées en agence avant le passage du batch nocturne Mainframe J-1."
        ),
        "columns": {
            "customer_id": "Identifiant unique client Banque Hexagone (clé de rapprochement inter-silos CUSTxxxxxxxx).",
            "first_name": "Prénom d'état civil déclaré lors de l'entrée en relation (PII).",
            "last_name": "Nom patronymique du titulaire (PII).",
            "birth_date": "Date de naissance du client (format ISO YYYY-MM-DD, PII).",
            "age": "Âge révolu du client calculé dans le CRM.",
            "age_segment": "Tranche d'âge marketing CRM (ex. 18-32, 33-49, 50-64, 65+).",
            "segment": "Segment commercial réseau (Mass Retail, Affluent, Jeunes Actifs, Patrimonial).",
            "csp": "Catégorie socioprofessionnelle INSEE déclarée lors du KYC.",
            "declared_monthly_income_eur": "Revenu net mensuel déclaré en euros lors du dernier entretien KYC.",
            "region_code": "Code de la direction régionale commerciale (8 régions).",
            "region_name": "Libellé de la direction régionale commerciale.",
            "agency_code_4": "Code agence sur 4 caractères côté CRM.",
            "guichet_code_5": "Code guichet bancaire normalisé sur 5 chiffres (RIB/IBAN).",
            "city": "Ville d'implantation de l'agence de rattachement.",
            "onboarding_date": "Date d'entrée en relation commerciale (inclut les ouvertures J0 du jour).",
            "commercial_status": "Statut commercial du dossier dans le CRM (ACTIVE, PROSPECT).",
            "closed_date": "Date de clôture commerciale éventuelle (NULL si client actif).",
            "digital_opt_in": "Consentement RGPD actif pour les notifications et offres dans l'application mobile.",
            "crm_updated_at": "Horodatage UTC de dernière mise à jour de la fiche dans le SaaS CRM.",
        },
    },
    "crm_account_portfolio": {
        "description": (
            "Portefeuille des comptes détenus par les clients dans le SaaS CRM (comptes courants et épargne). "
            "Trace les ouvertures récentes du trimestre et la référence éventuelle d'avenant promotionnel signé en agence."
        ),
        "columns": {
            "account_id": "Identifiant technique unique du compte bancaire (ACCxxxxxxxxxx).",
            "num_compte_11": "Numéro de compte BBAN sur 11 caractères (norme CFONB / RIB français).",
            "iban": "Identifiant international de compte bancaire FR76 (donnée sensible soumise au masquage).",
            "customer_id": "Identifiant du client titulaire principal (jointure vers crm_customers).",
            "agency_code_4": "Code agence commercial sur 4 caractères.",
            "guichet_code_5": "Code guichet RIB sur 5 chiffres.",
            "account_type": "Nature du produit (CHECKING, LIVRET_A, LDDS, LIVRET_BOOST_PROMO, PEL).",
            "product_label": "Libellé commercial du produit affiché au conseiller et au client.",
            "rate_bps": "Taux nominal servi exprimé en points de base (100 bps = 1,00 %).",
            "account_status": "État opérationnel du compte dans le CRM (OPEN, PENDING_BATCH, CLOSED).",
            "opened_date": "Date de souscription du compte en agence ou sur mobile.",
            "closed_date": "Date de clôture du compte (NULL tant que le compte est ouvert).",
            "opened_in_current_quarter": "Booléen indiquant une ouverture sur le trimestre en cours.",
            "promo_contract_id": "Référence de l'avenant promotionnel PDF d'agence applicable (PROMO-2026-xxx, NULL sinon).",
            "crm_sync_source": "Canal d'origine de la création ou synchronisation (AGENCY_REALTIME_J0, BATCH_SYNC).",
        },
    },
    "crm_interactions": {
        "description": (
            "Historique des comptes-rendus de rendez-vous en agence, messages sécurisés et appels Call Center. "
            "Contient la qualification conseiller du risque de fuite d'épargne et une note libre potentiellement sensible."
        ),
        "columns": {
            "interaction_id": "Identifiant unique de l'interaction CRM / Call Center.",
            "customer_id": "Identifiant du client concerné par l'échange.",
            "guichet_code_5": "Code guichet sur 5 chiffres de l'agence ayant traité le contact.",
            "interaction_ts": "Horodatage UTC exact du contact client.",
            "channel": "Canal d'interaction (CALL_CENTER, AGENCY_MEETING, MOBILE_SECURE_MSG).",
            "topic_code": "Motif normalisé de contact (ex. plafond SEPA Instant / épargne externe, offre promo agence, suivi courant).",
            "advisor_sentiment_tag": "Signal qualifié par le conseiller (AT_RISK_LIQUIDITY_OUTFLOW, PROMO_SENSITIVE, NEUTRAL_SATISFIED).",
            "verbatim_note": "Compte-rendu libre saisi par le conseiller (attention : peut contenir des PII ou noms de concurrents).",
        },
    },
    "crm_branches_ref": {
        "description": (
            "Référentiel commercial des 450 agences Banque Hexagone réparties sur les 8 directions régionales, "
            "avec le contrat cadre promotionnel rattaché par défaut."
        ),
        "columns": {
            "agency_num": "Numéro interne séquentiel de l'agence (1 à 450).",
            "agency_code_4": "Code agence sur 4 caractères utilisé dans les systèmes commerciaux.",
            "guichet_code_5": "Code guichet interbancaire sur 5 chiffres.",
            "city": "Commune d'implantation de l'agence.",
            "region_code": "Code de la direction régionale (REG01 à REG08).",
            "region_name": "Nom de la direction régionale commerciale.",
            "default_promo_contract_id": "Identifiant du contrat promotionnel PDF par défaut de l'agence.",
        },
    },
}


def update_aws_glue_and_iceberg(aws_region: str, s3_bucket: str, glue_db: str) -> int:
    """Pousse les descriptions de tables et de colonnes dans Iceberg (S3) et AWS Glue."""
    os.environ.setdefault("AWS_DEFAULT_REGION", aws_region)
    warehouse = f"s3://{s3_bucket}/RAW/AWS_SAAS_ICEBERG"
    catalog = GlueCatalog(
        "aws_crm_saas",
        **{"warehouse": warehouse, "glue.region": aws_region, "s3.region": aws_region},
    )
    glue = boto3.client("glue", region_name=aws_region)

    documented_cols = 0
    for tbl_name, spec in TABLE_SPECS.items():
        identifier = f"{glue_db}.{tbl_name}"
        tbl = catalog.load_table(identifier)

        # 1. Commit dans le metadata.json Apache Iceberg sur S3 (propriété comment + doc par colonne)
        with tbl.transaction() as tx:
            tx.set_properties(comment=spec["description"])
            with tx.update_schema() as upd:
                for col_name, col_doc in spec["columns"].items():
                    upd.update_column(col_name, doc=col_doc)

        # 2. Synchronisation explicite des champs Description et Columns[].Comment dans AWS Glue
        raw_tbl = glue.get_table(DatabaseName=glue_db, Name=tbl_name)["Table"]
        allowed_keys = {
            "Name", "Description", "Owner", "Retention", "StorageDescriptor",
            "PartitionKeys", "ViewOriginalText", "ViewExpandedText", "TableType",
            "Parameters", "TargetTable",
        }
        table_input = {k: v for k, v in raw_tbl.items() if k in allowed_keys}
        table_input["Description"] = spec["description"]
        table_input.setdefault("Parameters", {})["comment"] = spec["description"]
        for col in table_input["StorageDescriptor"]["Columns"]:
            if col["Name"] in spec["columns"]:
                col["Comment"] = spec["columns"][col["Name"]]
                documented_cols += 1
        glue.update_table(DatabaseName=glue_db, TableInput=table_input)
        print(f"[aws-glue] {identifier:<38} table + {len(spec['columns'])} colonnes documentées")

    return documented_cols


def build_clean_overview_html(tbl_name: str, spec: dict, glue_db: str, s3_bucket: str) -> str:
    """Construit une fiche HTML sobre pour l'onglet Overview de Knowledge Catalog (zéro bordure colorée)."""
    rows = "".join(
        f"<tr><td><code>{html.escape(col)}</code></td><td>{html.escape(doc)}</td></tr>"
        for col, doc in spec["columns"].items()
    )
    return (
        f"<p><strong>Source fédérée Borderless Lakehouse :</strong> AWS Glue "
        f"<code>{html.escape(glue_db)}.{html.escape(tbl_name)}</code> "
        f"(<code>s3://{html.escape(s3_bucket)}/RAW/AWS_SAAS_ICEBERG/{html.escape(tbl_name)}</code>).</p>"
        f"<p>{html.escape(spec['description'])}</p>"
        f"<h4>Dictionnaire métier synchronisé depuis AWS Glue ({len(spec['columns'])} colonnes)</h4>"
        f"<table><thead><tr><th>Colonne</th><th>Description métier</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def sync_and_enrich_knowledge_catalog(
    project_id: str, location: str, catalog_id: str, glue_db: str, s3_bucket: str
) -> dict:
    """Déclenche le refresh BigLake et enrichit l'onglet Overview des entrées @biglake dans Knowledge Catalog."""
    env = {**os.environ, "CLOUDSDK_METRICS_ENVIRONMENT": "datacloud.antigravity"}
    subprocess.run(
        [
            "gcloud", "beta", "biglake", "iceberg", "catalogs", "update", catalog_id,
            f"--project={project_id}", "--refresh-interval=300s", "--quiet",
        ],
        check=True,
        env=env,
    )

    token = subprocess.check_output(["gcloud", "auth", "print-access-token"], text=True).strip()
    ctx = ssl.create_default_context(cafile=certifi.where())
    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": project_id,
        "Content-Type": "application/json",
    }

    # Récupère le numéro de projet via searchEntries
    params = urllib.parse.urlencode({"query": f"name:{catalog_id} system=BIGLAKE", "scope": f"projects/{project_id}"})
    req = urllib.request.Request(
        f"https://dataplex.googleapis.com/v1/projects/{project_id}/locations/global:searchEntries?{params}",
        data=b"",
        method="POST",
        headers=headers,
    )
    with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
        results = json.loads(resp.read().decode("utf-8")).get("results", [])

    table_entries: dict[str, str] = {}
    for item in results:
        ename = item.get("dataplexEntry", {}).get("name", "")
        for tbl_name in TABLE_SPECS:
            if ename.endswith(f"/tables/{tbl_name}"):
                table_entries[tbl_name] = ename

    # Publie l'aspect Overview (655216118709.global.overview) sur chaque entrée @biglake
    aspect_key = "655216118709.global.overview"
    aspect_type = "projects/655216118709/locations/global/aspectTypes/overview"
    for tbl_name, ename in table_entries.items():
        spec = TABLE_SPECS[tbl_name]
        overview_html = build_clean_overview_html(tbl_name, spec, glue_db, s3_bucket)
        patch_url = (
            f"https://dataplex.googleapis.com/v1/{ename}"
            f"?updateMask=aspects&aspectKeys={urllib.parse.quote(aspect_key)}"
        )
        payload = {
            "name": ename,
            "aspects": {
                aspect_key: {
                    "aspectType": aspect_type,
                    "data": {
                        "content": overview_html,
                        "contentType": "HTML",
                    },
                }
            },
        }
        patch_req = urllib.request.Request(
            patch_url,
            data=json.dumps(payload).encode("utf-8"),
            method="PATCH",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(patch_req, context=ctx, timeout=20) as r:
                r.read()
            print(f"[knowledge-catalog] Overview HTML publié sur {tbl_name}")
        except urllib.error.HTTPError as e:
            print(f"[WARN] {tbl_name} HTTP {e.code}: {e.read().decode('utf-8')[:300]}")

    return table_entries


if __name__ == "__main__":
    load_dotenv(REPO_ROOT / ".env")
    load_dotenv(REPO_ROOT / ".env.aws.local", override=True)
    cols = update_aws_glue_and_iceberg(
        aws_region=os.getenv("AWS_REGION", "eu-west-1"),
        s3_bucket=os.getenv("AWS_S3_BUCKET_CRM", "data-days-demo-aws-crm-835872720625"),
        glue_db=os.getenv("AWS_GLUE_DATABASE", "crm_callcenter_db"),
    )
    entries = sync_and_enrich_knowledge_catalog(
        project_id=os.getenv("GCP_PROJECT_ID", "data-days-demo"),
        location=os.getenv("GCP_REGION", "europe-west1"),
        catalog_id=os.getenv("BIGLAKE_AWS_CATALOG_ID", "aws_crm_catalog"),
        glue_db=os.getenv("AWS_GLUE_DATABASE", "crm_callcenter_db"),
        s3_bucket=os.getenv("AWS_S3_BUCKET_CRM", "data-days-demo-aws-crm-835872720625"),
    )
    print(f"Terminé : {cols} colonnes Glue documentées et {len(entries)} tables enrichies dans Knowledge Catalog.")
