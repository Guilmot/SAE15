
import pandas as pd

def liste():

    donnees = pd.read_csv(r"..\ref\ref\sup_exploitant.txt", sep=";")

    # On crée un dictionnaire à partir des données du fichier
    # set_index("ADM_ID") utilise les identifiants comme clés du dictionnaire
    # ["ADM_LB_NOM"] récupère les noms des exploitants
    # to_dict() transforme les données en dictionnaire Python
    bibliotheque_exploitants = donnees.set_index("ADM_ID")["ADM_LB_NOM"].to_dict()

    # On retourne le dictionnaire pour pouvoir l'utiliser ailleurs dans le programme
    return bibliotheque_exploitants


# On appelle la fonction et on récupère le dictionnaire
exploitants = liste()

# On affiche le dictionnaire complet
print(exploitants)

print(exploitants[149])
