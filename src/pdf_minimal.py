"""Ecriture de PDF minimalistes, pour fabriquer des factures d'essai.

Les tests doivent verifier une lecture par bornes de colonnes : il faut donc poser chaque
mot a une abscisse connue au point pres. Un generateur maison, avec la table de chasses
Helvetica, donne cette maitrise sans ajouter de dependance a l'outil livre.
"""

from __future__ import annotations

from dataclasses import dataclass

LARGEUR_A4 = 595.0
HAUTEUR_A4 = 842.0

# Chasses Helvetica, en millieme de point pour une taille de 1 point (fichier AFM standard).
_CHASSES = {
    " ": 278, "!": 278, '"': 355, "#": 556, "$": 556, "%": 889, "&": 667, "'": 191,
    "(": 333, ")": 333, "*": 389, "+": 584, ",": 278, "-": 333, ".": 278, "/": 278,
    ":": 278, ";": 278, "<": 584, "=": 584, ">": 584, "?": 556, "@": 1015,
    "A": 667, "B": 667, "C": 722, "D": 722, "E": 667, "F": 611, "G": 778, "H": 722,
    "I": 278, "J": 500, "K": 667, "L": 556, "M": 833, "N": 722, "O": 778, "P": 667,
    "Q": 778, "R": 722, "S": 667, "T": 611, "U": 722, "V": 667, "W": 944, "X": 667,
    "Y": 667, "Z": 611, "[": 278, "\\": 278, "]": 278, "^": 469, "_": 556, "`": 333,
    "a": 556, "b": 556, "c": 500, "d": 556, "e": 556, "f": 278, "g": 556, "h": 556,
    "i": 222, "j": 222, "k": 500, "l": 222, "m": 833, "n": 556, "o": 556, "p": 556,
    "q": 556, "r": 333, "s": 500, "t": 278, "u": 556, "v": 500, "w": 722, "x": 500,
    "y": 500, "z": 500, "{": 334, "|": 260, "}": 334, "~": 584,
    "°": 400, "º": 737, "³": 333, "€": 556, "é": 556, "è": 556, "É": 667, "´": 333,
}
_CHASSE_DEFAUT = 556


def largeur(texte: str, taille: float) -> float:
    """Largeur d'un texte en points, pour poser un mot aligne a droite."""
    return sum(_CHASSES.get(c, _CHASSE_DEFAUT) for c in texte) * taille / 1000.0


@dataclass
class Texte:
    """Un mot pose sur la page. `haut` se compte depuis le haut, comme dans pdfplumber."""

    x: float
    haut: float
    contenu: str
    taille: float = 7.0

    @classmethod
    def a_droite(cls, bord_droit: float, haut: float, contenu: str, taille: float = 7.0) -> "Texte":
        """Pose un mot dont le bord droit tombe a l'abscisse voulue (colonnes de nombres)."""
        return cls(bord_droit - largeur(contenu, taille), haut, contenu, taille)


def _echapper(texte: str) -> bytes:
    brut = texte.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    return brut.encode("cp1252", errors="replace")


def _flux(textes: list[Texte], hauteur: float) -> bytes:
    morceaux = [b"BT"]
    for texte in textes:
        # L'origine PDF est en bas de page : on retourne l'ordonnee, en tenant compte
        # de la hauteur de la ligne de base sous le sommet des lettres.
        y = hauteur - texte.haut - texte.taille
        morceaux.append(
            b"/F1 %.2f Tf 1 0 0 1 %.2f %.2f Tm (%s) Tj"
            % (texte.taille, texte.x, y, _echapper(texte.contenu))
        )
    morceaux.append(b"ET")
    return b"\n".join(morceaux)


def ecrire(pages: list[list[Texte]], largeur_page: float = LARGEUR_A4,
           hauteur_page: float = HAUTEUR_A4) -> bytes:
    """Assemble un PDF complet a partir des mots de chaque page."""
    objets: list[bytes] = []

    nombre = len(pages)
    references_pages = " ".join(f"{3 + 2 * i} 0 R" for i in range(nombre))
    objets.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objets.append(
        f"<< /Type /Pages /Kids [{references_pages}] /Count {nombre} >>".encode("ascii")
    )
    for index, textes in enumerate(pages):
        contenu = _flux(textes, hauteur_page)
        objets.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {largeur_page:.0f} {hauteur_page:.0f}] "
                f"/Resources << /Font << /F1 {3 + 2 * nombre} 0 R >> >> "
                f"/Contents {4 + 2 * index} 0 R >>"
            ).encode("ascii")
        )
        objets.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(contenu), contenu))
    objets.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    )

    sortie = bytearray(b"%PDF-1.4\n")
    positions = []
    for numero, corps in enumerate(objets, start=1):
        positions.append(len(sortie))
        sortie += b"%d 0 obj\n" % numero + corps + b"\nendobj\n"

    debut_xref = len(sortie)
    sortie += b"xref\n0 %d\n" % (len(objets) + 1)
    sortie += b"0000000000 65535 f \n"
    for position in positions:
        sortie += b"%010d 00000 n \n" % position
    sortie += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objets) + 1,
        debut_xref,
    )
    return bytes(sortie)
