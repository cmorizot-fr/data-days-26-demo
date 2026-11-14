"""
Générateur déterministe (seed=2026) du silo documentaire PDF de Banque Hexagone :

1. `00_data_generator/output/RAW/PROMO_CONTRACTS_PDF/` (250 fichiers PDF) :
   - Contrats et avenants promotionnels signés en agence / direction régionale (`PROMO-2026-001` à `250`),
     alignés à 100 % sur les codes agences et `promo_contract_id` du silo AWS CRM (`generate_aws_crm_s3.py`).
   - Alternance de 3 gabarits visuels et métier réalistes :
       * Gabarit A (95 PDF) : Décision Régionale de Taux Boosté « Livret Maison » (PCEC 602910)
       * Gabarit B (90 PDF) : Protocole Campagne « Conquête Jeunes Actifs 18-32 ans » (PCEC 602920)
       * Gabarit C (65 PDF) : Bordereau Dérogatoire Gratuité Tarifaire & Rétention (PCEC 708590, piège multi-montants)
   - Invariant financier strict (`AGENTS.md`) :
       SUM(committed_promo_cost_eur) == 14 300 000,00 € exactement (1 430 000 000 centimes),
       soit un impact certifié de -14,30 M€ sur le PNB trimestriel consolidé du CFO.

2. `00_data_generator/output/RAW/REGULATORY_CFO_PDF/` (6 fichiers PDF) :
   - Corpus normatif, comptable et prudentiel pour les questions exécutives du CFO (Démo #3 & Démo #4) :
       * REG_01_ANC_2014_07_DOCTRINE_PNB_PCEC.pdf
       * REG_02_CHARTE_ALM_TCI_REFINANCEMENT_BCE.pdf
       * REG_03_ILAAP_SEUILS_LCR_NSFR_ACPR_2026.pdf
       * REG_04_PV_COMITE_RISQUES_PLAFONDS_Q4_2026.pdf
       * REG_05_UE_2024_886_SEPA_INSTANT_RISQUE_LIQUIDITE.pdf
       * REG_06_ACPR_2024_R01_ENCADREMENT_OFFRES_EPARGNE.pdf

3. Vérité terrain de contrôle interne (hors `RAW/`, jamais exposée à BigQuery) :
   - `00_data_generator/data/universe/promo_pdfs_ground_truth.parquet`
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import time
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from shared_universe import (
    DEMO_SEED,
    FIRST_NAMES,
    LAST_NAMES,
    QUARTER_START_DATE,
    REGIONS_DEF,
    SNAPSHOT_DATE,
    UNIVERSE_CACHE_DIR,
    build_or_load_universe,
    distribute_exact_cents,
)

PAGE_W, PAGE_H = A4

NUM_PROMO_PDFS: int = 250
TARGET_PROMO_COST_CENTS: int = 1_430_000_000  # Exactement 14 300 000,00 € (-14,30 M€ impact PNB)

BASE_DIR: Path = Path(__file__).resolve().parent
DEFAULT_OUTPUT_RAW_DIR: Path = BASE_DIR / "output" / "RAW"


# ==============================================================================
# Utilitaires de formatage monétaire & dessin vectoriel ReportLab
# ==============================================================================
def fmt_eur_space(cents: int, suffix: str = "EUR") -> str:
    """Ex: 8200000 -> '82 000,00 EUR'."""
    sign = "-" if cents < 0 else ""
    abs_c = abs(int(cents))
    euros = abs_c // 100
    rem = abs_c % 100
    euro_str = f"{euros:,}".replace(",", " ")
    return f"{sign}{euro_str},{rem:02d} {suffix}"


def fmt_eur_dot(cents: int, suffix: str = "EUR") -> str:
    """Ex: 5016000 -> '50.160,00 EUR' (variante typographique réaliste)."""
    sign = "-" if cents < 0 else ""
    abs_c = abs(int(cents))
    euros = abs_c // 100
    rem = abs_c % 100
    euro_str = f"{euros:,}".replace(",", ".")
    return f"{sign}{euro_str},{rem:02d} {suffix}"


def draw_hexagon_logo(
    c: canvas.Canvas, cx: float, cy: float, r: float, stroke_col, fill_col=None
) -> None:
    """Dessine l'emblème géométrique de Banque Hexagone."""
    c.saveState()
    p = c.beginPath()
    for i in range(6):
        angle = math.radians(60 * i + 30)
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        if i == 0:
            p.moveTo(x, y)
        else:
            p.lineTo(x, y)
    p.close()
    c.setLineWidth(1.6)
    c.setStrokeColor(stroke_col)
    if fill_col is not None:
        c.setFillColor(fill_col)
        c.drawPath(p, stroke=1, fill=1)
    else:
        c.drawPath(p, stroke=1, fill=0)

    p2 = c.beginPath()
    r2 = r * 0.52
    for i in range(6):
        angle = math.radians(60 * i + 30)
        x = cx + r2 * math.cos(angle)
        y = cy + r2 * math.sin(angle)
        if i == 0:
            p2.moveTo(x, y)
        else:
            p2.lineTo(x, y)
    p2.close()
    c.setLineWidth(0.9)
    c.drawPath(p2, stroke=1, fill=0)
    c.restoreState()


def draw_watermark(c: canvas.Canvas, text: str) -> None:
    c.saveState()
    c.translate(PAGE_W / 2, PAGE_H / 2)
    c.rotate(34)
    c.setFillColor(colors.Color(0.86, 0.88, 0.91, alpha=0.25))
    c.setFont("Helvetica-Bold", 28)
    c.drawCentredString(0, 0, text)
    c.restoreState()


def draw_footer(
    c: canvas.Canvas, doc_ref: str, left_x_mm: float = 18.0, page_str: str = "Page 1 / 1"
) -> None:
    c.saveState()
    lx = left_x_mm * mm
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.6)
    c.line(lx, 16 * mm, PAGE_W - 18 * mm, 16 * mm)
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 7.0)
    c.drawString(
        lx,
        11.8 * mm,
        "BANQUE HEXAGONE SA — Capital social 1 450 000 000 EUR — Siège : 24 Bd Haussmann, 75009 Paris — RCS Paris 542 089 302",
    )
    c.drawString(
        lx,
        8.4 * mm,
        f"Établissement de crédit agréé ACPR (Code Banque CIB 30002 · BIC HEXAFRLPXXX) — Réf. archive GED : {doc_ref}",
    )
    c.setFont("Helvetica-Bold", 7.4)
    c.drawRightString(PAGE_W - 18 * mm, 10.0 * mm, page_str)
    c.restoreState()


def draw_stamp(
    c: canvas.Canvas,
    x: float,
    y: float,
    line1: str,
    line2: str,
    line3: str,
    hex_color: str = "#991B1B",
    angle: float = -6.0,
    half_w_mm: float = 28.0,
) -> None:
    c.saveState()
    c.translate(x, y)
    c.rotate(angle)
    col = colors.HexColor(hex_color)
    hw = half_w_mm * mm
    c.setStrokeColor(col)
    c.setLineWidth(1.4)
    c.roundRect(-hw, -9.5 * mm, 2 * hw, 19 * mm, 2 * mm, stroke=1, fill=0)
    c.setLineWidth(0.5)
    c.roundRect(
        -hw + 1.3 * mm, -8.2 * mm, 2 * hw - 2.6 * mm, 16.4 * mm, 1.4 * mm, stroke=1, fill=0
    )
    c.setFillColor(col)
    c.setFont("Helvetica-Bold", 7.4)
    c.drawCentredString(0, 3.8 * mm, line1)
    c.setFont("Helvetica-Bold", 6.6)
    c.drawCentredString(0, -0.4 * mm, line2)
    c.setFont("Helvetica", 6.1)
    c.drawCentredString(0, -4.5 * mm, line3)
    c.restoreState()


def draw_signature_curve(c: canvas.Canvas, x: float, y: float, seed_variant: int = 1) -> None:
    c.saveState()
    c.setStrokeColor(colors.HexColor("#1E3A8A"))
    c.setLineWidth(1.1)
    p = c.beginPath()
    v = seed_variant % 3
    if v == 0:
        p.moveTo(x, y + 2)
        p.curveTo(x + 14, y + 20, x + 26, y - 4, x + 42, y + 14)
        p.curveTo(x + 54, y + 22, x + 62, y + 3, x + 76, y + 9)
    elif v == 1:
        p.moveTo(x, y)
        p.curveTo(x + 12, y + 18, x + 22, y - 6, x + 36, y + 12)
        p.curveTo(x + 48, y + 24, x + 55, y + 2, x + 74, y + 8)
        p.lineTo(x + 18, y + 3)
    else:
        p.moveTo(x + 4, y + 4)
        p.curveTo(x + 18, y + 22, x + 28, y + 20, x + 34, y + 2)
        p.curveTo(x + 44, y - 4, x + 60, y + 16, x + 78, y + 6)
    c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def wrap_paragraph(
    c: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    font_name: str = "Helvetica",
    font_size: float = 9.0,
    leading: float = 13.0,
    color=colors.HexColor("#1E293B"),
) -> float:
    c.setFont(font_name, font_size)
    c.setFillColor(color)
    words = text.split()
    line = ""
    cur_y = y
    for w in words:
        test = f"{line} {w}".strip()
        if c.stringWidth(test, font_name, font_size) <= max_width:
            line = test
        else:
            c.drawString(x, cur_y, line)
            cur_y -= leading
            line = w
    if line:
        c.drawString(x, cur_y, line)
        cur_y -= leading
    return cur_y


def draw_wrapped_cell(
    c: canvas.Canvas,
    text: str,
    x: float,
    top_y: float,
    max_width: float,
    font_name: str = "Helvetica",
    font_size: float = 7.3,
    leading: float = 9.4,
    color=colors.HexColor("#1E293B"),
) -> None:
    c.setFont(font_name, font_size)
    c.setFillColor(color)
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        if c.stringWidth(test, font_name, font_size) <= max_width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    start_y = top_y - 4.3 * mm if len(lines) > 1 else top_y - 6.5 * mm
    for idx, ln in enumerate(lines[:2]):
        c.drawString(x, start_y - idx * leading, ln)


