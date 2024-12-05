from flask import Flask, render_template, jsonify, Response 
import threading
import cv2
import os
import numpy as np
import face_recognition
from flask_mysqldb import MySQL
import base64
from dashboard import dashboard_bp

app = Flask(__name__)

# Enregistrement du Blueprint
app.register_blueprint(dashboard_bp)

# Configuration de la base de données
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'facelock'

mysql = MySQL(app)

# Variables globales
detected_name = None
is_recognition_active = False
recognition_thread = None
cap = None
stop_event = threading.Event()

# Charger les images des étudiants et leur encodage
def load_images(path='persons'):
    images, classNames = [], []
    for file_name in os.listdir(path):
        img_path = os.path.join(path, file_name)
        try:
            img = cv2.imread(img_path)
            if img is None:
                print(f"Image non lisible : {img_path}")
                continue
            images.append(img)
            classNames.append(os.path.splitext(file_name)[0])
        except Exception as e:
            print(f"Erreur lors du chargement de l'image {img_path}: {e}")
    return images, classNames


def findEncodings(images):
    encodeList = []
    for img in images:
        if img is None:
            print("Skipping invalid or corrupted image.")
            continue

        if img.dtype != np.uint8 or len(img.shape) != 3:
            print("Image format invalid, converting to RGB.")
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        encodes = face_recognition.face_encodings(img)
        if encodes:
            encodeList.append(encodes[0])
        else:
            print("No face encodings found in this image.")
    return encodeList

# Fonction pour capturer et transmettre les cadres vidéo
def generate_frames():
    global cap, detected_name
    images, classNames = load_images()
    encodeListKnown = findEncodings(images)
    cap = cv2.VideoCapture(0)

    while True:
        success, img = cap.read()
        if not success:
            break

        imgS = cv2.resize(img, (0, 0), fx=0.25, fy=0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

        faceCurrentFrame = face_recognition.face_locations(imgS)
        encodeCurrentFrame = face_recognition.face_encodings(imgS, faceCurrentFrame)

        detected_name = "Nom détecté introuvable !"  # Par défaut
        for encodeFace, faceLoc in zip(encodeCurrentFrame, faceCurrentFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
            matchIndex = np.argmin(faceDis)

            if matches[matchIndex]:
                detected_name = classNames[matchIndex].upper()
                y1, x2, y2, x1 = faceLoc
                cv2.rectangle(img, (x1 * 4, y1 * 4), (x2 * 4, y2 * 4), (0, 0, 255), 2)
                cv2.rectangle(img, (x1 * 4, y2 * 4 - 35), (x2 * 4, y2 * 4), (0, 0, 255), cv2.FILLED)
                cv2.putText(img, detected_name, (x1 * 4 + 6, y2 * 4 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

        ret, buffer = cv2.imencode('.jpg', img)
        frame = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

# Routes Flask
@app.route('/')
def index():
    return render_template('index.html')  # Sert la page HTML principale

@app.route('/video')
def video():
    return render_template('LiveVideo.html')  # Sert la page HTML contenant le flux vidéo en direct

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/start_recognition', methods=['GET'])
def start_recognition():
    global recognition_thread, is_recognition_active, stop_event
    if not is_recognition_active:
        stop_event.clear()
        recognition_thread = threading.Thread(target=generate_frames, daemon=True)
        recognition_thread.start()
        is_recognition_active = True
        return jsonify({'status': 'success', 'message': 'Reconnaissance démarrée.'}), 200
    return jsonify({'status': 'error', 'message': 'Déjà en cours.'}), 400


@app.route('/user_info/<name>', methods=['GET'])
def user_info(name):
    cursor = mysql.connection.cursor()
    try:
        # Requête SQL pour récupérer les informations de l'utilisateur, de l'examen et de la salle
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
        cursor.execute(query, (name,))
        result = cursor.fetchone()

        if result:
            # Transformation du tuple en dictionnaire
            columns = [desc[0] for desc in cursor.description]
            user = dict(zip(columns, result))

            # Gestion des données manquantes pour la salle et l'accès
            salle = user['nomSalle'] if user['nomSalle'] else 'Aucune salle assignée'
            acces_debut = user['dateDebut'] if user['dateDebut'] else 'Aucun accès assigné'
            acces_fin = user['dateFin'] if user['dateFin'] else 'Aucun accès assigné'

            print("Utilisateur trouvé :")
            print(f"Prénom : {user['prenom']}")
            print(f"Nom : {user['nom']}")
            print(f"Rôle : {user['role']}")
            print(f"Examen : {user['nomExamen']}")
            print(f"Date de l'examen : {user['date']}")
            print(f"Heure : {user['heure']} - {user['heureFin']}")
            print(f"Salle : {salle}")
            print(f"Accès à la salle : {acces_debut} - {acces_fin}")

            # Conversion de l'image en base64 si elle existe
            image_path = os.path.join("persons", f"{user['prenom']}.png")
            if os.path.exists(image_path):
                with open(image_path, "rb") as img_file:
                    img_data = img_file.read()
                    encoded_img = base64.b64encode(img_data).decode('utf-8')
                return render_template('user_info.html', user={
                    'prenom': user['prenom'],
                    'nom': user['nom'],
                    'role': user['role'],
                    'photo': encoded_img,
                    'examen': user['nomExamen'],
                    'date': user['date'],
                    'heure': user['heure'],
                    'heureFin': user['heureFin'],
                    'salle': salle,
                    'acces_debut': acces_debut,
                    'acces_fin': acces_fin
                })
            else:
                return render_template('user_info.html', user={
                    'prenom': user['prenom'],
                    'nom': user['nom'],
                    'role': user['role'],
                    'examen': user['nomExamen'],
                    'date': user['date'],
                    'heure': user['heure'],
                    'heureFin': user['heureFin'],
                    'salle': salle,
                    'acces_debut': acces_debut,
                    'acces_fin': acces_fin,
                    'error': 'Image non trouvée'
                })
        else:
            return render_template('user_info.html', user={'error': 'Utilisateur non trouvé'})

    except Exception as e:
        print(f"Erreur SQL : {e}")
        return render_template('user_info.html', user={'error': 'Erreur lors de la récupération des données'})
    finally:
        cursor.close()


@app.route('/get_detected_name', methods=['GET'])
def get_detected_name():
    global detected_name
    return jsonify({'detected_name': detected_name})

@app.route('/stop_recognition', methods=['GET'])
def stop_recognition():
    global is_recognition_active
    if is_recognition_active:
        stop_event.set()
        recognition_thread.join()  # Ensure thread stops
        is_recognition_active = False
        return jsonify({'status': 'success', 'message': 'Reconnaissance arrêtée.'}), 200
    return jsonify({'status': 'error', 'message': 'Aucune reconnaissance en cours.'}), 400


if __name__ == '__main__':
    app.run(debug=True)