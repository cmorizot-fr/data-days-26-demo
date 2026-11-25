#!/usr/bin/env bash
# Copyright 2026 Google LLC
# SPDX-License-Identifier: Apache-2.0
#
# Shared configuration auto-detection, interactive parameter confirmation,
# full GCP + AWS + CLI pre-flight audit, and permissioned remediation helpers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Capture any explicit caller overrides before loading .env
_CALLER_GCP_PROJECT="${GCP_PROJECT:-}"
_CALLER_AWS_REGION="${AWS_REGION:-}"
_CALLER_GCP_REGION="${GCP_REGION:-}"
_CALLER_S3_BUCKET="${S3_BUCKET:-}"

# Load .env overrides from repository root if present
if [[ -f "${REPO_ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${REPO_ROOT}/.env"
  set +a
fi

# Re-apply explicit environment overrides if passed on the command line
[[ -n "${_CALLER_GCP_PROJECT}" ]] && GCP_PROJECT="${_CALLER_GCP_PROJECT}"
[[ -n "${_CALLER_AWS_REGION}" ]] && AWS_REGION="${_CALLER_AWS_REGION}"
[[ -n "${_CALLER_GCP_REGION}" ]] && GCP_REGION="${_CALLER_GCP_REGION}"
[[ -n "${_CALLER_S3_BUCKET}" ]] && S3_BUCKET="${_CALLER_S3_BUCKET}"

_EXPLICIT_AWS_REGION="${AWS_REGION:-}"
_EXPLICIT_GCP_REGION="${GCP_REGION:-}"
_EXPLICIT_S3_BUCKET="${S3_BUCKET:-}"

log_step() {
  printf "\n\033[1;34m==> %s\033[0m\n" "$*"
}

log_info() {
  printf "    %s\n" "$*"
}

log_ok() {
  printf "\033[1;32m✔ %s\033[0m\n" "$*"
}

log_warn() {
  printf "\033[1;33m⚠ %s\033[0m\n" "$*" >&2
}

log_err() {
  printf "\033[1;31m✖ ERROR: %s\033[0m\n" "$*" >&2
}

require_cmd() {
  local cmd="$1"
  local hint="$2"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    log_err "Required CLI '${cmd}' was not found on PATH. ${hint}"
    exit 1
  fi
}

print_aws_cli_install_help() {
  local os_name arch_name zip_url
  os_name="$(uname -s 2>/dev/null || echo "Linux")"
  arch_name="$(uname -m 2>/dev/null || echo "x86_64")"

  log_info "Install or upgrade to AWS CLI v2.32.0+ (required for 'aws login --remote'):"
  if [[ "${os_name}" == "Darwin" ]]; then
    log_info "  brew install awscli || brew upgrade awscli"
  else
    if [[ "${arch_name}" == "aarch64" || "${arch_name}" == "arm64" ]]; then
      zip_url="https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip"
    else
      zip_url="https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip"
    fi
    log_info "  curl -fsSL \"${zip_url}\" -o \"/tmp/awscliv2.zip\""
    log_info "  unzip -q -o /tmp/awscliv2.zip -d /tmp"
    log_info "  /tmp/aws/install --update -i \"\$HOME/.local/aws-cli\" -b \"\$HOME/.local/bin\""
    log_info "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  fi
}

detect_aws_cli_version() {
  local raw
  raw="$(aws --version 2>&1 || true)"
  raw="${raw%%$'\n'*}"
  if [[ "${raw}" =~ aws-cli/([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    printf "%s" "${BASH_REMATCH[1]}"
  else
    printf "unknown"
  fi
}

aws_cli_version_ge_2_32() {
  local ver major minor
  ver="$(detect_aws_cli_version)"
  if [[ "${ver}" =~ ^([0-9]+)\.([0-9]+)\. ]]; then
    major="${BASH_REMATCH[1]}"
    minor="${BASH_REMATCH[2]}"
    if (( major > 2 )) || (( major == 2 && minor >= 32 )); then
      return 0
    fi
  fi
  return 1
}

region_metro_label() {
  case "${1}:${2}" in
    us-east-1:us-east4)       printf "Northern Virginia" ;;
    us-west-2:us-west1)       printf "Oregon" ;;
    eu-central-1:europe-west3) printf "Frankfurt" ;;
    eu-west-2:europe-west2)   printf "London" ;;
    *)                        printf "Custom Pair" ;;
  esac
}

resolve_region_pair() {
  REGION_FALLBACK_NOTE=""
  local raw_aws="${_EXPLICIT_AWS_REGION}"
  local raw_gcp="${_EXPLICIT_GCP_REGION}"

  if [[ -z "${raw_aws}" ]]; then
    raw_aws="${AWS_DEFAULT_REGION:-}"
  fi
  if [[ -z "${raw_aws}" ]] && command -v aws >/dev/null 2>&1; then
    raw_aws="$(aws configure get region 2>/dev/null | tr -d '\r\n' || true)"
  fi

  if [[ -z "${raw_gcp}" ]]; then
    case "${raw_aws}" in
      us-east-1)
        AWS_REGION="us-east-1"
        GCP_REGION="us-east4"
        ;;
      us-west-2)
        AWS_REGION="us-west-2"
        GCP_REGION="us-west1"
        ;;
      eu-central-1)
        AWS_REGION="eu-central-1"
        GCP_REGION="europe-west3"
        ;;
      eu-west-2)
        AWS_REGION="eu-west-2"
        GCP_REGION="europe-west2"
        ;;
      "")
        AWS_REGION="us-east-1"
        GCP_REGION="us-east4"
        ;;
      *)
        AWS_REGION="us-east-1"
        GCP_REGION="us-east4"
        REGION_FALLBACK_NOTE="AWS CLI region '${raw_aws}' is not one of the 4 co-located Lakehouse regions -> defaulted to us-east-1 <-> us-east4 (type 'r' to switch)."
        ;;
    esac
  else
    GCP_REGION="${raw_gcp}"
    if [[ -z "${raw_aws}" ]]; then
      case "${GCP_REGION}" in
        us-east4)     AWS_REGION="us-east-1" ;;
        us-west1)     AWS_REGION="us-west-2" ;;
        europe-west3) AWS_REGION="eu-central-1" ;;
        europe-west2) AWS_REGION="eu-west-2" ;;
        *)            AWS_REGION="us-east-1" ;;
      esac
    else
      AWS_REGION="${raw_aws}"
    fi
  fi

  if [[ "${ALLOW_CUSTOM_REGION_PAIR:-false}" != "true" ]]; then
    case "${AWS_REGION}:${GCP_REGION}" in
      us-east-1:us-east4|us-west-2:us-west1|eu-central-1:europe-west3|eu-west-2:europe-west2)
        ;;
      *)
        log_err "Unsupported or non-colocated region pair AWS_REGION='${AWS_REGION}' <-> GCP_REGION='${GCP_REGION}'."
        log_info "Supported co-located region pairs:"
        log_info "  AWS us-east-1    <-> GCP us-east4     (Northern Virginia)"
        log_info "  AWS us-west-2    <-> GCP us-west1     (Oregon)"
        log_info "  AWS eu-central-1 <-> GCP europe-west3 (Frankfurt)"
        log_info "  AWS eu-west-2    <-> GCP europe-west2 (London)"
        log_info "(Set ALLOW_CUSTOM_REGION_PAIR=true in .env to bypass this check.)"
        exit 1
        ;;
    esac
  fi

  export AWS_REGION GCP_REGION REGION_FALLBACK_NOTE
  export AWS_DEFAULT_REGION="${AWS_REGION}"
}