# ==============================================================================
# Rendu des 3 gabarits d'avenants commerciaux réseau (250 PDF -> 14 300 000,00 €)
# ==============================================================================
def render_promo_template_a(rec: dict, out_path: Path) -> None:
    """Gabarit A : Décision Régionale de Taux Boosté « Livret Maison » (PCEC 602910)."""
    c = canvas.Canvas(str(out_path), pagesize=A4)
    cid = rec["promo_contract_id"]
    c.setTitle(f"{cid} — Décision Régionale Taux Boosté Livret Maison ({rec['region_code']})")
    draw_watermark(c, "CONFIDENTIEL — DIRECTION RÉSEAU")

    navy = colors.HexColor("#0F2747")
    gold = colors.HexColor("#C89B3C")
    c.setFillColor(navy)
    c.rect(0, PAGE_H - 34 * mm, PAGE_W, 34 * mm, stroke=0, fill=1)
    c.setFillColor(gold)
    c.rect(0, PAGE_H - 35.4 * mm, PAGE_W, 1.4 * mm, stroke=0, fill=1)

    draw_hexagon_logo(c, 25 * mm, PAGE_H - 17 * mm, 7.2 * mm, gold)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 13.5)
    c.drawString(36 * mm, PAGE_H - 14.5 * mm, "BANQUE HEXAGONE")
    c.setFont("Helvetica", 7.7)
    c.setFillColor(colors.HexColor("#CBD5E1"))
    c.drawString(
        36 * mm,
        PAGE_H - 20.0 * mm,
        f"DIRECTION RÉGIONALE {rec['region_name'].upper()} ({rec['region_code']}) · COMITÉ COLLECTE",
    )
    c.drawString(36 * mm, PAGE_H - 24.6 * mm, "Code Banque 30002 · BIC HEXAFRLPXXX · Délégation Niveau II")

    c.setFillColor(colors.HexColor("#18365E"))
    c.roundRect(PAGE_W - 72 * mm, PAGE_H - 28 * mm, 54 * mm, 20 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(gold)
    c.setFont("Helvetica-Bold", 8.0)
    c.drawString(PAGE_W - 69 * mm, PAGE_H - 13.5 * mm, f"CONTRAT N° {cid}")
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 7.6)
    c.drawString(PAGE_W - 69 * mm, PAGE_H - 18.8 * mm, f"Date d'effet : {rec['effective_date_fr']}")
    c.drawString(
        PAGE_W - 69 * mm,
        PAGE_H - 23.8 * mm,
        f"Échéance : {rec['end_date_fr']} ({rec['duration_months']} mois)",
    )

    y = PAGE_H - 46 * mm
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 11.8)
    c.drawString(18 * mm, y, "AVENANT DÉROGATOIRE DE BONIFICATION — PRODUIT « LIVRET MAISON »")
    y -= 5.2 * mm
    c.setFont("Helvetica", 8.7)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(
        18 * mm,
        y,
        "Objet : Rétention des dépôts à vue face aux transferts SEPA Instant sortants vers courtiers et néobanques",
    )

    y -= 25 * mm
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.7)
    c.roundRect(18 * mm, y, PAGE_W - 36 * mm, 20.5 * mm, 2 * mm, stroke=1, fill=1)
    c.line(106 * mm, y + 2.5 * mm, 106 * mm, y + 18 * mm)

    meta_left = [
        ("Région :", f"{rec['region_code']} — {rec['region_name']} ({rec['primary_city']})"),
        ("Agences :", f"Groupe {rec['primary_city'].title()} ({rec['branch_codes_label']})"),
        ("Segments :", "JEUNE_ACTIF (18-32 ans) & AFFLUENT"),
    ]
    meta_right = [
        ("Produit :", "LIV_MAISON (Livret bancaire fiscalisé)"),
        ("Compte PCEC :", "602910 — Bonifications sur collecte"),
        ("Statut SAP :", "HORS-BILAN (Non saisi au 12/11/2026)"),
    ]
    ry = y + 14.5 * mm
    for k_lbl, v_lbl in meta_left:
        c.setFont("Helvetica-Bold", 7.7)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(21.5 * mm, ry, k_lbl)
        c.setFont("Helvetica", 7.6)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.drawString(41.5 * mm, ry, v_lbl[:38])
        ry -= 5.3 * mm

    ry = y + 14.5 * mm
    for k_lbl, v_lbl in meta_right:
        c.setFont("Helvetica-Bold", 7.7)
        c.setFillColor(colors.HexColor("#334155"))
        c.drawString(109.5 * mm, ry, k_lbl)
        c.setFont("Helvetica-Bold" if "HORS-BILAN" in v_lbl else "Helvetica", 7.6)
        c.setFillColor(
            colors.HexColor("#B91C1C") if "HORS-BILAN" in v_lbl else colors.HexColor("#0F172A")
        )
        c.drawString(132 * mm, ry, v_lbl)
        ry -= 5.3 * mm

    y -= 9 * mm
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 9.8)
    c.drawString(18 * mm, y, "1. EXPOSÉ DES MOTIFS & CONSTAT COMMERCIAL")
    y -= 5.2 * mm
    y = wrap_paragraph(
        c,
        f"Sur le périmètre des agences {rec['branch_codes_label']} ({rec['primary_city']}), le suivi commercial met "
        f"en évidence une fuite récurrente des soldes créditeurs sur comptes chèques (CC_CHQ) entre le 1er et le "
        f"5 du mois, aussitôt après le virement des salaires. Les transferts SEPA Instant sortants vers les BIC "
        f"REVOLT21XXX, TRBKDEBBXXX et BOURFRPPXXX pèsent sur la ressource à vue sans clôture de dossier ({rec['quarter_openings']} "
        f"ouvertures enregistrées sur le trimestre).",
        18 * mm,
        y,
        PAGE_W - 36 * mm,
    )
    y -= 2 * mm
    gross_rate_pct = (150 + rec["boost_rate_bps"]) / 100.0
    boost_pct = rec["boost_rate_bps"] / 100.0
    y = wrap_paragraph(
        c,
        f"Pour stabiliser la collecte avant l'arrêté trimestriel, la Direction Régionale {rec['region_code']} accorde "
        f"une bonification temporaire de +{rec['boost_rate_bps']} points de base (+{boost_pct:.2f} % annuel brut) "
        f"au-dessus du taux facial du Livret Maison (1,50 %), portant le taux servi à {gross_rate_pct:.2f} % brut "
        f"pendant {rec['duration_months']} mois sur les versements nets plafonnés à 50 000 EUR par client.",
        18 * mm,
        y,
        PAGE_W - 36 * mm,
    )

    y -= 6 * mm
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 9.8)
    c.drawString(18 * mm, y, "2. CHIFFRAGE ACTUARIEL DE L'ENGAGEMENT FERME (IMPACT PNB T4 2026)")
    y -= 5 * mm

    table_top = y
    row_h = 8.2 * mm
    cols = [18 * mm, 98 * mm, 129 * mm, 158 * mm, PAGE_W - 18 * mm]

    c.setFillColor(navy)
    c.rect(cols[0], table_top - row_h, cols[-1] - cols[0], row_h, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.0)
    c.drawString(cols[0] + 3 * mm, table_top - 5.5 * mm, "Poste d'engagement commercial")
    c.drawString(cols[1] + 2 * mm, table_top - 5.5 * mm, "Assiette / Volume")
    c.drawString(cols[2] + 2 * mm, table_top - 5.5 * mm, "Barème dérogatoire")
    c.drawRightString(cols[4] - 3 * mm, table_top - 5.5 * mm, "Charge nette EUR")

    cur = table_top - row_h
    for idx, (lbl, vol, rate_s, amt_c) in enumerate(rec["line_items"]):
        bg = colors.HexColor("#FFFFFF") if idx % 2 == 0 else colors.HexColor("#F8FAFC")
        c.setFillColor(bg)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.rect(cols[0], cur - row_h, cols[-1] - cols[0], row_h, stroke=1, fill=1)
        c.setFillColor(colors.HexColor("#1E293B"))
        c.setFont("Helvetica", 8.0)
        c.drawString(cols[0] + 3 * mm, cur - 5.4 * mm, lbl)
        c.drawString(cols[1] + 2 * mm, cur - 5.4 * mm, vol)
        c.drawString(cols[2] + 2 * mm, cur - 5.4 * mm, rate_s)
        c.setFont("Helvetica-Bold", 8.1)
        c.drawRightString(cols[4] - 3 * mm, cur - 5.4 * mm, fmt_eur_space(amt_c))
        cur -= row_h

    c.setFillColor(colors.HexColor("#FEF3C7"))
    c.setStrokeColor(gold)
    c.setLineWidth(1.0)
    c.rect(cols[0], cur - 9.5 * mm, cols[-1] - cols[0], 9.5 * mm, stroke=1, fill=1)
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 8.6)
    c.drawString(
        cols[0] + 3 * mm,
        cur - 6.2 * mm,
        "COÛT COMMERCIAL NET ENGAGÉ IMPUTABLE PNB (committed_promo_cost_eur)",
    )
    c.setFont("Helvetica-Bold", 9.8)
    c.drawRightString(cols[4] - 3 * mm, cur - 6.2 * mm, fmt_eur_space(rec["committed_cents"]))
    cur -= 15 * mm

    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 9.8)
    c.drawString(18 * mm, cur, "3. CLAUSE DE RATTACHEMENT COMPTABLE & CONTRÔLE INTERNE")
    cur -= 5.2 * mm
    wrap_paragraph(
        c,
        f"Conformément à la doctrine comptable PCEC (Règlement ANC n°2014-07), le présent engagement contractuel "
        f"(réf. {cid}) constitue une minoration ferme de marge nette d'intérêt sur l'exercice T4 2026 pour un "
        f"montant exact de {fmt_eur_space(rec['committed_cents'])}. L'écriture SAP n'étant passée qu'à l'échéance "
        f"promotionnelle, ce document fait foi pour le retraitement du Produit Net Bancaire consolidé du CFO.",
        18 * mm,
        cur,
        PAGE_W - 36 * mm,
    )

    sig_y = 32 * mm
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setLineWidth(0.6)
    c.roundRect(18 * mm, sig_y, 55 * mm, 27 * mm, 2 * mm, stroke=1, fill=0)
    c.roundRect(PAGE_W - 73 * mm, sig_y, 55 * mm, 27 * mm, 2 * mm, stroke=1, fill=0)

    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica-Bold", 7.4)
    c.drawString(20.5 * mm, sig_y + 21.8 * mm, f"Direction Régionale {rec['region_code']}")
    c.setFont("Helvetica", 7.0)
    c.drawString(20.5 * mm, sig_y + 17.3 * mm, f"{rec['signer_name']} — Directeur")
    draw_signature_curve(c, 22 * mm, sig_y + 5.5 * mm, seed_variant=rec["idx"])

    c.setFont("Helvetica-Bold", 7.4)
    c.drawString(PAGE_W - 70.5 * mm, sig_y + 21.8 * mm, "Contrôle Financier Réseau")
    c.setFont("Helvetica", 7.0)
    c.drawString(PAGE_W - 70.5 * mm, sig_y + 17.3 * mm, f"{rec['controller_name']} — Visa ALM")
    draw_signature_curve(c, PAGE_W - 69 * mm, sig_y + 5.5 * mm, seed_variant=rec["idx"] + 1)

    draw_stamp(
        c,
        PAGE_W / 2,
        sig_y + 13.5 * mm,
        "BON POUR ENGAGEMENT FERME",
        f"DÉLÉGATION {rec['region_code']} — {rec['effective_date_fr']}",
        f"Certifié : {fmt_eur_space(rec['committed_cents'])}",
        hex_color="#991B1B",
        angle=-5.5,
        half_w_mm=26.5,
    )

    draw_footer(c, cid)
    c.showPage()
    c.save()


