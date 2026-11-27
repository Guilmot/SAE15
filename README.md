# SAE15 - Cartographie des installations radioélectriques en France

Ce programme Python utilise les données ouvertes de l'ANFR (Agence nationale des fréquences) sur les installations radioélectriques de plus de 5 watts.

Il permet de rechercher les supports d'antennes par code postal, par lieu ou par région, de les afficher sur une carte interactive avec le détail de chaque site, et de consulter six graphiques sur l'ensemble des données de France.

Tout le code se trouve dans le fichier analyse_donnee_SAE15.py.


## Installation

Installer les bibliothèques :

```
pip install pandas folium matplotlib tkwry
```

Il faut les deux archives, data et ref, à décompresser à côté du script :

```
SAE15/
  analyse_donnee_SAE15.py
  data/
    sup_support.txt
    sup_station.txt
    sup_antenne.txt
    sup_emetteur.txt
    sup_bande.txt
  ref/
    sup_proprietaire.txt
    sup_nature.txt
    sup_exploitant.txt
    sup_type_antenne.txt
```

Lancer le programme :

```
python analyse_donnee_SAE15.py
```


## Utilisation

Au démarrage, le programme génère les graphiques, affiche une première carte sur Elbeuf (76500) puis ouvre la fenêtre de recherche.

Dans le panneau de gauche, on choisit le type de recherche, on tape la valeur puis on clique sur Rechercher :
- codepostal : un code postal, par exemple 76500
- lieu : le nom du lieu tel qu'il apparaît au début de l'adresse dans les fiches
- region : le nom de la région en minuscules sans espace ni accent (normandie, iledefrance, auvergnerhonealpes...) ou son code (28 pour la Normandie)

Le bouton Afficher les graphiques permet de passer de la carte aux graphiques.

Sur la carte, la couleur d'un point indique la nature du support (pylône, château d'eau, bâtiment...) et sa taille dépend de la hauteur du support. Un clic sur un point affiche sa fiche : adresse, propriétaire, hauteur, puis la liste des stations avec leurs antennes, émetteurs et fréquences.

Les six graphiques montrent :
- le nombre d'installations par exploitant
- les natures de support les plus fréquentes
- la répartition des propriétaires de support
- les systèmes utilisés par les émetteurs (GSM, LTE, 5G...)
- les bandes de fréquences les plus utilisées
- le nombre cumulé d'installations par année de mise en service depuis 1950

## Structure du code

Les données ANFR sont réparties en plusieurs tables reliées par des identifiants :
- sup_support contient les supports physiques et leurs coordonnées GPS. Un support peut porter plusieurs stations.
- sup_station contient les stations, une par exploitant (Orange, SFR, TDF...).
- sup_antenne et sup_emetteur contiennent les antennes et les émetteurs de chaque station.
- sup_bande contient les bandes de fréquences de chaque émetteur.
- les tables du dossier ref donnent les noms des propriétaires, natures, exploitants et types d'antennes.

Le script est organisé dans cet ordre :
1. Configuration : recherche des dossiers data et ref, paramètres (nombre maximum de supports affichés, taille des paquets de lecture...).
2. Chargement : lecture de sup_support et des tables de référence, transformées en dictionnaires.
3. Graphiques : fonction generer_image_graphiques qui crée l'image graphiques.png.
4. Lecture des détails : fonctions lire_filtre et charger_details qui lisent les grandes tables uniquement pour les stations à afficher.
5. Fiches : fonctions html_station, html_emetteur et details_support qui construisent le contenu des fiches.
6. Géographie : correspondance entre départements et régions.
7. Recherche : fonction userResearch.
8. Carte : fonction generateMap qui crée le fichier carte.html.
9. Interface : fonction lancer_interface qui crée la fenêtre Tkinter.

## Démarche algorithmique

1. Au lancement, seules la table des supports et les petites tables de référence sont chargées. Les tables de référence sont transformées en dictionnaires pour retrouver directement un nom à partir de son identifiant.

2. Les graphiques portent sur toute la France et ne dépendent pas de la recherche. Ils sont donc calculés une seule fois et enregistrés dans une image. Pour économiser la mémoire, seules les colonnes utiles sont lues.

3. La recherche filtre la table des supports en une seule opération pandas, sans parcourir les lignes une par une. Pour une recherche par région, le département est déduit des premiers chiffres du code postal, puis converti en région.

4. Un support apparaît sur plusieurs lignes (une par station). On garde une seule ligne par support, on compte ses stations, et on limite l'affichage à 250 supports pour que la carte reste fluide.

5. Les grandes tables (stations, antennes, émetteurs, bandes) sont lues par paquets de 500 000 lignes. On ne garde que les lignes qui concernent les stations à afficher.

6. Les coordonnées GPS sont fournies en degrés, minutes et secondes. Elles sont converties en degrés décimaux avec la formule degrés + minutes / 60 + secondes / 3600, et deviennent négatives pour le Sud et l'Ouest.

7. Pour chaque support, une fiche est construite : support, puis stations, puis antennes, puis émetteurs, puis bandes de fréquences.

8. Les points sont regroupés par nature de support, et chaque nature reçoit une couleur différente. Les points proches sont regroupés quand on dézoome. La carte est centrée automatiquement sur les résultats puis enregistrée dans carte.html.

9. L'interface recharge la carte seulement si le fichier a changé. Une recherche sans résultat garde donc la carte précédente.

## Contraintes pour les utilisateurs hors du groupe

- Les recherches par lieu et par région demandent une saisie exacte.
- La recherche par région ne fonctionne pas pour la Corse, mais la recherche par code postal fonctionne.
- Les fichiers carte.html et graphiques.png sont recréés à chaque lancement dans le dossier du script.


## Licence

Projet sous licence MIT (voir le fichier LICENSE).

Données : ANFR,
Fond de carte : IGN.