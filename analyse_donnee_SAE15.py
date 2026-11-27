import pandas as pd
import folium
from folium.plugins import MarkerCluster
import colorsys
import html
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from matplotlib import style
from matplotlib.figure import Figure

# Dossiers de données : accepte data/data ou data, comme carte_fusion.py
RACINE = Path(__file__).resolve().parent

def trouver_dossier(nom):
    candidats = [
        RACINE / nom / nom,
        RACINE / nom,
        RACINE.parent / nom / nom,
        RACINE.parent / nom,
    ]
    for dossier in candidats:
        if dossier.is_dir():
            return dossier
    # Ancien chemin relatif utilisé dans le projet
    return (RACINE.parent / nom).resolve()

DOSSIER_DATA = trouver_dossier("data")
DOSSIER_REF = trouver_dossier("ref")
FICHIER_CARTE = RACINE / "carte.html"
FICHIER_GRAPHIQUES = RACINE / "graphiques.png"
ANNEE_MIN = 1950
LARGEUR_GRAPHIQUES = 1270
HAUTEUR_GRAPHIQUES = 900

limiteRecherche = 250  # -1 pour ne pas limiter

print("CHARGEMENT DES DONNEES PRINCIPALES")

def lire_fichier(chemin):
    """Lit une table ANFR en texte et uniformise les noms de colonnes."""
    try:
        df = pd.read_csv(chemin, sep=";", dtype=str, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(chemin, sep=";", dtype=str, encoding="cp1252")
    df.columns = [str(c).strip().upper() for c in df.columns]
    return df

# On ne charge au démarrage que les supports et les tables de référence.
# Les tables volumineuses (stations, antennes, émetteurs, bandes) ne seront
# lues qu'après la recherche, et uniquement pour les sites à afficher.
sup_support_df = lire_fichier(DOSSIER_DATA / "sup_support.txt")
print("SUP SUPPORT chargé")

sup_proprietaire_df = lire_fichier(DOSSIER_REF / "sup_proprietaire.txt")
print("SUP PROPRIETAIRE chargé")
sup_nature_df = lire_fichier(DOSSIER_REF / "sup_nature.txt")
print("SUP NATURE chargé")
sup_exploitant_df = lire_fichier(DOSSIER_REF / "sup_exploitant.txt")
print("SUP EXPLOITANT chargé")
sup_type_antenne_df = lire_fichier(DOSSIER_REF / "sup_type_antenne.txt")
print("SUP TYPE ANTENNE chargé")
print("FIN DU CHARGEMENT INITIAL")

# Dictionnaires de référence : accès direct par identifiant
def table_reference(df, colonne_code, colonne_nom):
    return dict(zip(df[colonne_code].fillna("").str.strip(),
                    df[colonne_nom].fillna("").str.strip()))

proprietaires = table_reference(sup_proprietaire_df, "TPO_ID", "TPO_LB")
natures = table_reference(sup_nature_df, "NAT_ID", "NAT_LB_NOM")
exploitants = table_reference(sup_exploitant_df, "ADM_ID", "ADM_LB_NOM")
types_antennes = table_reference(sup_type_antenne_df, "TAE_ID", "TAE_LB")

# --------------------------------------------------
# GRAPHIQUES : génération unique au lancement du programme
# --------------------------------------------------
def lire_colonnes_graphique(nom_fichier, colonnes, type_donnees=str):
    """Lit uniquement les colonnes utiles aux graphiques."""
    chemin = DOSSIER_DATA / nom_fichier
    print(f"Lecture graphique : {nom_fichier}")
    for encodage in ("utf-8", "cp1252"):
        try:
            tableau = pd.read_csv(
                chemin, sep=";", usecols=colonnes, dtype=type_donnees,
                on_bad_lines="warn", encoding=encodage
            )
            tableau.columns = [str(c).strip().upper() for c in tableau.columns]
            return tableau
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Impossible de lire le fichier : {chemin}")


def texte_pourcentage(pourcentage):
    return f"{round(pourcentage, 1)}%" if pourcentage >= 3 else ""


def generer_image_graphiques():
    """Construit et enregistre une seule image contenant les six graphiques."""
    print("GENERATION DES GRAPHIQUES (une seule fois)...")
    stations_graph = lire_colonnes_graphique(
        "sup_station.txt", ["ADM_ID", "DTE_EN_SERVICE"]
    )
    emetteurs_graph = lire_colonnes_graphique(
        "sup_emetteur.txt", ["EMR_LB_SYSTEME"], "category"
    )
    bandes_graph = lire_colonnes_graphique(
        "sup_bande.txt", ["BAN_NB_F_DEB", "BAN_NB_F_FIN", "BAN_FG_UNITE"]
    )

    # Réutilisation des tables déjà chargées pour éviter de les relire.
    supports_graph = sup_support_df[["SUP_ID", "NAT_ID", "TPO_ID"]].copy()
    supports_graph = supports_graph.drop_duplicates(subset="SUP_ID")
    exploitants_graph = sup_exploitant_df[["ADM_ID", "ADM_LB_NOM"]].drop_duplicates("ADM_ID")
    natures_graph = sup_nature_df[["NAT_ID", "NAT_LB_NOM"]].drop_duplicates("NAT_ID")
    proprietaires_graph = sup_proprietaire_df[["TPO_ID", "TPO_LB"]].drop_duplicates("TPO_ID")

    stations_graph = stations_graph.merge(exploitants_graph, on="ADM_ID", how="left")
    supports_graph = supports_graph.merge(natures_graph, on="NAT_ID", how="left")
    supports_graph = supports_graph.merge(proprietaires_graph, on="TPO_ID", how="left")
    stations_graph["DTE_EN_SERVICE"] = pd.to_datetime(
        stations_graph["DTE_EN_SERVICE"], format="%d/%m/%Y", errors="coerce"
    )
    bandes_graph["BANDE"] = (
        bandes_graph["BAN_NB_F_DEB"].fillna("") + "-" +
        bandes_graph["BAN_NB_F_FIN"].fillna("") + " " +
        bandes_graph["BAN_FG_UNITE"].fillna("") + "Hz"
    )
    bandes_graph = bandes_graph[["BANDE"]].astype("category")

    style.use("seaborn-v0_8")
    figure = Figure(
        figsize=(LARGEUR_GRAPHIQUES / 100, HAUTEUR_GRAPHIQUES / 100), dpi=100
    )
    graphiques = figure.subplots(2, 3)

    top_exploitants = stations_graph["ADM_LB_NOM"].value_counts().head(10)
    if not top_exploitants.empty:
        top_exploitants.plot(kind="bar", ax=graphiques[0, 0], color="skyblue", xlabel="", ylabel="Nombre d'installations")
    graphiques[0, 0].set_title("Installations par exploitant")

    top_natures = supports_graph["NAT_LB_NOM"].value_counts().head(10)
    if not top_natures.empty:
        top_natures.plot(kind="bar", ax=graphiques[0, 1], color="lightcoral", xlabel="", ylabel="Nombre de supports")
    graphiques[0, 1].set_title("Natures de support (top 10)")

    for graphique in (graphiques[0, 0], graphiques[0, 1]):
        if graphique.containers:
            graphique.bar_label(graphique.containers[0], fontsize=7)
        graphique.margins(y=0.1)
        for etiquette in graphique.get_xticklabels():
            etiquette.set_rotation(45)
            etiquette.set_ha("right")

    parts_proprietaires = supports_graph["TPO_LB"].value_counts()
    total_autres = parts_proprietaires.iloc[10:].sum()
    parts_proprietaires = parts_proprietaires.iloc[:10].copy()
    if total_autres > 0:
        parts_proprietaires["Autres"] = total_autres
    couleurs = ["skyblue", "lightcoral", "lightgreen", "gold", "mediumpurple", "sandybrown", "turquoise", "hotpink", "yellowgreen", "plum", "lightgrey"]
    if not parts_proprietaires.empty:
        graphiques[0, 2].pie(parts_proprietaires, colors=couleurs[:len(parts_proprietaires)], autopct=texte_pourcentage, startangle=90, textprops={"fontsize": 7})
        graphiques[0, 2].legend(parts_proprietaires.index, loc="upper center", bbox_to_anchor=(0.5, 0), ncol=2, fontsize=7)
    graphiques[0, 2].set_title("Propriétaires de support")

    top_systemes = emetteurs_graph["EMR_LB_SYSTEME"].value_counts().head(10)
    if not top_systemes.empty:
        top_systemes.plot(kind="barh", ax=graphiques[1, 0], color="lightgreen", xlabel="Nombre d'émetteurs", ylabel="")
    graphiques[1, 0].set_title("Systèmes (émetteurs)")

    top_bandes = bandes_graph["BANDE"].value_counts().head(10)
    if not top_bandes.empty:
        top_bandes.plot(kind="barh", ax=graphiques[1, 1], color="gold", xlabel="Nombre d'émetteurs", ylabel="")
    graphiques[1, 1].set_title("Bandes de fréquences (top 10)")

    for graphique in (graphiques[1, 0], graphiques[1, 1]):
        graphique.invert_yaxis()
        if graphique.containers:
            graphique.bar_label(graphique.containers[0], padding=3, fontsize=7)
        graphique.margins(x=0.2)

    annees_service = stations_graph["DTE_EN_SERVICE"].dt.year.dropna().astype(int)
    annee_actuelle = pd.Timestamp.today().year
    annees_service = annees_service[
        (annees_service >= ANNEE_MIN) & (annees_service <= annee_actuelle)
    ]
    cumul = annees_service.value_counts().sort_index().cumsum()
    if not cumul.empty:
        graphiques[1, 2].plot(cumul.index, cumul.values, marker="o", markersize=3, color="purple")
    graphiques[1, 2].set_title("Installations actuelles (cumul)")
    graphiques[1, 2].set_xlabel("Année de mise en service")
    graphiques[1, 2].set_ylabel("Nombre d'installations")

    for graphique in graphiques.flat:
        graphique.tick_params(labelsize=7)
    figure.set_layout_engine("tight", h_pad=3, w_pad=2)
    figure.savefig(FICHIER_GRAPHIQUES)
    print(f"Image des graphiques créée : {FICHIER_GRAPHIQUES}")


# L'image est créée une fois ici, jamais lors d'une recherche ou d'un changement d'affichage.
generer_image_graphiques()

# return the string without space and upper letter
def correct_str(string):
    return str(string).lower().strip()

# Lecture différée des tables volumineuses : seules les lignes des stations
# recherchées sont conservées, comme dans carte_fusion.py.
TAILLE_PAQUET = 500_000
MAX_STATIONS_AFFICHEES = 30
UNITES = {"K": "kHz", "M": "MHz", "G": "GHz"}

def lire_filtre(nom_fichier, colonne, valeurs):
    chemin = DOSSIER_DATA / nom_fichier
    valeurs = {str(v).strip() for v in valeurs if pd.notna(v) and str(v).strip()}
    morceaux = []
    for encodage in ("utf-8", "cp1252"):
        try:
            lecteur = pd.read_csv(
                chemin, sep=";", dtype=str, encoding=encodage,
                chunksize=TAILLE_PAQUET
            )
            morceaux = []
            for paquet in lecteur:
                paquet.columns = [str(c).strip().upper() for c in paquet.columns]
                morceaux.append(paquet[paquet[colonne].fillna("").str.strip().isin(valeurs)])
            return pd.concat(morceaux, ignore_index=True) if morceaux else pd.DataFrame()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"Impossible de lire le fichier : {chemin}")

