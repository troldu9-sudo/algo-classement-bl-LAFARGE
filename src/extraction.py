"""Extraction des donnees d'une facture Lafarge.

Le tableau est lu par bornes de colonnes plutot que par expressions regulieres sur du
texte reconstitue : les colonnes de nombres sont alignees a droite dans le PDF, si bien
qu'un montant a cinq chiffres ne peut pas deborder sur la colonne voisine.
"""

from __future__ import annotations

import re
from pathlib import Path

from .config import Config
from .decoupe import BlocFacture
from .formats import date_fr, date_livraison, decomposer_bon, nombre_fr, quantite_unite
from .modeles import Chantier, Facture, Ligne, LigneAnnexe, LigneLivraison, LigneTva, Page

# Lignes d'habillage a ne jamais confondre avec des lignes de tableau.
_BRUIT = re.compile(r"^(@@|#####|Page\s+\d+\s*/\s*\d+\s*$)")



def _lignes_du_tableau(page: Page, deja_dans_tableau: bool) -> list[Ligne]:
    """Isole les lignes de tableau d'une page, en ecartant l'en-tete et le pied.

    L'en-tete de colonnes est repete sur chaque page du detail : sa position sert de
    frontiere. A defaut, une page de continuation est prise en entier, le bruit connu
    etant filtre ligne a ligne.
    """
    seuil: float | None = None
    for ligne in page.lignes:
        texte = ligne.texte
        if "N°" in texte and "Bon" in texte and "Libell" in texte:
            seuil = ligne.haut
            break
    if seuil is None:
        if not deja_dans_tableau:
            return []
        seuil = 0.0
    return [l for l in page.lignes if l.haut > seuil and not _BRUIT.match(l.texte.strip())]


def _entete(bloc: BlocFacture, config: Config, facture: Facture) -> None:
    """Renseigne les champs d'en-tete, la ligne technique primant sur la mise en page."""
    premiere = bloc.pages[0]
    technique = premiere.entete
    texte = premiere.texte

    facture.numero = technique.numero_facture
    if not facture.numero:
        trouve = config.motif("numero_facture").search(texte)
        facture.numero = trouve.group(1) if trouve else ""
        if facture.numero:
            facture.signaler("Numero lu sur la mise en page : ligne technique absente.")

    facture.date_facture = technique.date_facture
    if facture.date_facture is None:
        trouve = config.motif("date_facture").search(texte)
        facture.date_facture = date_fr(trouve.group(1)) if trouve else None

    trouve = config.motif("date_echeance").search(texte)
    facture.date_echeance = date_fr(trouve.group(1)) if trouve else None

    trouve = config.motif("agence").search(texte)
    facture.agence = trouve.group(1).strip() if trouve else ""

    trouve = config.motif("code_client").search(texte)
    facture.code_client = trouve.group(1).strip() if trouve else ""

    facture.nom_client = technique.nom_client
    facture.total_ttc_technique = technique.total_ttc

    if technique.type_page and technique.type_page != "FA":
        facture.signaler(f"Type de page inhabituel : « {technique.type_page} ».")
    for type_inconnu in dict.fromkeys(bloc.types_inconnus):
        facture.signaler(f"Type de page inhabituel : « {type_inconnu} ».")


def _totaux_visuels(bloc: BlocFacture, config: Config, facture: Facture) -> None:
    """Lit le total TTC imprime, qui sert de contre-verification a la ligne technique."""
    for page in bloc.pages:
        trouve = config.motif("total_ttc").search(page.texte)
        if trouve:
            facture.total_ttc = nombre_fr(trouve.group(1))
            return


def _recapitulatif_tva(ligne: Ligne) -> LigneTva | None:
    """Lit une ligne du recapitulatif : code, taux, montant HT, montant TVA, montant TTC.

    Le recapitulatif a ses propres colonnes, sans rapport avec celles du tableau de
    livraisons : il est ventile a part.
    """
    valeurs = {
        nom: nombre_fr(ligne.cellule_recap(nom))
        for nom in ("taux", "montant_ht", "montant_tva", "montant_ttc")
    }
    if any(valeur is None for valeur in valeurs.values()):
        return None
    return LigneTva(code=ligne.cellule_recap("code").strip(), **valeurs)


def _livraison(
    ligne: Ligne,
    facture: Facture,
    chantier: Chantier,
    libelle: str,
    numero: str,
    variante: str,
) -> LigneLivraison:
    quantite, unite = quantite_unite(ligne.cellule("quantite"))
    return LigneLivraison(
        n_bon_brut=ligne.cellule("n_bon").strip(),
        n_bon=numero,
        variante=variante,
        date_livraison=date_livraison(ligne.cellule("date_livraison"), facture.date_facture),
        site_expediteur=ligne.cellule("site_expediteur").strip(),
        libelle=libelle,
        quantite=quantite,
        unite=unite,
        prix_unitaire=nombre_fr(ligne.cellule("prix_unitaire")),
        montant_ht=nombre_fr(ligne.cellule("montant_ht")),
        code_tva=ligne.cellule("code_tva").strip(),
        poids_co2=ligne.cellule("poids_co2").strip(),
        reduction_co2=ligne.cellule("reduction_co2").strip(),
        classe_gwr=ligne.cellule("classe_gwr").strip(),
        chantier_code=chantier.code,
        chantier_nom=chantier.nom,
    )


