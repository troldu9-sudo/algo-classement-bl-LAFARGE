"""Rapprochement des PDF de bons de livraison presents dans le dossier.

Un bon est reconnu d'abord par le nom du fichier, ce qui ne coute rien, puis par son
contenu pour les fichiers restants. Les PDF de factures sont exclus de la recherche.
"""

from __future__ import annotations

from pathlib import Path

from . import lecture_pdf
from .formats import cle_comparaison
from .modeles import Facture


def _cle_fichier(chemin: Path) -> str:
    return cle_comparaison(chemin.stem)


def indexer(
    candidats: list[Path],
    bons_recherches: set[str],
    journal_erreurs: list[tuple[Path, str]] | None = None,
) -> dict[str, Path]:
    """Associe chaque numero de bon au PDF qui le porte.

    Un meme PDF peut couvrir plusieurs bons ; le premier fichier trouve l'emporte pour
    un numero donne, afin qu'un doublon ne change pas le resultat d'un passage a l'autre.
    """
    index: dict[str, Path] = {}
    if not bons_recherches:
        return index

    non_apparies = []
    for chemin in sorted(candidats):
        cle = _cle_fichier(chemin)
        trouves = [bon for bon in bons_recherches if bon and bon in cle]
        if trouves:
            for bon in trouves:
                index.setdefault(bon, chemin)
        else:
            non_apparies.append(chemin)

    restants = {bon for bon in bons_recherches if bon not in index}
    if not restants:
        return index

    for chemin in non_apparies:
        try:
            contenu = cle_comparaison(lecture_pdf.texte_complet(chemin))
        except Exception as err:  # PDF illisible ou protege : on le signale sans interrompre
            if journal_erreurs is not None:
                journal_erreurs.append((chemin, str(err)))
            continue
        for bon in sorted(restants):
            if bon in contenu:
                index.setdefault(bon, chemin)
        restants = {bon for bon in restants if bon not in index}
        if not restants:
            break
    return index


def rattacher(factures: list[Facture], index: dict[str, Path]) -> None:
    """Renseigne le PDF du bon sur chaque ligne de livraison qui en a un."""
    for facture in factures:
        for livraison in facture.livraisons:
            livraison.pdf_bon = index.get(livraison.n_bon)


def bons_recherches(factures: list[Facture]) -> set[str]:
    return {l.n_bon for f in factures for l in f.livraisons if l.n_bon}
