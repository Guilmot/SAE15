# =============================================================================
# CARTE INTERACTIVE DES ANTENNES ANFR (un seul fichier, Python + folium, sans JavaScript)
#
# Ce fichier fait tout :
#   - lit les fichiers ANFR des dossiers "data" et "ref"
#   - fabrique pour chaque site le texte de sa fenêtre de détails
#     (support, stations, antennes, émetteurs, bandes de fréquences)
#   - dessine la carte : vue satellite IGN, tous les sites ANFR (monde entier) regroupés
#     en "clusters" (bulles numérotées) quand on dézoome, zone de recherche (pour plus tard)
#   - détails au clic pour les départements choisis (épingles rouges)
#
# Arborescence attendue (celle d'origine, inchangée) :
#   SAE15/
#   ├── carte_anfr.py       (ce fichier)
#   ├── data/
#   │   ├── sup_support.txt     (sites : coordonnées, adresse, hauteur, propriétaire)
#   │   ├── sup_station.txt     (stations installées sur un site : exploitant, dates)
#   │   ├── sup_antenne.txt     (antennes de chaque station)
#   │   ├── sup_emetteur.txt    (émetteurs : système radio, date de service)
#   │   └── sup_bande.txt       (bandes de fréquences de chaque émetteur)
#   └── ref/
#       ├── sup_nature.txt        (traduit NAT_ID : nature du support)
#       ├── sup_proprietaire.txt  (traduit TPO_ID : propriétaire du support)
#       ├── sup_exploitant.txt    (traduit ADM_ID : exploitant de la station)
#       └── sup_type_antenne.txt  (traduit TAE_ID : type d'antenne)
#
# Les liens entre fichiers (la hiérarchie de l'ANFR) :
#   support --STA_NM_ANFR--> station --(STA_NM_ANFR, AER_ID)--> antenne
#   antenne --(STA_NM_ANFR, AER_ID)--> émetteur --EMR_ID--> bande
#
# Pour lancer :  python carte_anfr.py   puis ouvrir carte.html
# =============================================================================

import html
from pathlib import Path

import folium
import pandas as pd
from folium.plugins import FastMarkerCluster, MarkerCluster


# =============================================================================
# 0. RÉGLAGES (les seules lignes à modifier en temps normal)
# =============================================================================

# Départements dont les sites ont leur fenêtre de DÉTAILS au clic (épingles rouges) :
# liste des premiers chiffres du code INSEE
# Exemples : ["69"] (Rhône), ["69", "42"], ["2A"] (Corse-du-Sud), ["971"] (Guadeloupe)
# None = pas de filtre (les MAX_POINTS premiers sites du fichier auront leurs détails)
DEPARTEMENTS = ["69"]

# Propriétaires à afficher : None = tous, ou une liste de noms exacts
# Exemple : ["ORANGE", "SFR"]  (la liste des plus présents s'affiche au lancement)
PROPRIETAIRES_AFFICHES = None

# Nombre maximum de sites affichés : chaque site porte sa propre fenêtre de détails,
# qui est écrite dans la page. Au-delà de quelques milliers, la page devient très lourde.
MAX_POINTS = 5000

# True = affiche aussi TOUS les autres sites du fichier (monde entier : métropole et
# outre-mer), en position seule (épingles bleues regroupées en clusters, sans détails).
# False = n'affiche que les sites des départements choisis ci-dessus.
AFFICHER_TOUS_LES_SITES = True

# Réglages techniques (rarement à modifier)
RACINE = Path(__file__).parent          # Le dossier de ce fichier
DOSSIER_DATA = RACINE / "data"
DOSSIER_REF = RACINE / "ref"
TAILLE_PAQUET = 500_000                 # Lignes lues à la fois dans les gros fichiers
MAX_STATIONS_AFFICHEES = 30             # Au-delà, la fenêtre d'un site résume le reste
UNITES = {"K": "kHz", "M": "MHz", "G": "GHz"}   # Unités de fréquence du fichier sup_bande


