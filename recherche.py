import pandas as pd

Path_data = "../data/data" 
Path_ref = "../ref"

## dev_path to comment
##Path_data = "Z:/RT/Semestre1/SAE15/data/data" 
##Path_ref = "Z:/RT/Semestre1/SAE15/ref"

## la limite de recherche correspondra à la limite d'element qui sera afficher sur la carte. La fonction recherche ne sera pas affecté par la limite.
## Sinon, le filtre et classement par critère des élément recherché ne sera pas complet
limiteRecherche = 250 # by default
limiteRecherche = -1 # -1 mean no limit. Use for test. Comment to disable it


## all csv data frames in data folder
print("CHARGEMENT DES DATA")

sup_antenne_df = pd.read_csv(Path_data+"/sup_antenne.txt",sep=";")
sup_bande_df = pd.read_csv(Path_data+"/sup_bande.txt",sep=";")
sup_emetteur_df = pd.read_csv(Path_data+"/sup_emetteur.txt",sep=";")
sup_station_df = pd.read_csv(Path_data+"/sup_station.txt",sep=";")
sup_support_df = pd.read_csv(Path_data+"/sup_support.txt",sep=";")

## all csv data frames in ref folder
sup_exploitant_df = pd.read_csv(Path_ref+"/sup_exploitant.txt",sep=";")
sup_nature_df = pd.read_csv(Path_ref+"/sup_nature.txt",sep=";")
sup_proprietaire_df = pd.read_csv(Path_ref+"/sup_proprietaire.txt",sep=";")
sup_type_antenne_df = pd.read_csv(Path_ref+"/sup_type_antenne.txt",sep=";")


print("FIN DE CHARGEMENT DES DATA")

# return the string without space and upper letter
def correct_str(string):
    return str(string).lower().strip()

# dictionnary with code of every french region
regions_france = {
    "Guadeloupe": "01",
    "Martinique": "02",
    "Guyane": "03",
    "La Réunion": "04",
    "Mayotte": "06",
    "Île-de-France": "11",
    "Centre-Val de Loire": "24",
    "Bourgogne-Franche-Comté": "27",
    "Normandie": "28",
    "Hauts-de-France": "32",
    "Grand Est": "44",
    "Pays de la Loire": "52",
    "Bretagne": "53",
    "Nouvelle-Aquitaine": "75",
    "Occitanie": "76",
    "Auvergne-Rhône-Alpes": "84",
    "Provence-Alpes-Côte d'Azur": "93",
    "Corse": "94"
}

# dictionnary with the code of every department
departements_vers_region = {
    "01": "Auvergne-Rhône-Alpes", "02": "Hauts-de-France", "03": "Auvergne-Rhône-Alpes",
    "04": "Provence-Alpes-Côte d'Azur", "05": "Provence-Alpes-Côte d'Azur", "06": "Provence-Alpes-Côte d'Azur",
    "07": "Auvergne-Rhône-Alpes", "08": "Grand Est", "09": "Occitanie", "10": "Grand Est",
    "11": "Occitanie", "12": "Occitanie", "13": "Provence-Alpes-Côte d'Azur", "14": "Normandie",
    "15": "Auvergne-Rhône-Alpes", "16": "Nouvelle-Aquitaine", "17": "Nouvelle-Aquitaine",
    "18": "Centre-Val de Loire", "19": "Nouvelle-Aquitaine", "20": "Corse",
    "21": "Bourgogne-Franche-Comté", "22": "Bretagne", "23": "Nouvelle-Aquitaine",
    "24": "Nouvelle-Aquitaine", "25": "Bourgogne-Franche-Comté", "26": "Auvergne-Rhône-Alpes",
    "27": "Normandie", "28": "Centre-Val de Loire", "29": "Bretagne", "30": "Occitanie",
    "31": "Occitanie", "32": "Occitanie", "33": "Nouvelle-Aquitaine", "34": "Occitanie",
    "35": "Bretagne", "36": "Centre-Val de Loire", "37": "Centre-Val de Loire",
    "38": "Auvergne-Rhône-Alpes", "39": "Bourgogne-Franche-Comté", "40": "Nouvelle-Aquitaine",
    "41": "Centre-Val de Loire", "42": "Auvergne-Rhône-Alpes", "43": "Auvergne-Rhône-Alpes",
    "44": "Pays de la Loire", "45": "Centre-Val de Loire", "46": "Occitanie",
    "47": "Nouvelle-Aquitaine", "48": "Occitanie", "49": "Pays de la Loire", "50": "Normandie",
    "51": "Grand Est", "52": "Grand Est", "53": "Pays de la Loire", "54": "Grand Est",
    "55": "Grand Est", "56": "Bretagne", "57": "Grand Est", "58": "Bourgogne-Franche-Comté",
    "59": "Hauts-de-France", "60": "Hauts-de-France", "61": "Normandie", "62": "Hauts-de-France",
    "63": "Auvergne-Rhône-Alpes", "64": "Nouvelle-Aquitaine", "65": "Occitanie", "66": "Occitanie",
    "67": "Grand Est", "68": "Grand Est", "69": "Auvergne-Rhône-Alpes", "70": "Bourgogne-Franche-Comté",
    "71": "Bourgogne-Franche-Comté", "72": "Pays de la Loire", "73": "Auvergne-Rhône-Alpes",
    "74": "Auvergne-Rhône-Alpes", "75": "Île-de-France", "76": "Normandie", "77": "Île-de-France",
    "78": "Île-de-France", "79": "Nouvelle-Aquitaine", "80": "Hauts-de-France", "81": "Occitanie",
    "82": "Occitanie", "83": "Provence-Alpes-Côte d'Azur", "84": "Provence-Alpes-Côte d'Azur",
    "85": "Pays de la Loire", "86": "Nouvelle-Aquitaine", "87": "Nouvelle-Aquitaine",
    "88": "Grand Est", "89": "Bourgogne-Franche-Comté", "90": "Bourgogne-Franche-Comté",
    "91": "Île-de-France", "92": "Île-de-France", "93": "Île-de-France", "94": "Île-de-France",
    "95": "Île-de-France", "971": "Guadeloupe", "972": "Martinique", "973": "Guyane",
    "974": "La Réunion", "976": "Mayotte"
}

