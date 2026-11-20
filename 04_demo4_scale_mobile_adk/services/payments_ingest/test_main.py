"""Tests locaux du parsing pacs.008 (aucune connexion AlloyDB)."""

import os

os.environ.setdefault("ALLOYDB_INSTANCE_URI", "projects/p/locations/r/clusters/c/instances/i")
os.environ.setdefault("ALLOYDB_IAM_USER", "test@test.iam")

from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402

from main import InvalidMessage, parse_payment  # noqa: E402


def _msg(**over):
    msg = {
        "header": {"schema_version": "1", "event_id": "EVT-WITNESS-ABC",
                   "end_to_end_id": "E2EWITLIVE20261117BOULAN",
                   "execution_ts": "2026-11-17T08:12:00+00:00"},
        "settlement": {"payment_scheme": "CARD_CONTACTLESS", "tx_status": "ACSC",
                       "status_reason_code": None, "retry_attempt": 0},
        "instructed_amount": {"amount_cents": 680, "amount_eur": "6.80", "currency": "EUR"},
        "debtor": {"customer_id": "CUST00002026", "account_id": "ACC00002026",
                   "full_name": "LUCAS MARTIN", "iban": "FR76...", "agent_bic": "HEXAFRLPXXX"},
        "creditor": {"name": "BOULANGERIE ARTISANALE", "iban": "FR76...", "agent_bic": "SOGEFRPPXXX"},
        "remittance": {"unstructured_info": "CB BOULANGERIE ARTISANALE"},
    }
    for k, v in over.items():
        msg[k] = {**msg[k], **v}
    return msg


def test_debit_is_negative():
    p = parse_payment(_msg())
    assert p[0] == "E2EWITLIVE20261117BOULAN"
    assert p[8] == Decimal("6.80") and p[9] == Decimal("-6.80")


def test_inbound_is_positive():
    p = parse_payment(_msg(settlement={"payment_scheme": "SCT_INBOUND"}))
    assert p[9] == Decimal("6.80")


@pytest.mark.parametrize("over", [
    {"settlement": {"tx_status": "HACK"}},
    {"header": {"end_to_end_id": "x'; DROP TABLE live_movements;--"}},
    {"instructed_amount": {"amount_eur": "abc"}},
    {"instructed_amount": {"currency": "USD"}},
    {"header": {"execution_ts": "2026-11-17T08:12:00"}},
])
def test_rejects_invalid(over):
    with pytest.raises(InvalidMessage):
        parse_payment(_msg(**over))