def valeur_renseignee(v):
    return isinstance(v, str) and v.strip() != ""

def valeur_html(v):
    return html.escape(str(v)) if valeur_renseignee(v) else ""

def ligne_html(titre, valeur):
    return f"<b>{titre} :</b> {valeur_html(valeur)}<br>" if valeur_renseignee(valeur) else ""

def charger_details(stations):
    stations = {str(s).strip() for s in stations if pd.notna(s)}
    print(f"Lecture différée des détails pour {len(stations)} stations...")
    station = lire_filtre("sup_station.txt", "STA_NM_ANFR", stations)
    antenne = lire_filtre("sup_antenne.txt", "STA_NM_ANFR", stations)
    emetteur = lire_filtre("sup_emetteur.txt", "STA_NM_ANFR", stations)
    bande = lire_filtre("sup_bande.txt", "STA_NM_ANFR", stations)

    if not station.empty:
        station = station.drop_duplicates(subset="STA_NM_ANFR")
    if not antenne.empty:
        antenne = antenne.drop_duplicates(subset=["STA_NM_ANFR", "AER_ID"])

    return {
        "station": station.set_index("STA_NM_ANFR").to_dict("index") if not station.empty else {},
        "antennes": {k: g.to_dict("records") for k, g in antenne.groupby("STA_NM_ANFR")} if not antenne.empty else {},
        "emetteurs": {k: g.to_dict("records") for k, g in emetteur.groupby("STA_NM_ANFR")} if not emetteur.empty else {},
        "bandes": {k: g.to_dict("records") for k, g in bande.groupby("EMR_ID")} if not bande.empty else {},
    }