def render_promo_template_b(rec: dict, out_path: Path) -> None:
    """Gabarit B : Protocole Campagne « Prime Bienvenue & Jeunes Actifs 18-32 ans » (PCEC 602920)."""
    c = canvas.Canvas(str(out_path), pagesize=A4)
    cid = rec["promo_contract_id"]
    c.setTitle(f"{cid} — Protocole Campagne Conquête Jeunes Actifs ({rec['region_code']})")
    draw_watermark(c, "CAMPAGNE RÉSEAU T4 2026")

    teal = colors.HexColor("#133A36")
    mint_bg = colors.HexColor("#F0FDFA")
    accent = colors.HexColor("#0F766E")

    c.setFillColor(teal)
    c.rect(18 * mm, PAGE_H - 31 * mm, 3.2 * mm, 19 * mm, stroke=0, fill=1)
    draw_hexagon_logo(c, 29 * mm, PAGE_H - 21.5 * mm, 6.2 * mm, teal)
    c.setFillColor(teal)
    c.setFont("Helvetica-Bold", 11.8)
    c.drawString(38.5 * mm, PAGE_H - 18.2 * mm, "BANQUE HEXAGONE · ANIMATION RÉSEAU")
    c.setFont("Helvetica", 7.9)
    c.setFillColor(colors.HexColor("#475569"))
    c.drawString(
        38.5 * mm,
        PAGE_H - 23.4 * mm,
        f"Direction Régionale {rec['region_name']} ({rec['region_code']}) · Conquête Particuliers",
    )
    c.drawString(
        38.5 * mm,
        PAGE_H - 28.0 * mm,
        "Protocole local d'attribution de primes d'ouverture et de mobilité bancaire",
    )

    bx = PAGE_W - 50 * mm
    by = PAGE_H - 23.5 * mm
    c.setFillColor(colors.black)
    widths = [1.0, 0.5, 1.5, 0.5, 0.5, 1.3, 0.5, 0.9, 0.6, 1.4, 0.5, 0.8, 1.2, 0.5, 1.0, 0.5, 1.4]
    cur_x = bx
    for idx, w in enumerate(widths):
        if idx % 2 == 0:
            c.rect(cur_x, by, w * mm, 8.5 * mm, stroke=0, fill=1)
        cur_x += (w + 0.45) * mm
    c.setFont("Courier-Bold", 7.2)
    c.drawRightString(PAGE_W - 18 * mm, by - 3.4 * mm, f"GED-{cid}")

    y = PAGE_H - 43 * mm
    c.setFillColor(teal)
    c.roundRect(18 * mm, y - 9 * mm, PAGE_W - 36 * mm, 10.5 * mm, 1.8 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9.3)
    c.drawString(
        22 * mm,
        y - 5.2 * mm,
        f"PROTOCOLE CAMPAGNE « CONQUÊTE JEUNES ACTIFS 18-32 ANS » — RÉF. {cid}",
    )

    y -= 33 * mm
    c.setFillColor(mint_bg)
    c.setStrokeColor(colors.HexColor("#99F6E4"))
    c.roundRect(18 * mm, y, 84 * mm, 20.5 * mm, 2 * mm, stroke=1, fill=1)
    c.roundRect(PAGE_W - 102 * mm, y, 84 * mm, 20.5 * mm, 2 * mm, stroke=1, fill=1)

    c.setFillColor(teal)
    c.setFont("Helvetica-Bold", 8.0)
    c.drawString(22 * mm, y + 15.0 * mm, "PÉRIMÈTRE RÉSEAU COUVERT")
    c.setFont("Helvetica", 7.8)
    c.setFillColor(colors.HexColor("#1E293B"))
    c.drawString(22 * mm, y + 10.0 * mm, f"Région : {rec['region_code']} ({rec['region_name']})")
    c.drawString(22 * mm, y + 5.2 * mm, f"Agences ({rec['primary_city'].title()}) : {rec['branch_codes_label']}")

    c.setFillColor(teal)
    c.setFont("Helvetica-Bold", 8.0)
    c.drawString(PAGE_W - 98 * mm, y + 15.0 * mm, "FENÊTRE D'ENGAGEMENT & STATUT SAP")
    c.setFont("Helvetica", 7.8)
    c.setFillColor(colors.HexColor("#1E293B"))
    c.drawString(PAGE_W - 98 * mm, y + 10.0 * mm, "Ouvertures éligibles : du 15/08/2026 au 12/11/2026")
    c.setFillColor(colors.HexColor("#B45309"))
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(PAGE_W - 98 * mm, y + 5.2 * mm, "SAP PCEC 602920 : En attente déversement lot M+1")

    y -= 8 * mm
    c.setFillColor(teal)
    c.setFont("Helvetica-Bold", 9.8)
    c.drawString(18 * mm, y, "1. DISPOSITIF D'ACQUISITION & CONDITIONS D'OCTROI")
    y -= 5 * mm
    y = wrap_paragraph(
        c,
        f"Dans le cadre du plan national de conquête (+15 000 ouvertures de comptes sur le trimestre), le secteur "
        f"de {rec['primary_city'].title()} ({rec['branch_codes_label']}) engage une enveloppe ferme de primes de "
        f"bienvenue destinée aux nouveaux clients âgés de 18 à 32 ans ouvrant un compte courant (CC_CHQ) assorti "
        f"d'un mandat de mobilité bancaire SEPA ({rec['quarter_openings']} ouvertures rattachées au présent contrat "
        f"dans le portefeuille CRM AWS).",
        18 * mm,
        y,
        PAGE_W - 36 * mm,
    )

    y -= 5 * mm
    c.setFillColor(teal)
    c.setFont("Helvetica-Bold", 9.8)
    c.drawString(18 * mm, y, "2. DÉCOMPTE CERTIFIÉ DES DOSSIERS VALIDÉS AU 12/11/2026")
    y -= 5 * mm

    cols = [18 * mm, 40 * mm, 112 * mm, 138 * mm, 164 * mm, PAGE_W - 18 * mm]
    row_h = 8.4 * mm
    c.setFillColor(teal)
    c.rect(cols[0], y - row_h, cols[-1] - cols[0], row_h, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.0)
    c.drawString(cols[0] + 2 * mm, y - 5.5 * mm, "Code")
    c.drawString(cols[1] + 2 * mm, y - 5.5 * mm, "Libellé de la prime commerciale")
    c.drawRightString(cols[3] - 3 * mm, y - 5.5 * mm, "Dossiers")
    c.drawRightString(cols[4] - 3 * mm, y - 5.5 * mm, "Barème unit.")
    c.drawRightString(cols[5] - 3 * mm, y - 5.5 * mm, "Engagement EUR")

    cur = y - row_h
    for idx, (code, lbl, qty_s, unit_s, amt_c) in enumerate(rec["line_items"]):
        c.setFillColor(colors.white if idx % 2 == 0 else colors.HexColor("#F8FAFC"))
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.rect(cols[0], cur - row_h, cols[-1] - cols[0], row_h, stroke=1, fill=1)
        c.setFillColor(accent)
        c.setFont("Courier-Bold", 8.0)
        c.drawString(cols[0] + 2 * mm, cur - 5.5 * mm, code)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.setFont("Helvetica", 8.0)
        c.drawString(cols[1] + 2 * mm, cur - 5.5 * mm, lbl)
        c.drawRightString(cols[3] - 3 * mm, cur - 5.5 * mm, qty_s)
        c.drawRightString(cols[4] - 3 * mm, cur - 5.5 * mm, unit_s)
        c.setFont("Helvetica-Bold", 8.1)
        c.drawRightString(cols[5] - 3 * mm, cur - 5.5 * mm, fmt_eur_dot(amt_c))
        cur -= row_h

    c.setFillColor(mint_bg)
    c.setStrokeColor(accent)
    c.setLineWidth(1.1)
    c.rect(cols[0], cur - 9.8 * mm, cols[-1] - cols[0], 9.8 * mm, stroke=1, fill=1)
    c.setFillColor(teal)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(
        cols[0] + 3 * mm,
        cur - 6.4 * mm,
        "ENVELOPPE PROMOTIONNELLE FERME ENGAGÉE SUR LE TRIMESTRE (IMPACT PNB)",
    )
    c.setFont("Helvetica-Bold", 9.9)
    c.drawRightString(cols[5] - 3 * mm, cur - 6.4 * mm, fmt_eur_dot(rec["committed_cents"]))
    cur -= 16 * mm

    c.setFillColor(teal)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(18 * mm, cur, "3. RÈGLE DE PROVISIONNEMENT AU TITRE DE L'ARRÊTÉ TRIMESTRIEL")
    cur -= 5 * mm
    wrap_paragraph(
        c,
        f"Bien que le crédit effectif sur le compte des bénéficiaires intervienne à J+30 après constatation du "
        f"premier flux salarial, l'engagement juridique attaché au contrat {cid} est irrévocable à la date de "
        f"signature en agence. La somme exacte de {fmt_eur_space(rec['committed_cents'])} vient en minoration "
        f"directe du Produit Net Bancaire du 4e trimestre 2026.",
        18 * mm,
        cur,
        PAGE_W - 36 * mm,
    )

    sig_y = 33 * mm
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.line(18 * mm, sig_y + 24 * mm, PAGE_W - 18 * mm, sig_y + 24 * mm)
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica-Bold", 8.1)
    c.drawString(
        18 * mm, sig_y + 18 * mm, f"Directeur de Secteur ({rec['primary_city'].title()} · {rec['region_code']})"
    )
    c.setFont("Helvetica", 7.9)
    c.drawString(18 * mm, sig_y + 13.2 * mm, f"{rec['signer_name']} — Matricule RES-{rec['idx']:04d}")
    draw_signature_curve(c, 24 * mm, sig_y + 2 * mm, seed_variant=rec["idx"])

    draw_stamp(
        c,
        PAGE_W - 52 * mm,
        sig_y + 11 * mm,
        f"PROTOCOLE VALIDÉ — {rec['region_code']}",
        f"ARRÊTÉ DU {rec['effective_date_fr']}",
        f"Engagement PNB : {fmt_eur_space(rec['committed_cents'])}",
        hex_color="#0F766E",
        angle=4.5,
        half_w_mm=29.0,
    )

    draw_footer(c, cid)
    c.showPage()
    c.save()


