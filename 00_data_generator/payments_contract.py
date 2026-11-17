"""
Contrat de données partagé du silo Paiements (ISO 20022 pacs.008 & enrôlements IBAN).

Source de vérité unique utilisée à la fois par :
  - `generate_payments_stream.py` (archive historique 18 mois, Parquet 100 % Nested STRUCT),
  - `stream_payments_pubsub.py`   (flux temps réel Cloud Pub/Sub, même schéma STRUCT).

Garantit qu'un même client, une même contrepartie ou une même néobanque est décrit
exactement de la même façon dans l'historique et dans le temps réel :
  - IBAN externes des néobanques déterministes par (compte, BIC) avec clé MOD-97 valide,
  - catalogue unique des contreparties (nom, BIC, IBAN, schéma, libellé aligné sur le Mainframe CFONB),
  - contreparties récurrentes du client témoin Lucas Martin (mêmes BIC que le Mainframe),
  - attributs digitaux déterministes par client (canal, statut SCA, IP du terminal, libellé bénéficiaire).
"""

from __future__ import annotations

from dataclasses import dataclass

from shared_universe import BANK_BIC, NEOBANK_DESTINATIONS

PACS008_SCHEMA_VERSION = "iso20022.pacs.008.001.08"
IBAN_ENROLLMENT_SCHEMA_VERSION = "iban.enrollment.v2"

# Fenêtre de référence de l'invariant « fuite 2,42 Md€ » : fixe, l'historique s'arrête au snapshot.
LEAK_WINDOW_START_ISO = "2026-08-15"
LEAK_WINDOW_END_ISO = "2026-11-12"

NEOBANK_BICS: list[str] = [bic for bic, _ in NEOBANK_DESTINATIONS]
NEOBANK_LABELS: dict[str, str] = dict(NEOBANK_DESTINATIONS)

NEOBANK_DISPLAY_NAMES: dict[str, str] = {
    "REVOLT21XXX": "Revolut",
    "TRBKDEBBXXX": "Trade Republic",
    "NTSBDEB1XXX": "N26",
    "BOURFRPPXXX": "Boursobank",
    "DEGIRO2AXXX": "DEGIRO",
}

INBOUND_SCHEMES = {"SCT_INBOUND", "SCT_INST_INBOUND"}


# ==============================================================================
# IBAN ISO 13616 (clé MOD-97 réelle)
# ==============================================================================
def _alnum_to_digits(text: str) -> str:
    return "".join(str(int(ch, 36)) for ch in text)


def iban_from_bban(country: str, bban: str) -> str:
    """Construit un IBAN valide (clé de contrôle MOD-97) à partir du pays et du BBAN."""
    numeric = _alnum_to_digits(bban + country + "00")
    check = 98 - (int(numeric) % 97)
    return f"{country}{check:02d}{bban}"


def french_iban(bank: str, guichet: str, compte_11: str) -> str:
    """IBAN FR avec vraie clé RIB (identique à la méthode de `shared_universe.py`)."""
    rem = (89 * int(bank) + 15 * int(guichet) + 3 * (int(compte_11) % 97)) % 97
    cle = f"{97 - rem:02d}"
    return iban_from_bban("FR", f"{bank}{guichet}{compte_11}{cle}")


def neobank_beneficiary_iban(acc_idx: int, bic: str) -> str:
    """IBAN externe déterministe du compte néobanque ouvert par le client (même valeur partout)."""
    if bic == "REVOLT21XXX":
        return iban_from_bban("LT", f"32500{acc_idx:011d}")
    if bic == "TRBKDEBBXXX":
        return iban_from_bban("DE", f"10012345{acc_idx:010d}")
    if bic == "NTSBDEB1XXX":
        return iban_from_bban("DE", f"10011001{acc_idx:010d}")
    if bic == "BOURFRPPXXX":
        return french_iban("40618", "80280", f"{acc_idx:011d}")
    if bic == "DEGIRO2AXXX":
        return iban_from_bban("NL", f"FTSB{acc_idx:010d}")
    raise ValueError(f"BIC néobanque inconnu : {bic}")


# ==============================================================================
# Catalogue unique des contreparties (libellés alignés sur le Mainframe CFONB 120)
# ==============================================================================
@dataclass(frozen=True)
class Counterparty:
    key: str
    name: str
    bic: str
    iban: str
    scheme: str
    label: str
    min_cents: int
    max_cents: int
    weight: float

    @property
    def is_inbound(self) -> bool:
        return self.scheme in INBOUND_SCHEMES


def _cp(key, name, bic, bank, guichet, compte, scheme, label, lo, hi, w) -> Counterparty:
    return Counterparty(key, name, bic, french_iban(bank, guichet, compte), scheme, label, lo, hi, w)