def html_emetteur(e, details):
    morceaux = [f"<b>{valeur_html(e.get('EMR_LB_SYSTEME', ''))}</b>"]
    if valeur_renseignee(e.get("EMR_DT_SERVICE")):
        morceaux.append(f"service le {valeur_html(e['EMR_DT_SERVICE'])}")
    bandes = []
    for b in details["bandes"].get(e.get("EMR_ID"), []):
        unite_code = b.get("BAN_FG_UNITE", "")
        unite = UNITES.get(unite_code, unite_code)
        debut, fin = valeur_html(b.get("BAN_NB_F_DEB")), valeur_html(b.get("BAN_NB_F_FIN"))
        if debut or fin:
            bandes.append(f"{debut}–{fin} {valeur_html(unite)}".strip())
    if bandes:
        morceaux.append(" ; ".join(bandes))
    return "<div style='margin-left:14px'>" + " — ".join(morceaux) + "</div>"

def html_station(sta, details):
    info = details["station"].get(sta, {})
    nom_exploitant = exploitants.get(str(info.get("ADM_ID", "")).strip(), "Exploitant inconnu")
    entete = (
        ligne_html("Implantée le", info.get("DTE_IMPLANTATION"))
        + ligne_html("Mise en service le", info.get("DTE_EN_SERVICE"))
        + ligne_html("Dernière modification le", info.get("DTE_MODIF"))
        + ligne_html("N° de demande (COMSIS)", info.get("DEM_NM_COMSIS"))
    )
    emetteurs = details["emetteurs"].get(sta, [])
    par_antenne = {}
    for e in emetteurs:
        par_antenne.setdefault(e.get("AER_ID"), []).append(e)

    corps = ""
    for a in details["antennes"].get(sta, []):
        type_ant = types_antennes.get(str(a.get("TAE_ID", "")).strip(), "Type inconnu")
        caracteristiques = [valeur_html(type_ant)]
        for titre, champ in (("dimension", "AER_NB_DIMENSION"),
                             ("azimut", "AER_NB_AZIMUT"),
                             ("altitude basse", "AER_NB_ALT_BAS")):
            if valeur_renseignee(a.get(champ)):
                suffixe = "°" if champ == "AER_NB_AZIMUT" else ""
                caracteristiques.append(f"{titre} {valeur_html(a[champ])}{suffixe}")
        corps += "<div style='margin:4px 0 0 8px'>Antenne : " + ", ".join(caracteristiques)
        corps += "".join(html_emetteur(e, details) for e in par_antenne.pop(a.get("AER_ID"), []))
        corps += "</div>"

    restants = [e for groupe in par_antenne.values() for e in groupe]
    if restants:
        corps += "<div>Émetteurs sans antenne décrite :" + "".join(
            html_emetteur(e, details) for e in restants
        ) + "</div>"

    return (f"<details style='margin:4px 0'><summary><b>{valeur_html(nom_exploitant)}</b> "
            f"— station {valeur_html(sta)}</summary><div style='margin:4px 0 0 8px'>"
            f"{entete}{corps}</div></details>")