def _annexe(ligne: Ligne, chantier: Chantier, libelle: str) -> LigneAnnexe:
    quantite, unite = quantite_unite(ligne.cellule("quantite"))
    return LigneAnnexe(
        libelle=libelle,
        quantite=quantite,
        unite=unite,
        prix_unitaire=nombre_fr(ligne.cellule("prix_unitaire")),
        montant_ht=nombre_fr(ligne.cellule("montant_ht")),
        code_tva=ligne.cellule("code_tva").strip(),
        chantier_code=chantier.code,
        chantier_nom=chantier.nom,
    )


def extraire(bloc: BlocFacture, config: Config, source: Path) -> Facture:
    """Construit une facture complete a partir des pages qui la composent."""
    facture = Facture(pdf_source=source, pages_source=bloc.numeros_pages)
    _entete(bloc, config, facture)
    _totaux_visuels(bloc, config, facture)

    motif_chantier = config.motif("chantier")
    motif_sous_total = config.motif("sous_total")
    motif_total = config.motif("total_general")
    motif_recap = config.motif("entete_recap_tva")
    motif_adresse = config.motif("adresse")

    chantier: Chantier | None = None
    tampon_libelle = ""
    attente_adresse = False
    dans_recapitulatif = False
    tableau_termine = False

    for page in bloc.pages:
        for ligne in _lignes_du_tableau(page, chantier is not None):
            texte = ligne.texte.strip()
            libelle_cellule = ligne.cellule("libelle").strip()

            if motif_recap.search(texte):
                dans_recapitulatif = True
                tableau_termine = True
                continue

            if dans_recapitulatif:
                taux = _recapitulatif_tva(ligne)
                if taux:
                    facture.taux_tva.append(taux)
                elif facture.taux_tva:
                    dans_recapitulatif = False
                continue

            trouve = motif_chantier.match(libelle_cellule)
            if trouve:
                chantier = Chantier(code=(trouve.group(1) or "").strip(), nom=trouve.group(2).strip())
                facture.chantiers.append(chantier)
                tampon_libelle = ""
                attente_adresse = True
                continue

            if chantier is None or tableau_termine:
                continue

            if motif_sous_total.match(libelle_cellule):
                chantier.sous_total_quantite = quantite_unite(ligne.cellule("quantite"))[0]
                chantier.sous_total_ht = nombre_fr(ligne.cellule("montant_ht"))
                tampon_libelle = ""
                attente_adresse = False
                continue

            if motif_total.match(libelle_cellule):
                facture.volume_total, facture.unite_volume = quantite_unite(ligne.cellule("quantite"))
                facture.total_ht = nombre_fr(ligne.cellule("montant_ht"))
                tampon_libelle = ""
                tableau_termine = True
                continue

            montant = nombre_fr(ligne.cellule("montant_ht"))
            # Le prefixe de centrale et le texte accole au numero sont ecartes ici : seul
            # le numero de bon compte, le reste rejoint le libelle de la ligne.
            numero, variante, complement = decomposer_bon(
                ligne.cellule("n_bon"), config.longueur_min_numero_bon
            )
            libelle = " ".join(
                p for p in (tampon_libelle, libelle_cellule, complement) if p
            ).strip()

            if montant is not None and (numero or libelle):
                if numero:
                    facture.livraisons.append(
                        _livraison(ligne, facture, chantier, libelle, numero, variante)
                    )
                else:
                    facture.annexes.append(_annexe(ligne, chantier, libelle))
                tampon_libelle = ""
                attente_adresse = False
                continue

            if not libelle_cellule:
                continue

            est_adresse = (
                attente_adresse
                and motif_adresse.match(libelle_cellule)
                and len(chantier.adresse) < config.lignes_adresse_max
            )
            if est_adresse:
                chantier.adresse.append(libelle_cellule)
            else:
                attente_adresse = False
                tampon_libelle = " ".join(p for p in (tampon_libelle, libelle_cellule) if p).strip()

    if facture.taux_tva:
        facture.total_tva = sum(t.montant_tva for t in facture.taux_tva if t.montant_tva is not None)
        if facture.total_ht is None:
            facture.total_ht = sum(
                t.montant_ht for t in facture.taux_tva if t.montant_ht is not None
            )
    if facture.total_ttc is None:
        facture.total_ttc = facture.total_ttc_technique

    return facture
