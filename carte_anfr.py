# =============================================================================
# CARTE INTERACTIVE DES SITES ANFR (Python + folium uniquement, sans JavaScript)
#
# Ce fichier :
#   1. lit data/sup_support.txt et ref/sup_proprietaire.txt
#   2. crée la carte (fond IGN, vue limitée à la France)
#   3. place un rond par site, rangé dans une "couche" par propriétaire
#   4. enregistre le résultat dans "carte.html"
#
# Interactions fournies par folium lui-même :
#   - clic sur un point    -> fenêtre avec les détails du site
#   - sélecteur en haut à droite -> cocher / décocher chaque propriétaire (filtres)
#
# Où le placer : à la racine du projet, à côté des dossiers "data" et "ref"
#   SAE15/
#   ├── carte_anfr.py
#   ├── data/sup_support.txt
#   └── ref/sup_proprietaire.txt
#
# Pour lancer :  python carte_anfr.py   puis ouvrir carte.html
# =============================================================================

import colorsys
import html
from pathlib import Path

import folium
import pandas as pd


# =============================================================================
# 0. RÉGLAGES (les seules lignes à modifier en temps normal)
# =============================================================================

# Les fichiers de données, cherchés à côté de ce script
FICHIER_SUPPORT = Path(__file__).parent / "data" / "sup_support.txt"
FICHIER_PROPRIETAIRE = Path(__file__).parent / "ref" / "sup_proprietaire.txt"

# Le département à afficher : les premiers chiffres du code INSEE de la commune
# Exemples : "69" (Rhône), "13" (Bouches-du-Rhône), "2A" (Corse-du-Sud), "971" (Guadeloupe)
DEPARTEMENT = "76"

# Nombre maximum de points affichés.
# Ici chaque point est écrit un par un dans la page : au-delà de quelques milliers,
# la page devient lourde et lente à générer.
MAX_POINTS = 5000

# Propriétaires cochés au départ : None = tous, ou une liste de noms exacts
# Exemple : ["Orange", "SFR"] (les autres sont dans la liste, mais décochés)
PROPRIETAIRES_AFFICHES = None


# =============================================================================
# 1. LA LECTURE DES DONNÉES
# =============================================================================

def lire_fichier(chemin):
    """Lit un fichier ANFR (séparateur ;) en gardant tout en texte."""
    try:
        return pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8")
    except UnicodeDecodeError:
        # Certains fichiers ANFR sont en Windows-1252 au lieu d'UTF-8
        return pd.read_csv(chemin, sep=";", dtype=str, encoding="cp1252")


def nombre(serie):
    """Convertit une colonne de texte en nombres (accepte la virgule décimale)."""
    return pd.to_numeric(serie.str.replace(",", ".", regex=False), errors="coerce")


def dms_en_decimal(degres, minutes, secondes, hemisphere):
    """Convertit des degrés / minutes / secondes en degrés décimaux.

    Exemple : 45° 41' 43" N  ->  45.695278
    Les hémisphères S (sud) et W (ouest) donnent un nombre négatif.
    """
    valeur = nombre(degres) + nombre(minutes) / 60 + nombre(secondes) / 3600
    return valeur.where(~hemisphere.isin(["S", "W"]), -valeur)


def charger_proprietaires():
    """Lit ref/sup_proprietaire.txt et retourne un dictionnaire {code: nom}.

    Si le fichier est absent ou de format inattendu, retourne un dictionnaire vide :
    les filtres afficheront alors les codes à la place des noms.
    """
    if not FICHIER_PROPRIETAIRE.exists():
        print(f"Attention : {FICHIER_PROPRIETAIRE} introuvable, les filtres afficheront des codes.")
        return {}

    ref = lire_fichier(FICHIER_PROPRIETAIRE)
    print("Colonnes de sup_proprietaire :", list(ref.columns))
    if len(ref.columns) < 2:
        print("Attention : format inattendu (une seule colonne), les filtres afficheront des codes.")
        return {}

    # Colonne du code : TPO_ID si elle existe, sinon la première colonne
    col_code = "TPO_ID" if "TPO_ID" in ref.columns else ref.columns[0]
    # Colonne du nom : la première colonne finissant par _LB, sinon la suivante
    autres = [c for c in ref.columns if c != col_code]
    col_nom = next((c for c in autres if c.endswith("_LB")), autres[0])
    print(f"Code : {col_code}  /  Nom : {col_nom}")

    ref = ref.dropna(subset=[col_code, col_nom])
    return dict(zip(ref[col_code].str.strip(), ref[col_nom].str.strip()))


