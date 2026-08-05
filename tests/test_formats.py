"""Conversion des valeurs au format francais."""

from __future__ import annotations

from datetime import date

import pytest

from src.formats import (
    cle_comparaison,
    date_fr,
    date_iso,
    date_livraison,
    decomposer_bon,
    nombre_fr,
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
    "texte, numero, variante, complement",
    [
        # Formes relevees sur les factures reelles : prefixe de centrale et debut de
        # libelle accoles au numero.
        ("CE 293982(F65)", "293982", "F65", ""),
        ("CE 123482Retour", "123482", "", "Retour"),
        ("CE 124361Retour", "124361", "", "Retour"),
        ("147375PHeure", "147375", "", "PHeure"),
        ("153013Heure", "153013", "", "Heure"),
        ("CE 157594LOT", "157594", "", "LOT"),
        ("CE 244892Annulati", "244892", "", "Annulati"),
        ("CE 286803M3", "286803", "", "M3"),
        ("158010A7", "158010", "", "A7"),
        ("158022R4", "158022", "", "R4"),
        ("158022PM3", "158022", "", "PM3"),
        ("CE 161574PM3", "161574", "", "PM3"),
        # Numero deja propre.
        ("184047", "184047", "", ""),
        ("208720", "208720", "", ""),
        # Aucun numero : la cellule n'apporte qu'un fragment de libelle.
        ("Retour", "", "", "Retour"),
        ("", "", "", ""),
        (None, "", "", ""),
    ],
)
def test_decomposer_bon(texte, numero, variante, complement):
    assert decomposer_bon(texte) == (numero, variante, complement)


def test_decomposer_bon_ignore_les_chiffres_d_un_code_accole():
    """`M3` contient un 3 : il ne doit jamais etre pris pour le numero de bon."""
    assert decomposer_bon("CE 286803M3")[0] == "286803"
    assert decomposer_bon("158022PM3")[0] == "158022"


def test_decomposer_bon_retient_le_plus_long_groupe_si_aucun_n_est_assez_long():
    """Plutot qu'un numero vide, on garde le meilleur candidat disponible."""
    assert decomposer_bon("CE 42R4", longueur_min=6)[0] == "42"


def test_cle_comparaison_ignore_accents_et_ponctuation():
    assert cle_comparaison("Génie-Civil C35/45") == "GENIECIVILC3545"