refresh_derived_defaults() {
  export GLUE_DB="${GLUE_DB:-thelook_ecommerce}"
  export ATHENA_WORKGROUP="${ATHENA_WORKGROUP:-primary}"
  export AWS_ROLE_NAME="${AWS_ROLE_NAME:-gcp_lakehouse_glue_federation_role}"
  export FEDERATED_CATALOG="${FEDERATED_CATALOG:-thelook_catalog}"
  export CATALOG_NAMESPACE="${CATALOG_NAMESPACE:-${GLUE_DB}}"
  export BQ_DEMO_DATASET="${BQ_DEMO_DATASET:-thelook_commerce}"
  export SOURCE_BQ_PROJECT="${SOURCE_BQ_PROJECT:-bigquery-public-data}"
  export SOURCE_BQ_DATASET="${SOURCE_BQ_DATASET:-thelook_ecommerce}"

  if [[ -n "${_EXPLICIT_S3_BUCKET}" ]]; then
    S3_BUCKET="${_EXPLICIT_S3_BUCKET}"
  elif [[ -n "${AWS_ACCOUNT_ID:-}" ]]; then
    S3_BUCKET="thelook-lakehouse-${AWS_ACCOUNT_ID}-${AWS_REGION}"
  fi
  export S3_BUCKET="${S3_BUCKET:-}"

  if [[ -n "${GCP_PROJECT:-}" && -n "${AWS_ACCOUNT_ID:-}" ]]; then
    GCS_STAGE_BUCKET="gs://${GCP_PROJECT}-crosslook-stage-${AWS_ACCOUNT_ID}"
  fi
  export GCS_STAGE_BUCKET="${GCS_STAGE_BUCKET:-}"
}

detect_gcp_cli_session() {
  require_cmd "gcloud" "Install Google Cloud CLI: https://cloud.google.com/sdk/docs/install"
  require_cmd "bq" "Ensure BigQuery CLI ('bq') is installed with Google Cloud CLI."
  require_cmd "curl" "Install curl to call Google Cloud REST endpoints."
  require_cmd "python3" "Install Python 3.10+ for JSON parsing."

  if ! gcloud auth print-access-token --quiet >/dev/null 2>&1; then
    log_err "No active Google Cloud CLI session found."
    log_info "Sign in first with:"
    log_info "  gcloud auth login"
    exit 1
  fi

  GCP_USER="$(gcloud config get-value account 2>/dev/null | tr -d '\r\n' || true)"
  [[ "${GCP_USER}" == "(unset)" ]] && GCP_USER=""
  export GCP_USER

  if [[ -z "${GCP_PROJECT:-}" ]]; then
    GCP_PROJECT="$(gcloud config get-value project 2>/dev/null | tr -d '\r\n' || true)"
    [[ "${GCP_PROJECT}" == "(unset)" ]] && GCP_PROJECT=""
  fi
  export GCP_PROJECT
}

detect_aws_cli_session() {
  if ! command -v aws >/dev/null 2>&1; then
    log_err "Required CLI 'aws' (AWS CLI v2) was not found on PATH."
    print_aws_cli_install_help
    log_info "Then sign in with:"
    log_info "  aws login --remote"
    exit 1
  fi

  local sts_json
  if ! sts_json="$(aws sts get-caller-identity --output json 2>/dev/null)"; then
    local detected_ver
    detected_ver="$(detect_aws_cli_version)"
    log_err "No active AWS CLI credentials found (or your session expired)."
    if ! aws_cli_version_ge_2_32; then
      log_warn "Detected AWS CLI version '${detected_ver}' (< 2.32.0). Browser-based 'aws login --remote' requires v2.32.0+."
      print_aws_cli_install_help
      log_info "After upgrading (run 'hash -r' if needed), sign in with:"
    else
      log_info "Sign in with browser-based AWS Console login:"
    fi
    log_info "  aws login --remote"
    log_info "(Or 'aws login' / 'aws sso login' if preferred.)"
    exit 1
  fi

  read -r AWS_ACCOUNT_ID AWS_CALLER_ARN < <(
    python3 -c 'import json,sys; d=json.loads(sys.stdin.read()); print(d.get("Account",""), d.get("Arn",""))' <<< "${sts_json}"
  )

  if [[ -z "${AWS_ACCOUNT_ID}" || "${AWS_ACCOUNT_ID}" == "None" ]]; then
    log_err "Could not resolve AWS Account ID from 'aws sts get-caller-identity'."
    exit 1
  fi
  export AWS_ACCOUNT_ID AWS_CALLER_ARN
}

detect_all_parameters() {
  detect_gcp_cli_session
  detect_aws_cli_session
  resolve_region_pair
  refresh_derived_defaults
}

probe_existing_resources() {
  local probe_dir tmp_root
  tmp_root="${TMPDIR:-/tmp}"
  probe_dir="$(mktemp -d "${tmp_root%/}/crosslook-probe.XXXXXX")"

  (
    if aws s3api head-bucket --bucket "${S3_BUCKET}" --region "${AWS_REGION}" >/dev/null 2>&1; then
      printf "existing — will update" > "${probe_dir}/s3"
    else
      printf "new" > "${probe_dir}/s3"
    fi
  ) &

  (
    if aws glue get-database --region "${AWS_REGION}" --name "${GLUE_DB}" >/dev/null 2>&1; then
      printf "existing — will update" > "${probe_dir}/glue"
    else
      printf "new" > "${probe_dir}/glue"
    fi
  ) &

  (
    if aws iam get-role --role-name "${AWS_ROLE_NAME}" >/dev/null 2>&1; then
      printf "existing — will update" > "${probe_dir}/iam"
    else
      printf "new" > "${probe_dir}/iam"
    fi
  ) &

  (
    local tok code
    tok="$(gcloud auth print-access-token --quiet 2>/dev/null || true)"
    code="$(curl -s -o /dev/null -w "%{http_code}" \
      -H "Authorization: Bearer ${tok}" \
      -H "x-goog-user-project: ${GCP_PROJECT}" \
      "https://biglake.googleapis.com/iceberg/v1/restcatalog/extensions/projects/${GCP_PROJECT}/catalogs/${FEDERATED_CATALOG}" || echo "000")"
    if [[ "${code}" == "200" ]]; then
      printf "existing — will update" > "${probe_dir}/cat"
    else
      printf "new" > "${probe_dir}/cat"
    fi
  ) &

  (
    if bq --project_id="${GCP_PROJECT}" show --dataset "${GCP_PROJECT}:${BQ_DEMO_DATASET}" >/dev/null 2>&1; then
      printf "existing — will update" > "${probe_dir}/bq"
    else
      printf "new" > "${probe_dir}/bq"
    fi
  ) &

  (
    if [[ -n "${GCS_STAGE_BUCKET:-}" ]] && gcloud storage buckets describe "${GCS_STAGE_BUCKET}" --project="${GCP_PROJECT}" --quiet >/dev/null 2>&1; then
      printf "existing — will update" > "${probe_dir}/gcs"
    else
      printf "new" > "${probe_dir}/gcs"
    fi
  ) &

  wait || true

  STATE_S3="$(cat "${probe_dir}/s3" 2>/dev/null || echo "new")"
  STATE_GLUE="$(cat "${probe_dir}/glue" 2>/dev/null || echo "new")"
  STATE_IAM="$(cat "${probe_dir}/iam" 2>/dev/null || echo "new")"
  STATE_CAT="$(cat "${probe_dir}/cat" 2>/dev/null || echo "new")"
  STATE_BQ="$(cat "${probe_dir}/bq" 2>/dev/null || echo "new")"
  STATE_GCS="$(cat "${probe_dir}/gcs" 2>/dev/null || echo "new")"
  rm -rf "${probe_dir}" || true
}