def charger_points():
    """Retourne la liste des points (un dictionnaire par site) à afficher."""
    if not FICHIER_SUPPORT.exists():
        raise SystemExit(f"Fichier introuvable : {FICHIER_SUPPORT}")

    df = lire_fichier(FICHIER_SUPPORT)
    print(f"{len(df)} lignes lues dans {FICHIER_SUPPORT.name}")

    # Une ligne du fichier = un support + une station.
    # Un même support apparaît donc plusieurs fois : on compte ses stations...
    nb_stations = df.groupby("SUP_ID").size()
    # ... puis on ne garde qu'une ligne par support (un point par site)
    df = df.drop_duplicates(subset="SUP_ID").copy()
    print(f"{len(df)} sites uniques")

    # Filtre sur le département (début du code INSEE de la commune)
    if DEPARTEMENT:
        df = df[df["COM_CD_INSEE"].str.startswith(DEPARTEMENT)].copy()
        print(f"{len(df)} sites dans le département {DEPARTEMENT}")

    # Conversion des coordonnées : degrés/minutes/secondes -> degrés décimaux
    df["lat"] = dms_en_decimal(df["COR_NB_DG_LAT"], df["COR_NB_MN_LAT"],
                               df["COR_NB_SC_LAT"], df["COR_CD_NS_LAT"])
    df["lon"] = dms_en_decimal(df["COR_NB_DG_LON"], df["COR_NB_MN_LON"],
                               df["COR_NB_SC_LON"], df["COR_CD_EW_LON"])
    df = df.dropna(subset=["lat", "lon"])          # On retire les coordonnées illisibles

    # Limite de sécurité sur le nombre de points
    if len(df) > MAX_POINTS:
        print(f"Limitation à {MAX_POINTS} points (voir MAX_POINTS)")
        df = df.head(MAX_POINTS)

    # Table de traduction : code du propriétaire -> nom
    proprietaires = charger_proprietaires()

    # Construction de la liste de points
    points = []
    for _, ligne in df.iterrows():
        # Adresse : on assemble les morceaux non vides
        morceaux = [ligne["ADR_LB_LIEU"], ligne["ADR_LB_ADD1"], ligne["ADR_LB_ADD2"],
                    ligne["ADR_LB_ADD3"], ligne["ADR_NM_CP"]]
        adresse = ", ".join(m for m in morceaux if isinstance(m, str) and m.strip())

        # Code du propriétaire du support (vide si non renseigné)
        code_tpo = ligne["TPO_ID"].strip() if isinstance(ligne["TPO_ID"], str) else ""

        points.append({
            "nom": f"Support n° {ligne['SUP_ID']}",       # Titre affiché dans la fenêtre
            "lat": round(float(ligne["lat"]), 6),
            "lon": round(float(ligne["lon"]), 6),
            # Les champs suivants s'affichent tous dans la fenêtre de détails
            "Adresse": adresse,
            "Propriétaire": proprietaires.get(code_tpo, code_tpo) or "Non renseigné",
            "Hauteur (m)": ligne["SUP_NM_HAUT"] if isinstance(ligne["SUP_NM_HAUT"], str) else "",
            "Nature (code)": ligne["NAT_ID"],
            "Code INSEE commune": ligne["COM_CD_INSEE"],
            "Stations sur le site": int(nb_stations[ligne["SUP_ID"]]),
        })
    return points


# =============================================================================
# 2. OUTILS POUR L'AFFICHAGE
# =============================================================================

def couleur(i):
    """Génère une couleur bien distincte pour le i-ème élément de la liste."""
    teinte = (i * 0.618033988749895) % 1            # Le nombre d'or écarte bien les teintes successives
    r, g, b = colorsys.hls_to_rgb(teinte, 0.45, 0.75)
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def texte_sur(valeur):
    """Rend un texte sans danger pour l'affichage dans la page.

    html.escape neutralise les caractères spéciaux du HTML (< > & "),
    et on retire ceux qui pourraient casser le code généré par folium (` et \\).
    """
    return html.escape(str(valeur)).replace("`", "'").replace("\\", "/")


