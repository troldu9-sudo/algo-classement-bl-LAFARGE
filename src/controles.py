"""Controles de coherence.

Rien n'est ecarte en silence : ce qui n'a pas pu etre lu ou ne se recoupe pas doit
apparaitre dans l'onglet « A verifier » plutot que de manquer discretement dans un total.
"""

from __future__ import annotations

from collections import defaultdict

from .config import Config
from .modeles import Facture, Resultat


def _ecart(gauche: float | None, droite: float | None, tolerance: float) -> float | None:
    """Ecart absolu entre deux montants, ou None si la comparaison n'a pas de sens."""
    if gauche is None or droite is None:
        return None
    difference = abs(gauche - droite)
    return difference if difference > tolerance else None


def _euros(valeur: float | None) -> str:
    return "absent" if valeur is None else f"{valeur:.2f} €"


def _controler_facture(facture: Facture, resultat: Resultat, config: Config) -> None:
    tolerance = config.tolerance_totaux
    reference = facture.numero or (facture.pdf_source.name if facture.pdf_source else "?")
    fichier = facture.pdf_source.name if facture.pdf_source else ""

    for message in facture.anomalies:
        resultat.signaler("Lecture", reference, message, fichier)

    if not facture.numero:
        resultat.signaler("Lecture", reference, "Numero de facture introuvable.", fichier)
    if facture.date_facture is None:
        resultat.signaler("Lecture", reference, "Date de facture introuvable.", fichier)
    if not facture.livraisons:
        resultat.signaler(
            "Lecture", reference, "Aucune ligne portant un N° Bon n'a ete trouvee.", fichier
        )

    somme_lignes = sum(
        l.montant_ht for l in facture.livraisons if l.montant_ht is not None
    ) + sum(a.montant_ht for a in facture.annexes if a.montant_ht is not None)
    ecart = _ecart(somme_lignes, facture.total_ht, tolerance)
    if ecart is not None:
        resultat.signaler(
            "Total",
            reference,
            f"Somme des lignes {_euros(somme_lignes)} contre total HT {_euros(facture.total_ht)} "
            f"(ecart {ecart:.2f} €).",
            fichier,
        )

    somme_quantites = sum(
        l.quantite for l in facture.livraisons if l.quantite is not None and l.unite.upper() == "M3"
    )
    ecart = _ecart(somme_quantites, facture.volume_total, tolerance)
    if ecart is not None:
        resultat.signaler(
            "Total",
            reference,
            f"Somme des quantites livrees {somme_quantites:.3f} m³ contre volume total "
            f"{facture.volume_total:.3f} m³ (ecart {ecart:.3f}).",
            fichier,
        )

    if facture.total_ht is not None and facture.total_tva is not None:
        ecart = _ecart(facture.total_ht + facture.total_tva, facture.total_ttc, tolerance)
        if ecart is not None:
            resultat.signaler(
                "Total",
                reference,
                f"HT {_euros(facture.total_ht)} + TVA {_euros(facture.total_tva)} ne donne pas "
                f"le TTC {_euros(facture.total_ttc)} (ecart {ecart:.2f} €).",
                fichier,
            )

    ecart = _ecart(facture.total_ttc, facture.total_ttc_technique, tolerance)
    if ecart is not None:
        resultat.signaler(
            "Total",
            reference,
            f"TTC imprime {_euros(facture.total_ttc)} contre TTC de la ligne technique "
            f"{_euros(facture.total_ttc_technique)} (ecart {ecart:.2f} €).",
            fichier,
        )

    for chantier in facture.chantiers:
        lignes = [l for l in facture.livraisons if l.chantier_code == chantier.code]
        annexes = [a for a in facture.annexes if a.chantier_code == chantier.code]
        somme = sum(l.montant_ht for l in lignes if l.montant_ht is not None) + sum(
            a.montant_ht for a in annexes if a.montant_ht is not None
        )
        ecart = _ecart(somme, chantier.sous_total_ht, tolerance)
        if ecart is not None:
            resultat.signaler(
                "Total",
                reference,
                f"Chantier {chantier.intitule} : somme des lignes {_euros(somme)} contre "
                f"sous-total {_euros(chantier.sous_total_ht)} (ecart {ecart:.2f} €).",
                fichier,
            )

    # Un meme bon couvre parfois plusieurs lignes de produit : il ne doit etre
    # signale qu'une fois.
    deja_signales: set[str] = set()
    for livraison in facture.livraisons:
        if livraison.pdf_bon is None and livraison.n_bon not in deja_signales:
            deja_signales.add(livraison.n_bon)
            resultat.signaler(
                "Bon sans PDF",
                reference,
                f"Aucun PDF trouve pour le bon {livraison.n_bon}.",
                fichier,
            )
        if livraison.montant_ht is None:
            resultat.signaler(
                "Lecture",
                reference,
                f"Bon {livraison.n_bon} : montant HT illisible.",
                fichier,
            )


def _controler_doublons(factures: list[Facture], resultat: Resultat) -> None:
    par_numero: dict[str, list[Facture]] = defaultdict(list)
    for facture in factures:
        if facture.numero:
            par_numero[facture.numero].append(facture)
    for numero, groupe in sorted(par_numero.items()):
        if len(groupe) > 1:
            sources = ", ".join(sorted({f.pdf_source.name for f in groupe if f.pdf_source}))
            resultat.signaler(
                "Doublon",
                numero,
                f"Cette facture apparait {len(groupe)} fois : {sources}.",
            )


def _controler_bons_orphelins(resultat: Resultat, index_utilise: set) -> None:
    for cle, chemin in sorted(resultat.pdf_bons.items()):
        if cle not in index_utilise:
            resultat.signaler(
                "Bon orphelin",
                "",
                f"Le bon {cle} a ete trouve dans le dossier mais n'apparait sur aucune facture.",
                chemin.name,
            )


def appliquer(resultat: Resultat, config: Config) -> None:
    """Passe tous les controles et remplit la liste des anomalies."""
    for facture in resultat.factures:
        _controler_facture(facture, resultat, config)
    _controler_doublons(resultat.factures, resultat)
    utilises = {l.n_bon for f in resultat.factures for l in f.livraisons if l.n_bon}
    _controler_bons_orphelins(resultat, utilises)