def render_promo_template_c(rec: dict, out_path: Path) -> None:
    """Gabarit C : Bordereau Dérogatoire Gratuité Tarifaire & Rétention (piège multi-montants)."""
    c = canvas.Canvas(str(out_path), pagesize=A4)
    cid = rec["promo_contract_id"]
    c.setTitle(f"{cid} — Avenant Dérogatoire Gratuité Tarifaire & Rétention ({rec['region_code']})")
    draw_watermark(c, "AVENANT TARIFAIRE DÉROGATOIRE")

    plum = colors.HexColor("#3B1F2B")
    slate = colors.HexColor("#334155")

    c.setFillColor(colors.HexColor("#F1F5F9"))
    c.rect(0, PAGE_H - 31 * mm, PAGE_W, 31 * mm, stroke=0, fill=1)
    c.setFillColor(plum)
    c.rect(0, PAGE_H - 32.5 * mm, PAGE_W, 1.5 * mm, stroke=0, fill=1)

    draw_hexagon_logo(c, 24 * mm, PAGE_H - 16 * mm, 6.4 * mm, plum)
    c.setFillColor(plum)
    c.setFont("Helvetica-Bold", 11.2)
    c.drawString(34 * mm, PAGE_H - 14.5 * mm, "BANQUE HEXAGONE · GESTION PATRIMONIALE")
    c.setFont("Helvetica", 7.8)
    c.setFillColor(slate)
    c.drawString(
        34 * mm,
        PAGE_H - 19.8 * mm,
        f"Direction Régionale {rec['region_name']} ({rec['region_code']}) — Pôle {rec['primary_city'].title()}",
    )
    c.drawString(
        34 * mm,
        PAGE_H - 24.4 * mm,
        "Bordereau consolidé des remises tarifaires après alerte rétention Call Center",
    )

    c.setFont("Courier-Bold", 8.5)
    c.setFillColor(plum)
    c.drawRightString(PAGE_W - 18 * mm, PAGE_H - 14.5 * mm, f"RÉF : {cid}")
    c.setFont("Helvetica", 7.8)
    c.setFillColor(slate)
    c.drawRightString(
        PAGE_W - 18 * mm,
        PAGE_H - 19.8 * mm,
        f"Signé à {rec['primary_city'].title()}, le {rec['effective_date_fr']}",
    )

    # Cartouche d'indicateurs de contexte (multi-montants distracteurs réalistes)
    y = PAGE_H - 60 * mm
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.setFillColor(colors.white)
    c.roundRect(18 * mm, y, PAGE_W - 36 * mm, 21 * mm, 2 * mm, stroke=1, fill=1)

    kpis = [
        (
            "ENCOURS GÉRÉ DU PORTEFEUILLE",
            fmt_eur_space(rec["portfolio_aum_cents"]),
            "(Assiette client observée — hors coût)",
        ),
        (
            "PLAFOND ANNUEL DÉLÉGATION PÔLE",
            fmt_eur_space(rec["delegation_cap_cents"]),
            "(Limite maximale autorisée 2026)",
        ),
        (
            f"AGENCES RATTACHÉES ({rec['region_code']})",
            rec["branch_codes_label"],
            f"(Secteur {rec['primary_city'].title()})",
        ),
    ]
    col_w = (PAGE_W - 36 * mm) / 3
    for idx, (title, val, sub) in enumerate(kpis):
        kx = 18 * mm + idx * col_w + 3.5 * mm
        if idx > 0:
            c.setStrokeColor(colors.HexColor("#E2E8F0"))
            c.line(18 * mm + idx * col_w, y + 3 * mm, 18 * mm + idx * col_w, y + 18 * mm)
        c.setFont("Helvetica-Bold", 6.8)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(kx, y + 15.5 * mm, title)
        c.setFont("Helvetica-Bold", 9.6)
        c.setFillColor(colors.HexColor("#0F172A"))
        c.drawString(kx, y + 9.2 * mm, val)
        c.setFont("Helvetica-Oblique", 6.9)
        c.setFillColor(colors.HexColor("#64748B"))
        c.drawString(kx, y + 4.2 * mm, sub)

    y -= 9 * mm
    c.setFillColor(plum)
    c.setFont("Helvetica-Bold", 9.8)
    c.drawString(18 * mm, y, "1. JUSTIFICATION DES GESTES COMMERCIAUX DE RÉTENTION")
    y -= 5.2 * mm
    y = wrap_paragraph(
        c,
        f"Suite aux sollicitations enregistrées par le Centre de Relation Client (CRM AWS) concernant les frais "
        f"de tenue de compte et l'attractivité des courtiers en ligne (DEGIRO2AXXX, TRBKDEBBXXX), le Pôle "
        f"{rec['primary_city'].title()} ({rec['branch_codes_label']}) a accordé des remises tarifaires ciblées aux "
        f"clients Patrimoniaux et Affluent s'engageant à maintenir leur domiciliation principale sur 12 mois.",
        18 * mm,
        y,
        PAGE_W - 36 * mm,
    )

    y -= 5 * mm
    c.setFillColor(plum)
    c.setFont("Helvetica-Bold", 9.8)
    c.drawString(18 * mm, y, "2. VENTILATION DES REMISES & GRATUITÉS ENGAGÉES (IMPACT PNB NET)")
    y -= 5 * mm

    cols = [18 * mm, 102 * mm, 130 * mm, 158 * mm, PAGE_W - 18 * mm]
    row_h = 8.4 * mm
    c.setFillColor(plum)
    c.rect(cols[0], y - row_h, cols[-1] - cols[0], row_h, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.0)
    c.drawString(cols[0] + 3 * mm, y - 5.5 * mm, "Nature de l'avenant tarifaire")
    c.drawRightString(cols[2] - 3 * mm, y - 5.5 * mm, "Bénéficiaires")
    c.drawRightString(cols[3] - 3 * mm, y - 5.5 * mm, "Remise unit.")
    c.drawRightString(cols[4] - 3 * mm, y - 5.5 * mm, "Coût PNB (EUR)")

    cur = y - row_h
    for idx, (lbl, ben_s, unit_s, amt_c) in enumerate(rec["line_items"]):
        c.setFillColor(colors.white if idx % 2 == 0 else colors.HexColor("#FAF8F9"))
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.rect(cols[0], cur - row_h, cols[-1] - cols[0], row_h, stroke=1, fill=1)
        c.setFillColor(colors.HexColor("#1E293B"))
        c.setFont("Helvetica", 8.0)
        c.drawString(cols[0] + 3 * mm, cur - 5.5 * mm, lbl)
        c.drawRightString(cols[2] - 3 * mm, cur - 5.5 * mm, ben_s)
        c.drawRightString(cols[3] - 3 * mm, cur - 5.5 * mm, unit_s)
        c.setFont("Helvetica-Bold", 8.1)
        c.drawRightString(cols[4] - 3 * mm, cur - 5.5 * mm, fmt_eur_space(amt_c))
        cur -= row_h

    c.setFillColor(colors.HexColor("#FDF2F8"))
    c.setStrokeColor(plum)
    c.setLineWidth(1.1)
    c.rect(cols[0], cur - 9.8 * mm, cols[-1] - cols[0], 9.8 * mm, stroke=1, fill=1)
    c.setFillColor(plum)
    c.setFont("Helvetica-Bold", 8.6)
    c.drawString(
        cols[0] + 3 * mm, cur - 6.3 * mm, "CHARGE COMMERCIALE NETTE ENGAGÉE T4 2026 (À DÉDUIRE DU PNB)"
    )
    c.setFont("Helvetica-Bold", 9.8)
    c.drawRightString(cols[4] - 3 * mm, cur - 6.3 * mm, fmt_eur_space(rec["committed_cents"]))
    cur -= 15.5 * mm

    wrap_paragraph(
        c,
        f"Note à l'attention du Contrôle de Gestion Groupe : ne pas confondre l'encours sous gestion du portefeuille "
        f"({fmt_eur_space(rec['portfolio_aum_cents'])}) ni le plafond annuel de délégation "
        f"({fmt_eur_space(rec['delegation_cap_cents'])}) avec la charge nette effectivement imputable au PNB "
        f"commissions du trimestre pour l'avenant {cid}, arrêtée à {fmt_eur_space(rec['committed_cents'])} "
        f"(compte PCEC 708590 — Rétrocessions et gratuités non intégrées dans l'extraction SAP du 12/11/2026).",
        18 * mm,
        cur,
        PAGE_W - 36 * mm,
        font_name="Helvetica-Oblique",
        font_size=8.3,
    )

    sig_y = 33 * mm
    c.setFillColor(slate)
    c.setFont("Helvetica-Bold", 8.1)
    c.drawString(
        18 * mm,
        sig_y + 18 * mm,
        f"Responsable du Pôle Patrimonial {rec['primary_city'].title()} ({rec['region_code']})",
    )
    c.setFont("Helvetica", 7.9)
    c.drawString(18 * mm, sig_y + 13.2 * mm, f"{rec['signer_name']} — Délégation GP-{rec['idx']:04d}")
    draw_signature_curve(c, 22 * mm, sig_y + 2 * mm, seed_variant=rec["idx"])

    draw_stamp(
        c,
        PAGE_W - 52 * mm,
        sig_y + 11 * mm,
        "AVENANT RÉTENTION CERTIFIÉ",
        f"PÔLE PATRIMONIAL {rec['region_code']} — {rec['effective_date_fr']}",
        f"Impact net PNB : -{fmt_eur_space(rec['committed_cents'])}",
        hex_color="#831843",
        angle=-5.0,
        half_w_mm=29.0,
    )

    draw_footer(c, cid)
    c.showPage()
    c.save()