save_resolved_dotenv() {
  cat > "${REPO_ROOT}/.env" <<EOF
# Auto-saved by ./deploy.sh — keeps cleanup.sh, helper scripts & notebook in sync
GCP_PROJECT="${GCP_PROJECT}"
AWS_REGION="${AWS_REGION}"
GCP_REGION="${GCP_REGION}"
S3_BUCKET="${S3_BUCKET}"
GCS_STAGE_BUCKET="${GCS_STAGE_BUCKET}"
GLUE_DB="${GLUE_DB}"
ATHENA_WORKGROUP="${ATHENA_WORKGROUP}"
AWS_ROLE_NAME="${AWS_ROLE_NAME}"
FEDERATED_CATALOG="${FEDERATED_CATALOG}"
BQ_DEMO_DATASET="${BQ_DEMO_DATASET}"
SOURCE_BQ_PROJECT="${SOURCE_BQ_PROJECT}"
SOURCE_BQ_DATASET="${SOURCE_BQ_DATASET}"
EOF
}

print_parameter_summary() {
  local metro
  metro="$(region_metro_label "${AWS_REGION}" "${GCP_REGION}")"
  probe_existing_resources

  printf "\n==============================================================================\n"
  printf " Cross-Look — Detected Parameters (from gcloud & aws CLI config)\n"
  printf "==============================================================================\n"
  printf "  Google Cloud Account : %s\n" "${GCP_USER:-active-credentials}"
  printf "  Google Cloud Project : %s\n" "${GCP_PROJECT}"
  printf "  AWS Account & Caller : %s (%s)\n" "${AWS_ACCOUNT_ID}" "${AWS_CALLER_ARN}"
  printf "  Co-Located Regions   : AWS %s  <->  GCP %s (%s)\n" "${AWS_REGION}" "${GCP_REGION}" "${metro}"
  printf "  Amazon S3 Bucket     : s3://%s [%s]\n" "${S3_BUCKET}" "${STATE_S3}"
  printf "  AWS Glue Database    : %s [%s]\n" "${GLUE_DB}" "${STATE_GLUE}"
  printf "  AWS OIDC IAM Role    : %s [%s]\n" "${AWS_ROLE_NAME}" "${STATE_IAM}"
  printf "  GCS Staging Bucket   : %s [%s]\n" "${GCS_STAGE_BUCKET}" "${STATE_GCS}"
  printf "  Federated Catalog    : %s.%s [%s]\n" "${GCP_PROJECT}" "${FEDERATED_CATALOG}" "${STATE_CAT}"
  printf "  BigQuery Dataset     : %s:%s [%s]\n" "${GCP_PROJECT}" "${BQ_DEMO_DATASET}" "${STATE_BQ}"
  if [[ -n "${REGION_FALLBACK_NOTE:-}" ]]; then
    printf "  Region Note          : %s\n" "${REGION_FALLBACK_NOTE}"
  fi
  printf "==============================================================================\n"
}

confirm_parameters_interactively() {
  local auto_approve="${1:-false}"
  detect_all_parameters

  if [[ "${auto_approve}" == "true" ]]; then
    if [[ -z "${GCP_PROJECT}" ]]; then
      log_err "GCP_PROJECT is not set in gcloud config, environment, or .env (required with --yes)."
      log_info "Run 'gcloud config set project YOUR_EXISTING_PROJECT_ID' or omit --yes to enter it interactively."
      exit 1
    fi
    print_parameter_summary
    save_resolved_dotenv
    return 0
  fi

  while [[ -z "${GCP_PROJECT}" ]]; do
    read -r -p "No default project in gcloud config. Enter an existing Google Cloud Project ID: " GCP_PROJECT
    GCP_PROJECT="$(printf "%s" "${GCP_PROJECT}" | tr -d '[:space:]')"
  done
  export GCP_PROJECT

  while true; do
    print_parameter_summary
    printf "Confirm [Enter/y], type another existing GCP project ID, 'r' to switch region pair, or 'q' to quit: "
    local reply=""
    read -r reply
    reply="$(printf "%s" "${reply}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

    case "${reply}" in
      ""|y|Y|yes|YES)
        save_resolved_dotenv
        log_ok "Parameters confirmed and saved to .env (project: '${GCP_PROJECT}', regions: ${AWS_REGION} <-> ${GCP_REGION})."
        return 0
        ;;
      q|Q|n|N|no|NO|quit|exit)
        log_info "Deployment cancelled."
        exit 0
        ;;
      r|R|region|regions)
        printf "\n  Select a co-located AWS <-> Google Cloud region pair:\n"
        printf "    1) AWS us-east-1    <-> GCP us-east4     (Northern Virginia)\n"
        printf "    2) AWS us-west-2    <-> GCP us-west1     (Oregon)\n"
        printf "    3) AWS eu-central-1 <-> GCP europe-west3 (Frankfurt)\n"
        printf "    4) AWS eu-west-2    <-> GCP europe-west2 (London)\n"
        local rchoice=""
        read -r -p "  Enter choice [1-4] (default 1): " rchoice
        case "${rchoice}" in
          ""|1) AWS_REGION="us-east-1";    GCP_REGION="us-east4" ;;
          2)    AWS_REGION="us-west-2";    GCP_REGION="us-west1" ;;
          3)    AWS_REGION="eu-central-1"; GCP_REGION="europe-west3" ;;
          4)    AWS_REGION="eu-west-2";    GCP_REGION="europe-west2" ;;
          *)    log_warn "Invalid selection '${rchoice}' — keeping ${AWS_REGION} <-> ${GCP_REGION}." ;;
        esac
        REGION_FALLBACK_NOTE=""
        export AWS_REGION GCP_REGION AWS_DEFAULT_REGION="${AWS_REGION}" REGION_FALLBACK_NOTE
        refresh_derived_defaults
        ;;
      *)
        if [[ "${reply}" =~ ^[a-z][a-z0-9-]{4,29}$ ]]; then
          GCP_PROJECT="${reply}"
          export GCP_PROJECT
          log_info "Switched Google Cloud project to '${GCP_PROJECT}' — refreshing summary..."
        else
          log_warn "'${reply}' is not a valid Google Cloud Project ID (must be 6-30 lowercase letters, digits, or hyphens)."
        fi
        ;;
    esac
  done
}