def fenetre_details(point):
    """Construit le texte de la fenêtre qui s'ouvre au clic sur un point."""
    lignes = [f"<h4 style='margin:0 0 6px'>{texte_sur(point['nom'])}</h4>"]
    for cle, valeur in point.items():
        if cle not in ("nom", "lat", "lon"):          # Tous les champs sauf nom et coordonnées
            lignes.append(f"<b>{texte_sur(cle)} :</b> {texte_sur(valeur)}<br>")
    lignes.append(f"<b>Coordonnées :</b> {point['lat']}, {point['lon']}")
    return "".join(lignes)


# =============================================================================
# 3. LA CARTE
# =============================================================================

URL_IGN = (
    "https://data.geopf.fr/wmts?REQUEST=GetTile&SERVICE=WMTS&VERSION=1.0.0"
    "&STYLE=normal&TILEMATRIXSET=PM&FORMAT=image/png"
    "&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2"
    "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}"
)

POINTS = charger_points()
print(f"{len(POINTS)} points à afficher")

carte = folium.Map(
    location=[46.6, 2.5],        # Centre de départ (on recadrera sur les points ensuite)
    zoom_start=6,
    min_zoom=5,
    min_lat=41, max_lat=52,      # Limites : France métropolitaine
    min_lon=-6, max_lon=10.5,    # (à retirer si tu affiches l'outre-mer)
    max_bounds=True,
    tiles=None,                  # Pas de fond par défaut : on ajoute celui de l'IGN
    prefer_canvas=True,          # Dessin plus rapide quand il y a beaucoup de points
)

folium.TileLayer(
    tiles=URL_IGN,
    attr="© IGN - Géoplateforme",
    name="Plan IGN",
    control=False,               # Le fond n'apparaît pas dans le sélecteur de couches
).add_to(carte)


# =============================================================================
# 4. LES POINTS, RANGÉS PAR PROPRIÉTAIRE
# =============================================================================

# On regroupe les points par propriétaire : {nom du propriétaire: [points]}
par_proprietaire = {}
for p in POINTS:
    par_proprietaire.setdefault(p["Propriétaire"], []).append(p)

# Une couche (FeatureGroup) par propriétaire, triée par ordre alphabétique.
# Chaque couche devient une case à cocher dans le sélecteur en haut à droite.
for i, nom in enumerate(sorted(par_proprietaire)):
    liste = par_proprietaire[nom]
    teinte = couleur(i)

    # Le nom de la couche : pastille de couleur + nom + nombre de sites
    etiquette = f"<span style='color:{teinte}'>&#9679;</span> {texte_sur(nom)} ({len(liste)})"
    coche = PROPRIETAIRES_AFFICHES is None or nom in PROPRIETAIRES_AFFICHES
    couche = folium.FeatureGroup(name=etiquette, show=coche).add_to(carte)

    for p in liste:
        folium.CircleMarker(
            location=[p["lat"], p["lon"]],
            radius=6,
            color="#333333", weight=1,                       # Contour du rond
            fill=True, fill_color=teinte, fill_opacity=0.85,  # Remplissage coloré
            tooltip=texte_sur(p["nom"]),                     # Texte au survol
            popup=folium.Popup(fenetre_details(p), max_width=320),  # Fenêtre au clic
        ).add_to(couche)

# Le sélecteur de couches : toujours déplié, en haut à droite
folium.LayerControl(position="topright", collapsed=False).add_to(carte)

# On recadre la carte sur l'ensemble des points affichés
if POINTS:
    carte.fit_bounds([
        [min(p["lat"] for p in POINTS), min(p["lon"] for p in POINTS)],
        [max(p["lat"] for p in POINTS), max(p["lon"] for p in POINTS)],
    ])


# =============================================================================
# 5. L'ENREGISTREMENT
# =============================================================================

carte.save("carte.html")
print("Carte générée : carte.html")