# =============================================================================
# 1. OUTILS DE LECTURE
# =============================================================================

def lire_fichier(chemin):
    """Lit un fichier ANFR entier (séparateur ;), tout en texte."""
    if not chemin.exists():
        raise SystemExit(f"Fichier introuvable : {chemin}")
    try:
        return pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8")
    except UnicodeDecodeError:
        # Certains fichiers ANFR sont en Windows-1252 au lieu d'UTF-8
        return pd.read_csv(chemin, sep=";", dtype=str, encoding="cp1252")


def lire_filtre(chemin, colonne, valeurs):
    """Lit un gros fichier par paquets et ne garde que les lignes utiles.

    On ne garde que les lignes dont la colonne `colonne` est dans `valeurs`
    (par exemple les stations des sites affichés) : la mémoire reste raisonnable
    même pour le fichier des bandes (plus de 4 millions de lignes).
    """
    if not chemin.exists():
        raise SystemExit(f"Fichier introuvable : {chemin}")
    for encodage in ("utf-8", "cp1252"):
        try:
            paquets = pd.read_csv(chemin, sep=";", dtype=str, encoding=encodage,
                                  chunksize=TAILLE_PAQUET)
            return pd.concat([p[p[colonne].isin(valeurs)] for p in paquets],
                             ignore_index=True)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"Encodage illisible : {chemin}")


def charger_table(nom_fichier, col_code, col_nom):
    """Lit une table de référence du dossier ref et retourne {code: libellé}."""
    table = lire_fichier(DOSSIER_REF / nom_fichier).dropna(subset=[col_code, col_nom])
    return dict(zip(table[col_code].str.strip(), table[col_nom].str.strip()))


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


# =============================================================================
# 2. OUTILS D'AFFICHAGE (HTML)
# =============================================================================

def renseigne(valeur):
    """Vrai si la valeur est un texte non vide (les cases vides sont lues comme NaN)."""
    return isinstance(valeur, str) and valeur.strip() != ""


def h(valeur):
    """Rend une valeur sûre pour l'affichage HTML (neutralise < > & ")."""
    return html.escape(str(valeur)) if renseigne(valeur) else ""


def ligne(titre, valeur):
    """Une ligne « titre : valeur », ou rien si la valeur est vide."""
    return f"<b>{titre} :</b> {h(valeur)}<br>" if renseigne(valeur) else ""


def format_bande(b):
    """Met en forme une bande de fréquences, par exemple « 1805–1880 MHz »."""
    unite = UNITES.get(b["BAN_FG_UNITE"], b["BAN_FG_UNITE"] if renseigne(b["BAN_FG_UNITE"]) else "")
    debut, fin = b["BAN_NB_F_DEB"], b["BAN_NB_F_FIN"]
    if renseigne(debut) and renseigne(fin):
        return f"{h(debut)}–{h(fin)} {h(unite)}".strip()
    return f"{h(debut)} {h(unite)}".strip()


# =============================================================================
# 3. LES SITES (fichier sup_support)
# =============================================================================