COUNTERPARTIES: list[Counterparty] = [
    # Crédits entrants (sens donné par settlement.payment_scheme = *_INBOUND)
    _cp("SALAIRE", "EMPLOYEUR SEPA", "EMPLOYEURFR", "30004", "00828", "00010012345", "SCT_INBOUND", "VIR SEPA SALAIRE ENTREPRISE", 145_000, 680_000, 0.14),
    _cp("RETRAITE", "CAISSE NATIONALE RETRAITE", "CNAVFRPPXXX", "30001", "00064", "00000750099", "SCT_INBOUND", "VIR CAISSE RETRAITE", 95_000, 420_000, 0.02),
    _cp("CPAM", "CPAM ILE DE FRANCE", "CPAMIDF7500", "30001", "00064", "00000750001", "SCT_INBOUND", "VIR CPAM REMBOURSEMENT SANTE", 1_800, 42_000, 0.03),
    _cp("MUTUELLE", "MUTUELLE GENERALE", "CCBPFRPPXXX", "10207", "00026", "04012345678", "SCT_INBOUND", "VIR MUTUELLE COMPLEMENTAIRE", 1_800, 35_000, 0.02),
    # Prélèvements SEPA
    _cp("EDF", "EDF ENERGIE", "EDFPROXIMIT", "30003", "03620", "00020135711", "SEPA_SDD", "PRLV SEPA EDF ENERGIE", 4_500, 18_000, 0.06),
    _cp("LOYER", "BAILLEUR HABITAT", "MANDATLOYER", "30066", "10021", "00010444555", "SEPA_SDD", "PRLV SEPA LOYER HABITAT", 48_000, 135_000, 0.06),
    _cp("ORANGE", "ORANGE FIBRE", "BNPAFRPPXXX", "30004", "01000", "00040777888", "SEPA_SDD", "PRLV SEPA ORANGE FIBRE", 2_999, 5_999, 0.05),
    _cp("DGFIP", "DGFIP IMPOTS", "BDFEFRPPCCT", "30001", "00001", "00000000901", "SEPA_SDD", "PRLV SEPA IMPOTS DGFIP", 8_000, 95_000, 0.03),
    _cp("ASSURANCE", "ASSURANCE AUTO HEXA", "AXABFRPPXXX", "12548", "02998", "00055566677", "SEPA_SDD", "PRLV SEPA ASSURANCE AUTO", 3_500, 14_000, 0.04),
    _cp("STRMFLIX", "STRMFLIX DIGITAL", "STRMFLIXEUR", "30004", "00828", "00099900199", "SEPA_SDD", "PRLV SEPA STRMFLIX ABO", 1_599, 1_999, 0.04),
    # Paiements carte (acquéreurs)
    _cp("CARREFOUR", "CARREFOUR HYPER", "BNPAFRPPXXX", "30004", "02550", "00011122233", "CARD_CONTACTLESS", "CB CARREFOUR HYPER", 850, 18_500, 0.08),
    _cp("LECLERC", "LECLERC DISTRIBUTION", "CMCIFRPPXXX", "10278", "06041", "00020304050", "CARD_CONTACTLESS", "CB LECLERC DISTRIBUTION", 900, 21_000, 0.07),
    _cp("SNCF", "SNCF VOYAGES", "CMCIFRPPXXX", "10278", "06041", "00098765432", "CARD_ECOMMERCE", "CB SNCF VOYAGES", 2_500, 28_500, 0.05),
    _cp("PHARMACIE", "PHARMACIE CENTRALE", "CEPAFRPPXXX", "11315", "00001", "08001234567", "CARD_CONTACTLESS", "CB PHARMACIE CENTRALE", 600, 9_500, 0.05),
    _cp("BOULANGERIE", "BOULANGERIE ARTISANALE", "SOGEFRPPXXX", "30003", "00450", "00050123456", "CARD_CONTACTLESS", "CB BOULANGERIE ARTISANALE", 450, 2_500, 0.06),
    _cp("TOTAL", "TOTALENERGIES STATION", "SOGEFRPPXXX", "30003", "00450", "00050987654", "CARD_CONTACTLESS", "CB TOTALENERGIES STATION", 2_000, 9_500, 0.04),
    _cp("AMAZON", "AMAZON EU SARL", "BNPAFRPPXXX", "30004", "00828", "00080088008", "CARD_ECOMMERCE", "CB AMAZON EU SARL", 900, 25_000, 0.06),
    _cp("RESTAURANT", "RESTAURANT BRASSERIE", "AGRIFRPPXXX", "30006", "00001", "00070707070", "CARD_CONTACTLESS", "CB RESTAURANT BRASSERIE", 1_200, 9_800, 0.05),
]

OUTBOUND_COUNTERPARTIES: list[Counterparty] = [c for c in COUNTERPARTIES if not c.is_inbound]


def _normalized(weights: list[float]) -> list[float]:
    total = sum(weights)
    return [w / total for w in weights]


COUNTERPARTY_WEIGHTS: list[float] = _normalized([c.weight for c in COUNTERPARTIES])
OUTBOUND_WEIGHTS: list[float] = _normalized([c.weight for c in OUTBOUND_COUNTERPARTIES])

