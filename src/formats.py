"""Conversion des valeurs telles qu'elles sortent du PDF (format francais)."""

from __future__ import annotations

import re
import unicodedata
from datetime import date

# Espaces employes comme separateur de milliers dans les PDF Lafarge : ordinaire,
# insecable, insecable etroite, fine, ultra-fine, plus la tabulation.
ESPACES = " \u00a0\u202f\u2009\u200a\t"
_ESPACES_RE = re.compile(f"[{ESPACES}]")

_QUANTITE_RE = re.compile(r"^(-?[\d.,]*\d)\s*([A-Za-z³][A-Za-z0-9³]*)?$")


def sans_espaces(texte: str) -> str:
    """Retire tous les espaces, y compris insecables et fins."""
    return _ESPACES_RE.sub("", texte or "")


def nombre_fr(texte: str | None) -> float | None:
    """Convertit un nombre ecrit a la francaise. `1 234,56` -> 1234.56, `1,500` -> 1.5.

    Retourne None si le texte ne contient pas de nombre exploitable, plutot que de
    lever : une cellule vide est un cas normal dans une facture.
    """
    if texte is None:
        return None
    brut = sans_espaces(texte).replace("€", "").replace("EUR", "")
    if not brut or not any(c.isdigit() for c in brut):
        return None
    negatif = brut.startswith("-") or (brut.startswith("(") and brut.endswith(")"))
    brut = brut.strip("()-+")
    if "," in brut:
        # La virgule est le separateur decimal : les points sont des milliers.
        brut = brut.replace(".", "").replace(",", ".")
    # Sans virgule, un point isole est traite comme separateur decimal.
    try:
        valeur = float(brut)
    except ValueError:
        return None
    return -valeur if negatif else valeur


def date_fr(texte: str | None) -> date | None:
    """Convertit `30/06/2026` en date. Retourne None si le format ne correspond pas."""
    if not texte:
        return None
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texte)
    if not m:
        return None
    jour, mois, annee = (int(g) for g in m.groups())
    try:
        return date(annee, mois, jour)
    except ValueError:
        return None


def date_iso(texte: str | None) -> date | None:
    """Convertit `2026-06-30` (ligne technique de dematerialisation) en date."""
    if not texte:
        return None
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", texte)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def date_livraison(texte: str | None, reference: date | None) -> date | None:
    """Complete une date de livraison `16/06` avec l'annee de la facture.

    Une livraison posterieure au mois de facturation appartient a l'annee precedente :
    une livraison du 28/12 facturee en janvier ne doit pas basculer dans le futur.
    """
    if not texte:
        return None
    complete = date_fr(texte)
    if complete:
        return complete
    m = re.search(r"^(\d{1,2})/(\d{1,2})$", texte.strip())
    if not m or reference is None:
        return None
    jour, mois = int(m.group(1)), int(m.group(2))
    annee = reference.year - 1 if mois > reference.month else reference.year
    try:
        return date(annee, mois, jour)
    except ValueError:
        return None


def quantite_unite(texte: str | None) -> tuple[float | None, str]:
    """Separe la quantite de son unite : `1,500M3` -> (1.5, "M3"), `1Pce` -> (1.0, "Pce")."""
    if not texte:
        return None, ""
    brut = sans_espaces(texte)
    m = _QUANTITE_RE.match(brut)
    if not m:
        return nombre_fr(brut), ""
    return nombre_fr(m.group(1)), (m.group(2) or "")


_CHIFFRES = re.compile(r"\d+")
_PARENTHESE = re.compile(r"\(([^)]*)\)")


def decomposer_bon(texte: str | None, longueur_min: int = 4) -> tuple[str, str, str]:
    """Isole le numero de bon du reste de la cellule N° Bon.

    Rend `(numero, variante, complement)` :

        `CE 293982(F65)`     -> ("293982", "F65", "")
        `CE 123482Retour`    -> ("123482", "",    "Retour")
        `158022PM3`          -> ("158022", "",    "PM3")
        `184047`             -> ("184047", "",    "")

    Le prefixe de centrale (`CE`) ne fait pas partie du numero et est ecarte. Le texte
    accole apres le numero appartient au libelle de la ligne : il est rendu a part pour
    y etre rattache, plutot que d'etre perdu.

    `longueur_min` evite de confondre le numero avec les chiffres d'un code accole
    (`M3`, `R4`, `A7`) : seuls les groupes assez longs sont candidats, et a defaut le
    plus long groupe present est retenu pour ne jamais rendre un numero vide a tort.
    """
    if not texte:
        return "", "", ""

    variante = ""
    trouve = _PARENTHESE.search(texte)
    if trouve:
        variante = trouve.group(1).strip()
        texte = texte[: trouve.start()] + " " + texte[trouve.end() :]

    groupes = list(_CHIFFRES.finditer(texte))
    if not groupes:
        return "", variante, texte.strip()

    assez_longs = [g for g in groupes if len(g.group()) >= longueur_min]
    numero = max(assez_longs or groupes, key=lambda g: len(g.group()))
    return numero.group(), variante, texte[numero.end() :].strip(" -").strip()


def sans_accents(texte: str) -> str:
    """Retire les accents, pour comparer des libelles sans dependre de la casse ni des accents."""
    decompose = unicodedata.normalize("NFD", texte or "")
    return "".join(c for c in decompose if unicodedata.category(c) != "Mn")


def cle_comparaison(texte: str) -> str:
    """Forme canonique d'un texte : sans accents, sans ponctuation, en majuscules."""
    return re.sub(r"[^A-Z0-9]", "", sans_accents(texte or "").upper())
