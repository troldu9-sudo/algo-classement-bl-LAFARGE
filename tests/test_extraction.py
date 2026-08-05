"""Extraction des champs d'une facture.

Les valeurs attendues de `facture_simple` reprennent celles de la facture 1900200711
reellement emise par Lafarge, y compris ses arrondis.
"""

from __future__ import annotations

from datetime import date

from conftest import extraire_une

from src import demo


def test_entete_de_facture(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    assert facture.numero == "1900200711"
    assert facture.date_facture == date(2026, 6, 30)
    assert facture.date_echeance == date(2026, 8, 14)
    assert facture.agence == "AG OCCITANIE LB"
    assert facture.code_client == "367478"
    assert facture.nom_client == "SOLETANCHE BACHY FR 92 RUEIL MALMAI"


def test_totaux_de_facture(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    assert facture.total_ht == 401.12
    assert facture.total_tva == 80.22
    assert facture.total_ttc == 481.34
    assert facture.total_ttc_technique == 481.34
    assert facture.volume_total == 1.5
    assert facture.unite_volume == "M3"


def test_recapitulatif_de_tva(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    assert len(facture.taux_tva) == 1
    taux = facture.taux_tva[0]
    assert (taux.code, taux.taux) == ("1", 20.0)
    assert (taux.montant_ht, taux.montant_tva, taux.montant_ttc) == (401.12, 80.22, 481.34)


def test_chantier_et_son_adresse(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    assert len(facture.chantiers) == 1
    chantier = facture.chantiers[0]
    assert (chantier.code, chantier.nom) == ("PBL", "PUITS BALANSA")
    assert chantier.adresse == ["25 Avenue Benjamin Balansa", "31500 Toulouse"]
    assert chantier.sous_total_ht == 401.12
    assert chantier.sous_total_quantite == 1.5


def test_ligne_de_livraison(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    assert len(facture.livraisons) == 1
    ligne = facture.livraisons[0]
    assert ligne.n_bon_brut == "CE 293982(F65)"
    assert ligne.n_bon == "293982"
    assert ligne.variante == "F65"
    assert ligne.date_livraison == date(2026, 6, 16)
    assert ligne.site_expediteur == "LARRIEU"
    assert ligne.quantite == 1.5
    assert ligne.unite == "M3"
    assert ligne.prix_unitaire == 165.80
    assert ligne.montant_ht == 248.70
    assert ligne.code_tva == "1"
    assert ligne.chantier_code == "PBL"


def test_libelle_reconstitue_depuis_la_ligne_precedente(dossier_demo, config_demo):
    """La designation du produit est imprimee au-dessus de la ligne qui porte le bon."""
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    assert facture.livraisons[0].libelle == "D2B10 Agilia Génie-Civil C35/45 D16 SF2 XA2 SRPM"


def test_indicateurs_environnementaux(dossier_demo, config_demo):
    ligne = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo).livraisons[0]
    assert ligne.poids_co2 == "401"
    assert ligne.reduction_co2 == "0 - 9"
    assert ligne.classe_gwr == "GWR0"


def test_lignes_annexes_sans_numero_de_bon(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200711.pdf", config_demo)
    libelles = [a.libelle for a in facture.annexes]
    assert libelles == [
        "Forfait Livraison en 8x4 / Jour",
        "CONTRIBUTION ENVIRONEMENTALE METRO LOT 4",
        "CONTRIBUTION CLIMAT ENERGIE METRO",
    ]
    assert [a.montant_ht for a in facture.annexes] == [142.50, 3.20, 6.72]
    assert facture.annexes[0].unite == "Pce"


def test_plusieurs_chantiers_et_plusieurs_taux(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200712_multi-chantiers.pdf", config_demo)
    assert [c.code for c in facture.chantiers] == ["PBL", "GAR"]
    assert len(facture.livraisons) == 3
    assert {l.chantier_code for l in facture.livraisons} == {"PBL", "GAR"}
    assert sorted(t.code for t in facture.taux_tva) == ["1", "2"]
    assert {t.taux for t in facture.taux_tva} == {20.0, 10.0}


def test_montant_superieur_a_mille(dossier_demo, config_demo):
    """Le separateur de milliers coupe le nombre en deux mots : il doit etre recolle."""
    facture = extraire_une(dossier_demo / "Facture_1900200712_multi-chantiers.pdf", config_demo)
    ligne = next(l for l in facture.livraisons if l.n_bon == "294250")
    assert ligne.quantite == 12.0
    assert ligne.prix_unitaire == 138.40
    assert ligne.montant_ht == 1660.80
    assert facture.total_ht == 3538.56


def test_livraison_de_decembre_facturee_plus_tard(dossier_demo, config_demo):
    facture = extraire_une(dossier_demo / "Facture_1900200712_multi-chantiers.pdf", config_demo)
    ligne = next(l for l in facture.livraisons if l.n_bon == "294101")
    assert ligne.date_livraison == date(2025, 12, 28)


def test_les_totaux_extraits_recoupent_les_donnees_d_origine(dossier_demo, config_demo):
    """Verification croisee : ce qui est lu doit egaler ce que la facture d'essai contient."""
    modele = demo.facture_multi_chantiers()
    facture = extraire_une(dossier_demo / "Facture_1900200712_multi-chantiers.pdf", config_demo)
    assert facture.total_ht == modele.total_ht
    assert facture.total_ttc == modele.total_ttc
    assert facture.volume_total == modele.volume
    assert len(facture.livraisons) == sum(len(c.lignes) for c in modele.chantiers)


def test_un_bon_de_livraison_n_est_pas_pris_pour_une_facture(dossier_demo, config_demo):
    from conftest import extraire_toutes

    assert extraire_toutes(dossier_demo / "BL_CE293982.pdf", config_demo) == []


def test_le_numero_de_bon_est_debarrasse_du_prefixe_et_du_texte_accole(
    dossier_demo, config_demo
):
    """Seul le numero est retenu : ni le prefixe de centrale, ni le libelle accole."""
    facture = extraire_une(dossier_demo / "Facture_1900200713_numeros-bruites.pdf", config_demo)
    assert [l.n_bon for l in facture.livraisons] == [
        "123482",
        "147375",
        "244892",
        "158022",
        "184047",
        "158010",
    ]


def test_aucun_numero_de_bon_ne_contient_de_lettre(dossier_demo, config_demo):
    from conftest import extraire_toutes

    for pdf in sorted(dossier_demo.glob("Facture*.pdf")):
        for facture in extraire_toutes(pdf, config_demo):
            for ligne in facture.livraisons:
                assert ligne.n_bon.isdigit(), f"{pdf.name} : {ligne.n_bon!r}"


def test_le_texte_accole_au_numero_rejoint_le_libelle(dossier_demo, config_demo):
    """Ce qui est retire du N° Bon n'est pas perdu : il appartient au libelle de la ligne."""
    facture = extraire_une(dossier_demo / "Facture_1900200713_numeros-bruites.pdf", config_demo)
    libelles = {l.n_bon: l.libelle for l in facture.livraisons}
    assert libelles["123482"] == "D2B10 Agilia C35/45 Retour"
    assert libelles["158022"] == "D2B16 Chape fluide PM3"
    assert libelles["184047"] == "D2B18 Mortier de montage"


def test_les_totaux_restent_justes_malgre_les_numeros_bruites(dossier_demo, config_demo):
    modele = demo.facture_numeros_bruites()
    facture = extraire_une(dossier_demo / "Facture_1900200713_numeros-bruites.pdf", config_demo)
    assert facture.total_ht == modele.total_ht
    assert facture.volume_total == modele.volume