# ==============================================================================
# Rendu générique du corpus réglementaire CFO (6 PDF normatifs ACPR / PCEC / ALM)
# ==============================================================================
def render_regulatory_cfo_doc(doc_spec: dict, out_path: Path) -> None:
    c = canvas.Canvas(str(out_path), pagesize=A4)
    c.setTitle(f"{doc_spec['doc_ref']} — {doc_spec['title']}")
    draw_watermark(c, doc_spec["watermark"])

    dark = colors.HexColor("#111827")
    crimson = colors.HexColor("#991B1B")
    c.setFillColor(dark)
    c.rect(0, 0, 9 * mm, PAGE_H, stroke=0, fill=1)
    c.saveState()
    c.translate(6.2 * mm, PAGE_H / 2)
    c.rotate(90)
    c.setFillColor(colors.HexColor("#9CA3AF"))
    c.setFont("Helvetica-Bold", 7.0)
    c.drawCentredString(
        0,
        0,
        "DOCUMENT NORMATIF GROUPE · SUPERVISION PRUDENTIELLE ACPR / BCE · CLASSIFICATION : COMITÉ EXÉCUTIF & CFO",
    )
    c.restoreState()

    x0 = 19 * mm
    max_w = PAGE_W - x0 - 16 * mm

    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 12.2)
    c.drawString(x0, PAGE_H - 18 * mm, f"BANQUE HEXAGONE — {doc_spec['issuer']}")
    c.setFont("Helvetica-Bold", 8.1)
    c.setFillColor(crimson)
    c.drawString(
        x0,
        PAGE_H - 23.2 * mm,
        f"CORPUS RÉGLEMENTAIRE CFO · RÉF. : {doc_spec['doc_ref']} · {doc_spec['subtitle']}",
    )
    c.setStrokeColor(dark)
    c.setLineWidth(1.1)
    c.line(x0, PAGE_H - 26.5 * mm, PAGE_W - 16 * mm, PAGE_H - 26.5 * mm)

    y = PAGE_H - 49 * mm
    c.setFillColor(colors.HexColor("#F8FAFC"))
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setLineWidth(0.7)
    c.rect(x0, y, max_w, 18.5 * mm, stroke=1, fill=1)
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x0 + 3 * mm, y + 13.4 * mm, "Textes de référence :")
    c.setFont("Helvetica", 7.3)
    c.drawString(x0 + 33 * mm, y + 13.4 * mm, doc_spec["legal_refs"])
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x0 + 3 * mm, y + 8.4 * mm, "Organe d'approbation :")
    c.setFont("Helvetica", 7.3)
    c.drawString(x0 + 33 * mm, y + 8.4 * mm, doc_spec["approval_body"])
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x0 + 3 * mm, y + 3.4 * mm, "Périmètre d'application :")
    c.setFont("Helvetica", 7.3)
    c.drawString(x0 + 33 * mm, y + 3.4 * mm, doc_spec["scope"])

    y -= 8 * mm
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x0, y, doc_spec["art1_title"])
    y -= 4.8 * mm
    y = wrap_paragraph(c, doc_spec["art1_body"], x0, y, max_w, font_size=8.5, leading=12.1)

    y -= 4 * mm
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x0, y, doc_spec["table_section_title"])
    y -= 4.5 * mm

    cols = [x0, x0 + 62 * mm, x0 + 102 * mm, PAGE_W - 16 * mm]
    hdr_h = 8.4 * mm
    row_h = 11.8 * mm
    c.setFillColor(dark)
    c.rect(cols[0], y - hdr_h, cols[-1] - cols[0], hdr_h, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 7.5)
    h1, h2, h3 = doc_spec["table_headers"]
    c.drawString(cols[0] + 2.5 * mm, y - 5.5 * mm, h1)
    c.drawString(cols[1] + 2.5 * mm, y - 5.5 * mm, h2)
    c.drawString(cols[2] + 2.5 * mm, y - 5.5 * mm, h3)

    cur = y - hdr_h
    for idx, (col1, col2, col3) in enumerate(doc_spec["table_rows"]):
        c.setFillColor(colors.white if idx % 2 == 0 else colors.HexColor("#FEF2F2"))
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.rect(cols[0], cur - row_h, cols[-1] - cols[0], row_h, stroke=1, fill=1)
        c.line(cols[1], cur - row_h, cols[1], cur)
        c.line(cols[2], cur - row_h, cols[2], cur)
        draw_wrapped_cell(
            c,
            col1,
            cols[0] + 2.2 * mm,
            cur,
            (cols[1] - cols[0]) - 4.4 * mm,
            font_name="Helvetica-Bold",
            font_size=7.2,
            color=dark,
        )
        draw_wrapped_cell(
            c,
            col2,
            cols[1] + 2.2 * mm,
            cur,
            (cols[2] - cols[1]) - 4.4 * mm,
            font_name="Helvetica-Bold",
            font_size=7.3,
            color=crimson,
        )
        draw_wrapped_cell(
            c,
            col3,
            cols[2] + 2.2 * mm,
            cur,
            (cols[3] - cols[2]) - 4.4 * mm,
            font_name="Helvetica",
            font_size=7.1,
            color=colors.HexColor("#1E293B"),
        )
        cur -= row_h

    cur -= 6 * mm
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x0, cur, doc_spec["art3_title"])
    cur -= 4.8 * mm
    cur = wrap_paragraph(c, doc_spec["art3_p1"], x0, cur, max_w, font_size=8.5, leading=12.1)
    cur -= 1.8 * mm
    wrap_paragraph(c, doc_spec["art3_p2"], x0, cur, max_w, font_size=8.5, leading=12.1)

    draw_stamp(
        c,
        PAGE_W - 48 * mm,
        32 * mm,
        doc_spec["stamp_l1"],
        doc_spec["stamp_l2"],
        doc_spec["stamp_l3"],
        hex_color="#1E293B",
        angle=0.0,
        half_w_mm=29.0,
    )

    draw_footer(c, doc_spec["doc_ref"], left_x_mm=19.0)
    c.showPage()
    c.save()


