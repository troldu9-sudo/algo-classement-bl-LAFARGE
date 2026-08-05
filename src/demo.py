"""Fabrication de factures d'essai reproduisant la mise en page Lafarge.

Sert au mode demonstration (`LANCER.bat demo`) et aux tests. Les abscisses reprennent
celles relevees sur une facture reelle, de sorte que la lecture par colonnes est
eprouvee sur la geometrie qu'elle rencontrera en production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from .pdf_minimal import Texte, ecrire, largeur

# Abscisses des colonnes, relevees sur la facture 1900200711.
X_DATE = 35.0
X_SITE = 58.0
X_BON = 91.0
X_LIBELLE = 143.0
X_COMPLEMENT = 161.0
X_CO2 = 314.0
X_REDUCTION = 331.0
X_GWR = 361.0
X_SOUS_TOTAL = 213.0
BORD_QUANTITE = 478.8
BORD_PRIX = 513.0
BORD_MONTANT = 548.5
BORD_CODE_TVA = 565.5

_HAUT_PREMIERE_LIGNE = 286.0
_PAS_LIGNE = 14.0


def montant_fr(valeur: float) -> str:
    return f"{valeur:,.2f}".replace(",", " ").replace(".", ",")


def quantite_fr(valeur: float, unite: str) -> str:
    if unite.upper() == "M3":
        return f"{valeur:.3f}".replace(".", ",") + unite
    return f"{valeur:g}" + unite


@dataclass
class LigneDemo:
    n_bon: str
    designation: str
    quantite: float
    prix: float
    date_livraison: str = "16/06"
    site: str = "LARRIEU"
    complement: str = ""
    code_tva: str = "1"
    unite: str = "M3"

    @property
    def montant(self) -> float:
        return round(self.quantite * self.prix, 2)


@dataclass
class AnnexeDemo:
    libelle: str
    quantite: float
    prix: float
    unite: str = "Pce"
    code_tva: str = "1"
    libelle_suite: str = ""
    # Lafarge arrondit certaines contributions au demi-centime superieur : le montant
    # imprime peut donc differer du produit quantite x prix.
    montant_force: float | None = None

    @property
    def montant(self) -> float:
        if self.montant_force is not None:
            return self.montant_force
        return round(self.quantite * self.prix, 2)


@dataclass
class ChantierDemo:
    code: str
    nom: str
    adresse: list[str] = field(default_factory=list)
    lignes: list[LigneDemo] = field(default_factory=list)
    annexes: list[AnnexeDemo] = field(default_factory=list)

    @property
    def total_ht(self) -> float:
        return round(sum(l.montant for l in self.lignes) + sum(a.montant for a in self.annexes), 2)

    @property
    def volume(self) -> float:
        return round(sum(l.quantite for l in self.lignes if l.unite.upper() == "M3"), 3)


@dataclass
class FactureDemo:
    numero: str
    jour: date
    echeance: date
    chantiers: list[ChantierDemo]
    client: str = "SOLETANCHE BACHY FR 92 RUEIL MALMAI"
    code_client: str = "367478"
    agence: str = "AG OCCITANIE LB"
    taux: dict[str, float] = field(default_factory=lambda: {"1": 20.0})

    @property
    def total_ht(self) -> float:
        return round(sum(c.total_ht for c in self.chantiers), 2)

    @property
    def volume(self) -> float:
        return round(sum(c.volume for c in self.chantiers), 3)

    def ht_par_code(self) -> dict[str, float]:
        cumul: dict[str, float] = {}
        for chantier in self.chantiers:
            for ligne in chantier.lignes:
                cumul[ligne.code_tva] = round(cumul.get(ligne.code_tva, 0.0) + ligne.montant, 2)
            for annexe in chantier.annexes:
                cumul[annexe.code_tva] = round(cumul.get(annexe.code_tva, 0.0) + annexe.montant, 2)
        return cumul

    @property
    def total_tva(self) -> float:
        return round(
            sum(ht * self.taux[code] / 100.0 for code, ht in self.ht_par_code().items()), 2
        )

    @property
    def total_ttc(self) -> float:
        return round(self.total_ht + self.total_tva, 2)


def _verifier_placement(
    texte: str, debut: float, fin_colonne: float, debut_suivant: float, colonne: str
) -> None:
    """Verifie qu'une donnee d'essai reste lisible dans sa colonne.

    Deux regles distinctes, tirees de la facture reelle : un mot est attribue a une
    colonne d'apres son bord GAUCHE, si bien qu'un numero de bon peut deborder
    visuellement sur la colonne suivante sans poser probleme ; en revanche le texte ne
    doit jamais chevaucher celui de la colonne d'a cote, sinon les deux se confondent.
    """
    curseur = debut
    for mot in texte.split(" "):
        if mot and not (debut <= curseur < fin_colonne):
            raise ValueError(
                f"La donnee d'essai « {texte} » place le mot « {mot} » a {curseur:.1f} points, "
                f"hors de la colonne {colonne} [{debut:.0f}, {fin_colonne:.0f}]."
            )
        curseur += largeur(mot + " ", 7.0)
    if curseur > debut_suivant:
        raise ValueError(
            f"La donnee d'essai « {texte} » chevauche la colonne suivante : elle s'arrete a "
            f"{curseur:.1f} points alors que la suivante commence a {debut_suivant:.0f}."
        )


def _entete(facture: FactureDemo, type_page: str, index: int) -> list[Texte]:
    ttc = montant_fr(facture.total_ttc)
    return [
        Texte(3, 2, f"@@@@@;92506;C281043473;{facture.numero};;;{type_page};{index};"
                    f"{facture.jour.isoformat()};DJ;FR70;{ttc};", 6),
        Texte(3, 12, "@@NM@;FR;;;;;vc_7tou4_fr@pdf.basware.com;;", 6),
        Texte(3, 20, f"@@M1@;FRBD-10-40;1;C100038258;{facture.client};C281930566;;DJ;;", 6),
        Texte(532, 28, f"Page {index} / 1", 6),
    ]


def _entete_facture(facture: FactureDemo) -> list[Texte]:
    jour = facture.jour.strftime("%d/%m/%Y")
    return [
        Texte(396, 40, f"FACTURE Nº{facture.numero}", 9),
        Texte(424, 54, f"du {jour}", 7),
        Texte(31, 78, facture.agence, 7),
        Texte(31, 90, "Avenue de Larrieu 23", 7),
        Texte(31, 104, "31100 TOULOUSE", 7),
        Texte(329, 102, f"Code client: {facture.code_client}", 7),
        Texte(34, 262, "Date", 6),
        Texte(29, 268, "livraison", 6),
        Texte(56, 262, "Site expéditeur", 6),
        Texte(111, 262, "N° Bon", 6),
        Texte(210, 262, "Libellé", 6),
        Texte(440, 262, "Quantité", 6),
        Texte(469, 262, "Unité", 6),
        Texte(494, 258, "Prix", 6),
        Texte(520, 258, "Montant", 6),
        Texte(552, 262, "TVA", 6),
    ]


def _corps(facture: FactureDemo) -> list[Texte]:
    textes: list[Texte] = []
    haut = _HAUT_PREMIERE_LIGNE

    for chantier in facture.chantiers:
        textes.append(Texte(X_LIBELLE, haut, f"Chantier: {chantier.code} - {chantier.nom}"))
        haut += _PAS_LIGNE
        for ligne_adresse in chantier.adresse:
            textes.append(Texte(X_LIBELLE, haut, ligne_adresse))
            haut += _PAS_LIGNE

        for ligne in chantier.lignes:
            _verifier_placement(ligne.site, X_SITE, X_BON, X_BON, "site expediteur")
            fin = X_COMPLEMENT if ligne.complement else X_CO2
            _verifier_placement(ligne.n_bon, X_BON, X_LIBELLE, fin, "N° Bon")
            textes.append(Texte(X_LIBELLE, haut, ligne.designation))
            haut += 8.0
            textes += [
                Texte(X_DATE, haut, ligne.date_livraison),
                # La facture reelle separe ces colonnes par un vrai caractere espace :
                # sans lui, les deux mots voisins seraient lus comme un seul.
                Texte(X_SITE, haut, ligne.site + " "),
                Texte(X_BON, haut, ligne.n_bon + " "),
                Texte(X_CO2, haut, "401"),
                Texte(X_REDUCTION, haut, "0 - 9"),
                Texte(X_GWR, haut, "GWR0"),
                Texte.a_droite(BORD_QUANTITE, haut, quantite_fr(ligne.quantite, ligne.unite)),
                Texte.a_droite(BORD_PRIX, haut, montant_fr(ligne.prix)),
                Texte.a_droite(BORD_MONTANT, haut, montant_fr(ligne.montant)),
                # Le code TVA est imprime legerement au-dessus du reste de sa ligne.
                Texte.a_droite(BORD_CODE_TVA, haut - 1.0, ligne.code_tva),
            ]
            if ligne.complement:
                textes.append(Texte(X_COMPLEMENT, haut, ligne.complement))
            haut += _PAS_LIGNE

        for annexe in chantier.annexes:
            if annexe.libelle_suite:
                textes.append(Texte(X_LIBELLE, haut, annexe.libelle))
                haut += 8.0
                intitule = annexe.libelle_suite
            else:
                intitule = annexe.libelle
            textes += [
                Texte(X_LIBELLE, haut, intitule),
                Texte.a_droite(BORD_QUANTITE, haut, quantite_fr(annexe.quantite, annexe.unite)),
                Texte.a_droite(BORD_PRIX, haut, montant_fr(annexe.prix)),
                Texte.a_droite(BORD_MONTANT, haut, montant_fr(annexe.montant)),
                Texte.a_droite(BORD_CODE_TVA, haut - 1.0, annexe.code_tva),
            ]
            haut += _PAS_LIGNE

        textes += [
            Texte(X_SOUS_TOTAL, haut, "SOUS TOTAL CHANTIER"),
            Texte.a_droite(BORD_QUANTITE, haut, quantite_fr(chantier.volume, "M3")),
            Texte.a_droite(BORD_MONTANT, haut, montant_fr(chantier.total_ht)),
        ]
        haut += _PAS_LIGNE * 2

    textes += [
        Texte(X_LIBELLE, haut, "VOLUME TOTAL CLIENT + TOTAL HT"),
        Texte.a_droite(BORD_QUANTITE, haut, quantite_fr(facture.volume, "M3")),
        Texte.a_droite(BORD_MONTANT, haut, montant_fr(facture.total_ht)),
    ]
    return textes


def _pied(facture: FactureDemo) -> list[Texte]:
    haut = 552.0
    textes = [
        Texte(32, haut, "CODE"),
        Texte(75, haut, "TAUX TVA"),
        Texte(133, haut, "MONTANT HT"),
        Texte(189, haut, "MONTANT TVA"),
        Texte(256, haut, "A PAYER TTC"),
        Texte(370, haut + 2, "A PAYER TTC"),
        Texte.a_droite(484, haut + 2, montant_fr(facture.total_ttc)),
        Texte(490, haut + 2, "EUR"),
    ]
    ligne = haut + 14
    for code, ht in sorted(facture.ht_par_code().items()):
        taux = facture.taux[code]
        tva = round(ht * taux / 100.0, 2)
        textes += [
            Texte.a_droite(44.7, ligne, code),
            Texte.a_droite(102.1, ligne, montant_fr(taux)),
            Texte.a_droite(168.1, ligne, montant_fr(ht)),
            Texte.a_droite(224.0, ligne, montant_fr(tva)),
            Texte.a_droite(291.4, ligne, montant_fr(round(ht + tva, 2))),
        ]
        ligne += 12
    textes.append(
        Texte(329, ligne + 12, f"DATE D´ECHEANCE: {facture.echeance.strftime('%d/%m/%Y')}")
    )
    return textes


def _page_conditions(facture: FactureDemo, index: int) -> list[Texte]:
    return _entete(facture, "CG", index) + [
        Texte(31, 60, "CONDITIONS GENERALES DE VENTE", 10),
        Texte(31, 80, "ARTICLE 1 - GENERALITES", 7),
        Texte(31, 92, "Les presentes conditions s'appliquent a toutes nos ventes.", 7),
    ]


def pages_facture(facture: FactureDemo, avec_conditions: bool = True) -> list[list[Texte]]:
    """Les pages d'une facture : la facture elle-meme, puis ses conditions generales."""
    principale = _entete(facture, "FA", 1) + _entete_facture(facture) + _corps(facture) + _pied(facture)
    pages = [principale]
    if avec_conditions:
        pages.append(_page_conditions(facture, 2))
    return pages