def charger_sites(departements, proprietaires_affiches, max_points, ref):
    """Retourne (details, liens, autres) :
      - details : les sites dont on affiche les détails au clic
      - liens   : les stations de ces sites (pour aller chercher leurs détails)
      - autres  : tous les autres sites du fichier (position seule)
    """
    df = lire_fichier(DOSSIER_DATA / "sup_support.txt")
    print(f"{len(df)} lignes lues dans sup_support.txt")

    # Une ligne du fichier = un support + une station : un même support apparaît
    # autant de fois qu'il porte de stations. On garde la liste de ces liens...
    liens_tous = df[["SUP_ID", "STA_NM_ANFR"]].drop_duplicates()
    # ... et une seule ligne par support pour dessiner les points
    sites = df.drop_duplicates(subset="SUP_ID").copy()
    print(f"{len(sites)} sites uniques")

    # Conversion des coordonnées : degrés/minutes/secondes -> degrés décimaux
    sites["lat"] = dms_en_decimal(sites["COR_NB_DG_LAT"], sites["COR_NB_MN_LAT"],
                                  sites["COR_NB_SC_LAT"], sites["COR_CD_NS_LAT"])
    sites["lon"] = dms_en_decimal(sites["COR_NB_DG_LON"], sites["COR_NB_MN_LON"],
                                  sites["COR_NB_SC_LON"], sites["COR_CD_EW_LON"])
    sites = sites.dropna(subset=["lat", "lon"]).copy()    # Coordonnées illisibles : on retire

    # Nom du propriétaire (traduit avec ref/sup_proprietaire.txt)
    codes = sites["TPO_ID"].fillna("").str.strip()
    sites["proprietaire"] = codes.map(lambda c: ref["proprietaire"].get(c, c) or "Non renseigné")
    print("Propriétaires les plus présents :",
          sites["proprietaire"].value_counts().head(8).to_dict())

    # Sites dont on affiche les détails : filtre départements, propriétaires, limite
    details = sites
    if departements:
        details = details[details["COM_CD_INSEE"].str.startswith(tuple(departements))]
        print(f"{len(details)} sites dans les départements {departements}")
    if proprietaires_affiches is not None:
        details = details[details["proprietaire"].isin(proprietaires_affiches)]
        print(f"{len(details)} sites pour les propriétaires {proprietaires_affiches}")
    if max_points and len(details) > max_points:
        print(f"Limitation à {max_points} sites détaillés (voir MAX_POINTS en haut du fichier)")
        details = details.head(max_points)
    details = details.copy()

    liens = liens_tous[liens_tous["SUP_ID"].isin(details["SUP_ID"])]
    autres = sites[~sites["SUP_ID"].isin(details["SUP_ID"])]
    return details, liens, autres


# =============================================================================
# 4. LES DÉTAILS DE CHAQUE SITE (stations, antennes, émetteurs, bandes)
# =============================================================================

def charger_details(stations):
    """Lit les 4 fichiers de détails, en ne gardant que les stations demandées."""
    print(f"Lecture des détails pour {len(stations)} stations...")
    station = lire_filtre(DOSSIER_DATA / "sup_station.txt", "STA_NM_ANFR", stations)
    antenne = lire_filtre(DOSSIER_DATA / "sup_antenne.txt", "STA_NM_ANFR", stations)
    emetteur = lire_filtre(DOSSIER_DATA / "sup_emetteur.txt", "STA_NM_ANFR", stations)
    bande = lire_filtre(DOSSIER_DATA / "sup_bande.txt", "STA_NM_ANFR", stations)
    print(f"  {len(station)} stations, {len(antenne)} antennes, "
          f"{len(emetteur)} émetteurs, {len(bande)} bandes")

    # Dictionnaires pour retrouver instantanément les lignes d'une station ou d'un émetteur
    antenne = antenne.drop_duplicates(subset=["STA_NM_ANFR", "AER_ID"])
    return {
        "station": station.set_index("STA_NM_ANFR").to_dict("index"),
        "antennes": {k: g.to_dict("records") for k, g in antenne.groupby("STA_NM_ANFR")},
        "emetteurs": {k: g.to_dict("records") for k, g in emetteur.groupby("STA_NM_ANFR")},
        "bandes": {k: g.to_dict("records") for k, g in bande.groupby("EMR_ID")},
    }


def html_emetteur(emetteur, details):
    """Une ligne par émetteur : système radio, date de service, bandes de fréquences."""
    morceaux = [f"<b>{h(emetteur['EMR_LB_SYSTEME'])}</b>"]
    if renseigne(emetteur["EMR_DT_SERVICE"]):
        morceaux.append(f"service le {h(emetteur['EMR_DT_SERVICE'])}")
    bandes = [format_bande(b) for b in details["bandes"].get(emetteur["EMR_ID"], [])]
    if bandes:
        morceaux.append(" ; ".join(bandes))
    return "<div style='margin-left:14px'>" + " — ".join(morceaux) + "</div>"


