"""Conversion des valeurs au format francais."""

from __future__ import annotations

from datetime import date

import pytest

from src.formats import (
    cle_comparaison,
    date_fr,
    date_iso,
    date_livraison,
    nombre_fr,
    normaliser_bon,
    quantite_unite,
)


@pytest.mark.parametrize(
    "texte, attendu",
    [
        ("165,80", 165.80),
        ("481,34", 481.34),
        # Separateurs de milliers rencontres dans les PDF Lafarge.
        ("2 538,56", 2538.56),
        ("1 845,56", 1845.56),
        ("38 465 394,00", 38465394.0),
        ("401,12 €", 401.12),
        ("481,34 EUR", 481.34),
        ("-12,50", -12.50),
        ("1.234,56", 1234.56),
        ("", None),
        ("   ", None),
        (None, None),
        ("Page", None),
    ],
)
def test_nombre_fr(texte, attendu):
    assert nombre_fr(texte) == attendu


def test_date_fr_et_iso():
    assert date_fr("du 30/06/2026") == date(2026, 6, 30)
    assert date_iso("2026-06-30") == date(2026, 6, 30)
    assert date_fr("32/13/2026") is None


def test_date_livraison_prend_l_annee_de_la_facture():
    assert date_livraison("16/06", date(2026, 6, 30)) == date(2026, 6, 16)


def test_date_livraison_bascule_sur_l_annee_precedente():
    """Une livraison de decembre facturee en janvier appartient a l'annee d'avant."""
    assert date_livraison("28/12", date(2026, 1, 15)) == date(2025, 12, 28)


def test_date_livraison_complete_est_conservee():
    assert date_livraison("16/06/2024", date(2026, 6, 30)) == date(2024, 6, 16)


@pytest.mark.parametrize(
    "texte, quantite, unite",
    [
        ("1,500M3", 1.5, "M3"),
        ("1Pce", 1.0, "Pce"),
        ("12,000M3", 12.0, "M3"),
        ("1 250,500M3", 1250.5, "M3"),
        ("", None, ""),
    ],
)
def test_quantite_unite(texte, quantite, unite):
    assert quantite_unite(texte) == (quantite, unite)


@pytest.mark.parametrize(
    "texte, cle, variante",
    [
        ("CE 293982(F65)", "CE293982", "F65"),
        ("CE293982", "CE293982", ""),
        ("ce 293982 (f65)", "CE293982", "f65"),
        ("", "", ""),
    ],
)
def test_normaliser_bon(texte, cle, variante):
    assert normaliser_bon(texte) == (cle, variante)


def test_cle_comparaison_ignore_accents_et_ponctuation():
    assert cle_comparaison("Génie-Civil C35/45") == "GENIECIVILC3545"