# function that return a tuple with the region name and its code
def getRegion(code_postal):
    cp = str(code_postal).strip()

    ## some region as a code composed of 3 number so we need to detect it
    dept = cp[:3] if cp.startswith(("97", "98")) else cp[:2]
    
    nom_region = departements_vers_region.get(dept)
    if nom_region:
        code_region = regions_france[nom_region]
        return nom_region, code_region
    return None, None


## retrun a dictionnary of index corresponding to the result of a research that can be by postal code, city name, region name
## contain two parameters : researchType indicate the research value ("CodePostal" for postal code, "Region" for the region, "Commune" for the city )
## researchValue is the value to research for exemple a postal code, city name ...
def userResearch(researchType : str, researchValue):
    print("Recupération des adresses global")

    ## add a dictionnary that contains important id, result of an actual research
    def newEntry(table,x,df):
        ListResResult.append(
            {
                "SUP_ID" : df["SUP_ID"][x].item(),
                "STA_NM_ANFR" : df["STA_NM_ANFR"][x], ## L'Identifiant STA_NM_ANFR Permet une jointure avec toutes les autres tables
                "NAT_ID" : df["NAT_ID"][x].item(),
                "TPO_ID" : df["TPO_ID"][x].item()
                #"ADM_ID": sup_station_df.loc[sup_station_df["STA_NM_ANFR"] == df["STA_NM_ANFR"].iloc[x], "ADM_ID"].iloc[0].item() if not sup_station_df.loc[sup_station_df["STA_NM_ANFR"] == df["STA_NM_ANFR"].iloc[x]].empty else None,
                #"AER_ID": sup_antenne_df.loc[sup_antenne_df["STA_NM_ANFR"] == df["STA_NM_ANFR"].iloc[x], "AER_ID"].iloc[0].item() if not sup_antenne_df.loc[sup_antenne_df["STA_NM_ANFR"] == df["STA_NM_ANFR"].iloc[x]].empty else None,
                #"TAE_ID": sup_antenne_df.loc[sup_antenne_df["STA_NM_ANFR"] == df["STA_NM_ANFR"].iloc[x], "TAE_ID"].iloc[0].item() if not sup_antenne_df.loc[sup_antenne_df["STA_NM_ANFR"] == df["STA_NM_ANFR"].iloc[x]].empty else None,
                #"EMR_ID": sup_emetteur_df.loc[sup_emetteur_df["STA_NM_ANFR"] == df["STA_NM_ANFR"].iloc[x], "EMR_ID"].iloc[0].item() if not sup_emetteur_df.loc[sup_emetteur_df["STA_NM_ANFR"] == df["STA_NM_ANFR"].iloc[x]].empty else None,
                #"BAN_ID": sup_bande_df.loc[sup_bande_df["STA_NM_ANFR"] == df["STA_NM_ANFR"].iloc[x], "BAN_ID"].iloc[0].item() if not sup_bande_df.loc[sup_bande_df["STA_NM_ANFR"] == df["STA_NM_ANFR"].iloc[x]].empty else None
            }
        )

    df = sup_support_df
    correctResearchType = correct_str(researchType)
    shape = df["ADR_LB_LIEU"].shape
    taille_x = shape[0]
    
    ListResResult = []
    
    if correctResearchType not in ["codepostal","region","lieu"] :
        print("Ne peut pas rechercher : type de recherche incorrecte : "+researchType)
        return
    
    ## Search by a for loop to see if we found a value
    for x in range (taille_x):
        
        ## in the case make a research by a postal code
        if correctResearchType == "codepostal":
            codePostalActuel = str(df["ADR_NM_CP"][x])
       
            if codePostalActuel == str(researchValue):
                newEntry(ListResResult,x,df)

        ## in the case the research is made by name
        if correctResearchType == "lieu":
            lieuActuel = correct_str(df["ADR_LB_LIEU"][x])

            if lieuActuel == str(researchValue):
                newEntry(ListResResult,x,df)

        ## in the case the research is made by region name
        if correctResearchType == "region":
            regionActuel = getRegion(str(df["ADR_NM_CP"][x]))

            if regionActuel[0] == str(researchValue) or regionActuel[1] == str(researchValue):
                newEntry(ListResResult,x,df)
                
    return ListResResult

print(userResearch("codepostal","76690"))
            