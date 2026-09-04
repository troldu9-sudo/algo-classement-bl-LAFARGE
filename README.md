# Suivi des bons de livraison Lafarge

Cet outil lit les factures Lafarge en PDF déposées dans votre dossier de suivi béton, en
extrait tous les bons de livraison associés, et produit un **tableur Excel** de suivi avec
des liens cliquables vers chaque document.

Il se lance **en double-cliquant sur `LANCER.bat`**.

---

## Première utilisation

1. Double-cliquez sur **`LANCER.bat`**.
2. La première fois, l'outil installe ce dont il a besoin — comptez une minute. Les fois
   suivantes, il démarre immédiatement.
3. Le tableur s'ouvre tout seul à la fin.

Si un message vous dit que **Python n'est pas installé**, deux solutions :

- l'installer depuis [python.org](https://www.python.org/downloads/) en cochant bien
  **« Add python.exe to PATH »** sur le premier écran ;
- ou utiliser la **version `.exe` autonome**, qui ne demande aucune installation
  (voir plus bas).

## Utilisation courante

Déposez vos factures PDF dans :

```
C:\Users\A.MOLIA\OneDrive - BYCN\Documents\sUIVI BETON\FA-Lafarge\
```

puis double-cliquez sur `LANCER.bat`. Vous obtenez à la racine de ce dossier un fichier
`Suivi-Lafarge_2026-08-05.xlsx` (avec la date du jour).

Vous pouvez relancer l'outil autant de fois que vous voulez : il repart des fichiers
présents et ne refait pas deux fois le même travail.

---

## Ce que contient le tableur

| Onglet | À quoi il sert |
|---|---|
| **Synthèse** | Une ligne par facture : numéro, date, échéance, client, chantiers, nombre de bons, volume, HT / TVA / TTC |
| **Detail BL** | **L'onglet principal.** Une ligne par bon de livraison : n° de bon, date de livraison, site expéditeur, chantier, désignation du béton, m³, prix unitaire, montant, indicateurs CO2, et les liens vers les PDF |
| **Lignes annexes** | Forfaits de livraison et contributions environnementales, rattachés à leur chantier |
| **A verifier** | Tout ce qui mérite un coup d'œil (voir ci-dessous) |
| **Parametres** | Les réglages utilisés et la date d'exécution, pour retrouver comment un tableur a été produit |

Les colonnes **PDF facture** et **PDF bon** sont cliquables : un clic ouvre le document.

### La colonne N° Bon

Elle ne contient **que le numéro du bon**, rien d'autre. La colonne N° Bon des factures
Lafarge ramène en effet deux choses parasites :

- un **préfixe de centrale** (`CE 123482`) ;
- le **début du libellé collé au numéro** (`123482Retour`, `147375PHeure`, `158022PM3`,
  `244892Annulati`, `158010A7`…).

L'outil isole le numéro et l'écrit seul : `123482`, `147375`, `158022`. Le texte qui suivait
le numéro n'est pas jeté pour autant — il rejoint la colonne **Designation** de la même
ligne, à laquelle il appartient.

Le numéro est écrit en **texte** et non en nombre : c'est un identifiant, jamais une
grandeur à additionner, et la colonne reste ainsi homogène quel que soit le bon.

Un même bon peut apparaître sur plusieurs lignes : c'est normal quand une livraison
couvre plusieurs produits.

### L'onglet « A verifier »

C'est le garde-fou de l'outil. **Rien n'est jamais écarté en silence** : ce qui n'a pas pu
être lu ou ne se recoupe pas y apparaît noir sur blanc, plutôt que de manquer discrètement
dans un total. Vous y trouverez notamment :

- une somme de lignes qui ne tombe pas sur le total HT de la facture ;
- un total HT + TVA qui ne donne pas le TTC ;
- un bon de livraison dont le PDF n'a pas été retrouvé ;
- un PDF scanné en image, donc illisible automatiquement ;
- une facture présente en double dans le dossier.

Si cet onglet est vide, tout se recoupe.

---

## Ce que l'outil fait de vos fichiers

**Il ne déplace, ne renomme et ne supprime jamais rien.** Vos PDF restent exactement où
ils sont.

La seule chose qu'il **écrit** :