def html_antenne(antenne, emetteurs, ref, details):
    """Un bloc par antenne : ses caractéristiques, puis ses émetteurs."""
    type_antenne = ref["type_antenne"].get(antenne["TAE_ID"], f"type {antenne['TAE_ID']}")
    morceaux = [f"<u>{h(type_antenne)}</u>"]
    if renseigne(antenne["AER_NB_DIMENSION"]):
        morceaux.append(f"dimension {h(antenne['AER_NB_DIMENSION'])}")
    if renseigne(antenne["AER_NB_AZIMUT"]):
        morceaux.append(f"azimut {h(antenne['AER_NB_AZIMUT'])}°")
    if renseigne(antenne["AER_NB_ALT_BAS"]):
        morceaux.append(f"altitude basse {h(antenne['AER_NB_ALT_BAS'])}")
    bloc = "<div style='margin:4px 0 0 8px'>Antenne : " + ", ".join(morceaux)
    bloc += "".join(html_emetteur(e, details) for e in emetteurs) + "</div>"
    return bloc


def html_station(sta, ref, details):
    """Un bloc repliable par station : exploitant, dates, antennes, émetteurs, bandes."""
    info = details["station"].get(sta, {})
    exploitant = ref["exploitant"].get(info.get("ADM_ID"), "Exploitant inconnu")

    entete = (ligne("Implantée le", info.get("DTE_IMPLANTATION"))
              + ligne("Mise en service le", info.get("DTE_EN_SERVICE"))
              + ligne("Dernière modification le", info.get("DTE_MODIF"))
              + ligne("N° de demande (COMSIS)", info.get("DEM_NM_COMSIS")))

    # Les émetteurs sont rangés sous l'antenne qui porte le même AER_ID
    emetteurs = details["emetteurs"].get(sta, [])
    par_antenne = {}
    for e in emetteurs:
        par_antenne.setdefault(e["AER_ID"], []).append(e)

    antennes = details["antennes"].get(sta, [])
    corps = ""
    for a in antennes:
        corps += html_antenne(a, par_antenne.pop(a["AER_ID"], []), ref, details)

    # Émetteurs dont l'antenne n'est pas décrite dans sup_antenne
    restants = [e for liste in par_antenne.values() for e in liste]
    if restants:
        corps += ("<div style='margin:4px 0 0 8px'>Émetteurs sans antenne décrite :"
                  + "".join(html_emetteur(e, details) for e in restants) + "</div>")

    return (f"<details style='margin:4px 0'><summary><b>{h(exploitant)}</b> "
            f"— station {h(sta)}</summary><div style='margin:4px 0 0 8px'>"
            f"{entete}{corps}</div></details>")


