"""Regroupement des pages par facture et decoupage des PDF groupes."""

from __future__ import annotations

from datetime import date

from pypdf import PdfReader

from src import decoupe, lecture_pdf


def _blocs(chemin, config):
    return decoupe.grouper(lecture_pdf.lire(chemin, config), config)


def test_les_conditions_generales_sont_ecartees(dossier_demo, config_demo):
    blocs = _blocs(dossier_demo / "Facture_1900200711.pdf", config_demo)
    assert len(blocs) == 1
    assert blocs[0].numeros_pages == [1]
    assert blocs[0].pages_ignorees == [2]


def test_un_pdf_groupe_donne_une_facture_par_bloc(dossier_demo, config_demo):
    blocs = _blocs(dossier_demo / "Factures_groupees.pdf", config_demo)
    assert [b.numero for b in blocs] == ["1900300001", "1900300002", "1900300003"]
    assert [b.numeros_pages for b in blocs] == [[1], [3], [5]]
    assert [b.pages_ignorees for b in blocs] == [[2], [4], [6]]


def test_un_bon_de_livraison_ne_produit_aucun_bloc(dossier_demo, config_demo):
    """Sans numero de facture identifiable, le PDF n'est pas traite comme une facture."""
    assert _blocs(dossier_demo / "BL_CE293982.pdf", config_demo) == []


def test_ecriture_d_un_pdf_par_facture(dossier_demo, config_demo, tmp_path):
    source = dossier_demo / "Factures_groupees.pdf"
    blocs = _blocs(source, config_demo)
    destination = tmp_path / "sortie"

    cible = decoupe.ecrire(source, blocs[1], date(2026, 5, 11), destination)

    assert cible.name == "FACTURE_1900300002_2026-05-11.pdf"
    assert len(PdfReader(str(cible)).pages) == 1
    # Le PDF d'origine reste intact et a sa place.
    assert len(PdfReader(str(source)).pages) == 6


def test_le_pdf_decoupe_ne_contient_que_la_bonne_facture(dossier_demo, config_demo, tmp_path):
    source = dossier_demo / "Factures_groupees.pdf"
    blocs = _blocs(source, config_demo)
    cible = decoupe.ecrire(source, blocs[2], date(2026, 5, 12), tmp_path / "sortie")

    pages = lecture_pdf.lire(cible, config_demo)
    assert [p.entete.numero_facture for p in pages] == ["1900300003"]
    assert "CONDITIONS GENERALES" not in pages[0].texte