def details_support(support_id, stations, details):
    html_details = ""
    stations = sorted(set(stations), key=lambda s: exploitants.get(
        str(details["station"].get(s, {}).get("ADM_ID", "")).strip(), "~"
    ))
    for sta in stations[:MAX_STATIONS_AFFICHEES]:
        html_details += html_station(sta, details)
    if len(stations) > MAX_STATIONS_AFFICHEES:
        html_details += f"<i>… et {len(stations) - MAX_STATIONS_AFFICHEES} autres stations non affichées</i>"
    return html_details

# dictionnary with code of every french region
regions_france = {
    "guadeloupe": "01",
    "martinique": "02",
    "guyane": "03",
    "lareunion": "04",
    "mayotte": "06",
    "iledefrance": "11",
    "centrevaldeloire": "24",
    "bourgognefranchecomte": "27",
    "normandie": "28",
    "hautsdefrance": "32",
    "grandest": "44",
    "paysdelaloire": "52",
    "bretagne": "53",
    "nouvelleaquitaine": "75",
    "occitanie": "76",
    "auvergnerhonealpes": "84",
    "provencealpescotedazur": "93",
    "corse": "94"
}

# dictionnary with the code of every department
departements_vers_region = {
    "01": "auvergnerhonealpes",
    "02": "hautsdefrance",
    "03": "auvergnerhonealpes",
    "04": "provencealpescotedazur",
    "05": "provencealpescotedazur",
    "06": "provencealpescotedazur",
    "07": "auvergnerhonealpes",
    "08": "grandest",
    "09": "occitanie",
    "10": "grandest",
    "11": "occitanie",
    "12": "occitanie",
    "13": "provencealpescotedazur",
    "14": "normandie",
    "15": "auvergnerhonealpes",
    "16": "nouvelleaquitaine",
    "17": "nouvelleaquitaine",
    "18": "centrevaldeloire",
    "19": "nouvelleaquitaine",
    "2a": "corse",
    "2b": "corse",
    "21": "bourgognefranchecomte",
    "22": "bretagne",
    "23": "nouvelleaquitaine",
    "24": "nouvelleaquitaine",
    "25": "bourgognefranchecomte",
    "26": "auvergnerhonealpes",
    "27": "normandie",
    "28": "centrevaldeloire",
    "29": "bretagne",
    "30": "occitanie",
    "31": "occitanie",
    "32": "occitanie",
    "33": "nouvelleaquitaine",
    "34": "occitanie",
    "35": "bretagne",
    "36": "centrevaldeloire",
    "37": "centrevaldeloire",
    "38": "auvergnerhonealpes",
    "39": "bourgognefranchecomte",
    "40": "nouvelleaquitaine",
    "41": "centrevaldeloire",
    "42": "auvergnerhonealpes",
    "43": "auvergnerhonealpes",
    "44": "paysdelaloire",
    "45": "centrevaldeloire",
    "46": "occitanie",
    "47": "nouvelleaquitaine",
    "48": "occitanie",
    "49": "paysdelaloire",
    "50": "normandie",
    "51": "grandest",
    "52": "grandest",
    "53": "paysdelaloire",
    "54": "grandest",
    "55": "grandest",
    "56": "bretagne",
    "57": "grandest",
    "58": "bourgognefranchecomte",
    "59": "hautsdefrance",
    "60": "hautsdefrance",
    "61": "normandie",
    "62": "hautsdefrance",
    "63": "auvergnerhonealpes",
    "64": "nouvelleaquitaine",
    "65": "occitanie",
    "66": "occitanie",
    "67": "grandest",
    "68": "grandest",
    "69": "auvergnerhonealpes",
    "70": "bourgognefranchecomte",
    "71": "bourgognefranchecomte",
    "72": "paysdelaloire",
    "73": "auvergnerhonealpes",
    "74": "auvergnerhonealpes",
    "75": "iledefrance",
    "76": "normandie",
    "77": "iledefrance",
    "78": "iledefrance",
    "79": "nouvelleaquitaine",
    "80": "hautsdefrance",
    "81": "occitanie",
    "82": "occitanie",
    "83": "provencealpescotedazur",
    "84": "provencealpescotedazur",
    "85": "paysdelaloire",
    "86": "nouvelleaquitaine",
    "87": "nouvelleaquitaine",
    "88": "grandest",
    "89": "bourgognefranchecomte",
    "90": "bourgognefranchecomte",
    "91": "iledefrance",
    "92": "iledefrance",
    "93": "iledefrance",
    "94": "iledefrance",
    "95": "iledefrance",
    "971": "guadeloupe",
    "972": "martinique",
    "973": "guyane",
    "974": "lareunion",
    "976": "mayotte"
}