def get_regulatory_cfo_specs() -> list[dict]:
    """Définit les 6 documents réglementaires, comptables et prudentiels du CFO."""
    return [
        {
            "filename": "REG_01_ANC_2014_07_DOCTRINE_PNB_PCEC.pdf",
            "doc_ref": "REG-FIN-PCEC-2026-01",
            "issuer": "DIRECTION COMPTABLE GROUPE & NORMES ANC / IFRS",
            "title": "Doctrine Comptable Groupe — Règlement ANC n°2014-07 & Arrêté du PNB",
            "subtitle": "RÈGLES D'ASSIETTE DU PRODUIT NET BANCAIRE (PCEC)",
            "watermark": "DOCTRINE COMPTABLE ANC / PCEC",
            "legal_refs": "Règlement ANC n°2014-07 (PCEC) · IAS 37 / IFRS 9 · Instruction ACPR 2025-I-04 (SURFI)",
            "approval_body": "Comité des Normes Comptables & Direction Financière Groupe — 02/06/2026",
            "scope": "Arrêtés trimestriels PNB Banque de Détail France (SAP Grand Livre, ALM & Engagements Réseau)",
            "art1_title": "ARTICLE 1 — PROHIBITION DES SOMMES NON SIGNÉES & ÉLIMINATION DES FLUX INTERNES",
            "art1_body": (
                "En application du Plan Comptable des Établissements de Crédit (PCEC), toute requête ou agrégation "
                "portant sur le grand livre SAP (table BSEG/BKPF) doit impérativement appliquer la convention de "
                "signe liée au code sens SHKZG ('H' = Crédit / Produit positif ; 'S' = Débit / Charge négative). "
                "L'agrégation naïve des montants bruts non signés ou l'inclusion des virements internes compte-à-livret "
                "(opérations codifiées 58* / 0580 entre CC_CHQ et livrets d'épargne du même établissement) constitue "
                "une anomalie matérielle grave conduisant à une surestimation artificielle de la marge (+42,80 M EUR "
                "observés lors des tests d'audit sur requêtes non gouvernées)."
            ),
            "table_section_title": "ARTICLE 2 — TABLE DE RATTACHEMENT OBLIGATOIRE AU PNB CONSOLIDÉ",
            "table_headers": ("Nature de l'opération / Silo", "Compte PCEC / Règle", "Traitement obligatoire dans le PNB"),
            "table_rows": [
                (
                    "Écritures SAP Grand Livre (commissions & intérêts)",
                    "SHKZG 'H' (+) / 'S' (-)",
                    "Appliquer strictement le signe comptable ; exclure les comptes de bilan classe 1 à 5.",
                ),
                (
                    "Virements internes compte-à-livret (codes 58* / 0580)",
                    "Neutralisation intra-entité",
                    "Exclusion intégrale à 100 % du calcul de collecte nette et de commissionnement PNB.",
                ),
                (
                    "Refinancement interne de la collecte perdue (TCI ALM)",
                    "PCEC 601320 (-24,12 M EUR)",
                    "Déduction analytique obligatoire du PNB Banque de Détail au taux de remplacement €STR.",
                ),
                (
                    "Primes, gratuités & taux boostés signés en PDF agence",
                    "PCEC 602910/20 & 708590",
                    "Provisionnement intégral en déduction directe du PNB (-14,30 M EUR), hors frais généraux.",
                ),
            ],
            "art3_title": "ARTICLE 3 — RATTACHEMENT DES AVENANTS PDF HORS-BILAN AU CUT-OFF TRIMESTRIEL",
            "art3_p1": (
                "3.1 Principe de séparation des exercices : Tout avenant promotionnel (taux boosté Livret Maison, "
                "prime de bienvenue 18-32 ans ou remise tarifaire de rétention) dûment signé par une Direction "
                "Régionale avant la date de cut-off (12/11/2026) constitue un engagement ferme diminuant le PNB "
                "du trimestre en cours, quand bien même le déversement informatique vers SAP interviendrait à M+1."
            ),
            "art3_p2": (
                "3.2 Réconciliation certifiée : Seule la formule certifiée dans le glossaire Groupe (intégrant le "
                "solde net SAP signé, la charge TCI ALM de -24,12 M EUR et la somme exhaustive des 250 PDF d'agences "
                "pour -14,30 M EUR, soit un écart PNB certifié de -38,42 M EUR) est opposable en Comité Exécutif."
            ),
            "stamp_l1": "DOCTRINE COMPTABLE CERTIFIÉE",
            "stamp_l2": "DIRECTION FINANCIÈRE GROUPE",
            "stamp_l3": "Réf. ANC-2014-07 · PCEC V2026",
        },
        {
            "filename": "REG_02_CHARTE_ALM_TCI_REFINANCEMENT_BCE.pdf",
            "doc_ref": "REG-ALM-TCI-2026-02",
            "issuer": "DIRECTION TRÉSORERIE CENTRALE & GESTION ACTIF-PASSIF (ALM)",
            "title": "Convention Groupe ALM — Taux de Cession Interne (TCI) & Refinancement BCE",
            "subtitle": "TARIFICATION ANALYTIQUE DE LA COLLECTE À VUE & COÛT DE REMPLACEMENT",
            "watermark": "CHARTE ALM — TCI / FTP",
            "legal_refs": "Orientation EBA/GL/2018/02 (IRRBB & FTP) · Décision BCE Taux Facilité de Dépôt / €STR 2026",
            "approval_body": "Comité Actif-Passif (ALCO) Groupe Banque Hexagone — Séance du 03/08/2026",
            "scope": "Facturation interne entre la Trésorerie Centrale et le Réseau Banque de Détail (8 régions)",
            "art1_title": "ARTICLE 1 — MÉCANISME DU TAUX DE CESSION INTERNE (TCI) SUR DÉPÔTS À VUE",
            "art1_body": (
                "Les dépôts à vue de la clientèle particulière (comptes chèques CC_CHQ rémunérés à 0,00 %) "
                "constituent la ressource structurelle primaire du bilan de Banque Hexagone. Lorsqu'une fuite "
                "nette de dépôts à vue se matérialise par virements SEPA Instant sortants (2,42 Md EUR constatés "
                "sur 90 jours glissants vers néobanques et courtiers), la Trésorerie Centrale doit emprunter "
                "immédiatement un montant équivalent sur le marché monétaire européen pour maintenir l'équilibre "
                "emplois-ressources des crédits immobiliers à taux fixe."
            ),
            "table_section_title": "ARTICLE 2 — PARAMÈTRES OFFICIELS DE REFACTURATION ALM (T4 2026)",
            "table_headers": ("Paramètre ALM / Trésorerie", "Valeur Certifiée T4", "Impact analytique sur le PNB Réseau"),
            "table_rows": [
                (
                    "Assiette de fuite nette dépôts à vue (90 jours)",
                    "2 420 000 000,00 EUR",
                    " Déficit de collecte à 0 % remplacé par tirage marché interbancaire court terme.",
                ),
                (
                    "Taux de référence monétaire (€STR moyen + spread)",
                    "3,65 % + 32 bps (3,97 %)",
                    "Taux complet de cession interne (TCI marginal de liquidité) facturé au Réseau.",
                ),
                (
                    "Charge nette de refinancement ALM trimestrielle",
                    "-24 120 000,00 EUR",
                    "Comptabilisée sous PCEC 601320 ; déduite obligatoirement du PNB consolidé CFO.",
                ),
                (
                    "Sensibilité additionnelle par 100 M EUR de fuite",
                    "-997 000 EUR / trimestre",
                    "Priorité stratégique accordée à la rétention digitale sur la cohorte 18-32 ans.",
                ),
            ],
            "art3_title": "ARTICLE 3 — INTERDICTION D'OMISSION DANS LES REPORTINGS DE MARGE",
            "art3_p1": (
                "3.1 Opposabilité ALCO : Aucun tableau de bord de rentabilité commerciale ne peut présenter les "
                "commissions ou produits d'intérêts bruts du réseau sans imputer simultanément la charge de "
                "refinancement TCI ALM (-24,12 M EUR sur la période du 15/08/2026 au 12/11/2026)."
            ),
            "art3_p2": (
                "3.2 Couplage avec le coût commercial réseau : Le coût complet de l'érosion des dépôts additionne "
                "le coût de remplacement ALM (-24,12 M EUR) et le coût des campagnes défensives d'agences signées "
                "en PDF (-14,30 M EUR), établissant l'impact total sur le PNB à -38,42 M EUR."
            ),
            "stamp_l1": "CONVENTION ALCO APPLICABLE",
            "stamp_l2": "TRÉSORERIE CENTRALE & ALM",
            "stamp_l3": "TCI Marginal : 3,97 % · PCEC 601320",
        },
        {
            "filename": "REG_03_ILAAP_SEUILS_LCR_NSFR_ACPR_2026.pdf",
            "doc_ref": "REG-ALM-ILAAP-2026-03",
            "issuer": "DIRECTION GÉNÉRALE DES RISQUES & CONFORMITÉ PRUDENTIELLE",
            "title": "Dispositif Prudentiel Liquidité ILAAP / LCR & Seuils d'Alerte ACPR 2026",
            "subtitle": "SURVEILLANCE DU RATIO LCR (CRR II) & SEUILS DE DÉCLARATION SUPERVISEUR",
            "watermark": "NORME PRUDENTIELLE — ACPR / ILAAP",
            "legal_refs": "Règlement (UE) n°575/2013 (CRR II Art. 412 & 421 LCR) · EBA/GL/2016/10 (ILAAP) · ACPR 2024-R-01",
            "approval_body": "Comité des Risques & ALM du Conseil d'Administration — Délibération du 18/07/2026",
            "scope": "Directeur Financier (CFO), Direction des Risques, Trésorerie ALM, Inspection Générale",
            "art1_title": "ARTICLE 1 — QUALIFICATION PRUDENTIELLE DES DÉPÔTS À VUE & FUITE SEPA INSTANT",
            "art1_body": (
                "En application de l'article 421 du Règlement CRR II, les dépôts à vue de la clientèle de détail "
                "(CC_CHQ) bénéficient d'un taux d'écoulement prudentiel LCR standard de 5 % uniquement lorsqu'ils "
                "constituent des dépôts stables. Lorsqu'une cohorte démographique présente des virements SEPA "
                "Instant récurrents vers des néobanques ou courtiers en ligne absorbant plus de 50 % des flux "
                "sortants dans les 5 premiers jours du mois (observé à 68,0 % sur les 18-32 ans), ce compartiment "
                "doit impérativement être reclassé en dépôts moins stables avec un coefficient de fuite LCR à 15 %."
            ),
            "table_section_title": "ARTICLE 2 — GRILLE DES SEUILS D'ALERTE INTERNES (ILAAP) & PLAFONDS DE DÉLÉGATION",
            "table_headers": ("Indicateur de surveillance CFO / Risques", "Seuil / Plafond", "Mesure corrective obligatoire en cas de brèche"),
            "table_rows": [
                (
                    "Fuite cumulée dépôts à vue sur 90 jours glissants",
                    "> 2,00 Md EUR",
                    "Notification Comité ALM & déclaration superviseur ACPR sous 5 jours ouvrés.",
                ),
                (
                    "Concentration fuite J+1..J+5 cohorte 18-32 ans",
                    "> 50,0 % du flux",
                    "Reclassement compartiment LCR de 5 % à 15 % + dotation coussin HQLA.",
                ),
                (
                    "Enveloppe trimestrielle remises & taux boostés PDF",
                    "Max 9,00 M EUR / trim.",
                    "Gel immédiat des délégations régionales & audit Inspection Générale.",
                ),
                (
                    "Ratio de couverture de liquidité interne (LCR cible)",
                    "Alerte < 115 % (Min 100 %)",
                    "Activation du plan d'urgence de liquidité et réallocation d'actifs HQLA.",
                ),
            ],
            "art3_title": "ARTICLE 3 — PROCÉDURE D'ESCALADE IMMÉDIATE DU CFO EN CAS DE DOUBLE BRÈCHE",
            "art3_p1": (
                "3.1 Escalade ACPR : Tout franchissement simultané du seuil d'érosion de 2,00 Md EUR sur 90 jours "
                "(constaté à 2,42 Md EUR, soit +420 M EUR au-dessus de la limite rouge) et du seuil de vélocité "
                "jeunes actifs (68,0 % > 50,0 %) impose l'inscription immédiate à l'ordre du jour du Comité Exécutif."
            ),
            "art3_p2": (
                "3.2 Remédiation structurelle : Le remplacement des dérogations tarifaires papier par un dispositif "
                "automatisé et plafonné de rétention mobile (conforme ACPR 2024-R-01) constitue la mesure de "
                "remédiation privilégiée attendue par le superviseur."
            ),
            "stamp_l1": "NORME EN VIGUEUR — T4 2026",
            "stamp_l2": "DIRECTION DES RISQUES & CONFORMITÉ",
            "stamp_l3": "Réf. ACPR-ILAAP-30002-V4.2",
        },
        {
            "filename": "REG_04_PV_COMITE_RISQUES_PLAFONDS_Q4_2026.pdf",
            "doc_ref": "REG-GOV-CORISK-2026-04",
            "issuer": "SECRÉTARIAT GÉNÉRAL DU CONSEIL — COMITÉ DES RISQUES & DÉLÉGATIONS",
            "title": "Extrait Certifié du PV du Comité des Risques — Plafonds Promotionnels T4 2026",
            "subtitle": "ENCADREMENT DES ENVELOPPES DE PRIMES & TAUX BOOSTÉS DU RÉSEAU D'AGENCES",
            "watermark": "PROCÈS-VERBAL COMITÉ DES RISQUES",
            "legal_refs": "Arrêté du 3 novembre 2014 relatif au contrôle interne (Art. 106 à 114) · Charte Délégations Réseau",
            "approval_body": "Comité des Risques du Conseil d'Administration — Séance plénière du 12/08/2026",
            "scope": "8 Directions Régionales (REG1 à REG8), 450 Agences & Contrôle Financier Central",
            "art1_title": "ARTICLE 1 — BILAN DU T3 2026 & PLAFONNEMENT STRICT DU T4 2026",
            "art1_body": (
                "Au cours du 3e trimestre 2026, les sorties nettes de dépôts à vue vers les acteurs néobanques "
                "s'étaient établies à 0,95 Md EUR (sous le seuil d'alerte ILAAP de 2,00 Md EUR). Pour le 4e "
                "trimestre 2026, afin de protéger le Produit Net Bancaire contre une inflation non maîtrisée des "
                "gestes commerciaux accordés localement en agence sous forme d'avenants PDF, le Comité des Risques "
                "fixe un plafond national impératif et non révisable de 9 000 000,00 EUR (9,00 M EUR) toutes "
                "natures d'avantages confondues (taux boostés, primes d'ouverture et gratuités)."
            ),
            "table_section_title": "ARTICLE 2 — RÉPARTITION RÉGIONALE AUTORISÉE DU PLAFOND DE 9,00 M EUR",
            "table_headers": ("Périmètre Régional", "Plafond Autorisé T4", "Règle de blocage et d'audit hors-SAP"),
            "table_rows": [
                (
                    "REG1 Île-de-France & REG2 Auvergne-Rhône-Alpes",
                    "Max 3,51 M EUR cumulés",
                    "2,16 M EUR (REG1) + 1,35 M EUR (REG2) ; visa préalable obligatoire au-delà de 75 k EUR.",
                ),
                (
                    "REG3 Nouvelle-Aquitaine, REG4 Occitanie & REG5 Nord",
                    "Max 2,88 M EUR cumulés",
                    "0,99 M EUR (REG3) + 0,99 M EUR (REG4) + 0,90 M EUR (REG5).",
                ),
                (
                    "REG6 Grand Est, REG7 PACA & REG8 Grand Ouest",
                    "Max 2,61 M EUR cumulés",
                    "0,81 M EUR (REG6) + 0,90 M EUR (REG7) + 0,90 M EUR (REG8).",
                ),
                (
                    "Total National autorisé sur l'ensemble des PDF réseau",
                    "9 000 000,00 EUR TTC",
                    "Tout dépassement global constaté (> 9,00 M EUR) entraîne la suspension des délégations.",
                ),
            ],
            "art3_title": "ARTICLE 3 — SANCTION DES ENGAGEMENTS HORS-SAP NON DÉCLARÉS",
            "art3_p1": (
                "3.1 Risque opérationnel de sous-estimation : Le Comité attire l'attention du CFO sur le délai de "
                "saisie des avenants PDF stockés sur serveur documentaire. Si le recensement exhaustif par IA "
                "révèle un cumul supérieur à 9,00 M EUR (14,30 M EUR effectivement engagés, soit +5,30 M EUR de "
                "dépassement non autorisé), l'écart intégral doit être provisionné dès T4."
            ),
            "art3_p2": (
                "3.2 Bascule vers pilotage centralisé : En cas de dépassement avéré, les campagnes papier locales "
                "sont closes et remplacées par des offres personnalisées temps réel pilotées centralement."
            ),
            "stamp_l1": "EXTRAIT CERTIFIÉ CONFORME",
            "stamp_l2": "SECRÉTARIAT COMITÉ DES RISQUES",
            "stamp_l3": "Plafond National T4 : 9,00 M EUR",
        },
        {
            "filename": "REG_05_UE_2024_886_SEPA_INSTANT_RISQUE_LIQUIDITE.pdf",
            "doc_ref": "REG-PAY-UE886-2026-05",
            "issuer": "DIRECTION CONFORMITÉ PAIEMENTS & FLUX EUROPÉENS SEPA",
            "title": "Note Réglementaire UE 2024/886 — Gratuité SEPA Instant & Risque Intrajournalier",
            "subtitle": "IMPACT DE L'INSTANT PAYMENT MANDATORY SUR LE COMPORTEMENT D'ÉPARGNE CLIENT",
            "watermark": "RÈGLEMENT UE 2024/886 — SEPA",
            "legal_refs": "Règlement (UE) 2024/886 (Instant Payments Regulation) · Rulebook EPC SCT Inst ISO 20022 pacs.008",
            "approval_body": "Comité Paiements & Conformité Réglementaire — Note du 01/09/2026",
            "scope": "Flux temps réel Pub/Sub ISO 20022 (pacs.008), Relevés CFONB 120 (code 0810) & Mobile Banking",
            "art1_title": "ARTICLE 1 — ÉGALITÉ TARIFAIRE OBLIGATOIRE & PHÉNOMÈNE DE « SALARY SWEEPING »",
            "art1_body": (
                "Depuis l'entrée en application complète du Règlement (UE) 2024/886, les virements SEPA Instant "
                "exécutés en moins de 10 secondes (24h/24, 7j/7) sont obligatoirement facturés au même tarif nul "
                "que les virements SEPA standards pour la clientèle des particuliers. Cette gratuité réglementaire "
                "interdit toute barrière tarifaire à la sortie et favorise le transfert programmé ou impulsif de "
                "l'épargne mensuelle dès réception du salaire (entre le 1er et le 5 du mois) vers les BIC "
                "REVOLT21XXX, TRBKDEBBXXX, NTSBDEB1XXX, BOURFRPPXXX et DEGIRO2AXXX."
            ),
            "table_section_title": "ARTICLE 2 — RÈGLES DE STATUTS ISO 20022 (PACS.008) POUR L'ANALYTIQUE & LE PNB",
            "table_headers": ("Statut ISO 20022 / Anomalie", "Signification Réglementaire", "Règle d'exclusion ou d'inclusion analytique"),
            "table_rows": [
                (
                    "Statut ACSC (AcceptedSettlementCompleted)",
                    "Règlement interbancaire final",
                    "Seul statut comptablement valide à retenir pour mesurer la fuite réelle des dépôts.",
                ),
                (
                    "Statut RJCT (Rejected — AM04, AC04, RR04)",
                    "Virement rejeté < 10 secondes",
                    "Aucun mouvement de fonds ; doit impérativement être exclu des volumes de fuite.",
                ),
                (
                    "Statut PDNG (Pending — criblage LCB-FT / VoP)",
                    "En attente de validation",
                    "Exclure des agrégats réglés tant que la confirmation ACSC n'est pas reçue.",
                ),
                (
                    "Doublons techniques de réémission (end_to_end_id)",
                    "At-least-once broker retry",
                    "Dédoublonnage obligatoire sur end_to_end_id avant tout calcul financier (~3,4 % du flux).",
                ),
            ],
            "art3_title": "ARTICLE 3 — INTERDICTION DE FRICTION ILLÉGALE & RÉPONSE PAR LA VALEUR",
            "art3_p1": (
                "3.1 Conformité UE 2024/886 : Il est strictement interdit de brider artificiellement les plafonds "
                "SEPA Instant ou d'introduire des délais de traitement pour ralentir les transferts vers les "
                "néobanques européennes."
            ),
            "art3_p2": (
                "3.2 Levier autorisé : La seule réponse conforme consiste à proposer proactivement dans l'application "
                "mobile, dès la tombée du salaire, une allocation d'épargne instantanée en 1 clic basée sur le "
                "reste à vivre prévisionnel réel du client."
            ),
            "stamp_l1": "CONFORMITÉ SEPA CERTIFIÉE",
            "stamp_l2": "DIRECTION PAIEMENTS & FLUX",
            "stamp_l3": "Règlement UE 2024/886 · SCT Inst",
        },
        {
            "filename": "REG_06_ACPR_2024_R01_ENCADREMENT_OFFRES_EPARGNE.pdf",
            "doc_ref": "REG-CONF-ACPR-2026-06",
            "issuer": "DIRECTION DE LA CONFORMITÉ & PROTECTION DE LA CLIENTÈLE",
            "title": "Recommandation ACPR 2024-R-01 — Commercialisation Digitale d'Épargne",
            "subtitle": "GARDE-FOUS OBLIGATOIRES POUR LES AGENTS IA & CONSEILLERS MOBILES (DÉMO #4)",
            "watermark": "CONFORMITÉ ACPR — PROTECTION CLIENT",
            "legal_refs": "Recommandation ACPR 2024-R-01 · Code Monétaire et Financier Art. L.533-12 · AI Act UE (Transparence)",
            "approval_body": "Direction de la Conformité Groupe (RCSI) — Mise à jour du 15/09/2026",
            "scope": "Application Mobile Banque Hexagone, Modèles BQML de Propension & Agents Conversationnels ADK",
            "art1_title": "ARTICLE 1 — DEVOIR DE CONSEIL & VÉRIFICATION DU RESTE À VIVRE PRÉVISIONNEL",
            "art1_body": (
                "Tout système automatisé ou agent conversationnel proposant un placement d'épargne sur canal mobile "
                "doit préalablement calculer le reste à vivre prévisionnel de fin de mois du client en tenant compte "
                "du salaire versé, des charges fixes récurrentes (loyer, énergie, abonnements et dérives éventuelles "
                "de facturation) et des dépenses courantes estimées. Il est interdit d'inciter un client à immobiliser "
                "ou transférer un montant susceptible de placer son compte courant en découvert."
            ),
            "table_section_title": "ARTICLE 2 — HIÉRARCHIE DES PRODUITS & PLAFONDS PROMOTIONNELS AUTORISÉS SUR MOBILE",
            "table_headers": ("Règle de Conformité ACPR", "Paramètre Impératif", "Application concrète par l'Agent Mobile ADK"),
            "table_rows": [
                (
                    "Règle n°1 — Coussin de sécurité budgétaire",
                    "Max 70 % du surplus fin de mois",
                    "Exemple : pour un excédent projeté de +300 EUR, recommander un versement prudent de 180 à 200 EUR.",
                ),
                (
                    "Règle n°2 — Priorité à l'épargne réglementée",
                    "Livret A / LDDS en 1er rang",
                    "Vérifier d'abord la marge disponible sur Livret A / LDDS (3,00 % net d'impôt) avant produit fiscalisé.",
                ),
                (
                    "Règle n°3 — Plafonnement du Livret Maison boosté",
                    "Max +200 bps durant 3 mois",
                    "Taux boosté digital plafonné à 3,50 % brut sur 3 mois, puis mention explicite du taux de base 1,50 %.",
                ),
                (
                    "Règle n°4 — Transparence sur les hausses de charges",
                    "Alerte proactive abonnements",
                    "Signaler toute hausse détectée sur prélèvement récurrent (ex: +4,00 EUR abonnement streaming).",
                ),
            ],
            "art3_title": "ARTICLE 3 — TRAÇABILITÉ & CONSENTEMENT EXPLICITE EN APPLICATION MOBILE",
            "art3_p1": (
                "3.1 Explicabilité client : Toute recommandation formulée par l'agent mobile doit exposer en langage "
                "clair le calcul du budget prévisionnel, le taux net ou brut applicable et la disponibilité "
                "immédiate des fonds sans pénalité de sortie."
            ),
            "art3_p2": (
                "3.2 Validation transactionnelle : Aucune écriture de virement interne vers livret ni souscription "
                "ne peut être exécutée dans la base opérationnelle AlloyDB sans confirmation explicite du client."
            ),
            "stamp_l1": "VISA CONFORMITÉ RCSI",
            "stamp_l2": "PROTECTION DE LA CLIENTÈLE",
            "stamp_l3": "Conforme ACPR 2024-R-01 & AI Act",
        },
    ]