- le tableur `Suivi-Lafarge_<date>.xlsx` à la racine du dossier ;
- si un PDF contient **plusieurs factures à la suite** (téléchargement groupé), un PDF par
  facture dans un sous-dossier `_Factures-decoupees\`, les pages de conditions générales
  étant écartées. Le fichier d'origine reste intact à sa place.

---

## Réglages

Le fichier **`config.json`** s'ouvre au Bloc-notes. Les réglages courants :

| Réglage | Effet |
|---|---|
| `dossier` | Le dossier analysé. S'il est introuvable, une fenêtre vous demande de le choisir |
| `decouper_pdf_groupes` | Mettre `false` pour ne pas découper les PDF contenant plusieurs factures |
| `apparier_bons_de_livraison` | Mettre `false` pour ne pas chercher les PDF de bons dans le dossier |
| `ouvrir_tableur_a_la_fin` | Mettre `false` pour ne pas ouvrir Excel automatiquement |
| `tolerance_totaux` | Écart en euros toléré avant de signaler une incohérence (0,02 € par défaut) |
| `longueur_min_numero_bon` | Nombre minimum de chiffres d'un numéro de bon (4 par défaut). Empêche de confondre le numéro avec les chiffres d'un code collé comme `M3`, `R4` ou `A7` |

Les sections `colonnes` et `motifs` décrivent la mise en page des factures Lafarge. Vous
n'avez normalement pas à y toucher — sauf si Lafarge change la présentation de ses
factures, auquel cas voyez le mode diagnostic ci-dessous.

---

## Si le tableur est déjà ouvert dans Excel

C'est le cas le plus courant, puisque l'outil ouvre lui-même le tableur à la fin : au
lancement suivant, Excel tient encore le fichier et Windows en interdit la réécriture.

L'outil ne perd pas votre exécution pour autant :

- il vous **prévient dès le départ**, avant de relire tout le dossier ;
- à la fin, il enregistre sous un nom voisin — `Suivi-Lafarge_2026-08-05_2.xlsx` — et vous
  dit lequel il a écrit.

Pour retrouver le nom habituel, fermez simplement Excel avant de relancer. Les fichiers
`_2`, `_3`… ne servent à rien une fois lus : vous pouvez les supprimer.

Si l'outil signale qu'aucun nom n'est utilisable, c'est que le dossier est en lecture
seule ou que OneDrive n'a pas fini de synchroniser.

## Si une valeur est mal lue

Ouvrez une invite de commandes dans ce dossier et lancez :

```
LANCER.bat diagnostic "C:\Users\A.MOLIA\OneDrive - BYCN\Documents\sUIVI BETON\FA-Lafarge\ma-facture.pdf"
```

L'outil affiche, pour chaque ligne du PDF, le texte lu, la colonne dans laquelle chaque
valeur a été rangée, et la position exacte de chaque mot en points.

Repérez la valeur mal placée, notez sa position `x0` (bord gauche) ou `x1` (bord droit),
et ajustez les bornes `min` / `max` de la colonne concernée dans `config.json`. Les
colonnes de nombres utilisent `"repere": "droite"` : c'est leur bord droit qui compte, car
c'est lui qui reste stable quel que soit le nombre de chiffres.

## Voir l'outil fonctionner avant de l'utiliser

```
LANCER.bat demo
```

Fabrique un jeu de factures d'essai — dont une à plusieurs chantiers, une à deux taux de
TVA et un téléchargement groupé de trois factures — puis déroule toute la chaîne et ouvre
le tableur obtenu. Rien n'est touché dans vos vrais dossiers.

---

## Version `.exe` autonome

Si votre service informatique n'autorise pas l'installation de Python :

1. Rendez-vous sur l'onglet **Actions** du dépôt GitHub.
2. Ouvrez la dernière exécution de « Construire le .exe Windows ».
3. Téléchargez l'artefact **Suivi-Lafarge-windows**.
4. Décompressez-le : vous obtenez `Suivi-Lafarge.exe` et `config.json`. **Gardez les deux
   dans le même dossier** — c'est ce `config.json` que l'exécutable lit.

---

## Pour le développeur

```
pip install -r requirements.txt pytest
python -m pytest tests/ -q
```

Les tests tournent sur des factures fabriquées par `src/demo.py`, qui reproduisent la
géométrie relevée sur une facture Lafarge réelle (abscisses des colonnes, caractères
espace entre colonnes, séparateurs de milliers, code TVA décalé en hauteur).

Pour valider aussi sur de vrais documents, déposez des PDF dans `tests/fixtures/reel/` :
les tests de `test_facture_reelle.py` s'activent alors automatiquement. Ce dossier est
exclu du dépôt, une facture contenant des données commerciales et bancaires.

### Comment la lecture fonctionne

Chaque page d'une facture Lafarge porte une ligne technique de dématérialisation,
invisible à l'impression :

```
@@@@@;92506;C281043473;1900200711;;;FA;1;2026-06-30;DJ;FR70;481,34;
```

Elle donne le numéro de facture, le **type de page** (`FA` = facture, `CG` = conditions
générales), la date et le total TTC, sans dépendre de la mise en page. C'est elle qui rend
le découpage des PDF groupés et l'élimination des conditions générales **déterministes**
plutôt qu'approximatifs, et elle sert de contre-vérification aux valeurs lues à l'écran.

Le tableau des livraisons, lui, est lu **par bornes de colonnes** et non par expressions
régulières : les colonnes de nombres étant alignées à droite dans le PDF, un montant à
cinq chiffres ne peut pas déborder sur la colonne voisine.