def fenetre_site(site, stations, ref, details):
    """Construit le texte HTML de la fenêtre d'un site."""
    nature = ref["nature"].get((site["NAT_ID"] or "").strip(), site["NAT_ID"])
    morceaux_adresse = [site["ADR_LB_LIEU"], site["ADR_LB_ADD1"], site["ADR_LB_ADD2"],
                        site["ADR_LB_ADD3"], site["ADR_NM_CP"]]
    adresse = ", ".join(m for m in morceaux_adresse if renseigne(m))

    texte = f"<h4 style='margin:0 0 6px'>Support n° {h(site['SUP_ID'])}</h4>"
    texte += ligne("Nature", nature) + ligne("Adresse", adresse)
    texte += ligne("Propriétaire", site["proprietaire"])
    texte += ligne("Hauteur (m)", site["SUP_NM_HAUT"])
    texte += ligne("Code INSEE commune", site["COM_CD_INSEE"])
    texte += f"<b>Coordonnées :</b> {site['lat']:.5f}, {site['lon']:.5f}<br>"
    texte += f"<b>Stations sur le site :</b> {len(stations)}<hr style='margin:6px 0'>"

    # Les stations, triées par nom d'exploitant, limitées pour garder une fenêtre lisible
    def nom_exploitant(sta):
        return ref["exploitant"].get(details["station"].get(sta, {}).get("ADM_ID"), "~")
    stations = sorted(stations, key=nom_exploitant)
    for sta in stations[:MAX_STATIONS_AFFICHEES]:
        texte += html_station(sta, ref, details)
    if len(stations) > MAX_STATIONS_AFFICHEES:
        texte += f"<i>… et {len(stations) - MAX_STATIONS_AFFICHEES} autres stations non affichées</i>"

    # Habillage : largeur fixe, défilement si la fenêtre est longue
    texte = ("<div style='width:430px; max-height:320px; overflow:auto; "
             "font:13px Arial, sans-serif'>" + texte + "</div>")
    # Retire les caractères qui pourraient casser le code généré par folium
    return texte.replace("`", "'").replace("\\", "/").replace("${", "$ {")


# =============================================================================
# 5. FONCTION PRINCIPALE
# =============================================================================

def construire_sites(departements=None, proprietaires_affiches=None, max_points=None):
    """Retourne (sites, positions) :
      - sites : liste de dictionnaires (nom, lat, lon, popup) pour les sites détaillés
      - positions : liste [[lat, lon], ...] de tous les autres sites (position seule)
    """
    # Tables de référence (codes -> libellés), dossier ref
    ref = {
        "proprietaire": charger_table("sup_proprietaire.txt", "TPO_ID", "TPO_LB"),
        "nature": charger_table("sup_nature.txt", "NAT_ID", "NAT_LB_NOM"),
        "exploitant": charger_table("sup_exploitant.txt", "ADM_ID", "ADM_LB_NOM"),
        "type_antenne": charger_table("sup_type_antenne.txt", "TAE_ID", "TAE_LB"),
    }

    details_df, liens, autres = charger_sites(departements, proprietaires_affiches, max_points, ref)
    details = charger_details(set(liens["STA_NM_ANFR"]))

    stations_par_site = liens.groupby("SUP_ID")["STA_NM_ANFR"].apply(list).to_dict()

    sites = []
    for site in details_df.to_dict("records"):
        sites.append({
            "nom": f"Support n° {site['SUP_ID']}",
            "lat": round(float(site["lat"]), 6),
            "lon": round(float(site["lon"]), 6),
            "popup": fenetre_site(site, stations_par_site.get(site["SUP_ID"], []), ref, details),
        })

    # Les autres sites : seulement leurs coordonnées (légères à écrire dans la page)
    positions = [[round(float(la), 5), round(float(lo), 5)]
                 for la, lo in zip(autres["lat"], autres["lon"])]
    return sites, positions


# =============================================================================
# 6. LES DONNÉES : lecture des fichiers et fabrication des fenêtres de détails
# =============================================================================

SITES, POSITIONS = construire_sites(DEPARTEMENTS, PROPRIETAIRES_AFFICHES, MAX_POINTS)
if not AFFICHER_TOUS_LES_SITES:
    POSITIONS = []
print(f"{len(SITES)} sites avec détails, {len(POSITIONS)} sites en position seule")


# =============================================================================
# 7. LA CARTE (vue satellite IGN)
# =============================================================================

# Photographies aériennes de l'IGN (Géoplateforme), du zoom 0 au zoom 19
URL_SATELLITE = (
    "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
    "&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg"
    "&TILEMATRIXSET=PM_0_19"
    "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}"
)

carte = folium.Map(
    location=[20, 10],           # Centre de départ (recadré sur les points plus bas)
    zoom_start=2,
    min_zoom=1,                  # On peut dézoomer jusqu'à voir le monde entier
    max_zoom=19,                 # Zoom maximum des photographies IGN
    tiles=None,                  # Pas de fond par défaut : on ajoute celui de l'IGN
)

