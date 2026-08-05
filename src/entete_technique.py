"""Decodage des lignes de dematerialisation presentes en haut de chaque page.

Chaque page d'une facture Lafarge porte des lignes techniques invisibles a l'impression :

    @@@@@;92506;C281043473;1900200711;;;FA;1;2026-06-30;DJ;FR70;481,34;
    @@M1@;FRBD-10-40;1;C100038258;SOLETANCHE BACHY FR 92 RUEIL MALMAI;C281930566;;DJ;;

Elles donnent le numero de facture, le type de page et la date sans dependre de la mise en
page, ce qui rend le decoupage des PDF groupes et l'elimination des conditions generales
deterministes plutot qu'heuristiques.
"""

from __future__ import annotations

from .formats import date_iso, nombre_fr
from .modeles import EnteteTechnique

MARQUEUR_DOCUMENT = "@@@@@;"
MARQUEUR_CLIENT = "@@M1@;"

# Position des champs dans la ligne @@@@@, comptee a partir de 0.
_DOC_CODE_POSTAL = 1
_DOC_CODE_DOCUMENT = 2
_DOC_NUMERO = 3
_DOC_TYPE_PAGE = 6
_DOC_INDEX_PAGE = 7
_DOC_DATE = 8
_DOC_TOTAL_TTC = 11

# Position des champs dans la ligne @@M1@.
_CLI_CODE = 3
_CLI_NOM = 4


def _champ(champs: list[str], position: int) -> str:
    """Lit un champ en tolerant une ligne plus courte que prevu."""
    return champs[position].strip() if position < len(champs) else ""


def decoder(texte_page: str) -> EnteteTechnique:
    """Extrait l'entete technique d'une page. Retourne un entete vide si elle est absente.

    Les lignes sont cherchees dans toute la page : selon la bibliotheque de lecture,
    elles ne ressortent pas toujours en premiere position.
    """
    entete = EnteteTechnique()
    for ligne in (texte_page or "").splitlines():
        ligne = ligne.strip()
        if ligne.startswith(MARQUEUR_DOCUMENT) and not entete.numero_facture:
            champs = ligne.split(";")
            entete.code_postal = _champ(champs, _DOC_CODE_POSTAL)
            entete.code_document = _champ(champs, _DOC_CODE_DOCUMENT)
            entete.numero_facture = _champ(champs, _DOC_NUMERO)
            entete.type_page = _champ(champs, _DOC_TYPE_PAGE).upper()
            entete.index_page = _champ(champs, _DOC_INDEX_PAGE)
            entete.date_facture = date_iso(_champ(champs, _DOC_DATE))
            entete.total_ttc = nombre_fr(_champ(champs, _DOC_TOTAL_TTC))
        elif ligne.startswith(MARQUEUR_CLIENT) and not entete.code_client_interne:
            champs = ligne.split(";")
            entete.code_client_interne = _champ(champs, _CLI_CODE)
            entete.nom_client = _champ(champs, _CLI_NOM)
    return entete
