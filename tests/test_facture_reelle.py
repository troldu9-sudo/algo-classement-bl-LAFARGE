"""Controle sur de vraies factures Lafarge.

Ces tests ne s'executent que si des PDF ont ete deposes dans `tests/fixtures/reel/`.
Ce dossier est exclu du depot : une facture contient des donnees commerciales et des
coordonnees bancaires qui n'ont pas a etre publiees sur GitHub.

Pour les activer : copier une ou plusieurs factures dans ce dossier, puis relancer pytest.
"""

from __future__ import annotations

import pytest
from conftest import extraire_toutes, factures_reelles

from src.config import charger

FICHIERS = factures_reelles()
sans_facture = pytest.mark.skipif(
    not FICHIERS, reason="Aucun PDF dans tests/fixtures/reel/ (voir l'entete du fichier)."
)


@pytest.fixture
def config_reelle(tmp_path):
    return charger(dossier_force=tmp_path)


@sans_facture
@pytest.mark.parametrize("chemin", FICHIERS, ids=lambda p: p.name)
def test_une_facture_reelle_est_lisible(chemin, config_reelle):
    factures = extraire_toutes(chemin, config_reelle)
    assert factures, "Aucune facture reconnue dans ce PDF."
    for facture in factures:
        assert facture.numero, "Numero de facture introuvable."
        assert facture.date_facture is not None, "Date de facture introuvable."
        assert facture.livraisons, "Aucune ligne portant un N° Bon."


@sans_facture
@pytest.mark.parametrize("chemin", FICHIERS, ids=lambda p: p.name)
def test_les_totaux_d_une_facture_reelle_se_recoupent(chemin, config_reelle):
    for facture in extraire_toutes(chemin, config_reelle):
        somme = sum(l.montant_ht or 0 for l in facture.livraisons) + sum(
            a.montant_ht or 0 for a in facture.annexes
        )
        assert facture.total_ht is not None, "Total HT introuvable."
        assert abs(somme - facture.total_ht) <= 0.02, (
            f"Somme des lignes {somme:.2f} contre total HT {facture.total_ht:.2f}."
        )
        if facture.total_tva is not None and facture.total_ttc is not None:
            ecart = abs(facture.total_ht + facture.total_tva - facture.total_ttc)
            assert ecart <= 0.02, "HT + TVA ne donne pas le TTC."