# Contreparties récurrentes du client témoin (BIC strictement identiques au Mainframe CFONB)
WITNESS_COUNTERPARTIES: dict[str, Counterparty] = {
    "VIR SALAIRE TECHCORP SAS": _cp("W_SALAIRE", "TECHCORP SAS", "EMPLOYEURFR", "30004", "00828", "00010099887", "SCT_INBOUND", "VIR SALAIRE TECHCORP SAS", 185_000, 185_000, 0),
    "PRLV LOYER FONCIERE PARIS": _cp("W_LOYER", "FONCIERE PARIS", "MANDATLOYER", "30066", "10021", "00010777666", "SEPA_SDD", "PRLV LOYER FONCIERE PARIS", 72_000, 72_000, 0),
    "PRLV SEPA STRMFLIX ABO": next(c for c in COUNTERPARTIES if c.key == "STRMFLIX"),
    "PRLV EDF ENERGIE": _cp("W_EDF", "EDF ENERGIE", "EDFPROXIMIT", "30003", "03620", "00020135711", "SEPA_SDD", "PRLV EDF ENERGIE", 6_401, 6_401, 0),
    "VIR CPAM REMBOURSEMENT SANTE": next(c for c in COUNTERPARTIES if c.key == "CPAM"),
    "CB CARREFOUR CITY PARIS": _cp("W_CARREFOUR", "CARREFOUR CITY PARIS", "BNPAFRPPXXX", "30004", "02550", "00011122299", "CARD_CONTACTLESS", "CB CARREFOUR CITY PARIS", 15_000, 15_000, 0),
    "CB MONOPRIX OPERA PARIS": _cp("W_MONOPRIX", "MONOPRIX OPERA PARIS", "SOGEFRPPXXX", "30003", "00450", "00050333444", "CARD_CONTACTLESS", "CB MONOPRIX OPERA PARIS", 22_000, 22_000, 0),
    "CB FNAC SAINT LAZARE": _cp("W_FNAC", "FNAC SAINT LAZARE", "CMCIFRPPXXX", "10278", "06041", "00020555666", "CARD_CONTACTLESS", "CB FNAC SAINT LAZARE", 19_000, 19_000, 0),
    "CB SNCF VOYAGES": next(c for c in COUNTERPARTIES if c.key == "SNCF"),
    "CB BOULANGERIE ARTISANALE": next(c for c in COUNTERPARTIES if c.key == "BOULANGERIE"),
    "CB PHARMACIE CENTRALE": next(c for c in COUNTERPARTIES if c.key == "PHARMACIE"),
}

REJECT_REASONS: list[tuple[str, str]] = [
    ("RJCT", "AM04"),
    ("RJCT", "AM02"),
    ("RJCT", "AC04"),
    ("PDNG", "AB05"),
]


def settlement_method_for(scheme: str) -> str:
    return "CLRG_RT1_INST" if scheme.startswith("SCT_INST") else "CLRG_STEP2"


# ==============================================================================
# Attributs digitaux déterministes par client (historique & temps réel identiques)
# ==============================================================================
DIGITAL_CHANNELS = ["MOBILE_APP_ANDROID", "MOBILE_APP_IOS", "WEB_HOMEBANKING"]


def customer_channel(cust_idx: int) -> str:
    return DIGITAL_CHANNELS[cust_idx % len(DIGITAL_CHANNELS)]


def customer_sca_status(cust_idx: int) -> str:
    return "VERIFIED_PASSKEY" if customer_channel(cust_idx) == "WEB_HOMEBANKING" else "VERIFIED_BIOMETRIC"


def customer_device_ip(cust_idx: int) -> str:
    return f"90.{(cust_idx * 7) % 110 + 10}.{(cust_idx * 13) % 249 + 1}.{(cust_idx * 31) % 252 + 2}"


def beneficiary_custom_label(first_name: str, bic: str) -> str:
    return f"Compte {NEOBANK_DISPLAY_NAMES.get(bic, bic[:6])} {first_name.title()}"


def full_name(first_name: str, last_name: str) -> str:
    return f"{first_name} {last_name}"


__all__ = [
    "BANK_BIC",
    "COUNTERPARTIES",
    "COUNTERPARTY_WEIGHTS",
    "IBAN_ENROLLMENT_SCHEMA_VERSION",
    "LEAK_WINDOW_END_ISO",
    "LEAK_WINDOW_START_ISO",
    "NEOBANK_BICS",
    "NEOBANK_LABELS",
    "OUTBOUND_COUNTERPARTIES",
    "OUTBOUND_WEIGHTS",
    "PACS008_SCHEMA_VERSION",
    "REJECT_REASONS",
    "WITNESS_COUNTERPARTIES",
    "beneficiary_custom_label",
    "customer_channel",
    "customer_device_ip",
    "customer_sca_status",
    "full_name",
    "iban_from_bban",
    "neobank_beneficiary_iban",
    "settlement_method_for",
]