# function that return a tuple with the region name and its code or None if not found
def getRegion(code_postal):
    cp = str(code_postal).strip() ## convert in string and strip for security

    dept = cp[:3] if cp.startswith("97") else cp[:2] # we check first if its a 3 letters department (every 3 letters dept start with 97) otherwise we slice the cp string to only get the department code

    nom_region = departements_vers_region.get(dept.lower()) ## the method .get allow to immediatly found and get the value from a specified key (here is dept lowered)

    if nom_region is None: ## if its not found
        return None, None

    code_region = regions_france.get(nom_region) ## after getting the region name by the dept code we can return the region code

    return nom_region, code_region


## retrun a dictionnary of index corresponding to the result of a research that can be by postal code, city name, region name
## contain two parameters : researchType indicate the research value ("CodePostal" for postal code, "Region" for the region, "Commune" for the city )
## researchValue is the value to research for exemple a postal code, region name ...
def userResearch(researchType: str, researchValue):
    """Recherche vectorisée dans la table des supports (sans boucle ligne par ligne)."""
    print(f"Début d'une recherche par {researchType} avec l'argument {researchValue}")
    df = sup_support_df
    type_recherche = correct_str(researchType)
    valeur = str(researchValue).strip()

    if type_recherche == "codepostal":
        masque = df["ADR_NM_CP"].fillna("").astype(str).str.strip() == valeur
    elif type_recherche == "lieu":
        masque = (
            df["ADR_LB_LIEU"].fillna("").astype(str).str.strip().str.lower()
            == correct_str(valeur)
        )
    elif type_recherche == "region":
        cp = df["ADR_NM_CP"].fillna("").astype(str).str.strip()
        departements = cp.str[:3].where(cp.str.startswith("97"), cp.str[:2]).str.lower()
        regions = departements.map(departements_vers_region)
        valeur_norm = correct_str(valeur)
        code_region = regions_france.get(valeur_norm)
        masque = (regions == valeur_norm) | (regions_france.get(valeur_norm) == valeur)
        if code_region is not None:
            masque = regions == valeur_norm
        else:
            masque = regions == next(
                (nom for nom, code in regions_france.items() if code == valeur), ""
            )
    else:
        print("Type de recherche incorrect :", researchType)
        return []

    resultat = df.loc[masque, ["STA_NM_ANFR", "SUP_ID", "NAT_ID", "TPO_ID"]]
    return resultat.fillna("").to_dict("records")