def facture_simple() -> FactureDemo:
    """Reproduit la structure de la facture reelle : un chantier, un bon, un taux."""
    return FactureDemo(
        numero="1900200711",
        jour=date(2026, 6, 30),
        echeance=date(2026, 8, 14),
        chantiers=[
            ChantierDemo(
                code="PBL",
                nom="PUITS BALANSA",
                adresse=["25 Avenue Benjamin Balansa", "31500 Toulouse"],
                lignes=[
                    LigneDemo(
                        n_bon="CE 293982(F65)",
                        designation="D2B10 Agilia Génie-Civil C35/45 D16 SF2 XA2",
                        complement="SRPM",
                        quantite=1.5,
                        prix=165.80,
                    )
                ],
                annexes=[
                    AnnexeDemo("Forfait Livraison en 8x4 / Jour", 1, 142.50),
                    AnnexeDemo(
                        "CONTRIBUTION ENVIRONEMENTALE METRO",
                        1.5,
                        2.13,
                        unite="M3",
                        libelle_suite="LOT 4",
                        montant_force=3.20,
                    ),
                    AnnexeDemo("CONTRIBUTION CLIMAT ENERGIE METRO", 1.5, 4.48, unite="M3"),
                ],
            )
        ],
    )


def facture_multi_chantiers() -> FactureDemo:
    """Deux chantiers, trois bons, deux taux de TVA : les cas non couverts par l'exemple reel."""
    return FactureDemo(
        numero="1900200712",
        jour=date(2026, 7, 31),
        echeance=date(2026, 9, 15),
        taux={"1": 20.0, "2": 10.0},
        chantiers=[
            ChantierDemo(
                code="PBL",
                nom="PUITS BALANSA",
                adresse=["25 Avenue Benjamin Balansa", "31500 Toulouse"],
                lignes=[
                    LigneDemo("CE 294100(F65)", "D2B10 Agilia Génie-Civil C35/45", 6.0, 150.00),
                    LigneDemo(
                        "CE 294101(F65)",
                        "D2B12 Beton XC4 C30/37",
                        4.5,
                        142.00,
                        date_livraison="28/12",
                        code_tva="2",
                    ),
                ],
                annexes=[AnnexeDemo("Forfait Livraison en 8x4 / Jour", 2, 142.50)],
            ),
            ChantierDemo(
                code="GAR",
                nom="GARE MATABIAU",
                adresse=["1 Boulevard Pierre Semard", "31000 Toulouse"],
                lignes=[
                    LigneDemo(
                        "CE 294250(F70)",
                        "D2B14 Beton XA1 C25/30",
                        12.0,
                        138.40,
                        site="PORTET",
                        date_livraison="15/07",
                    )
                ],
                annexes=[AnnexeDemo("CONTRIBUTION CLIMAT ENERGIE METRO", 12.0, 4.48, unite="M3")],
            ),
        ],
    )


