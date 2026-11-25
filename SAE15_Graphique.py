import os # os sert à construire les chemins vers les fichiers
import tkinter as tk # tkinter sert à créer la fenêtre
import pandas as pd # pandas sert à lire et manipuler les tableaux de données


DOSSIER_SCRIPT = os.path.dirname(os.path.abspath(__file__)) # Dossier où se trouve ce script
DOSSIER_DATA = os.path.join(DOSSIER_SCRIPT, 'data') # Dossier des tables principales
DOSSIER_REF = os.path.join(DOSSIER_SCRIPT, 'ref') # Dossier des tables de référence (les libellés)


def lire_fichier(dossier, nom_fichier, colonnes, type_donnees=str): # Fonction qui lit un fichier ANFR en ne gardant que les colonnes demandées
    chemin_fichier = os.path.join(dossier, nom_fichier) # Chemin complet du fichier
    print("Lecture de", nom_fichier) # On affiche dans la console le fichier en cours de lecture
    tableau = pd.read_csv(chemin_fichier, sep=';', usecols=colonnes, dtype=type_donnees, on_bad_lines='warn')
    return tableau # On renvoie le tableau


# 1. Lecture des données (seulement les colonnes utiles aux graphiques)

stations = lire_fichier(DOSSIER_DATA, 'SUP_STATION.txt', ['ADM_ID', 'DTE_EN_SERVICE']) # Stations : code exploitant, date de mise en service
supports = lire_fichier(DOSSIER_DATA, 'SUP_SUPPORT.txt', ['SUP_ID', 'NAT_ID', 'TPO_ID']) # Supports : numéro du support, code nature, code propriétaire
emetteurs = lire_fichier(DOSSIER_DATA, 'SUP_EMETTEUR.txt', ['EMR_LB_SYSTEME'], 'category') # Émetteurs : seulement le système, en category car très répété
bandes = lire_fichier(DOSSIER_DATA, 'SUP_BANDE.txt', ['BAN_NB_F_DEB', 'BAN_NB_F_FIN', 'BAN_FG_UNITE']) # Bandes : fréquence de début, fréquence de fin et unité

ref_exploitants = lire_fichier(DOSSIER_REF, 'SUP_EXPLOITANT.txt', ['ADM_ID', 'ADM_LB_NOM']) # Table de référence : code exploitant -> nom de l'exploitant
ref_natures = lire_fichier(DOSSIER_REF, 'SUP_NATURE.txt', ['NAT_ID', 'NAT_LB_NOM']) # Table de référence : code nature -> nom de la nature du support
ref_proprietaires = lire_fichier(DOSSIER_REF, 'SUP_PROPRIETAIRE.txt', ['TPO_ID', 'TPO_LB']) # Table de référence : code propriétaire -> nom du propriétaire


# 2. Préparation des données

ref_exploitants = ref_exploitants.drop_duplicates(subset='ADM_ID') # Si un code apparaissait 2 fois, le merge doublerait des lignes et fausserait les comptes : on garde chaque code une seule fois
ref_natures = ref_natures.drop_duplicates(subset='NAT_ID') # Pareil pour les natures
ref_proprietaires = ref_proprietaires.drop_duplicates(subset='TPO_ID') # Pareil pour les propriétaires

supports = supports.drop_duplicates(subset='SUP_ID') # Un même support (pylône, château d'eau...) peut porter plusieurs installations : on le garde une seule fois pour compter les supports physiques
stations = stations.merge(ref_exploitants, on='ADM_ID', how='left') # On ajoute le nom de l'exploitant à chaque station grâce au code ADM_ID
supports = supports.merge(ref_natures, on='NAT_ID', how='left') # On ajoute le nom de la nature à chaque support grâce au code NAT_ID
supports = supports.merge(ref_proprietaires, on='TPO_ID', how='left') # On ajoute le nom du propriétaire à chaque support grâce au code TPO_ID

stations['DTE_EN_SERVICE'] = pd.to_datetime(stations['DTE_EN_SERVICE'], format='%d/%m/%Y', errors='coerce') # On transforme le texte "jj/mm/aaaa" en vraie date (les dates invalides deviennent vides)

bandes['BANDE'] = bandes['BAN_NB_F_DEB'] + '-' + bandes['BAN_NB_F_FIN'] + ' ' + bandes['BAN_FG_UNITE'] + 'Hz' # On fabrique un libellé lisible pour chaque bande, par exemple "925,1-935,1 MHz"
bandes = bandes[['BANDE']].astype('category') # On ne garde que le libellé, en category car très répété


# 4. Fenêtre Tkinter

fenetre = tk.Tk() # On crée la fenêtre principale
fenetre.title("Analyse des installations radio ANFR") # Titre de la fenêtre
fenetre.geometry("1300x850") # Taille de la fenêtre en pixels
titre_fenetre = tk.Label(fenetre, text="Analyse des installations radio ANFR", font=("Arial", 16, "bold")) # On ajoute un titre en haut de la fenêtre
titre_fenetre.pack(pady=10) # On place le titre dans la fenêtre

barre_defilement = tk.Scrollbar(fenetre, orient=tk.VERTICAL) # On crée la barre de défilement verticale
barre_defilement.pack(side=tk.RIGHT, fill=tk.Y) # On la place à droite de la fenêtre, sur toute la hauteur
zone_defilement = tk.Canvas(fenetre, yscrollcommand=barre_defilement.set, highlightthickness=0) # On crée une zone qui peut défiler, reliée à la barre (highlightthickness=0 : sans bordure noire)
zone_defilement.pack(side=tk.LEFT, fill=tk.BOTH, expand=True) # On la place à gauche de la barre, en prenant toute la place restante
barre_defilement.config(command=zone_defilement.yview) # Quand on bouge la barre, la zone défile

fenetre.mainloop() # On lance la fenêtre