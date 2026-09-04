"""Point d'entree de l'outil : lit le dossier, produit le tableur, l'ouvre."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path

from . import appariement, controles, decoupe, excel, extraction, lecture_pdf
from .config import Config, ConfigInvalide, charger
from .journal import Journal, empreinte
from .modeles import Facture, Resultat


def _dire(message: str = "") -> None:
    print(message, flush=True)


def _demander_dossier(titre: str) -> Path | None:
    """Ouvre un selecteur de dossier. Retourne None si l'affichage est impossible."""
    try:
        import tkinter as tk
        from tkinter import filedialog

        racine = tk.Tk()
        racine.withdraw()
        choisi = filedialog.askdirectory(title=titre)
        racine.destroy()
        return Path(choisi) if choisi else None
    except Exception:
        return None


def _resoudre_dossier(config: Config) -> Path | None:
    if config.dossier and config.dossier.is_dir():
        return config.dossier
    if config.dossier:
        _dire(f"Le dossier configure est introuvable : {config.dossier}")
    else:
        _dire("Aucun dossier n'est configure dans config.json.")
    _dire("Selection manuelle du dossier a analyser...")
    choisi = _demander_dossier("Choisir le dossier des factures Lafarge")
    if choisi is None:
        _dire("Aucun dossier selectionne.")
    return choisi


def _lister_pdf(config: Config) -> list[Path]:
    """Tous les PDF du dossier, sauf ceux que l'outil a lui-meme produits."""
    decoupes = config.dossier_decoupe.resolve()
    fichiers = []
    for chemin in sorted(config.dossier.rglob("*.pdf")):
        if decoupes in chemin.resolve().parents:
            continue
        fichiers.append(chemin)
    return fichiers


def _traiter_pdf(
    chemin: Path, config: Config, resultat: Resultat, journal: Journal
) -> list[Path]:
    """Lit un PDF. Renvoie les fichiers candidats au rapprochement des bons."""
    pages = lecture_pdf.lire(chemin, config)
    if not pages:
        resultat.signaler("Lecture", "", "PDF vide ou illisible.", chemin.name)
        return []

    if all(page.sans_couche_texte for page in pages):
        resultat.signaler(
            "PDF scanne",
            "",
            "Ce PDF ne contient aucun texte : il a ete scanne en image et ne peut pas "
            "etre lu automatiquement.",
            chemin.name,
        )
        return []

    blocs = decoupe.grouper(pages, config)
    if not blocs:
        resultat.pdf_ignores.append(chemin)
        return [chemin]

    factures: list[Facture] = []
    for bloc in blocs:
        facture = extraction.extraire(bloc, config, chemin)
        factures.append(facture)

    if config.decouper_pdf_groupes and len(blocs) > 1:
        _decouper(chemin, blocs, factures, config, journal)

    resultat.factures.extend(factures)
    return []


def _decouper(
    source: Path,
    blocs: list[decoupe.BlocFacture],
    factures: list[Facture],
    config: Config,
    journal: Journal,
) -> None:
    """Ecrit un PDF par facture. Le fichier d'origine reste intact et a sa place."""
    condensat = empreinte(source)
    connues = journal.cibles_connues(source)
    if journal.a_jour(source, condensat, blocs):
        for facture, cible in zip(factures, connues):
            facture.pdf_decoupe = cible
        return

    cibles = []
    for bloc, facture in zip(blocs, factures):
        cible = decoupe.ecrire(source, bloc, facture.date_facture, config.dossier_decoupe)
        facture.pdf_decoupe = cible
        cibles.append(cible)
    journal.enregistrer(source, condensat, cibles)


def analyser(config: Config) -> Resultat:
    """Chaine complete : lecture, decoupage, extraction, rapprochement, controles."""
    resultat = Resultat()
    fichiers = _lister_pdf(config)
    _dire(f"{len(fichiers)} fichier(s) PDF trouve(s) dans {config.dossier}")
    if not fichiers:
        return resultat

    journal = Journal(config.dossier_decoupe)
    candidats: list[Path] = []

    for index, chemin in enumerate(fichiers, start=1):
        _dire(f"  [{index}/{len(fichiers)}] {chemin.name}")
        try:
            candidats += _traiter_pdf(chemin, config, resultat, journal)
        except Exception as err:
            resultat.signaler("Lecture", "", f"Echec de lecture : {err}", chemin.name)

    journal.sauvegarder()

    if config.apparier_bons_de_livraison:
        recherches = appariement.bons_recherches(resultat.factures)
        _dire(f"Rapprochement de {len(recherches)} bon(s) parmi {len(candidats)} fichier(s)...")
        erreurs: list[tuple[Path, str]] = []
        resultat.pdf_bons = appariement.indexer(candidats, recherches, erreurs)
        appariement.rattacher(resultat.factures, resultat.pdf_bons)
        for chemin, message in erreurs:
            resultat.signaler("Lecture", "", f"Fichier illisible : {message}", chemin.name)

    controles.appliquer(resultat, config)
    return resultat