def factures_groupees() -> list[FactureDemo]:
    """Trois factures dans un meme PDF, chacune suivie de ses conditions generales."""
    base = facture_simple()
    resultat = []
    for decalage, numero in enumerate(("1900300001", "1900300002", "1900300003")):
        facture = FactureDemo(
            numero=numero,
            jour=date(2026, 5, 10 + decalage),
            echeance=date(2026, 6, 25 + decalage),
            chantiers=[
                ChantierDemo(
                    code=base.chantiers[0].code,
                    nom=base.chantiers[0].nom,
                    adresse=list(base.chantiers[0].adresse),
                    lignes=[
                        LigneDemo(
                            n_bon=f"CE 29500{decalage}(F65)",
                            designation="D2B10 Agilia Génie-Civil C35/45 D16 SF2 XA2",
                            quantite=3.0 + decalage,
                            prix=160.00,
                            date_livraison=f"0{decalage + 1}/05",
                        )
                    ],
                )
            ],
        )
        resultat.append(facture)
    return resultat


def bon_de_livraison(numero: str, facture: str, quantite: float) -> bytes:
    """Un PDF de bon de livraison, tel qu'on peut le telecharger separement."""
    textes = [
        Texte(60, 60, "LAFARGE BETONS - BON DE LIVRAISON", 12),
        Texte(60, 100, f"N° Bon : {numero}", 9),
        Texte(60, 120, f"Facture : {facture}", 9),
        Texte(60, 140, f"Quantite : {quantite_fr(quantite, 'M3')}", 9),
        Texte(60, 160, "Chantier : PBL - PUITS BALANSA", 9),
    ]
    return ecrire([textes])


