"""Lecture d'un PDF : texte, mots positionnes, regroupement en lignes et en colonnes."""

from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from . import entete_technique
from .config import Config
from .modeles import Ligne, Mot, Page


def _grouper_en_lignes(mots: list[Mot], tolerance: float) -> list[Ligne]:
    """Regroupe les mots par ordonnee.

    La tolerance rattrape les elements legerement decales : sur les factures Lafarge le
    code TVA est imprime 1 a 2 points au-dessus du reste de sa ligne.
    """
    lignes: list[Ligne] = []
    for mot in sorted(mots, key=lambda m: (m.haut, m.x0)):
        if lignes and abs(mot.haut - lignes[-1].haut) <= tolerance:
            lignes[-1].mots.append(mot)
        else:
            lignes.append(Ligne(haut=mot.haut, mots=[mot]))
    return lignes


_FRAGMENT_MILLIERS = re.compile(r"^\d{1,3}$")


def _recoller_milliers(
    attribution: list[list], seuil: float
) -> None:
    """Rattache a sa colonne le debut d'un nombre coupe par un separateur de milliers.

    `2 538,56` ressort en deux mots ; sans ce recollage, le `2` tombe dans la colonne
    voisine et le montant devient 538,56. Le parcours va de droite a gauche pour traiter
    aussi les nombres a plusieurs groupes, comme `1 234 567,89`.
    """
    for index in range(len(attribution) - 2, -1, -1):
        mot, colonne = attribution[index]
        suivant, colonne_suivante = attribution[index + 1]
        if colonne_suivante is None or colonne is colonne_suivante:
            continue
        if colonne_suivante.repere != "droite":
            continue
        if suivant.x0 - mot.x1 > seuil:
            continue
        if not _FRAGMENT_MILLIERS.match(mot.texte) or not suivant.texte[:1].isdigit():
            continue
        attribution[index][1] = colonne_suivante


def _ventiler(ligne: Ligne, colonnes: list, seuil: float) -> dict[str, str]:
    """Range chaque mot dans sa colonne, d'apres sa position horizontale."""
    attribution: list[list] = []
    for mot in sorted(ligne.mots, key=lambda m: m.x0):
        colonne = next((c for c in colonnes if c.contient(mot.x0, mot.x1)), None)
        attribution.append([mot, colonne])
    _recoller_milliers(attribution, seuil)

    cellules: dict[str, list[str]] = {}
    for mot, colonne in attribution:
        if colonne is not None:
            cellules.setdefault(colonne.nom, []).append(mot.texte)
    return {nom: " ".join(mots) for nom, mots in cellules.items()}


def _ventiler_en_colonnes(ligne: Ligne, config: Config) -> None:
    ligne.cellules = _ventiler(ligne, config.colonnes, config.seuil_fusion_nombre)
    ligne.cellules_recap = _ventiler(
        ligne, config.colonnes_recap_tva, config.seuil_fusion_nombre
    )


def lire(chemin: Path, config: Config) -> list[Page]:
    """Lit toutes les pages d'un PDF."""
    pages: list[Page] = []
    with pdfplumber.open(str(chemin)) as pdf:
        for index, page_pdf in enumerate(pdf.pages, start=1):
            texte = page_pdf.extract_text() or ""
            mots = [
                Mot(texte=m["text"], x0=float(m["x0"]), x1=float(m["x1"]), haut=float(m["top"]))
                for m in page_pdf.extract_words()
            ]
            lignes = _grouper_en_lignes(mots, config.tolerance_ligne)
            for ligne in lignes:
                _ventiler_en_colonnes(ligne, config)
            pages.append(
                Page(
                    numero=index,
                    texte=texte,
                    lignes=lignes,
                    entete=entete_technique.decoder(texte),
                    largeur=float(page_pdf.width),
                    hauteur=float(page_pdf.height),
                )
            )
    return pages


def texte_complet(chemin: Path) -> str:
    """Texte brut d'un PDF, sans analyse de mise en page.

    Sert au rapprochement des bons de livraison, ou seule la presence d'un numero compte.
    """
    morceaux = []
    with pdfplumber.open(str(chemin)) as pdf:
        for page in pdf.pages:
            morceaux.append(page.extract_text() or "")
    return "\n".join(morceaux)