run_full_preflight() {
  local auto_approve="${1:-false}"
  local skip_export="${2:-false}"
  local skip_glue="${3:-false}"

  log_step "Running Full Pre-Flight Check (CLI, Google Cloud '${GCP_PROJECT}' & AWS '${AWS_ACCOUNT_ID}')..."

  local has_gcloud_biglake="false"
  local ga_create_help
  ga_create_help="$(gcloud biglake iceberg catalogs create --help 2>&1 || true)"
  if grep -q -- '--federated-catalog-type' <<< "${ga_create_help}" \
     || gcloud beta biglake iceberg catalogs --help >/dev/null 2>&1 \
     || gcloud alpha biglake iceberg catalogs --help >/dev/null 2>&1; then
    has_gcloud_biglake="true"
  fi

  local gcp_token
  gcp_token="$(gcloud auth print-access-token --quiet)"

  local enabled_services
  enabled_services="$(gcloud services list --enabled --project="${GCP_PROJECT}" --format="value(config.name)" --quiet 2>/dev/null || true)"

  local pf_json_file tmp_root
  tmp_root="${TMPDIR:-/tmp}"
  rm -f "${tmp_root%/}/crosslook-pf.XXXXXX.json" 2>/dev/null || true
  pf_json_file="$(mktemp "${tmp_root%/}/crosslook-pf.XXXXXX")"

  GCP_TOKEN="${gcp_token}" \
  ENABLED_SERVICES_RAW="${enabled_services}" \
  HAS_GCLOUD_BIGLAKE="${has_gcloud_biglake}" \
  SKIP_EXPORT="${skip_export}" \
  SKIP_GLUE="${skip_glue}" \
  PF_OUT="${pf_json_file}" \
  python3 - <<'PY'
from __future__ import annotations
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.request

gcp_project = os.environ["GCP_PROJECT"]
gcp_user = os.environ.get("GCP_USER", "")
gcp_region = os.environ["GCP_REGION"]
aws_region = os.environ["AWS_REGION"]
aws_account = os.environ["AWS_ACCOUNT_ID"]
aws_caller_arn = os.environ.get("AWS_CALLER_ARN", "")
s3_bucket = os.environ["S3_BUCKET"]
glue_db = os.environ["GLUE_DB"]
athena_wg = os.environ["ATHENA_WORKGROUP"]
aws_role = os.environ["AWS_ROLE_NAME"]
token = os.environ["GCP_TOKEN"]
has_biglake_cli = os.environ["HAS_GCLOUD_BIGLAKE"] == "true"
skip_export = os.environ["SKIP_EXPORT"] == "true"
skip_glue = os.environ["SKIP_GLUE"] == "true"
pf_out = os.environ["PF_OUT"]

enabled_set = {
    line.strip()
    for line in os.environ.get("ENABLED_SERVICES_RAW", "").splitlines()
    if line.strip()
}

REQUIRED_APIS = [
    "bigquery.googleapis.com",
    "biglake.googleapis.com",
    "bigqueryconnection.googleapis.com",
    "aiplatform.googleapis.com",
    "storage.googleapis.com",
    "dataform.googleapis.com",
    "compute.googleapis.com",
    "dataplex.googleapis.com",
    "geminidataanalytics.googleapis.com",
    "cloudaicompanion.googleapis.com",
]


def _make_ssl_ctx() -> ssl.SSLContext:
    for cafile in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
        if os.path.isfile(cafile):
            try:
                return ssl.create_default_context(cafile=cafile)
            except Exception:
                pass
    return ssl.create_default_context()


_SSL_CTX = _make_ssl_ctx()


def _curl_fallback(method: str, url: str, headers: dict[str, str], payload: dict | None) -> tuple[int, dict]:
    cmd = ["curl", "-sS", "-X", method, "-w", "\n%{http_code}"]
    for k, v in headers.items():
        cmd.extend(["-H", f"{k}: {v}"])
    if payload is not None:
        cmd.extend(["-d", json.dumps(payload)])
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
    if p.returncode != 0:
        return 0, {"error": {"message": p.stderr.strip() or f"curl exit {p.returncode}"}}
    out = p.stdout
    raw_body, _, code_str = out.rpartition("\n")
    try:
        code = int(code_str.strip())
    except Exception:
        code = 0
    try:
        body = json.loads(raw_body) if raw_body.strip() else {}
    except Exception:
        body = {"raw": raw_body}
    return code, (body if isinstance(body, dict) else {"data": body})


def http_json(method: str, url: str, payload: dict | None = None) -> tuple[int, dict]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "x-goog-user-project": gcp_project,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20, context=_SSL_CTX) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw.strip() else {}
            return resp.status, (parsed if isinstance(parsed, dict) else {"data": parsed})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except Exception:
            body = {"raw": raw}
        return exc.code, (body if isinstance(body, dict) else {"raw": raw})
    except Exception:
        return _curl_fallback(method, url, headers, payload)


def extract_err_detail(body: dict, code: int) -> str:
    err = body.get("error") if isinstance(body, dict) else None
    if isinstance(err, dict):
        return str(err.get("message") or f"HTTP {code}")
    if isinstance(err, str) and err:
        return err
    return f"HTTP {code}"


def test_gcp_permissions(perms: list[str]) -> set[str]:
    if not perms:
        return set()
    url = f"https://cloudresourcemanager.googleapis.com/v1/projects/{gcp_project}:testIamPermissions"
    code, body = http_json("POST", url, {"permissions": perms})
    if code == 200:
        return set(body.get("permissions") or [])
    # Fallback one-by-one if a permission ID was rejected with 400
    granted: set[str] = set()
    for p in perms:
        c1, b1 = http_json("POST", url, {"permissions": [p]})
        if c1 == 200 and p in (b1.get("permissions") or []):
            granted.add(p)
        elif c1 == 400:
            # Unrecognized permission string on this endpoint; do not false-fail
            granted.add(p)
    return granted


def run_cmd(args: list[str]) -> tuple[int, str, str]:
    p = subprocess.run(args, capture_output=True, text=True, timeout=25)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


checks: list[dict] = []
blockers: list[dict] = []
remediations: list[dict] = []

