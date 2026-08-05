"""Chargement et validation de config.json."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Dans le .exe autonome, config.json est le fichier pose a cote de l'executable :
# c'est celui que l'utilisateur modifie, pas une copie enfouie dans le paquet.
if getattr(sys, "frozen", False):
    RACINE = Path(sys.executable).resolve().parent
else:
    RACINE = Path(__file__).resolve().parent.parent
CHEMIN_CONFIG = RACINE / "config.json"


class ConfigInvalide(Exception):
    """config.json est illisible ou mal forme : le message dit quoi corriger."""


@dataclass
class Colonne:
    """Bornes horizontales d'une colonne du tableau, en points PDF."""

    nom: str
    repere: str  # "gauche" (bord gauche du mot) ou "droite" (colonnes de nombres)
    mini: float
    maxi: float

    def contient(self, x0: float, x1: float) -> bool:
        x = x1 if self.repere == "droite" else x0
        return self.mini <= x < self.maxi


@dataclass
class Config:
    dossier: Path
    sous_dossier_decoupe: str = "_Factures-decoupees"
    prefixe_tableur: str = "Suivi-Lafarge"
    decouper_pdf_groupes: bool = True
    apparier_bons_de_livraison: bool = True
    ouvrir_tableur_a_la_fin: bool = True
    types_page_ignores: tuple[str, ...] = ("CG",)
    tolerance_ligne: float = 4.0
    tolerance_totaux: float = 0.02
    lignes_adresse_max: int = 4
    seuil_fusion_nombre: float = 6.0
    colonnes: list[Colonne] = field(default_factory=list)
    colonnes_recap_tva: list[Colonne] = field(default_factory=list)
    motifs: dict[str, re.Pattern[str]] = field(default_factory=dict)

    @property
    def dossier_decoupe(self) -> Path:
        return self.dossier / self.sous_dossier_decoupe

    def motif(self, nom: str) -> re.Pattern[str]:
        if nom not in self.motifs:
            raise ConfigInvalide(f"Le motif « {nom} » manque dans config.json, section « motifs ».")
        return self.motifs[nom]


def _colonnes(brut: dict) -> list[Colonne]:
    colonnes = []
    for nom, valeurs in brut.items():
        try:
            colonne = Colonne(
                nom=nom,
                repere=str(valeurs.get("repere", "gauche")),
                mini=float(valeurs["min"]),
                maxi=float(valeurs["max"]),
            )
        except (KeyError, TypeError, ValueError) as err:
            raise ConfigInvalide(
                f"Colonne « {nom} » mal definie dans config.json : il faut « min » et « max » numeriques."
            ) from err
        if colonne.repere not in ("gauche", "droite"):
            raise ConfigInvalide(
                f"Colonne « {nom} » : « repere » vaut « {colonne.repere} », "
                "attendu « gauche » ou « droite »."
            )
        if colonne.mini >= colonne.maxi:
            raise ConfigInvalide(f"Colonne « {nom} » : « min » doit etre inferieur a « max ».")
        colonnes.append(colonne)
    return colonnes


def _motifs(brut: dict) -> dict[str, re.Pattern[str]]:
    compiles = {}
    for nom, motif in brut.items():
        try:
            compiles[nom] = re.compile(motif, re.IGNORECASE | re.MULTILINE)
        except re.error as err:
            raise ConfigInvalide(
                f"Le motif « {nom} » de config.json n'est pas une expression reguliere valide : {err}"
            ) from err
    return compiles


def charger(chemin: Path | None = None, dossier_force: Path | None = None) -> Config:
    """Lit config.json. `dossier_force` a la priorite sur le chemin configure."""
    chemin = chemin or CHEMIN_CONFIG
    try:
        brut = json.loads(chemin.read_text(encoding="utf-8"))
    except FileNotFoundError as err:
        raise ConfigInvalide(f"config.json est introuvable ({chemin}).") from err
    except json.JSONDecodeError as err:
        raise ConfigInvalide(
            f"config.json est mal forme, ligne {err.lineno} : {err.msg}. "
            "Une virgule ou un guillemet manque probablement."
        ) from err

    dossier = Path(dossier_force) if dossier_force else Path(str(brut.get("dossier", "")).strip())

    return Config(
        dossier=dossier,
        sous_dossier_decoupe=str(brut.get("sous_dossier_decoupe", "_Factures-decoupees")),
        prefixe_tableur=str(brut.get("prefixe_tableur", "Suivi-Lafarge")),
        decouper_pdf_groupes=bool(brut.get("decouper_pdf_groupes", True)),
        apparier_bons_de_livraison=bool(brut.get("apparier_bons_de_livraison", True)),
        ouvrir_tableur_a_la_fin=bool(brut.get("ouvrir_tableur_a_la_fin", True)),
        types_page_ignores=tuple(str(t).upper() for t in brut.get("types_page_ignores", ["CG"])),
        tolerance_ligne=float(brut.get("tolerance_ligne", 4.0)),
        tolerance_totaux=float(brut.get("tolerance_totaux", 0.02)),
        lignes_adresse_max=int(brut.get("lignes_adresse_max", 4)),
        seuil_fusion_nombre=float(brut.get("seuil_fusion_nombre", 6.0)),
        colonnes=_colonnes(brut.get("colonnes", {})),
        colonnes_recap_tva=_colonnes(brut.get("colonnes_recap_tva", {})),
        motifs=_motifs(brut.get("motifs", {})),
    )
