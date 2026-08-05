"""Structures de donnees representant une facture Lafarge et ses lignes."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


@dataclass
class Mot:
    """Un mot du PDF avec sa position, en points (origine en haut a gauche)."""

    texte: str
    x0: float
    x1: float
    haut: float


@dataclass
class Ligne:
    """Une ligne visuelle du PDF : les mots regroupes par ordonnee, ventiles par colonne."""

    haut: float
    mots: list[Mot] = field(default_factory=list)
    cellules: dict[str, str] = field(default_factory=dict)
    cellules_recap: dict[str, str] = field(default_factory=dict)

    def cellule(self, nom: str) -> str:
        return self.cellules.get(nom, "")

    def cellule_recap(self, nom: str) -> str:
        return self.cellules_recap.get(nom, "")

    @property
    def texte(self) -> str:
        return " ".join(m.texte for m in sorted(self.mots, key=lambda m: m.x0))


@dataclass
class EnteteTechnique:
    """Ligne de dematerialisation presente en haut de chaque page (`@@@@@;...`).

    Source la plus fiable des champs cles : elle ne depend d'aucune mise en page.
    """

    numero_facture: str = ""
    type_page: str = ""
    index_page: str = ""
    date_facture: date | None = None
    total_ttc: float | None = None
    code_postal: str = ""
    code_document: str = ""
    code_client_interne: str = ""
    nom_client: str = ""

    @property
    def exploitable(self) -> bool:
        return bool(self.numero_facture)


@dataclass
class Page:
    """Une page lue : son texte, ses lignes positionnees et son entete technique."""

    numero: int
    texte: str
    lignes: list[Ligne]
    entete: EnteteTechnique
    largeur: float = 0.0
    hauteur: float = 0.0

    @property
    def sans_couche_texte(self) -> bool:
        """Un PDF scanne ne rend aucun texte : il faudrait l'OCR pour l'exploiter."""
        return len(self.texte.strip()) < 20


@dataclass
class Chantier:
    code: str = ""
    nom: str = ""
    adresse: list[str] = field(default_factory=list)
    sous_total_quantite: float | None = None
    sous_total_ht: float | None = None

    @property
    def intitule(self) -> str:
        return f"{self.code} - {self.nom}" if self.code else self.nom


@dataclass
class LigneLivraison:
    """Une ligne de facture portant un N° Bon : le coeur du suivi."""

    n_bon_brut: str = ""
    n_bon: str = ""
    variante: str = ""
    date_livraison: date | None = None
    site_expediteur: str = ""
    libelle: str = ""
    quantite: float | None = None
    unite: str = ""
    prix_unitaire: float | None = None
    montant_ht: float | None = None
    code_tva: str = ""
    poids_co2: str = ""
    reduction_co2: str = ""
    classe_gwr: str = ""
    chantier_code: str = ""
    chantier_nom: str = ""
    pdf_bon: Path | None = None


@dataclass
class LigneAnnexe:
    """Ligne facturee sans N° Bon : forfait de livraison, contributions."""

    libelle: str = ""
    quantite: float | None = None
    unite: str = ""
    prix_unitaire: float | None = None
    montant_ht: float | None = None
    code_tva: str = ""
    chantier_code: str = ""
    chantier_nom: str = ""


@dataclass
class LigneTva:
    code: str = ""
    taux: float | None = None
    montant_ht: float | None = None
    montant_tva: float | None = None
    montant_ttc: float | None = None


@dataclass
class Facture:
    numero: str = ""
    date_facture: date | None = None
    date_echeance: date | None = None
    agence: str = ""
    code_client: str = ""
    nom_client: str = ""
    total_ht: float | None = None
    total_tva: float | None = None
    total_ttc: float | None = None
    total_ttc_technique: float | None = None
    volume_total: float | None = None
    unite_volume: str = ""
    taux_tva: list[LigneTva] = field(default_factory=list)
    chantiers: list[Chantier] = field(default_factory=list)
    livraisons: list[LigneLivraison] = field(default_factory=list)
    annexes: list[LigneAnnexe] = field(default_factory=list)
    pdf_source: Path | None = None
    pages_source: list[int] = field(default_factory=list)
    pdf_decoupe: Path | None = None
    anomalies: list[str] = field(default_factory=list)

    @property
    def chantiers_intitules(self) -> str:
        return " ; ".join(c.intitule for c in self.chantiers)

    @property
    def pdf_a_referencer(self) -> Path | None:
        """Le PDF vers lequel pointer dans le tableur : le decoupe s'il existe."""
        return self.pdf_decoupe or self.pdf_source

    def signaler(self, message: str) -> None:
        if message not in self.anomalies:
            self.anomalies.append(message)


@dataclass
class Anomalie:
    """Une entree de l'onglet « A verifier »."""

    categorie: str
    facture: str
    detail: str
    fichier: str = ""


@dataclass
class Resultat:
    """Ce que produit un passage complet de l'outil."""

    factures: list[Facture] = field(default_factory=list)
    anomalies: list[Anomalie] = field(default_factory=list)
    pdf_bons: dict[str, Path] = field(default_factory=dict)
    pdf_ignores: list[Path] = field(default_factory=list)

    def signaler(self, categorie: str, facture: str, detail: str, fichier: str = "") -> None:
        self.anomalies.append(Anomalie(categorie, facture, detail, fichier))