# 1. Local CLI: gcloud beta/alpha biglake iceberg catalogs
if has_biglake_cli:
    checks.append({"status": "PASS", "area": "CLI", "msg": "gcloud BigLake federated catalog CLI ('beta') installed"})
else:
    checks.append({"status": "MISSING", "area": "CLI", "msg": "gcloud 'beta' component is not installed (needed for federated catalog commands)"})
    remediations.append({
        "kind": "install_gcloud_beta",
        "summary": "Install gcloud 'beta' CLI component (gcloud components install beta --quiet)",
    })

# 2. GCP Project Access & Billing
p_code, p_body = http_json("GET", f"https://cloudresourcemanager.googleapis.com/v1/projects/{gcp_project}")
project_ok = False
if p_code == 200 and p_body.get("lifecycleState") == "ACTIVE":
    project_ok = True
    checks.append({"status": "PASS", "area": "GCP", "msg": f"Project '{gcp_project}' exists and is ACTIVE"})
else:
    detail = extract_err_detail(p_body, p_code)
    checks.append({"status": "BLOCKER", "area": "GCP", "msg": f"Cannot access active GCP project '{gcp_project}' ({detail})"})
    blockers.append({
        "title": f"GCP project '{gcp_project}' is inaccessible or does not exist",
        "cmd": "Re-run ./deploy.sh and enter an existing Google Cloud Project ID that your account can access.",
    })

if project_ok:
    b_code, b_body = http_json("GET", f"https://cloudbilling.googleapis.com/v1/projects/{gcp_project}/billingInfo")
    if b_code == 200 and b_body.get("billingEnabled") is False:
        checks.append({"status": "BLOCKER", "area": "GCP", "msg": f"Billing is NOT enabled on GCP project '{gcp_project}'"})
        blockers.append({
            "title": f"Enable billing on '{gcp_project}'",
            "cmd": f"gcloud billing accounts list --filter='open=true'\ngcloud billing projects link \"{gcp_project}\" --billing-account=YOUR_BILLING_ACCOUNT_ID",
        })
    elif b_code == 200 and b_body.get("billingEnabled") is True:
        checks.append({"status": "PASS", "area": "GCP", "msg": f"Billing is enabled on '{gcp_project}'"})
    else:
        checks.append({"status": "PASS", "area": "GCP", "msg": f"Project '{gcp_project}' active (billing managed at org level)"})

# 3. GCP APIs & IAM Permissions
if project_ok:
    all_probe_perms = [
        "resourcemanager.projects.setIamPolicy",
        "resourcemanager.projects.getIamPolicy",
        "serviceusage.services.enable",
        "serviceusage.services.list",
        "bigquery.datasets.create",
        "bigquery.jobs.create",
        "storage.buckets.create",
        "biglake.catalogs.create",
        "aiplatform.endpoints.predict",
        "compute.networks.list",
        "compute.networks.create",
    ]
    granted_perms = test_gcp_permissions(all_probe_perms)
    can_set_iam = "resourcemanager.projects.setIamPolicy" in granted_perms
    can_enable_apis = "serviceusage.services.enable" in granted_perms

    # Also inspect direct role bindings if getIamPolicy is permitted (detects roles/owner cleanly)
    direct_user_roles: set[str] = set()
    if "resourcemanager.projects.getIamPolicy" in granted_perms and gcp_user:
        ic, ib = http_json("POST", f"https://cloudresourcemanager.googleapis.com/v1/projects/{gcp_project}:getIamPolicy", {})
        if ic == 200:
            target_member = f"user:{gcp_user.lower()}"
            for binding in ib.get("bindings") or []:
                members = [m.lower() for m in (binding.get("members") or [])]
                if target_member in members:
                    direct_user_roles.add(binding.get("role", ""))

    is_owner = "roles/owner" in direct_user_roles

    # If gcloud services list returned empty because serviceusage wasn't readable via CLI, try REST fallback
    if not enabled_set and "serviceusage.services.list" in granted_perms:
        sc, sb = http_json("GET", f"https://serviceusage.googleapis.com/v1/projects/{gcp_project}/services?filter=state:ENABLED&pageSize=200")
        if sc == 200:
            for svc in sb.get("services") or []:
                cfg_name = ((svc.get("config") or {}).get("name")) or svc.get("name", "").rsplit("/", 1)[-1]
                if cfg_name:
                    enabled_set.add(cfg_name)

    missing_apis = [api for api in REQUIRED_APIS if api not in enabled_set]
    if not missing_apis:
        checks.append({"status": "PASS", "area": "GCP", "msg": f"All {len(REQUIRED_APIS)} required Google Cloud APIs are enabled"})
    elif can_enable_apis or is_owner:
        checks.append({
            "status": "MISSING",
            "area": "GCP",
            "msg": f"{len(missing_apis)}/{len(REQUIRED_APIS)} Google Cloud APIs need to be enabled: {', '.join(missing_apis)}",
        })
        remediations.append({
            "kind": "enable_gcp_apis",
            "apis": missing_apis,
            "summary": f"Enable {len(missing_apis)} Google Cloud API(s) on '{gcp_project}': {', '.join(missing_apis)}",
        })
    else:
        checks.append({
            "status": "BLOCKER",
            "area": "GCP",
            "msg": f"{len(missing_apis)} Google Cloud APIs are disabled and caller lacks 'serviceusage.services.enable'",
        })
        blockers.append({
            "title": f"Ask a Project Admin to enable required APIs on '{gcp_project}'",
            "cmd": f"gcloud services enable {' '.join(missing_apis)} --project=\"{gcp_project}\" --quiet",
        })

    # Evaluate GCP IAM capability groups
    cap_specs = [
        ("BigQuery datasets, graphs & jobs", ["bigquery.datasets.create", "bigquery.jobs.create"], ["roles/bigquery.admin"], True),
        ("Cloud Storage Parquet staging", ["storage.buckets.create"], ["roles/storage.admin"], not skip_export),
        ("BigLake federated catalog", ["biglake.catalogs.create"], ["roles/biglake.admin"], True),
        ("Vertex AI (AI.* queries)", ["aiplatform.endpoints.predict"], ["roles/aiplatform.user"], True),
    ]

    missing_roles: list[str] = []
    missing_cap_labels: list[str] = []
    for label, req_p, rec_roles, active in cap_specs:
        if not active or is_owner:
            continue
        if any(r in direct_user_roles for r in rec_roles):
            continue
        if not all(p in granted_perms for p in req_p):
            missing_cap_labels.append(label)
            for rr in rec_roles:
                if rr not in missing_roles:
                    missing_roles.append(rr)

    # If user can self-grant IAM, also check optional Studio/Graph-Chat UI roles if not owner/editor
    if can_set_iam and not is_owner and gcp_user:
        for ui_role in ("roles/bigquery.studioUser", "roles/aiplatform.colabEnterpriseUser", "roles/geminidataanalytics.dataAgentCreator", "roles/cloudaicompanion.user"):
            if ui_role not in direct_user_roles and "roles/editor" not in direct_user_roles:
                if ui_role not in missing_roles and missing_roles:
                    missing_roles.append(ui_role)

    if not missing_roles:
        checks.append({"status": "PASS", "area": "GCP", "msg": f"GCP IAM permissions verified for '{gcp_user or 'active caller'}'"})
    elif can_set_iam and gcp_user:
        checks.append({
            "status": "MISSING",
            "area": "GCP",
            "msg": f"Missing GCP IAM permissions ({', '.join(missing_cap_labels)}) -> roles needed: {', '.join(missing_roles)}",
        })
        remediations.append({
            "kind": "grant_gcp_roles",
            "roles": missing_roles,
            "member": f"user:{gcp_user}",
            "summary": f"Grant {len(missing_roles)} IAM role(s) to user:{gcp_user} on '{gcp_project}': {', '.join(missing_roles)}",
        })
    else:
        checks.append({
            "status": "BLOCKER",
            "area": "GCP",
            "msg": f"Missing GCP IAM permissions ({', '.join(missing_cap_labels)}) and caller cannot self-grant IAM policies",
        })
        role_lines = " \\\n  ".join(missing_roles)
        blockers.append({
            "title": f"Ask a Project IAM Admin to grant these roles to '{gcp_user or 'YOUR_EMAIL'}' on '{gcp_project}'",
            "cmd": (
                f"for role in \\\n  {role_lines}; do\n"
                f"  gcloud projects add-iam-policy-binding \"{gcp_project}\" \\\n"
                f"    --member=\"user:{gcp_user or 'YOUR_EMAIL'}\" --role=\"${{role}}\" --condition=None --quiet\n"
                f"done"
            ),
        })

    # 4. Smart Non-Blocking VPC Check (for BigQuery Studio zero-config runtime)
    if "compute.googleapis.com" in enabled_set and "compute.networks.list" in granted_perms:
        nc, nb = http_json("GET", f"https://compute.googleapis.com/compute/v1/projects/{gcp_project}/global/networks?maxResults=5")
        if nc == 200:
            nets = [it.get("name", "") for it in (nb.get("items") or []) if it.get("name")]
            if nets:
                checks.append({"status": "PASS", "area": "GCP", "msg": f"VPC network ready for BigQuery Studio Notebooks ({', '.join(nets[:3])})"})
            elif "compute.networks.create" in granted_perms or is_owner:
                checks.append({"status": "MISSING", "area": "GCP", "msg": "0 VPC networks in project (BigQuery Studio default runtime expects a VPC network)"})
                remediations.append({
                    "kind": "create_default_vpc",
                    "summary": f"Create 'default' auto-mode VPC network on '{gcp_project}' (non-blocking if restricted by org policy)",
                })
            else:
                checks.append({"status": "WARN", "area": "GCP", "msg": "0 local VPC networks found (use a Shared VPC / Runtime Template in BigQuery Studio)"})

