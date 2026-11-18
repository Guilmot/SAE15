
import pandas as pd

def liste():

    donnees_sup_exploitant = pd.read_csv(r"..\ref\ref\sup_exploitant.txt", sep=";")
    donnees_sup_nature = pd.read_csv(r"..\ref\ref\sup_nature.txt", sep=";")
    donnees_sup_proprietaire = pd.read_csv(r"..\ref\ref\sup_proprietaire.txt", sep=";")
    donnees_sup_type_antenne = pd.read_csv(r"..\ref\ref\sup_type_antenne.txt", sep=";")

    # On crée un dictionnaire à partir des données du fichier
    # set_index("ADM_ID") utilise les identifiants comme clés du dictionnaire
    # ["ADM_LB_NOM"] récupère les noms des exploitants

    # to_dict() transforme les données en dictionnaire Python
    bibliotheque_sup_exploitant = donnees_sup_exploitant.set_index("ADM_ID")["ADM_LB_NOM"].to_dict()
    bibliotheque_sup_nature = donnees_sup_nature.set_index("NAT_ID")["NAT_LB_NOM"].to_dict()
    bibliotheque_sup_proprietaire = donnees_sup_proprietaire.set_index("TPO_ID")["TPO_LB"].to_dict()
    bibliotheque_sup_type_antenne = donnees_sup_type_antenne.set_index("TAE_ID")["TAE_LB"].to_dict()

    # On retourne le dictionnaire pour pouvoir l'utiliser ailleurs dans le programme
    return bibliotheque_sup_exploitant, bibliotheque_sup_nature, bibliotheque_sup_proprietaire, bibliotheque_sup_type_antenne

# On appelle la fonction et on récupère le dictionnaire
exploitants, natures, proprietaires, types_antennes = liste()
print(" ")
print("Afficher les exploitants de l'antenne")
print(" ")
# Afficher les natures disponibles
for ID, nom in exploitants.items():
    print(ID, ":", nom)
print(" ")
print("Afficher les types de natures ou ce situent les antennes")
print(" ")
# Afficher les natures disponibles
for ID, nom in natures.items():
    print(ID, ":", nom)
print(" ")
print("Afficher le propriétaires de l'antenne")
print(" ")
# Afficher les propriétaires disponibles
for ID, nom in proprietaires.items():
    print(ID, ":", nom)
print(" ")
print("Afficher les différents type d'antenne")
print(" ")
# Afficher les types d'antennes disponibles
for ID, nom in types_antennes.items():
    print(ID, ":", nom)