def generateMap(researchType, researchValue):

    def nombre(serie):
        ## a line of a data frame can be an object called "serie"
        ## this function simply convert the number contained in a serie to be used normally in python as float or integer
        ## the pandas "to_numeric" function is used
        return pd.to_numeric(
            serie.astype(str).str.replace(",", ".", regex=False),
            errors="coerce"
        )

    def dms_en_decimal(degres, minutes, secondes, hemisphere):
        ## Convert DMS degrees into numeric degrees
        valeur = (
            nombre(degres)
            + nombre(minutes) / 60
            + nombre(secondes) / 3600
        )

        hemisphere = hemisphere.astype(str).str.upper().str.strip() ## security to exclude incorrect conversion

        return valeur.where(~hemisphere.isin(["S", "W"]), -valeur)
        # in this return, we use hemisphere.isin and valeur.where, .where means if the result of the first parameter is correct we keep it otherwise we chose the value on the second parameter

    def couleur(i):
        teinte = (i * 0.618033988749895) % 1
        r, g, b = colorsys.hls_to_rgb(teinte, 0.45, 0.75)
        ## this part help distributing unique color for an "i" number that represent the owner color
        ## it convert the hls format into rgb using colorsys functions and parameter like brigthness or saturation
        ## so it return for r, g and b a number between 1 and 0

        return "#{:02x}{:02x}{:02x}".format(
            int(r * 255),
            int(g * 255),
            int(b * 255)
        )
    # here we formated the value of the decimals r, g and b to 2 digit hexadecimal using the format ":02x"

    def texte_sur(valeur):
        # html can be sensible of string char like ' / `. This function securise the string in parameter using html.escape to replace special character to html safe equivalents

        return html.escape(str(valeur)).replace("`", "'").replace("\\", "/")

    def fenetre_details(point):
        #a function that build the white square windows for a point using its information on parameter

        # html header balise with style
        # lignes is the table that will contain every line of text to show on the white window
        lignes = [
            f"<h4 style='margin:0 0 6px'>{texte_sur(point['nom'])}</h4>"
        ]

        for cle, valeur in point.items(): ## loop through every key value of the dictionnary "point"

            if cle not in ("nom", "lat", "lon", "details_html"): ## we exclude some key in the "point" dictionnary
                lignes.append(
                    f"<b>{texte_sur(cle)} :</b> "
                    f"{texte_sur(valeur)}<br>"
                )

        lignes.append(
            f"<b>Coordonnées :</b> {point['lat']}, {point['lon']}<br>"
        )
        lignes.append(point.get("details_html", ""))

        return ("<div style='width:430px; max-height:320px; overflow:auto; "
                "font:13px Arial,sans-serif'>" + "".join(lignes) + "</div>")

    # 1 - We get the research result by the parameter researchType and researchValue

    resultats = userResearch(researchType, researchValue)

    if not resultats:
        print("Aucun résultat trouvé pour cette recherche.")
        return

    print(f"{len(resultats)} résultats trouvés.")

    # get the corresponding support
    ids_support = [str(resultat["SUP_ID"]).strip() for resultat in resultats]
    df_complet = sup_support_df[
        sup_support_df["SUP_ID"].fillna("").str.strip().isin(ids_support)
    ].copy()

    # One line by support to conserv the link
    nb_stations = df_complet.groupby("SUP_ID")["STA_NM_ANFR"].nunique()
    df = df_complet.drop_duplicates(subset="SUP_ID").copy()

    if limiteRecherche != -1 and len(df) > limiteRecherche:
        print(f"Limitation de {len(df)} à {limiteRecherche} supports.")
        df = df.head(limiteRecherche)

    print(f"{len(df)} supports seront affichés sur la carte.")

    ids_affiches = set(df["SUP_ID"].astype(str).str.strip())
    liens = df_complet[
        df_complet["SUP_ID"].astype(str).str.strip().isin(ids_affiches)
    ][["SUP_ID", "STA_NM_ANFR"]].dropna().drop_duplicates()
    stations_par_support = liens.groupby("SUP_ID")["STA_NM_ANFR"].apply(
        lambda serie: [str(x).strip() for x in serie if str(x).strip()]
    ).to_dict()

    # Voluminous table read only for loaded section
    stations_a_lire = set(liens["STA_NM_ANFR"].astype(str).str.strip())
    details = charger_details(stations_a_lire)

    # GPS conversion

    df["lat"] = dms_en_decimal(
        df["COR_NB_DG_LAT"],
        df["COR_NB_MN_LAT"],
        df["COR_NB_SC_LAT"],
        df["COR_CD_NS_LAT"]
    )

    df["lon"] = dms_en_decimal(
        df["COR_NB_DG_LON"],
        df["COR_NB_MN_LON"],
        df["COR_NB_SC_LON"],
        df["COR_CD_EW_LON"]
    )

    # Invalide coordinate
    df = df.dropna(subset=["lat", "lon"])

    # get the author and the installions nature

    # refs dict loaded only on start

    # point build on the map

    points = []

    for _, ligne in df.iterrows():

        # add the adress
        morceaux = [
            ligne.get("ADR_LB_LIEU"),
            ligne.get("ADR_LB_ADD1"),
            ligne.get("ADR_LB_ADD2"),
            ligne.get("ADR_LB_ADD3"),
            ligne.get("ADR_NM_CP")
        ]

        adresse = ", ".join(
            str(m).strip()
            for m in morceaux
            if pd.notna(m) and str(m).strip()
        )

        # Number of station associated on the support
        nb = int(nb_stations.loc[ligne["SUP_ID"]])

        points.append({

            "nom": f"Support n° {ligne['SUP_ID']}",

            "lat": round(float(ligne["lat"]), 6),
            "lon": round(float(ligne["lon"]), 6),

            "Adresse": adresse,

            "Propriétaire": proprietaires.get(
                str(ligne["TPO_ID"]).strip() if pd.notna(ligne["TPO_ID"]) else "",
                "Propriétaire inconnu"
            ),
            
            "Hauteur (m)": ligne.get("SUP_NM_HAUT", ""),

            "Nature": natures.get(
                str(ligne.get("NAT_ID", "")).strip(),
                "Nature inconnue"
            ),

            "Code INSEE commune": ligne.get("COM_CD_INSEE", ""),

            "Stations sur le site": nb,

            "details_html": details_support(
                str(ligne["SUP_ID"]).strip(),
                stations_par_support.get(str(ligne["SUP_ID"]).strip(), []),
                details
            )
        })

    if not points:
        print("Aucun support avec des coordonnées GPS valides.")
        return

    # build of the map

    URL_IGN = (
    "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0"
    "&LAYER=ORTHOIMAGERY.ORTHOPHOTOS&STYLE=normal&FORMAT=image/jpeg"
    "&TILEMATRIXSET=PM_0_19"
    "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}"
    )

    carte = folium.Map(
        location=[46.6, 2.5],
        zoom_start=6,
        tiles=None,
        prefer_canvas=True
    )

    folium.TileLayer(
        tiles=URL_IGN,
        attr="© IGN - Géoplateforme",
        name="Plan IGN",
        control=False
    ).add_to(carte)

    # link the point by authors

    par_nature = {}

    for p in points:

        natureTitle = p["Nature"]

        # limit the length of the nature name
        if len(natureTitle) > 15:
            natureTitle = natureTitle[:15] + "..."

        liste = par_nature.setdefault(natureTitle, [])

        liste.append(p)

    # build of the left panel with the filter marks

    for i, nom in enumerate(sorted(par_nature)):

        liste = par_nature[nom]

        teinte = couleur(i)

        etiquette = (
            f"<span style='color:{teinte}'>&#9679;</span> "
            f"{texte_sur(nom)} ({len(liste)})"
        )

        couche = folium.FeatureGroup(
            name=etiquette,
            show=True
        ).add_to(carte)

        # Use MarkerCluster to link same filter point together when zoom
        regroupement = MarkerCluster(
            name=f"Regroupement - {nom}",
            show=True,
            options={
                "chunkedLoading": True,
                "disableClusteringAtZoom": 16,
                "spiderfyOnMaxZoom": True
            }
        ).add_to(couche)

        for p in liste:

            hauteur = pd.to_numeric(
                p["Hauteur (m)"],
                errors="coerce"
            )

            if pd.isna(hauteur):
                hauteur = 0

            hauteur = float(hauteur)
            
            coefTailleRadius = hauteur * 0.125
            coefTailleWeight = hauteur * 0.035
            
            if coefTailleRadius > 15:
                coefTailleRadius = 15
                coefTailleWeight = 5
                

            # To keep the style of the points
            taille = int(2 * (6 + coefTailleRadius))
            epaisseur = int(2 + coefTailleWeight)

            icone = folium.DivIcon(
                html=f"""
                    <div style="
                        width:{taille}px;
                        height:{taille}px;
                        background:{teinte};
                        border:{epaisseur}px solid #333333;
                        border-radius:50%;
                        opacity:0.85;
                        box-sizing:border-box;
                    "></div>
                """,
                icon_size=(taille, taille),
                icon_anchor=(taille // 2, taille // 2)
            )

            folium.Marker(
                location=[p["lat"], p["lon"]],
                icon=icone,
                tooltip=texte_sur(p["nom"]),
                popup=folium.Popup(
                    fenetre_details(p),
                    max_width=320
                )
            ).add_to(regroupement)

    # Configuration of the layer selector

    folium.LayerControl(
        position="topleft",
        collapsed=False
    ).add_to(carte)

    # Automatic zoom on points

    carte.fit_bounds([

        [
            min(p["lat"] for p in points),
            min(p["lon"] for p in points)
        ],

        [
            max(p["lat"] for p in points),
            max(p["lon"] for p in points)
        ]

    ])

    # save the new loaded map

    carte.save(str(FICHIER_CARTE))

    print(f"Carte générée : {len(points)} supports affichés.")
    print("Fichier : carte.html")
    

print("RECHERCHE INITIAL à ELBEUF")
generateMap("codepostal", "76500") 
 

def lancer_interface():

    from pathlib import Path
    from tkwry import WebView
    import os

    fenetre = tk.Tk()
    fenetre.title("Recherche des installations")
    fenetre.state("zoomed")

    # left frame
    cadre_recherche = ttk.Frame(fenetre, padding=10)
    cadre_recherche.pack(side="left", fill="y")

    titre = tk.Label(
        cadre_recherche,
        text="Rechercher des installations",
        font=("Arial", 14)
    )
    titre.grid(pady=10, row=0, column=0)

    # selecting box to chose  the research type
    type_recherche = ttk.Combobox(
        cadre_recherche,
        values=["codepostal", "lieu", "region"],
        state="readonly"
    )
    type_recherche.set("codepostal")
    type_recherche.grid(pady=5, row=1, column=0)

    # Search bar
    barre_recherche = tk.Entry(
        cadre_recherche,
        width=35
    )
    barre_recherche.grid(pady=5, row=2, column=0)
    
    # Correction of a focus bug when clicking on the map and the wanted to write in the text entry
    barre_recherche.bind(
        "<Button-1>",
        lambda event: fenetre.after(
            100,
            barre_recherche.focus_force
        ),
        add="+"
    )

    # Right frame
    cadre_carte = ttk.Frame(fenetre)
    cadre_carte.pack(side="right", fill="both", expand=True)

    fichier_carte = FICHIER_CARTE

    # add the navigator and the web page iin tkinter
    dossier_webview = (
        Path(os.environ["LOCALAPPDATA"])
        / "Cartographie"
        / "WebView2"
    )

    dossier_webview.mkdir(parents=True, exist_ok=True)

    cadre_navigateur = ttk.Frame(cadre_carte)
    cadre_navigateur.pack(fill="both", expand=True)

    navigateur = WebView(
        cadre_navigateur,
        url=fichier_carte.as_uri(),
        user_data_dir=str(dossier_webview)
    )
    navigateur.pack(fill="both", expand=True)

    # Graphics view
    cadre_graphiques = ttk.Frame(cadre_carte)
    cadre_image = ttk.Frame(cadre_graphiques)
    cadre_image.pack(fill="both", expand=True)
    barre_graphique = ttk.Scrollbar(cadre_image, orient="vertical")
    barre_graphique.pack(side="right", fill="y")
    zone_graphique = tk.Canvas(
        cadre_image, yscrollcommand=barre_graphique.set, highlightthickness=0
    )
    zone_graphique.pack(side="left", fill="both", expand=True)
    barre_graphique.config(command=zone_graphique.yview)
    image_graphiques = tk.PhotoImage(file=str(FICHIER_GRAPHIQUES))
    zone_graphique.create_image(0, 0, image=image_graphiques, anchor="nw")
    zone_graphique.config(scrollregion=(0, 0, LARGEUR_GRAPHIQUES, HAUTEUR_GRAPHIQUES))

    mode_affichage = {"graphique": False}

    def permuter_affichage():
        if mode_affichage["graphique"]:
            cadre_graphiques.pack_forget()
            cadre_navigateur.pack(fill="both", expand=True)
            bouton_permuter.config(text="Afficher les graphiques")
            mode_affichage["graphique"] = False
        else:
            cadre_navigateur.pack_forget()
            cadre_graphiques.pack(fill="both", expand=True)
            bouton_permuter.config(text="Afficher la carte")
            mode_affichage["graphique"] = True

    # function called when we click the search button
    def recharger_map():

        recherche = barre_recherche.get()
        type_choisi = type_recherche.get()

        if recherche.strip() == "":
            texteIndicatif.config(
                text="Veuillez saisir une recherche correcte."
            )
            return

        texteIndicatif.config(text="Recherche en cours ...")
        fenetre.update_idletasks()

        # we memorize the last map load to not regenarate a new map if no changes
        try:
            ancienne_modification = fichier_carte.stat().st_mtime_ns
        except FileNotFoundError:
            ancienne_modification = None

        try:
            generateMap(type_choisi, recherche)

            try:
                nouvelle_modification = fichier_carte.stat().st_mtime_ns
            except FileNotFoundError:
                nouvelle_modification = None

            if (
                nouvelle_modification is not None
                and nouvelle_modification != ancienne_modification
            ):
                navigateur.reload()
                texteIndicatif.config(text="Carte actualisée.")
            else:
                texteIndicatif.config(
                    text="Aucun résultat : la carte précédente est conservée."
                )

        except Exception as erreur:
            texteIndicatif.config(text="Erreur pendant la recherche.")
            print("Erreur :", erreur)

    # Bouton rechercher
    bouton = tk.Button(
        cadre_recherche,
        text="Rechercher",
        command=recharger_map
    )
    bouton.grid(pady=5, row=3, column=0)

    bouton_permuter = tk.Button(
        cadre_recherche,
        text="Afficher les graphiques",
        command=permuter_affichage
    )
    bouton_permuter.grid(pady=5, row=4, column=0)

    texteIndicatif = tk.Label(
        cadre_recherche,
        text=""
    )
    texteIndicatif.grid(pady=5, row=5, column=0)

    fenetre.mainloop()


lancer_interface()
  