def _ouvrir(chemin: Path) -> None:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(chemin))  # noqa: S606 - ouverture du tableur produit
        elif sys.platform == "darwin":
            subprocess.run(["open", str(chemin)], check=False)
        else:
            subprocess.run(["xdg-open", str(chemin)], check=False)
    except Exception:
        _dire("Le tableur n'a pas pu etre ouvert automatiquement, ouvrez-le a la main.")


def _resumer(resultat: Resultat, cible: Path) -> None:
    bons = sum(len(f.livraisons) for f in resultat.factures)
    rapproches = sum(1 for f in resultat.factures for l in f.livraisons if l.pdf_bon)
    volume = sum(f.volume_total or 0 for f in resultat.factures)
    montant = sum(f.total_ht or 0 for f in resultat.factures)
    _dire()
    _dire("=" * 62)
    _dire(f"  Factures lues .................. {len(resultat.factures)}")
    _dire(f"  Bons de livraison extraits ..... {bons}")
    _dire(f"  Bons rapproches d'un PDF ....... {rapproches}")
    _dire(f"  Volume total ................... {volume:.3f} m3")
    _dire(f"  Total HT ....................... {montant:.2f} EUR")
    _dire(f"  Anomalies a verifier ........... {len(resultat.anomalies)}")
    _dire("=" * 62)
    _dire(f"  Tableur : {cible}")
    if resultat.anomalies:
        _dire("  Consultez l'onglet « A verifier » du tableur.")
    _dire()


def _diagnostic(chemin: Path, config: Config) -> int:
    """Affiche le contenu d'un PDF pour recalibrer les bornes de colonnes."""
    if not chemin.is_file():
        _dire(f"Fichier introuvable : {chemin}")
        return 1
    pages = lecture_pdf.lire(chemin, config)
    _dire(f"{chemin.name} : {len(pages)} page(s)")
    for page in pages:
        _dire()
        _dire("=" * 78)
        _dire(f"PAGE {page.numero} - {page.largeur:.0f} x {page.hauteur:.0f} points")
        entete = page.entete
        _dire(
            f"  ligne technique : facture={entete.numero_facture!r} type={entete.type_page!r} "
            f"date={entete.date_facture} ttc={entete.total_ttc}"
        )
        _dire("=" * 78)
        for ligne in page.lignes:
            _dire(f"  y={ligne.haut:7.2f}  {ligne.texte}")
            for nom, valeur in ligne.cellules.items():
                _dire(f"            [{nom}] {valeur!r}")
            for mot in sorted(ligne.mots, key=lambda m: m.x0):
                _dire(f"                x0={mot.x0:6.2f} x1={mot.x1:6.2f}  {mot.texte!r}")
    return 0


def _mode_demo(config: Config) -> Config:
    from . import demo

    dossier = Path(tempfile.gettempdir()) / "demo-factures-lafarge"
    _dire(f"Mode demonstration : creation de factures d'essai dans {dossier}")
    for ancien in dossier.rglob("*.pdf"):
        ancien.unlink()
    demo.generer(dossier)
    config.dossier = dossier
    return config


def executer(arguments: list[str]) -> int:
    try:
        config = charger()
    except ConfigInvalide as err:
        _dire(f"ERREUR : {err}")
        return 2

    mode = arguments[0].lower() if arguments else ""

    if mode == "diagnostic":
        if len(arguments) < 2:
            _dire('Usage : LANCER.bat diagnostic "chemin\\vers\\facture.pdf"')
            return 1
        return _diagnostic(Path(arguments[1]), config)

    if mode == "demo":
        config = _mode_demo(config)
    else:
        dossier = _resoudre_dossier(config)
        if dossier is None:
            return 1
        config.dossier = dossier

    cible = config.dossier / excel.nom_fichier(config)
    if excel.verrouille(cible):
        # Prevenir maintenant plutot qu'apres plusieurs minutes de lecture.
        _dire()
        _dire(f"ATTENTION : {cible.name} est ouvert dans Excel.")
        _dire("Fermez-le pour qu'il soit mis a jour ; sinon un fichier voisin sera cree.")
        _dire()

    resultat = analyser(config)
    if not resultat.factures and not resultat.anomalies:
        _dire("Aucune facture Lafarge n'a ete trouvee dans ce dossier.")
        return 1

    try:
        ecrit = excel.ecrire(resultat, config, cible)
    except excel.TableurVerrouille as err:
        _dire()
        _dire(f"ERREUR : {err}")
        return 4

    if ecrit != cible:
        _dire()
        _dire(f"{cible.name} etant ouvert dans Excel, le tableur a ete enregistre")
        _dire(f"sous {ecrit.name}. Fermez Excel avant de relancer pour retrouver")
        _dire("le nom habituel.")

    _resumer(resultat, ecrit)

    if config.ouvrir_tableur_a_la_fin:
        _ouvrir(ecrit)
    return 0


def main() -> int:
    try:
        return executer(sys.argv[1:])
    except KeyboardInterrupt:
        _dire("Interrompu.")
        return 130
    except Exception:
        _dire("ERREUR INATTENDUE :")
        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