# 5. AWS Pre-Flight (S3, Glue, Athena, IAM)
aws_issues: list[str] = []

if not skip_export:
    rc_hb, _, _ = run_cmd(["aws", "s3api", "head-bucket", "--bucket", s3_bucket, "--region", aws_region])
    if rc_hb != 0:
        rc_lb, _, err_lb = run_cmd(["aws", "s3api", "list-buckets", "--query", "Buckets[0].Name", "--output", "text"])
        if rc_lb != 0 and "AccessDenied" in err_lb:
            aws_issues.append(f"S3: AccessDenied listing/checking bucket 's3://{s3_bucket}' (need s3:CreateBucket, s3:PutObject, s3:GetObject, s3:ListBucket)")

rc_gl, _, err_gl = run_cmd(["aws", "glue", "get-databases", "--region", aws_region, "--max-results", "1", "--output", "json"])
if rc_gl != 0:
    aws_issues.append(f"AWS Glue ({aws_region}): cannot read Glue Data Catalog ({err_gl.splitlines()[-1] if err_gl else 'AccessDenied'})")

if not skip_glue:
    rc_ath, out_ath, err_ath = run_cmd([
        "aws", "athena", "get-work-group",
        "--region", aws_region,
        "--work-group", athena_wg,
        "--query", "WorkGroup.State",
        "--output", "text",
    ])
    if rc_ath != 0:
        aws_issues.append(f"Athena ({aws_region}): cannot access workgroup '{athena_wg}' ({err_ath.splitlines()[-1] if err_ath else 'error'})")
    elif out_ath.strip() and out_ath.strip() != "ENABLED":
        aws_issues.append(f"Athena workgroup '{athena_wg}' in {aws_region} is '{out_ath.strip()}' (must be ENABLED)")

rc_iam, _, err_iam = run_cmd(["aws", "iam", "get-role", "--role-name", aws_role])
if rc_iam != 0 and "NoSuchEntity" not in err_iam:
    aws_issues.append(f"AWS IAM: cannot inspect/manage role '{aws_role}' (need iam:GetRole, iam:CreateRole, iam:PutRolePolicy, iam:UpdateAssumeRolePolicy)")

# Note: Do NOT gate on `aws iam simulate-principal-policy` here — browser-based
# `aws login` sessions and MFA/SCP conditions (`aws:MultiFactorAuthPresent`,
# `aws:ViaAWSService`, etc.) are omitted from SimulatePrincipalPolicy's synthetic
# request context, causing false-positive denials for valid admin sessions.

if not aws_issues:
    checks.append({"status": "PASS", "area": "AWS", "msg": f"AWS S3, Glue, Athena ('{athena_wg}') & IAM verified in {aws_region}"})
else:
    for issue in aws_issues:
        checks.append({"status": "BLOCKER", "area": "AWS", "msg": issue})
    blockers.append({
        "title": f"Grant required AWS permissions to '{aws_caller_arn or 'your AWS principal'}'",
        "cmd": (
            f"Ensure your AWS IAM principal allows:\n"
            f"  - S3: s3:CreateBucket, s3:ListBucket, s3:GetObject, s3:PutObject, s3:DeleteObject on arn:aws:s3:::{s3_bucket}[/*]\n"
            f"  - Glue: glue:Get*, glue:CreateDatabase, glue:CreateTable, glue:DeleteTable in {aws_region}\n"
            f"  - Athena: athena:StartQueryExecution, athena:GetQueryExecution, athena:GetQueryResults, athena:GetWorkGroup on '{athena_wg}'\n"
            f"  - IAM: iam:GetRole, iam:CreateRole, iam:PutRolePolicy, iam:UpdateAssumeRolePolicy on arn:aws:iam::{aws_account}:role/{aws_role}"
        ),
    })

with open(pf_out, "w", encoding="utf-8") as fh:
    json.dump({"checks": checks, "blockers": blockers, "remediations": remediations}, fh, indent=2)
PY

  # Print formatted Pre-Flight Checklist
  python3 - "${pf_json_file}" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
