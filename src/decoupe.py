"""Regroupement des pages par facture et decoupage des PDF groupes.

Un PDF telecharge depuis le portail Lafarge contient souvent plusieurs factures a la
suite, chacune suivie de ses conditions generales de vente. La ligne technique en haut de
page porte le numero de facture et le type de page (`FA` = facture, `CG` = conditions
generales), ce qui permet de decouper sans deviner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .config import Config
from .modeles import Page


@dataclass
class BlocFacture:
    """Les pages d'une seule facture au sein d'un PDF."""

    numero: str = ""
    pages: list[Page] = field(default_factory=list)
    pages_ignorees: list[int] = field(default_factory=list)
    types_inconnus: list[str] = field(default_factory=list)

    @property
    def numeros_pages(self) -> list[int]:
        return [p.numero for p in self.pages]


def _numero_visuel(page: Page, config: Config) -> str:
    """Repli quand la ligne technique manque : on lit le numero imprime."""
    trouve = config.motif("numero_facture").search(page.texte)
    return trouve.group(1) if trouve else ""


def grouper(pages: list[Page], config: Config) -> list[BlocFacture]:
    """Repartit les pages d'un PDF en blocs, un par facture.

    Les pages sans numero identifiable sont rattachees a la facture en cours : ce sont des
    suites de tableau. Les pages de conditions generales sont mises de cote.
    """
    blocs: list[BlocFacture] = []
    for page in pages:
        numero = page.entete.numero_facture or _numero_visuel(page, config)
        type_page = page.entete.type_page

        if numero and (not blocs or blocs[-1].numero != numero):
            blocs.append(BlocFacture(numero=numero))
        elif not blocs:
            # Tant qu'aucune facture n'est identifiee, le PDF n'en est pas une : c'est
            # probablement un bon de livraison, qui sera traite comme tel.
            continue

        bloc = blocs[-1]
        if type_page and type_page in config.types_page_ignores:
            bloc.pages_ignorees.append(page.numero)
        else:
            if type_page and type_page != "FA":
                bloc.types_inconnus.append(type_page)
            bloc.pages.append(page)
    return [b for b in blocs if b.pages]


def _nom_fichier(numero: str, date_facture: date | None) -> str:
    suffixe = f"_{date_facture.isoformat()}" if date_facture else ""
    return f"FACTURE_{numero or 'SANS-NUMERO'}{suffixe}.pdf"


def ecrire(
    source: Path,
    bloc: BlocFacture,
    date_facture: date | None,
    destination: Path,
) -> Path:
    """Ecrit les pages d'une facture dans un PDF distinct. Le PDF d'origine n'est pas touche."""
    destination.mkdir(parents=True, exist_ok=True)
    cible = destination / _nom_fichier(bloc.numero, date_facture)

    lecteur = PdfReader(str(source))
    ecrivain = PdfWriter()
    for numero_page in bloc.numeros_pages:
        ecrivain.add_page(lecteur.pages[numero_page - 1])
    with cible.open("wb") as flux:
        ecrivain.write(flux)
    return cible
