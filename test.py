import mysql.connector

# Connexion à la base de données MySQL
def connect_db():
    try:
        # Configuration de la connexion à la base de données
        connection = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',  # Votre mot de passe si nécessaire
            database='facelock'
        )
        if connection.is_connected():
            print("Connexion réussie à la base de données.")
        return connection
    except mysql.connector.Error as err:
        print(f"Erreur de connexion : {err}")
        return None

# Fonction pour rechercher un utilisateur par prénom
def find_user_by_first_name(prenom):
    connection = connect_db()
    if connection is None:
        return

    cursor = connection.cursor(dictionary=True)
    try:
        # Requête SQL pour rechercher un utilisateur par prénom
        query = """
            SELECT u.prenom, u.nom, u.role, e.nomExamen, e.date, e.heure, e.heureFin, s.nomSalle, a.dateDebut, a.dateFin
            FROM utilisateur u
            LEFT JOIN examen_etudiant ee ON u.idUtilisateur = ee.idEtudiant
            LEFT JOIN examen e ON ee.idExamen = e.idExamen
            LEFT JOIN examensalle es ON e.idExamen = es.IdExamen
            LEFT JOIN salle s ON es.IdSalle = s.idSalle
            LEFT JOIN acces a ON u.idUtilisateur = a.idUtilisateur AND a.idSalle = s.idSalle
            WHERE LOWER(u.prenom) = LOWER(%s);
        """
        cursor.execute(query, (prenom,))
        user = cursor.fetchone()

        if user:
            print("Utilisateur trouvé :")
            print(f"Prénom : {user['prenom']}")
            print(f"Nom : {user['nom']}")
            print(f"Rôle : {user['role']}")
            print(f"Examen : {user['nomExamen']}")
            print(f"Date de l'examen : {user['date']}")
            print(f"Heure : {user['heure']} - {user['heureFin']}")
            print(f"Salle : {user['nomSalle'] if user['nomSalle'] else 'Aucune salle assignée'}")
            print(f"Accès à la salle : {user['dateDebut'] if user['dateDebut'] else 'Aucun accès assigné'} - {user['dateFin'] if user['dateFin'] else 'Aucun accès assigné'}")
        else:
            print(f"Aucun utilisateur trouvé pour le prénom '{prenom}'.")
    except mysql.connector.Error as err:
        print(f"Erreur lors de la requête : {err}")
    finally:
        cursor.close()
        connection.close()

# Test de la fonction de recherche
if __name__ == "__main__":
    prenom_to_test = "DHOUHA"  # Testez avec le prénom que vous recherchez
    find_user_by_first_name(prenom_to_test)

