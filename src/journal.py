"""Memoire des PDF deja decoupes, pour qu'un second passage ne refasse pas le travail."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

NOM_JOURNAL = ".journal.json"


def empreinte(chemin: Path) -> str:
    """Empreinte SHA-256 d'un fichier, lue par blocs pour ne pas charger tout le PDF."""
    condensat = hashlib.sha256()
    with chemin.open("rb") as flux:
        for bloc in iter(lambda: flux.read(1 << 16), b""):
            condensat.update(bloc)
    return condensat.hexdigest()


class Journal:
    """Associe l'empreinte d'un PDF source aux fichiers qui en ont ete tires."""

    def __init__(self, dossier: Path):
        self.chemin = dossier / NOM_JOURNAL
        self.entrees: dict[str, dict] = {}
        if self.chemin.exists():
            try:
                self.entrees = json.loads(self.chemin.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                # Un journal illisible n'est pas bloquant : au pire le decoupage est refait.
                self.entrees = {}

    def a_jour(self, source: Path, condensat: str, cibles: list[Path]) -> bool:
        """Vrai si ce PDF a deja ete decoupe a l'identique et que les fichiers sont toujours la."""
        entree = self.entrees.get(source.name)
        if not entree or entree.get("empreinte") != condensat:
            return False
        return all(Path(c).exists() for c in entree.get("cibles", [])) and len(
            entree.get("cibles", [])
        ) == len(cibles)

    def cibles_connues(self, source: Path) -> list[Path]:
        entree = self.entrees.get(source.name, {})
        return [Path(c) for c in entree.get("cibles", [])]

    def enregistrer(self, source: Path, condensat: str, cibles: list[Path]) -> None:
        self.entrees[source.name] = {
            "empreinte": condensat,
            "cibles": [str(c) for c in cibles],
        }

    def sauvegarder(self) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.chemin.write_text(
            json.dumps(self.entrees, indent=2, ensure_ascii=False), encoding="utf-8"
        )
