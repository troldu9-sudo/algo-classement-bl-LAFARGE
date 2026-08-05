"""Fixtures communes aux tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from src import decoupe, demo, extraction, lecture_pdf  # noqa: E402
from src.config import charger  # noqa: E402
from src.modeles import Facture  # noqa: E402

# Facture reelle, deposee a la main par l'utilisateur. Absente du depot : elle contient
# des donnees commerciales et des coordonnees bancaires qui n'ont rien a faire sur GitHub.
DOSSIER_REEL = RACINE / "tests" / "fixtures" / "reel"


@pytest.fixture
def dossier_demo(tmp_path: Path) -> Path:
    """Un dossier neuf contenant le jeu complet de factures d'essai."""
    dossier = tmp_path / "FA-Lafarge"
    demo.generer(dossier)
    return dossier


@pytest.fixture
def config_demo(dossier_demo: Path):
    return charger(dossier_force=dossier_demo)


def extraire_toutes(chemin: Path, config) -> list[Facture]:
    """Lit un PDF et rend les factures qu'il contient."""
    pages = lecture_pdf.lire(chemin, config)
    return [extraction.extraire(bloc, config, chemin) for bloc in decoupe.grouper(pages, config)]


def extraire_une(chemin: Path, config) -> Facture:
    factures = extraire_toutes(chemin, config)
    assert len(factures) == 1, f"{chemin.name} contient {len(factures)} factures"
    return factures[0]


def factures_reelles() -> list[Path]:
    if not DOSSIER_REEL.is_dir():
        return []
    return sorted(DOSSIER_REEL.glob("*.pdf"))
