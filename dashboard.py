from flask import Flask, render_template, Blueprint
import mysql.connector
import plotly.express as px
import plotly.io as pio


# Déclarez un Blueprint pour encapsuler les routes liées au tableau de bord
dashboard_bp = Blueprint('dashboard', __name__)

# Connexion à la base de données MySQL
def get_db_connection():
    connection = mysql.connector.connect(
        host='localhost',
        user='root',  # Remplacez par votre nom d'utilisateur
        password='',  # Remplacez par votre mot de passe
        database='facelock'
    )
    return connection

# Fonction pour récupérer les examens programmés
def get_examens_programmes():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM examen")
    examens = cursor.fetchall()
    connection.close()
    return examens

# Fonction pour récupérer les accès aux salles
def get_acces_salles():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM acces")
    acces_salles = cursor.fetchall()
    connection.close()
    return acces_salles

# Fonction pour récupérer les présences aux examens
def get_presences_examens():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT examen.nomExamen, utilisateur.nom, utilisateur.prenom, examen_etudiant.estPresent 
        FROM examen_etudiant
        JOIN examen ON examen.idExamen = examen_etudiant.idExamen
        JOIN utilisateur ON utilisateur.idUtilisateur = examen_etudiant.idEtudiant
    """)
    presences = cursor.fetchall()
    connection.close()
    return presences

# Fonction pour récupérer les données de détection de visages
def get_face_detection_data():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT timestamp, status, nombreVisages, faceVectorAvg
        FROM face_detection
        ORDER BY timestamp DESC
        LIMIT 100
    """)
    data = cursor.fetchall()
    connection.close()
    return data

@dashboard_bp.route('/dashboard')
def dashboard():
    # Récupérer les données depuis la base de données
    examens = get_examens_programmes()
    acces_salles = get_acces_salles()
    presences = get_presences_examens()
    face_data = get_face_detection_data()
    
    # Préparer les données pour le graphique des examens
    dates_examens = [exam['date'] for exam in examens]
    counts_examens = [1] * len(dates_examens)  # Exemple pour comptabiliser les examens par date
    
    # Créer un graphique des examens programmés avec Plotly
    fig_examens = px.bar(x=dates_examens, y=counts_examens, labels={'x': 'Date', 'y': 'Nombre d\'examens'}, title='Examens Programmés')

    # Préparer les données pour le graphique de détection de visages
    timestamps = [d['timestamp'] for d in face_data]
    face_numbers = [d['nombreVisages'] for d in face_data]
    
    # Créer un graphique des visages détectés avec Plotly
    fig_faces = px.line(x=timestamps, y=face_numbers, labels={'x': 'Timestamp', 'y': 'Nombre de Visages Détectés'},
                        title='Nombre de Visages Détectés au Fil du Temps')

    # Convertir les graphiques en HTML
    graphique_examens_html = pio.to_html(fig_examens, full_html=False)
    graphique_faces_html = pio.to_html(fig_faces, full_html=False)

    # Passer les données au template HTML
    return render_template('dashboard.html', 
                           examens=examens,
                           acces_salles=acces_salles,
                           presences=presences,
                           graphique_examens=graphique_examens_html,
                           graphique_faces=graphique_faces_html)
