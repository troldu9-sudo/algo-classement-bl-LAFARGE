"""Decodage des lignes de dematerialisation, socle de fiabilite de l'outil."""

from __future__ import annotations

from datetime import date

from src.entete_technique import decoder

# Lignes relevees telles quelles sur une facture Lafarge.
PAGE_FACTURE = (
    "@@@@@;92506;C281043473;1900200711;;;FA;1;2026-06-30;DJ;FR70;481,34;\n"
    "#####DEMAT-FJ;Electronique (ESI);EnvoiPDF;FAC;Facture;1;\n"
    "@@NM@;FR;;;;;vc_7tou4_fr@pdf.basware.com;;\n"
    "@@M1@;FRBD-10-40;1;C100038258;SOLETANCHE BACHY FR 92 RUEIL MALMAI;C281930566;;DJ;;\n"
    "FACTURE Nº1900200711\n"
)

PAGE_CONDITIONS = (
    "@@@@@;92506;C281043473;1900200711;;;CG;2;2026-06-30;DJ;FR70;481,34;\n"
    "CONDITIONS GENERALES DE VENTE\n"
)


def test_decode_une_page_de_facture():
    entete = decoder(PAGE_FACTURE)
    assert entete.numero_facture == "1900200711"
    assert entete.type_page == "FA"
    assert entete.index_page == "1"
    assert entete.date_facture == date(2026, 6, 30)
    assert entete.total_ttc == 481.34
    assert entete.code_postal == "92506"
    assert entete.code_client_interne == "C100038258"
    assert entete.nom_client == "SOLETANCHE BACHY FR 92 RUEIL MALMAI"
    assert entete.exploitable


def test_distingue_les_conditions_generales():
    """C'est ce marqueur qui permet d'ecarter les CGV sans les lire."""
    assert decoder(PAGE_CONDITIONS).type_page == "CG"


def test_page_sans_ligne_technique():
    entete = decoder("Un bon de livraison quelconque")
    assert not entete.exploitable
    assert entete.numero_facture == ""


def test_ligne_tronquee_ne_leve_pas():
    entete = decoder("@@@@@;92506;C281043473;\n")
    assert entete.numero_facture == ""
    assert entete.date_facture is None


def test_ordre_des_lignes_indifferent():
    """Selon la bibliotheque de lecture, la ligne technique ne sort pas toujours en premier."""
    melange = "\n".join(reversed(PAGE_FACTURE.splitlines()))
    assert decoder(melange).numero_facture == "1900200711"