# ==============================================================================
# Construction déterministe des 250 contrats agences + 6 PDF réglementaires CFO
# ==============================================================================
def build_250_promo_specs(universe: dict[str, pl.DataFrame]) -> list[dict]:
    rng = np.random.default_rng(DEMO_SEED + 505)
    agencies_df = universe["agencies"]
    regions_df = universe["regions"]
    accounts_df = universe["accounts"]

    reg_name_map = dict(
        zip(regions_df["region_code"].to_list(), regions_df["region_name"].to_list())
    )
    reg_weight_map = {r[0]: r[2] for r in REGIONS_DEF}

    # Reproduit exactement le mapping de `generate_aws_crm_s3.py` :
    # agence d'indice i (0..449) -> PROMO-2026-{(i % 250) + 1:03d}
    ag_rows = agencies_df.to_dicts()
    contract_to_branches: dict[str, list[dict]] = {
        f"PROMO-2026-{k:03d}": [] for k in range(1, NUM_PROMO_PDFS + 1)
    }
    guichet_to_contract: dict[str, str] = {}
    for i, ag in enumerate(ag_rows):
        cid = f"PROMO-2026-{(i % NUM_PROMO_PDFS) + 1:03d}"
        contract_to_branches[cid].append(ag)
        guichet_to_contract[ag["guichet_code_5"]] = cid

    # Comptage exact des ouvertures du trimestre par contrat (total = 15 000)
    q_open = accounts_df.filter(pl.col("is_opened_in_quarter"))
    open_counts: dict[str, int] = {f"PROMO-2026-{k:03d}": 0 for k in range(1, NUM_PROMO_PDFS + 1)}
    for g in q_open["guichet_code_5"].to_list():
        open_counts[guichet_to_contract[g]] += 1

    # Répartition exacte des 3 gabarits : 95 Type A, 90 Type B, 65 Type C = 250 PDF
    template_pool = ["A"] * 95 + ["B"] * 90 + ["C"] * 65
    rng.shuffle(template_pool)
    # Garantir que PROMO-2026-042 (Agence 0042 Paris de Lucas Martin) est un Gabarit A emblématique
    if template_pool[41] != "A":
        first_a = template_pool.index("A")
        template_pool[first_a], template_pool[41] = template_pool[41], "A"

    # Poids déterministes pour répartir exactement 14 300 000,00 € (1 430 000 000 centimes)
    weights = np.zeros(NUM_PROMO_PDFS, dtype=np.float64)
    chosen_primary_branch: list[dict] = []
    for k in range(1, NUM_PROMO_PDFS + 1):
        cid = f"PROMO-2026-{k:03d}"
        b_list = contract_to_branches[cid]
        # Sélectionne l'agence d'ancrage pour couvrir équitablement REG1..REG8 (en gardant 0042 sur REG1)
        if len(b_list) > 1 and k >= 116 and k != 42:
            prim = b_list[1]
        else:
            prim = b_list[0]
        chosen_primary_branch.append(prim)

        tpl = template_pool[k - 1]
        tpl_mult = 1.28 if tpl == "A" else (0.94 if tpl == "B" else 0.78)
        reg_w = reg_weight_map[prim["region_code"]]
        jitter = float(rng.uniform(0.82, 1.22))
        weights[k - 1] = tpl_mult * (0.55 + 2.2 * reg_w) * jitter

    alloc_cents = distribute_exact_cents(
        weights=weights,
        target_cents=TARGET_PROMO_COST_CENTS,
        min_cents=1_850_000,   # min 18 500,00 €
        max_cents=16_500_000,  # max 165 000,00 €
    )
    assert int(alloc_cents.sum()) == TARGET_PROMO_COST_CENTS

    specs: list[dict] = []
    q_days = (SNAPSHOT_DATE - QUARTER_START_DATE).days

    for k in range(1, NUM_PROMO_PDFS + 1):
        cid = f"PROMO-2026-{k:03d}"
        tpl = template_pool[k - 1]
        prim = chosen_primary_branch[k - 1]
        b_list = contract_to_branches[cid]
        reg_code = prim["region_code"]
        reg_name = reg_name_map[reg_code]
        city = prim["city"]
        # Affiche les agences de la même région en priorité + codes rattachés
        same_reg_codes = [b["agency_code_4"] for b in b_list if b["region_code"] == reg_code]
        branch_codes = same_reg_codes if same_reg_codes else [prim["agency_code_4"]]
        branch_label = ", ".join(branch_codes)

        eff_date: date = QUARTER_START_DATE + timedelta(days=int(rng.integers(0, max(1, q_days - 3))))
        dur_months = int(rng.choice([3, 4, 6]))
        end_date: date = eff_date + timedelta(days=30 * dur_months)

        signer = f"{FIRST_NAMES[(k * 3) % len(FIRST_NAMES)].title()} {LAST_NAMES[(k * 5) % len(LAST_NAMES)]}"
        controller = f"{FIRST_NAMES[(k * 7 + 4) % len(FIRST_NAMES)].title()} {LAST_NAMES[(k * 11 + 2) % len(LAST_NAMES)]}"

        total_c = int(alloc_cents[k - 1])
        q_cnt = max(18, open_counts[cid])

        if tpl == "A":
            boost_bps = int(rng.choice([150, 175, 200, 225, 250]))
            l1 = (total_c * 76 // 10000) * 100
            l2 = (total_c * 18 // 10000) * 100
            l3 = total_c - l1 - l2
            # Assiette correspondante en euros entiers
            factor = (boost_bps / 10_000.0) * (dur_months / 12.0)
            assiette_1_cents = int(round(l1 / factor / 100.0)) * 100
            assiette_2_cents = int(round(l2 / factor / 100.0)) * 100
            n_prog = int(rng.integers(90, 240))
            promo_type = "TAUX_BOOSTE_LIVRET_MAISON"
            pcec = "602910"
            fname = f"{cid}_{reg_code}_TAUX_BOOSTE_LIVRET.pdf"
            line_items = [
                (
                    "Bonification d'intérêt Livret Maison (tranche principale)",
                    fmt_eur_space(assiette_1_cents),
                    f"+{boost_bps} bps × {dur_months}/12 mois",
                    l1,
                ),
                (
                    "Bonification d'intérêt Jeunes Actifs 18-32 ans",
                    fmt_eur_space(assiette_2_cents),
                    f"+{boost_bps} bps × {dur_months}/12 mois",
                    l2,
                ),
                (
                    "Prime forfaitaire d'activation versement programmé",
                    f"{n_prog} dossiers",
                    "Forfait campagne",
                    l3,
                ),
            ]
            welcome_bonus_eur = 0.0
            portfolio_aum_c = 0
            delegation_cap_c = 0

        elif tpl == "B":
            boost_bps = 0
            unit_cc_eur = int(rng.choice([80, 90, 100]))
            unit_mob_eur = int(rng.choice([50, 60]))
            qty_cc = max(10, int((total_c * 0.58) // (unit_cc_eur * 100)))
            l1 = qty_cc * unit_cc_eur * 100
            qty_mob = max(8, int((total_c * 0.26) // (unit_mob_eur * 100)))
            l2 = qty_mob * unit_mob_eur * 100
            l3 = total_c - l1 - l2
            qty_sav = max(12, int(l3 // 4500))
            promo_type = "PRIME_BIENVENUE_CONQUETE"
            pcec = "602920"
            fname = f"{cid}_{reg_code}_PRIME_BIENVENUE_JEUNES.pdf"
            line_items = [
                (
                    "PRM-CC1",
                    "Prime ouverture Compte Chèque CC_CHQ (18-32 ans)",
                    str(qty_cc),
                    f"{unit_cc_eur},00 EUR",
                    l1,
                ),
                (
                    "PRM-MOB",
                    "Bonus domiciliation salaire & mobilité SEPA",
                    str(qty_mob),
                    f"{unit_mob_eur},00 EUR",
                    l2,
                ),
                (
                    "PRM-SAV",
                    "Enveloppe couplée ouverture LDDS / parrainage digital",
                    str(qty_sav),
                    "Forfait lot",
                    l3,
                ),
            ]
            welcome_bonus_eur = float(unit_cc_eur)
            portfolio_aum_c = 0
            delegation_cap_c = 0

        else:
            boost_bps = 0
            welcome_bonus_eur = 0.0
            qty_card = max(8, int((total_c * 0.52) // 16_800))
            l1 = qty_card * 16_800
            qty_fee = max(10, int((total_c * 0.22) // 4_200))
            l2 = qty_fee * 4_200
            l3 = total_c - l1 - l2
            qty_ret = max(5, int(l3 // 25_000))
            portfolio_aum_c = int(rng.integers(11_500_000, 34_800_000)) * 100
            delegation_cap_c = int(rng.integers(110_000, 195_000)) * 100
            promo_type = "AVENANT_GRATUITE_RETENTION"
            pcec = "708590"
            fname = f"{cid}_{reg_code}_AVENANT_RETENTION.pdf"
            line_items = [
                (
                    "Exonération 12 mois cotisation Carte Visa Premier",
                    f"{qty_card} clients",
                    "168,00 EUR",
                    l1,
                ),
                (
                    "Rétrocession forfaitaire frais de tenue de compte",
                    f"{qty_fee} clients",
                    "42,00 EUR",
                    l2,
                ),
                (
                    "Prime contractuelle de maintien d'encours à 6 mois",
                    f"{qty_ret} dossiers",
                    "Barème pôle",
                    l3,
                ),
            ]

        assert l1 + l2 + l3 == total_c, f"Écart interne sur {cid}"

        specs.append(
            {
                "idx": k,
                "promo_contract_id": cid,
                "filename": fname,
                "template_code": tpl,
                "promo_type": promo_type,
                "region_code": reg_code,
                "region_name": reg_name,
                "primary_branch_code": prim["agency_code_4"],
                "primary_guichet_code": prim["guichet_code_5"],
                "primary_city": city,
                "branch_codes_label": branch_label,
                "pcec_account": pcec,
                "effective_date_iso": eff_date.isoformat(),
                "effective_date_fr": eff_date.strftime("%d/%m/%Y"),
                "end_date_iso": end_date.isoformat(),
                "end_date_fr": end_date.strftime("%d/%m/%Y"),
                "duration_months": dur_months,
                "boost_rate_bps": boost_bps,
                "welcome_bonus_eur": welcome_bonus_eur,
                "quarter_openings": q_cnt,
                "committed_cents": total_c,
                "committed_promo_cost_eur": round(total_c / 100.0, 2),
                "portfolio_aum_cents": portfolio_aum_c,
                "delegation_cap_cents": delegation_cap_c,
                "signer_name": signer,
                "controller_name": controller,
                "line_items": line_items,
            }
        )

    return specs


def generate_all_pdfs(output_raw_dir: Path) -> dict:
    t0 = time.perf_counter()
    print("[1/4] Chargement du socle partagé (shared_universe, seed=2026)...")
    universe = build_or_load_universe(force_rebuild=False)

    promo_dir = output_raw_dir / "PROMO_CONTRACTS_PDF"
    reg_dir = output_raw_dir / "REGULATORY_CFO_PDF"

    if promo_dir.exists():
        shutil.rmtree(promo_dir)
    if reg_dir.exists():
        shutil.rmtree(reg_dir)
    promo_dir.mkdir(parents=True, exist_ok=True)
    reg_dir.mkdir(parents=True, exist_ok=True)

    print("[2/4] Génération des 250 PDF d'avenants promotionnels réseau (-14 300 000,00 €)...")
    promo_specs = build_250_promo_specs(universe)
    for rec in promo_specs:
        pdf_path = promo_dir / rec["filename"]
        if rec["template_code"] == "A":
            render_promo_template_a(rec, pdf_path)
        elif rec["template_code"] == "B":
            render_promo_template_b(rec, pdf_path)
        else:
            render_promo_template_c(rec, pdf_path)

    print("[3/4] Génération des 6 PDF réglementaires & normatifs CFO (ANC / ALM / ILAAP / ACPR)...")
    reg_specs = get_regulatory_cfo_specs()
    for rdoc in reg_specs:
        render_regulatory_cfo_doc(rdoc, reg_dir / rdoc["filename"])

    # Sauvegarde de la table de vérité terrain (hors RAW/, dans data/universe/) pour contrôle automatique
    print("[4/4] Vérification stricte des invariants financiers & sauvegarde du contrôle interne...")
    gt_rows = [
        {k: v for k, v in rec.items() if k != "line_items"}
        for rec in promo_specs
    ]
    gt_df = pl.DataFrame(gt_rows)
    UNIVERSE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    gt_parquet = UNIVERSE_CACHE_DIR / "promo_pdfs_ground_truth.parquet"
    gt_df.write_parquet(gt_parquet)

    promo_files = sorted(promo_dir.glob("*.pdf"))
    reg_files = sorted(reg_dir.glob("*.pdf"))
    total_cents = int(gt_df["committed_cents"].sum())

    assert len(promo_files) == NUM_PROMO_PDFS, f"Attendu 250 PDF promo, trouvé {len(promo_files)}"
    assert len(reg_files) == 6, f"Attendu 6 PDF réglementaires, trouvé {len(reg_files)}"
    assert total_cents == TARGET_PROMO_COST_CENTS, (
        f"Invariant violé : {total_cents} centimes != {TARGET_PROMO_COST_CENTS}"
    )
    assert all(p.stat().st_size > 2_000 for p in promo_files + reg_files), "Fichier PDF vide détecté"

    by_tpl = (
        gt_df.group_by(["template_code", "promo_type"])
        .agg(
            pl.len().alias("pdf_count"),
            (pl.col("committed_cents").sum() / 100.0).round(2).alias("total_eur"),
        )
        .sort("template_code")
        .to_dicts()
    )

    elapsed = time.perf_counter() - t0
    summary = {
        "seed": DEMO_SEED,
        "promo_contracts_pdf_dir": str(promo_dir),
        "promo_pdf_count": len(promo_files),
        "committed_promo_cost_cents": total_cents,
        "committed_promo_cost_eur": f"{total_cents / 100:,.2f}",
        "pnb_cfo_impact_eur": f"-{total_cents / 100:,.2f}",
        "breakdown_by_template": by_tpl,
        "regulatory_cfo_pdf_dir": str(reg_dir),
        "regulatory_cfo_pdf_count": len(reg_files),
        "regulatory_cfo_files": [p.name for p in reg_files],
        "ground_truth_parquet": str(gt_parquet),
        "elapsed_seconds": round(elapsed, 2),
    }

    # Supprime l'éventuel dossier temporaire samples_pdf s'il existait
    samples_tmp = BASE_DIR / "output" / "samples_pdf"
    if samples_tmp.exists():
        shutil.rmtree(samples_tmp)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Génère les 250 PDF d'avenants agences (-14,30 M€) et les 6 PDF réglementaires CFO."
    )
    parser.add_argument(
        "--output-raw-dir",
        type=Path,
        default=DEFAULT_OUTPUT_RAW_DIR,
        help="Dossier racine RAW de sortie (défaut: 00_data_generator/output/RAW)",
    )
    args = parser.parse_args()
    generate_all_pdfs(args.output_raw_dir)


if __name__ == "__main__":
    main()