for c in data["checks"]:
    st = c["status"]
    area = f"[{c['area']}]"
    if st == "PASS":
        print(f"  \033[1;32m✔ PASS   \033[0m {area:<6} {c['msg']}")
    elif st == "MISSING":
        print(f"  \033[1;33m⚠ MISSING\033[0m {area:<6} {c['msg']}")
    elif st == "WARN":
        print(f"  \033[1;36mℹ NOTE   \033[0m {area:<6} {c['msg']}")
    else:
        print(f"  \033[1;31m✖ BLOCKER\033[0m {area:<6} {c['msg']}")
PY

  local blocker_count remediation_count
  read -r blocker_count remediation_count < <(
    python3 - "${pf_json_file}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print(len(d["blockers"]), len(d["remediations"]))
PY
  )

  if (( blocker_count > 0 )); then
    printf "\n"
    log_err "Pre-flight found ${blocker_count} blocking prerequisite(s) that require admin action before deploying:"
    python3 - "${pf_json_file}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for idx, b in enumerate(d["blockers"], 1):
    print(f"\n  {idx}. {b['title']}:")
    for line in b["cmd"].splitlines():
        print(f"     {line}")
PY
    rm -f "${pf_json_file}" || true
    printf "\n"
    exit 1
  fi

  if (( remediation_count > 0 )); then
    printf "\n  \033[1;33mThe following %s item(s) are missing and can be enabled / granted now:\033[0m\n" "${remediation_count}"
    python3 - "${pf_json_file}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for idx, r in enumerate(d["remediations"], 1):
    print(f"    {idx}) {r['summary']}")
PY

    if [[ "${auto_approve}" != "true" ]]; then
      printf "\n  Enable / grant these missing prerequisite(s) now? [Y/n]: "
      local fix_reply=""
      read -r fix_reply
      if [[ -n "${fix_reply}" && ! "${fix_reply}" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        rm -f "${pf_json_file}" || true
        log_info "Cancelled — no APIs or IAM policies were modified."
        exit 0
      fi
    fi

    local needs_propagation_wait="false"

    # Execute approved remediations in deterministic order: CLI -> IAM roles -> GCP APIs -> optional default VPC
    if python3 -c 'import json,sys; sys.exit(0 if any(r["kind"]=="install_gcloud_beta" for r in json.load(open(sys.argv[1]))["remediations"]) else 1)' "${pf_json_file}"; then
      log_step "Installing gcloud 'beta' CLI component..."
      if ! gcloud components install beta --quiet; then
        log_err "Could not auto-install 'gcloud beta' (your Cloud SDK may be managed by an OS package manager)."
        log_info "Install the google-cloud-cli-beta package for your OS, then re-run ./deploy.sh."
        exit 1
      fi
      log_ok "gcloud 'beta' component installed."
    fi

    local roles_to_grant
    roles_to_grant="$(python3 -c 'import json,sys; print(" ".join(next((r["roles"] for r in json.load(open(sys.argv[1]))["remediations"] if r["kind"]=="grant_gcp_roles"), [])))' "${pf_json_file}")"
    if [[ -n "${roles_to_grant}" ]]; then
      log_step "Granting missing IAM role(s) to user:${GCP_USER} on '${GCP_PROJECT}'..."
      for role in ${roles_to_grant}; do
        log_info "Granting ${role}..."
        gcloud projects add-iam-policy-binding "${GCP_PROJECT}" \
          --member="user:${GCP_USER}" \
          --role="${role}" \
          --condition=None \
          --quiet >/dev/null
      done
      needs_propagation_wait="true"
      log_ok "Granted IAM role(s): ${roles_to_grant}"
    fi

    local apis_to_enable
    apis_to_enable="$(python3 -c 'import json,sys; print(" ".join(next((r["apis"] for r in json.load(open(sys.argv[1]))["remediations"] if r["kind"]=="enable_gcp_apis"), [])))' "${pf_json_file}")"
    if [[ -n "${apis_to_enable}" ]]; then
      log_step "Enabling missing Google Cloud API(s) on '${GCP_PROJECT}'..."
      # shellcheck disable=SC2086
      gcloud services enable ${apis_to_enable} --project="${GCP_PROJECT}" --quiet
      needs_propagation_wait="true"
      log_ok "Enabled API(s): ${apis_to_enable}"
    fi

    if python3 -c 'import json,sys; sys.exit(0 if any(r["kind"]=="create_default_vpc" for r in json.load(open(sys.argv[1]))["remediations"]) else 1)' "${pf_json_file}"; then
      log_step "Creating 'default' auto-mode VPC network on '${GCP_PROJECT}' (for BigQuery Studio runtime)..."
      if gcloud compute networks create default --project="${GCP_PROJECT}" --subnet-mode=auto --quiet >/dev/null 2>&1; then
        log_ok "Created 'default' VPC network."
      else
        log_warn "Could not create auto-mode 'default' VPC (restricted by organization policy) — continuing (use a Colab Runtime Template if needed)."
      fi
    fi

    if [[ "${needs_propagation_wait}" == "true" ]]; then
      log_info "Waiting 10s for newly enabled APIs / IAM bindings to propagate..."
      sleep 10
    fi

    # If compute.googleapis.com was just enabled for the first time, check if 0 VPC networks exist
    if [[ " ${apis_to_enable} " == *" compute.googleapis.com "* ]]; then
      local existing_vpc
      existing_vpc="$(gcloud compute networks list --project="${GCP_PROJECT}" --limit=1 --format="value(name)" --quiet 2>/dev/null | tr -d '\r\n' || true)"
      if [[ -z "${existing_vpc}" ]]; then
        log_info "0 VPC networks detected after enabling Compute Engine API — creating 'default' network for BigQuery Studio..."
        gcloud compute networks create default --project="${GCP_PROJECT}" --subnet-mode=auto --quiet >/dev/null 2>&1 || \
          log_warn "Auto-mode 'default' VPC restricted by org policy — use a Colab Runtime Template in BigQuery Studio if needed."
      fi
    fi
  fi

  rm -f "${pf_json_file}" || true
  export CROSSLOOK_PREFLIGHT_DONE="true"
  export GCP_APIS_VERIFIED="true"
  log_ok "Pre-flight complete — all CLI, Google Cloud, and AWS prerequisites ready."
}

confirm_resource_plan() {
  local auto_approve="${1:-false}"
  local skip_export="${2:-false}"
  local skip_glue="${3:-false}"

  probe_existing_resources

  local s3_plan glue_plan gcs_stage_plan
  if [[ "${skip_export}" == "true" ]]; then
    s3_plan="[skipped via --skip-export — reusing s3://${S3_BUCKET}/raw/]"
    gcs_stage_plan="[skipped via --skip-export]"
  else
    s3_plan="[${STATE_S3}] (AES256 encrypted, public access blocked + 7 raw Parquet prefixes)"
    gcs_stage_plan="[${STATE_GCS}] (US Parquet export staging; removed by ./cleanup.sh)"
  fi

  if [[ "${skip_glue}" == "true" ]]; then
    glue_plan="[skipped via --skip-glue — reusing ${GLUE_DB}.*]"
  else
    glue_plan="[${STATE_GLUE}] (7 managed Apache Iceberg tables via Athena '${ATHENA_WORKGROUP}')"
  fi

  cat <<EOF

==============================================================================
 Cross-Look — AWS & Google Cloud Resource Creation Plan
==============================================================================
  AWS Resources (Account: ${AWS_ACCOUNT_ID}, Region: ${AWS_REGION})
    • Amazon S3 Bucket       : s3://${S3_BUCKET}
                               ${s3_plan}
    • AWS Glue Database      : ${GLUE_DB} (s3://${S3_BUCKET}/iceberg/)
                               ${glue_plan}
    • Iceberg Tables (7)     : distribution_centers, users, products, orders,
                               order_items, inventory_items, events
    • AWS OIDC IAM Role      : arn:aws:iam::${AWS_ACCOUNT_ID}:role/${AWS_ROLE_NAME} [${STATE_IAM}]
                               (Keyless Web Identity trust + inline read policy)

  Google Cloud Resources (Project: ${GCP_PROJECT}, Region: ${GCP_REGION})
    • GCS Staging Bucket     : ${GCS_STAGE_BUCKET}
                               ${gcs_stage_plan}
    • Federated Catalog      : ${GCP_PROJECT}.${FEDERATED_CATALOG} [${STATE_CAT}]
                               (Federated to AWS Glue ${AWS_ACCOUNT_ID}/${GLUE_DB},
                                300s sync, Cross-Cloud Cache enabled)
    • BigQuery Dataset       : ${GCP_PROJECT}:${BQ_DEMO_DATASET} [${STATE_BQ}]
                               (Location: ${GCP_REGION}, 0 tables stored in BigQuery)
    • BigQuery Property Graph: ${GCP_PROJECT}.${BQ_DEMO_DATASET}.ecommerce_graph
                               (5 entity nodes, 4 edges, 6 MEASURE definitions)
==============================================================================
EOF

  if [[ "${auto_approve}" == "true" ]]; then
    log_ok "Resource creation plan auto-approved (--yes)."
    return 0
  fi

  printf "Ready to create/update these AWS and Google Cloud resources? [Y/n] (press Enter, 'y', or 'go' to start): "
  local go_reply=""
  read -r go_reply
  go_reply="$(printf "%s" "${go_reply}" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
  case "${go_reply}" in
    ""|y|Y|yes|YES|go|GO|Go|start|START)
      log_ok "Confirmed — starting cross-cloud provisioning..."
      ;;
    *)
      log_info "Deployment cancelled — no AWS or Google Cloud demo resources were created."
      exit 0
      ;;
  esac
}