folium.TileLayer(
    tiles=URL_SATELLITE,
    attr="© IGN - Géoplateforme",
    name="Photographies aériennes IGN",
    max_zoom=19,
    control=False,
).add_to(carte)


# =============================================================================
# 8. LES POINTS, REGROUPÉS EN CLUSTERS
# =============================================================================

# Un cluster = une bulle numérotée qui regroupe les points proches quand on dézoome.
# Un clic sur une bulle zoome dessus ; seul un point isolé est cliquable.
# chunkedLoading : charge les points par petits paquets pour ne pas figer la page.
# disableClusteringAtZoom : à partir de ce zoom, plus de bulles, chaque point est séparé.
OPTIONS_CLUSTER = {"chunkedLoading": True, "disableClusteringAtZoom": 15}

# 1. Tous les autres sites (monde entier) : épingles bleues, position seule.
#    FastMarkerCluster écrit seulement [latitude, longitude] pour chaque point : c'est
#    ce qui permet d'en afficher près de 100 000 sans alourdir la page.
if POSITIONS:
    FastMarkerCluster(
        POSITIONS,
        name="Autres sites (position seule)",
        options=OPTIONS_CLUSTER,
    ).add_to(carte)

# 2. Les sites détaillés : épingles rouges, avec leur fenêtre de détails au clic
cluster = MarkerCluster(name="Sites avec détails", options=OPTIONS_CLUSTER).add_to(carte)
for site in SITES:
    folium.Marker(
        location=[site["lat"], site["lon"]],
        tooltip=site["nom"],                                # Survol : le nom du support
        popup=folium.Popup(site["popup"], max_width=470),   # Clic : les détails
        icon=folium.Icon(color="red"),                      # Épingle rouge
    ).add_to(cluster)

# 3. On cadre la carte sur l'ensemble des points affichés (le monde entier si les
#    autres sites sont affichés, sinon seulement les départements choisis)
tous = [(s["lat"], s["lon"]) for s in SITES] + [(p[0], p[1]) for p in POSITIONS]
if tous:
    carte.fit_bounds([
        [min(p[0] for p in tous), min(p[1] for p in tous)],
        [max(p[0] for p in tous), max(p[1] for p in tous)],
    ])


# =============================================================================
# 9. LA ZONE DE RECHERCHE (pour plus tard : pas encore fonctionnelle)
# =============================================================================

# Simple champ de saisie en HTML, posé en haut à gauche, à droite des boutons de zoom
RECHERCHE_HTML = """
<div style="position: fixed; top: 10px; left: 55px; z-index: 1000;
            background: white; padding: 6px 8px; border-radius: 6px;
            box-shadow: 0 1px 5px rgba(0,0,0,0.4); font-family: Arial, sans-serif;">
  <input type="search" placeholder="Rechercher un site..." style="width: 260px; padding: 6px;">
</div>
"""
carte.get_root().html.add_child(folium.Element(RECHERCHE_HTML))


# Légende : explique la différence entre épingles rouges et bleues
if POSITIONS:
    LEGENDE_HTML = """
    <div style="position: fixed; bottom: 25px; left: 10px; z-index: 1000;
                background: white; padding: 8px 10px; border-radius: 6px;
                box-shadow: 0 1px 5px rgba(0,0,0,0.4); font: 13px Arial, sans-serif;">
      <b>Légende</b><br>
      <span style="color:#d33d2a">&#9679;</span> Épingle rouge : détails au clic<br>
      <span style="color:#38a3dd">&#9679;</span> Épingle bleue : position seule
    </div>
    """
    carte.get_root().html.add_child(folium.Element(LEGENDE_HTML))


# =============================================================================
# 10. L'ENREGISTREMENT
# =============================================================================

carte.save("carte.html")
print("Carte générée : carte.html")
