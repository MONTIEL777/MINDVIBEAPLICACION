from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from dotenv import load_dotenv
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import cv2
import numpy as np
import os
import pymysql
from deepface import DeepFace

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

# 📌 Configuración de correo
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT'))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS') == 'True'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
mail = Mail(app)

# 📌 Función para conexión a la base de datos
def get_db_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST"),
        port=int(os.getenv("MYSQL_PORT")),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
        cursorclass=pymysql.cursors.DictCursor
    )

# 📌 Ruta principal
@app.route('/')
def index():
    return render_template('principal.html')

@app.route('/verificar_correo', methods=['POST'])
def verificar_correo():
    correo_usuario = request.form['correo']
    msg = Message('🌟 Verificación de correo - MindVibe',
                  sender=app.config['MAIL_USERNAME'],
                  recipients=[correo_usuario])
    msg.html = f"""
    <html>
    <body>
        <h3>¡Hola 👋!</h3>
        <p>Este es un mensaje de verificación para tu cuenta en MindVibe.</p>
        <p>Correo: {correo_usuario}</p>
        <p>Si tú no solicitaste esto, puedes ignorarlo.</p>
    </body>
    </html>
    """
    try:
        mail.send(msg)
        return "Correo personalizado enviado con éxito ✅"
    except Exception as e:
        return f"Error al enviar el correo: {str(e)}"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def analyze_emotion(image_path):
    try:
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        if len(faces) == 0:
            return None
        analysis = DeepFace.analyze(img_path=image_path, actions=["emotion"], enforce_detection=True)
        return analysis[0]["dominant_emotion"] if isinstance(analysis, list) else None
    except Exception as e:
        print(f"❌ Error de análisis: {e}")
        return None

def chatbot_response(emotion):
    responses = {
        "happy": "¡Genial! Sigue disfrutando tu día. 😊",
        "sad": "Parece que estás triste. ¿Quieres escuchar música relajante? 🎶",
        "angry": "Respira profundo. ¿Te gustaría hacer una actividad para calmarte? 🧘",
        "surprise": "¡Vaya! Algo inesperado pasó. ¿Quieres compartirlo? 🤔",
        "fear": "Todo estará bien. Trata de relajarte un poco. 💙",
        "neutral": "Todo parece tranquilo. ¡Sigue adelante! 🚀",
        "disgust": "Algo te desagrada. Tal vez hablar de ello te ayude. 🧐",
        "contempt": "Pareces molesto. ¿Qué te gustaría hacer para relajarte? 🤨"
    }
    return responses.get(emotion, "No pude detectar la emoción. Inténtalo de nuevo.")

@app.route('/formulario')
def formulario():
    return render_template('formulario.html')

@app.route('/guardar', methods=['POST'])
def guardar():
    nombre = request.form['nombre']
    correo = request.form['correo']
    contraseña = request.form['contraseña']
    hashed_password = generate_password_hash(contraseña)

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("INSERT INTO usuarios (nombre, correo, contraseña) VALUES (%s, %s, %s)", 
                    (nombre, correo, hashed_password))
        conn.commit()
    conn.close()
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        correo = request.form['correo']
        contraseña = request.form['contraseña']
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT * FROM usuarios WHERE correo = %s', (correo,))
            usuario = cursor.fetchone()
        conn.close()

        if usuario and check_password_hash(usuario['contraseña'], contraseña):
            session.clear()
            session['usuario_id'] = usuario['id']
            session['nombre'] = usuario['nombre']
            session['correo'] = usuario['correo']
            return redirect(url_for('detectar'))
        else:
            msg = '⚠️ Credenciales incorrectas. Intenta de nuevo.'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/detectar', methods=['GET'])
def detectar():
    if 'nombre' in session:
        return render_template("index.html", usuario=session['nombre'])
    return redirect(url_for('login'))

@app.route("/analyze", methods=["POST"])
def analyze():
    if "file" not in request.files:
        return jsonify({"error": "No se envió ninguna imagen"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)
    emotion = analyze_emotion(file_path)
    if emotion is None:
        return jsonify({"error": "No se detectó un rostro humano."}), 400
    message = chatbot_response(emotion)

    if 'usuario_id' in session:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("INSERT INTO emociones (usuario_id, emocion) VALUES (%s, %s)", 
                        (session['usuario_id'], emotion))
            conn.commit()
        conn.close()
    return jsonify({"emotion": emotion, "message": message})

@app.route('/estadisticas')
def estadisticas():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    filtro = request.args.get('filtro', 'dia')
    hoy = datetime.today()

    if filtro == 'dia':
        fecha_inicio = hoy.date()
    elif filtro == 'semana':
        fecha_inicio = hoy - timedelta(days=7)
    elif filtro == '15dias':
        fecha_inicio = hoy - timedelta(days=15)
    elif filtro == 'mes':
        fecha_inicio = hoy - timedelta(days=30)
    else:
        fecha_inicio = hoy - timedelta(days=1)

    conn = get_db_connection()
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT emocion, COUNT(*) as total 
            FROM emociones 
            WHERE usuario_id = %s AND fecha >= %s 
            GROUP BY emocion
        """, (session['usuario_id'], fecha_inicio))
        resultados = cursor.fetchall()
    conn.close()

    return render_template('estadisticas.html', resultados=resultados, filtro=filtro)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
