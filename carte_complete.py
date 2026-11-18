# =============================================================================
# CARTE INTERACTIVE DE FRANCE AVEC VOLET LATÉRAL (tout-en-un)
#
# Ce fichier unique contient :
#   1. les données (les points et les couleurs)
#   2. la carte (fond IGN, vue limitée à la France)
#   3. le CSS  (l'apparence du volet de droite)
#   4. le HTML (le contenu du volet : recherche, filtres, détails)
#   5. le JavaScript (clic sur un point, filtres)
#   6. l'assemblage et l'enregistrement dans "carte.html"
#
# Pour lancer :  python carte_complete.py   puis ouvrir carte.html
# (ne pas nommer ce fichier "folium.py")
# =============================================================================

# json transforme les données Python en texte compris par JavaScript
import json

# folium crée la carte interactive
import folium


# =============================================================================
# 1. LES DONNÉES
# Exemples de test : à remplacer plus tard par les données ANFR
# =============================================================================

# Chaque point est un "dictionnaire" : des paires nom -> valeur.
# "nom", "lat" (latitude) et "lon" (longitude) sont obligatoires.
# Les autres champs sont libres : ils s'afficheront tous dans les détails.
POINTS = [
    {"nom": "Site Rouen Centre", "lat": 49.4432, "lon": 1.0993,
     "operateur": "Orange", "technologie": "4G", "adresse": "Rouen"},

    {"nom": "Site Paris Nord", "lat": 48.8566, "lon": 2.3522,
     "operateur": "SFR", "technologie": "5G", "adresse": "Paris"},

    {"nom": "Site Marseille Port", "lat": 43.2965, "lon": 5.3698,
     "operateur": "Bouygues", "technologie": "4G", "adresse": "Marseille"},

    {"nom": "Site Lyon Part-Dieu", "lat": 45.7640, "lon": 4.8357,
     "operateur": "Free", "technologie": "5G", "adresse": "Lyon"},

    {"nom": "Site Lille Gare", "lat": 50.6292, "lon": 3.0573,
     "operateur": "Orange", "technologie": "5G", "adresse": "Lille"},
     
    {"nom": "Site Bordeaux Lac", "lat": 44.8378, "lon": -0.5792,
     "operateur": "SFR", "technologie": "4G", "adresse": "Bordeaux"},
]

# Couleur du rond sur la carte, selon l'opérateur
COULEURS = {
    "Orange": "#ff7900",
    "SFR": "#e2001a",
    "Bouygues": "#009fe3",
    "Free": "#757575",
}


# =============================================================================
# 2. LA CARTE
# =============================================================================

# Adresse du serveur de tuiles de l'IGN (Plan IGN, accès libre et gratuit)
# {z}, {x} et {y} sont remplacés automatiquement selon la zone et le zoom affichés
URL_IGN = (
    "https://data.geopf.fr/wmts?REQUEST=GetTile&SERVICE=WMTS&VERSION=1.0.0"
    "&STYLE=normal&TILEMATRIXSET=PM&FORMAT=image/png"
    "&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2"
    "&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}"
)

# On crée la carte avec ses réglages de départ
carte = folium.Map(
    location=[46.6, 2.5],        # Centre de départ : [latitude, longitude], le milieu de la France
    zoom_start=6,                # Zoom de départ (6 = on voit toute la France)
    min_zoom=5,                  # On ne peut pas dézoomer plus loin que ça
    min_lat=41, max_lat=52,      # Limites nord-sud de la zone parcourable
    min_lon=-6, max_lon=10.5,    # Limites ouest-est de la zone parcourable
    max_bounds=True,             # Active le blocage dans ces limites
    tiles=None,                  # Aucun fond par défaut : on ajoute celui de l'IGN juste après
)

# On ajoute le fond de carte IGN
folium.TileLayer(
    tiles=URL_IGN,                 # L'adresse des tuiles définie plus haut
    attr="© IGN - Géoplateforme",  # Mention de la source, affichée en bas à droite
).add_to(carte)


# =============================================================================
# 3. LE CSS : l'apparence de la page
# =============================================================================

CSS = """
/* La carte laisse 340 px libres à droite pour le volet */
.folium-map {
  width: calc(100% - 340px) !important;
}

/* Le volet : collé à droite, sur toute la hauteur, avec défilement si trop long */
#panneau {
  position: fixed;            /* Reste en place même si on fait défiler la page */
  top: 0;
  right: 0;                   /* Collé au bord droit */
  width: 340px;
  height: 100%;
  box-sizing: border-box;     /* Le padding est compté dans la largeur */
  padding: 16px;              /* Marge intérieure */
  overflow-y: auto;           /* Barre de défilement si le contenu dépasse */
  background: #f7f7f9;        /* Gris très clair */
  border-left: 1px solid #ccc;
  font-family: Arial, sans-serif;
  font-size: 14px;
  z-index: 1000;              /* Passe au-dessus de la carte */
}

/* Titres du volet */
#panneau h2 { font-size: 16px; margin: 18px 0 8px; }
#panneau h3 { font-size: 15px; margin: 0 0 8px; }

/* Barre de recherche : pleine largeur */
#recherche {
  width: 100%;
  box-sizing: border-box;
  padding: 8px;
}

/* Cadre blanc de la zone de détails */
#details {
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  padding: 10px;
}
#details p { margin: 4px 0; }
"""