check_gcloud_biglake_cli() {
  local ga_help
  ga_help="$(gcloud biglake iceberg catalogs create --help 2>&1 || true)"
  if grep -q -- '--federated-catalog-type' <<< "${ga_help}"; then
    return 0
  elif gcloud beta biglake iceberg catalogs --help >/dev/null 2>&1; then
    return 0
  elif gcloud alpha biglake iceberg catalogs --help >/dev/null 2>&1; then
    return 0
  else
    log_err "Your gcloud CLI does not expose federated Iceberg catalog commands yet."
    log_info "Update Cloud SDK or install beta: gcloud components install beta --quiet (or run ./deploy.sh)."
    exit 1
  fi
}

preflight_gcp_only() {
  detect_gcp_cli_session
  if [[ -z "${GCP_PROJECT}" ]]; then
    log_err "GCP_PROJECT is not set (no active gcloud project or .env found)."
    log_info "Run './deploy.sh' first (or 'gcloud config set project YOUR_EXISTING_PROJECT_ID')."
    exit 1
  fi
  resolve_region_pair
  refresh_derived_defaults
}

preflight_checks() {
  if [[ "${CROSSLOOK_PREFLIGHT_DONE:-false}" == "true" ]]; then
    return 0
  fi
  detect_all_parameters
  if [[ -z "${GCP_PROJECT}" ]]; then
    log_err "GCP_PROJECT is not set (no active gcloud project or .env found)."
    log_info "Run './deploy.sh' to interactively select or confirm an existing GCP project."
    exit 1
  fi
  check_gcloud_biglake_cli
}

enable_required_gcp_apis() {
  if [[ "${GCP_APIS_VERIFIED:-false}" == "true" ]]; then
    return 0
  fi

  # When running a standalone step script directly outside ./deploy.sh, check APIs
  # first and ask for permission before enabling any disabled APIs.
  local enabled_services missing_apis=()
  enabled_services="$(gcloud services list --enabled --project="${GCP_PROJECT}" --format="value(config.name)" --quiet 2>/dev/null || true)"
  for svc in \
    bigquery.googleapis.com \
    biglake.googleapis.com \
    bigqueryconnection.googleapis.com \
    aiplatform.googleapis.com \
    storage.googleapis.com \
    dataform.googleapis.com \
    compute.googleapis.com \
    dataplex.googleapis.com \
    geminidataanalytics.googleapis.com \
    cloudaicompanion.googleapis.com; do
    if ! grep -qxF "${svc}" <<< "${enabled_services}"; then
      missing_apis+=("${svc}")
    fi
  done

  if (( ${#missing_apis[@]} > 0 )); then
    log_warn "Missing Google Cloud API(s) on '${GCP_PROJECT}': ${missing_apis[*]}"
    if [[ -t 0 ]]; then
      local reply=""
      read -r -p "    Enable these API(s) on '${GCP_PROJECT}' now? [Y/n]: " reply
      if [[ -n "${reply}" && ! "${reply}" =~ ^[Yy]([Ee][Ss])?$ ]]; then
        log_err "Aborted — required APIs are not enabled."
        exit 1
      fi
    fi
    gcloud services enable "${missing_apis[@]}" --project="${GCP_PROJECT}" --quiet
    sleep 10
  fi

  export GCP_APIS_VERIFIED="true"
}

# Run `gcloud [beta|alpha] biglake iceberg catalogs ...` using whichever SDK track
# exposes federated catalog flags (--federated-catalog-type / --cross-cloud-cache).
gcloud_biglake_catalogs() {
  local ga_help
  ga_help="$(gcloud biglake iceberg catalogs create --help 2>&1 || true)"
  if grep -q -- '--federated-catalog-type' <<< "${ga_help}"; then
    gcloud biglake iceberg catalogs "$@"
  elif gcloud beta biglake iceberg catalogs --help >/dev/null 2>&1; then
    gcloud beta biglake iceberg catalogs "$@"
  elif gcloud alpha biglake iceberg catalogs --help >/dev/null 2>&1; then
    gcloud alpha biglake iceberg catalogs "$@"
  else
    check_gcloud_biglake_cli
  fi
}