def pdf_sans_texte() -> bytes:
    """Un PDF vide de texte, comme un bon scanne : l'outil doit le signaler, pas le deviner."""
    return ecrire([[]])


def generer(dossier: Path) -> list[Path]:
    """Ecrit le jeu de PDF de demonstration et renvoie les fichiers crees."""
    dossier.mkdir(parents=True, exist_ok=True)
    fichiers = []

    simple = facture_simple()
    cible = dossier / f"Facture_{simple.numero}.pdf"
    cible.write_bytes(ecrire(pages_facture(simple)))
    fichiers.append(cible)

    multi = facture_multi_chantiers()
    cible = dossier / f"Facture_{multi.numero}_multi-chantiers.pdf"
    cible.write_bytes(ecrire(pages_facture(multi)))
    fichiers.append(cible)

    pages: list[list[Texte]] = []
    for facture in factures_groupees():
        pages += pages_facture(facture)
    cible = dossier / "Factures_groupees.pdf"
    cible.write_bytes(ecrire(pages))
    fichiers.append(cible)

    cible = dossier / "BL_CE293982.pdf"
    cible.write_bytes(bon_de_livraison("CE 293982(F65)", simple.numero, 1.5))
    fichiers.append(cible)

    cible = dossier / "bon_294100.pdf"
    cible.write_bytes(bon_de_livraison("CE 294100(F65)", multi.numero, 6.0))
    fichiers.append(cible)

    cible = dossier / "Bon_scanne.pdf"
    cible.write_bytes(pdf_sans_texte())
    fichiers.append(cible)

    return fichiers