# =============================================================================
# 4. LE HTML : le contenu du volet de droite
# =============================================================================

HTML = """
<div id="panneau">

  <h2>Recherche</h2>
  <!-- Barre de recherche : affichée, mais pas encore reliée à du code -->
  <input type="search" id="recherche" placeholder="Rechercher un site...">

  <h2>Filtres</h2>
  <b>Opérateur</b><br>
  <!-- Les cases à cocher sont créées automatiquement par le JavaScript -->
  <div id="filtres"></div>

  <h2>
    Détails
  </h2>
  <!-- Cette zone est remplie par le JavaScript quand on clique sur un point -->
  <div id="details">Clique sur un point de la carte pour voir ses détails.</div>

</div>
"""


# =============================================================================
# 5. LE JAVASCRIPT : le comportement de la page
# Les variables "carte", "points" et "couleurs" sont ajoutées juste avant ce code
# (voir l'assemblage plus bas)
# =============================================================================

JS = """
var marqueurs = [];   // On garde ici chaque rond avec son point

// Protège un texte pour l'afficher sans risque dans la page
function echapper(texte) {
  var d = document.createElement('div');
  d.textContent = texte;
  return d.innerHTML;
}

// Remplit la zone "Détails" avec les informations d'un point
function afficher(p) {
  var contenu = '<h3>' + echapper(p.nom) + '</h3>';
  Object.keys(p).forEach(function (cle) {
    // On affiche tous les champs sauf le nom (déjà en titre) et les coordonnées
    if (cle !== 'nom' && cle !== 'lat' && cle !== 'lon') {
      contenu += '<p><b>' + echapper(cle) + ' :</b> ' + echapper(p[cle]) + '</p>';
    }
  });
  contenu += '<p><b>Coordonnées :</b> ' + p.lat + ', ' + p.lon + '</p>';
  document.getElementById('details').innerHTML = contenu;
}

// Applique les filtres : montre les points dont l'opérateur est coché, cache les autres
function appliquerFiltres() {
  var coches = Array.from(document.querySelectorAll('.filtre:checked'))
                    .map(function (c) { return c.value; });
  marqueurs.forEach(function (m) {
    if (coches.indexOf(m.point.operateur) !== -1) {
      m.rond.addTo(carte);          // Opérateur coché : on affiche le point
    } else {
      carte.removeLayer(m.rond);    // Opérateur décoché : on le cache
    }
  });
}

// 1. On crée un rond coloré sur la carte pour chaque point
points.forEach(function (p) {
  var rond = L.circleMarker([p.lat, p.lon], {
    radius: 9,                                     // Taille du rond
    color: '#333', weight: 1,                      // Contour
    fillColor: couleurs[p.operateur] || '#3388ff', // Couleur selon l'opérateur
    fillOpacity: 0.9
  }).addTo(carte);

  rond.on('click', function () { afficher(p); });  // Au clic : afficher les détails
  marqueurs.push({ rond: rond, point: p });
});

// 2. On crée une case à cocher par opérateur présent dans les données
var operateurs = Array.from(new Set(points.map(function (p) { return p.operateur; }))).sort();
var zoneFiltres = document.getElementById('filtres');

operateurs.forEach(function (op) {
  var etiquette = document.createElement('label');     // Le texte cliquable
  var case_ = document.createElement('input');         // La case à cocher
  case_.type = 'checkbox';
  case_.className = 'filtre';
  case_.value = op;
  case_.checked = true;                                // Cochée au départ
  case_.addEventListener('change', appliquerFiltres);  // Au clic : on réapplique les filtres

  etiquette.appendChild(case_);
  etiquette.appendChild(document.createTextNode(' ' + op));
  zoneFiltres.appendChild(etiquette);
  zoneFiltres.appendChild(document.createElement('br'));
});
"""


# =============================================================================
# 6. L'ASSEMBLAGE ET L'ENREGISTREMENT
# =============================================================================

def en_json(valeur):
    """Convertit une donnée Python en texte JSON, sans risque dans une balise <script>."""
    texte = json.dumps(valeur, ensure_ascii=False)  # Conversion en texte JSON
    return texte.replace("</", "<\\/")              # Évite de casser la page si un texte contient "</"


# On donne au JavaScript la carte, les points et les couleurs
# (carte.get_name() est le nom interne de la carte dans la page, créé par folium)
donnees_js = (
    "var carte = " + carte.get_name() + ";\n"
    "var points = " + en_json(POINTS) + ";\n"
    "var couleurs = " + en_json(COULEURS) + ";\n"
)

# Le code est placé dans un événement "load" : il ne démarre qu'une fois la page
# entièrement chargée, donc après la création de la carte par folium
js_final = (
    "window.addEventListener('load', function () {\n"
    + donnees_js
    + JS
    + "\n});"
)

# On place chaque morceau au bon endroit de la page web
racine = carte.get_root()
racine.header.add_child(folium.Element("<style>" + CSS + "</style>"))  # CSS : dans l'en-tête
racine.html.add_child(folium.Element(HTML))                            # HTML : dans le corps de la page
racine.script.add_child(folium.Element(js_final))                      # JavaScript : dans la partie script

# On enregistre la page web finale
carte.save("carte.html")
print("Carte générée : carte.html")