import os

def nettoyer_fichiers_vfr(chemin_racine="."):
    mot_cle = "Points VFR"
    fichiers_a_supprimer = []

    # Étape 1 : Chercher et lister tous les fichiers concernés
    for dossier_racine, sous_dossiers, fichiers in os.walk(chemin_racine):
        for nom_fichier in fichiers:
            if mot_cle in nom_fichier:
                chemin_complet = os.path.join(dossier_racine, nom_fichier)
                fichiers_a_supprimer.append(chemin_complet)

    # S'il n'y a rien à faire, on arrête le script
    if not fichiers_a_supprimer:
        print(f"Aucun fichier contenant '{mot_cle}' n'a été trouvé.")
        return

    # Étape 2 : Afficher la liste et demander confirmation
    print(f"Attention, {len(fichiers_a_supprimer)} fichier(s) trouvé(s) :")
    for f in fichiers_a_supprimer:
        print(f" - {f}")
    
    reponse = input("\nVoulez-vous vraiment supprimer tous ces fichiers ? (o/n) : ").strip().lower()
    
    if reponse in ['o', 'oui', 'y', 'yes']:
        # Étape 3 : Suppression des fichiers
        print("\nSuppression des fichiers en cours...")
        for f in fichiers_a_supprimer:
            try:
                os.remove(f)
                print(f"Fichier supprimé : {f}")
            except Exception as e:
                print(f"Erreur lors de la suppression de {f} : {e}")
        
        # Étape 4 : Suppression des dossiers vides
        # On utilise topdown=False pour commencer par les dossiers les plus profonds
        print("\nVérification et nettoyage des dossiers vides...")
        dossiers_supprimes = 0
        for dossier_racine, sous_dossiers, fichiers in os.walk(chemin_racine, topdown=False):
            try:
                # Si le dossier est complètement vide, on le supprime
                if not os.listdir(dossier_racine):
                    os.rmdir(dossier_racine)
                    print(f"Dossier vide supprimé : {dossier_racine}")
                    dossiers_supprimes += 1
            except Exception:
                # On ignore silencieusement les erreurs liées aux permissions
                pass 
        
        print(f"\nTerminé ! {len(fichiers_a_supprimer)} fichier(s) et {dossiers_supprimes} dossier(s) vide(s) ont été supprimés.")
    else:
        print("\nOpération annulée. Aucun fichier n'a été modifié.")

if __name__ == "__main__":
    # Vous pouvez remplacer "." par le chemin de votre choix, ex: "C:/MonDossier"
    nettoyer_fichiers_vfr(".")