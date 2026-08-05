"""Rapprochement des PDF de bons de livraison."""

from __future__ import annotations

from conftest import extraire_une

from src import appariement, demo


def test_rapprochement_par_nom_de_fichier(dossier_demo):
    """`BL_CE293982.pdf` porte le numero dans son nom : aucune lecture n'est necessaire."""
    index = appariement.indexer([dossier_demo / "BL_CE293982.pdf"], {"293982"})
    assert index["293982"].name == "BL_CE293982.pdf"


def test_rapprochement_par_contenu(dossier_demo):
    """Ce fichier ne porte aucun numero dans son nom : il faut lire son contenu."""
    index = appariement.indexer([dossier_demo / "Bon-de-livraison-juillet.pdf"], {"294100"})
    assert index["294100"].name == "Bon-de-livraison-juillet.pdf"


def test_un_bon_absent_reste_absent(dossier_demo):
    index = appariement.indexer([dossier_demo / "BL_CE293982.pdf"], {"999999"})
    assert index == {}


def test_aucun_bon_recherche_evite_toute_lecture(dossier_demo):
    assert appariement.indexer(list(dossier_demo.glob("*.pdf")), set()) == {}


def test_fichier_illisible_est_signale_sans_interrompre(dossier_demo, tmp_path):
    """Le numero cherche n'est pas dans les noms de fichiers : il faut lire les contenus,
    et un fichier abime rencontre en chemin ne doit pas arreter la recherche."""
    casse = tmp_path / "abime.pdf"
    casse.write_bytes(b"ceci n'est pas un PDF")
    bon = tmp_path / "zz_bon.pdf"
    bon.write_bytes((dossier_demo / "Bon-de-livraison-juillet.pdf").read_bytes())
    erreurs = []

    index = appariement.indexer([casse, bon], {"294100"}, erreurs)

    assert index["294100"] == bon
    assert [chemin.name for chemin, _ in erreurs] == ["abime.pdf"]


def test_rattachement_sur_les_lignes_de_facture(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    index = appariement.indexer([dossier_demo / "BL_CE293982.pdf"], {"293982"})

    appariement.rattacher([facture], index)

    assert facture.livraisons[0].pdf_bon.name == "BL_CE293982.pdf"


def test_liste_des_bons_a_rechercher(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200712_multi-chantiers.pdf", config_demo)
    assert appariement.bons_recherches([facture]) == {"294100", "294101", "294250"}


def test_variante_de_formatage_du_numero(dossier_demo, tmp_path):
    """Le numero doit etre retrouve quel que soit son formatage dans le fichier."""
    fichier = tmp_path / "BL - ce 293982.pdf"
    fichier.write_bytes(demo.bon_de_livraison("CE 293982(F65)", "1900200711", 1.5))
    assert appariement.indexer([fichier], {"293982"})["293982"] == fichier
