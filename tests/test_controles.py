"""Controles de coherence : rien ne doit disparaitre en silence."""

from __future__ import annotations

from pathlib import Path

from conftest import extraire_une

from src import controles
from src.modeles import Facture, LigneLivraison, Resultat


def _categories(resultat: Resultat) -> list[str]:
    return [a.categorie for a in resultat.anomalies]


def _details(resultat: Resultat) -> str:
    return " | ".join(a.detail for a in resultat.anomalies)


def test_une_facture_coherente_ne_leve_rien(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    facture.livraisons[0].pdf_bon = Path("BL_CE293982.pdf")
    resultat = Resultat(factures=[facture])

    controles.appliquer(resultat, config_demo)

    assert resultat.anomalies == []


def test_somme_des_lignes_differente_du_total(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    facture.livraisons[0].montant_ht = 999.99
    resultat = Resultat(factures=[facture])

    controles.appliquer(resultat, config_demo)

    assert "Total" in _categories(resultat)
    assert "Somme des lignes" in _details(resultat)


def test_ht_plus_tva_different_du_ttc(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    facture.total_ttc = 500.00
    resultat = Resultat(factures=[facture])

    controles.appliquer(resultat, config_demo)

    assert "ne donne pas le TTC" in _details(resultat)


def test_ecart_avec_le_ttc_de_la_ligne_technique(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    facture.total_ttc_technique = 999.00
    resultat = Resultat(factures=[facture])

    controles.appliquer(resultat, config_demo)

    assert "ligne technique" in _details(resultat)


def test_un_ecart_sous_la_tolerance_est_admis(dossier_demo, config_demo):
    """Les arrondis au centime ne doivent pas polluer l'onglet « A verifier »."""
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    facture.livraisons[0].pdf_bon = Path("BL.pdf")
    facture.total_ttc = facture.total_ttc + 0.01
    resultat = Resultat(factures=[facture])

    controles.appliquer(resultat, config_demo)

    assert resultat.anomalies == []


def test_bon_sans_pdf_est_signale(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    resultat = Resultat(factures=[facture])

    controles.appliquer(resultat, config_demo)

    assert "Bon sans PDF" in _categories(resultat)


def test_facture_en_double(config_demo):
    doublon = [
        Facture(numero="1900200711", pdf_source=Path("a.pdf"), livraisons=[LigneLivraison()]),
        Facture(numero="1900200711", pdf_source=Path("b.pdf"), livraisons=[LigneLivraison()]),
    ]
    resultat = Resultat(factures=doublon)

    controles.appliquer(resultat, config_demo)

    assert "Doublon" in _categories(resultat)
    assert "a.pdf, b.pdf" in _details(resultat)


def test_bon_orphelin_present_dans_le_dossier(config_demo):
    resultat = Resultat(factures=[], pdf_bons={"CE999999": Path("BL_CE999999.pdf")})

    controles.appliquer(resultat, config_demo)

    assert "Bon orphelin" in _categories(resultat)


def test_facture_sans_aucune_ligne(config_demo):
    resultat = Resultat(factures=[Facture(numero="1900200711", pdf_source=Path("x.pdf"))])

    controles.appliquer(resultat, config_demo)

    assert "Aucune ligne portant un N° Bon" in _details(resultat)


def test_sous_total_de_chantier_incoherent(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200712_multi-chantiers.pdf", config_demo)
    facture.chantiers[0].sous_total_ht = 1.00
    resultat = Resultat(factures=[facture])

    controles.appliquer(resultat, config_demo)

    assert "sous-total" in _details(resultat)
