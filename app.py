from flask import Flask, request, jsonify, session
import os
from utils import services
import json  # Importa el módulo json para trabajar con la conversión de cadenas JSON


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

# Ruta para verificar el estado del backend
@app.route('/', methods=['GET'])
def pedidos():
    return 'InsectID'  # Retorna un mensaje simple

# Inicio de sesion
@app.route('/iniciosesion', methods=['POST'])
def iniciosesion():
    # Obtener los datos enviados en la solicitud
    data = request.json
    nombre = data.get('nombre')
    contraseña = data.get('contraseña')

    # Llamar a la función de validación de inicio de sesión
    exito, mensaje = services.validar_inicio_sesion(nombre, contraseña)

    # Devolver una respuesta adecuada en formato JSON
    if exito:
        return jsonify({"mensaje": mensaje, "status": "success"}), 200
    else:
        return jsonify({"mensaje": mensaje, "status": "fail"}), 401

# Crear usuario
@app.route('/registrousuario', methods=['POST'])
def registro():
# Obtener los datos enviados en la solicitud POST
    data = request.json
    nombre = data.get('nombre')
    password = data.get('contraseña')

    # Verificar si ambos campos están presentes
    if not nombre or not password:
        return jsonify({"status": "fail", "mensaje": "Faltan campos 'nombre' o 'contraseña'"}), 400

    # Llamar a la función crear_usuario
    resultado = services.crear_usuario(nombre, password)
    
    # Devolver el resultado en formato JSON
    return jsonify(resultado), 200 if resultado['status'] == "success" else 500

# Ruta para procesar la imagen
@app.route('/intelligentid', methods=['POST'])
def enviar_imagen():
    if 'image' not in request.files:
        return jsonify({"error": "No image found in the request"}), 400

    # Obtiene la imagen de la solicitud
    image = request.files['image']

    # Guarda temporalmente la imagen
    image_path = os.path.join('temp', image.filename)
    os.makedirs('temp', exist_ok=True)  # Crea el directorio temp si no existe
    image.save(image_path)

    try:
        # Llama a la función que procesa la imagen
        result = services.id_insect(image_path)
        print("Result from services.id_insect:", result)
        
        # Verifica si result ya es un objeto Python o si necesita deserializarse
        if isinstance(result, str):
            try:
                result_json = json.loads(result)  # Deserializa la cadena JSON si es necesario
            except json.JSONDecodeError as e:
                return jsonify({"error": "Error processing the JSON", "details": str(e)}), 500
        else:
            result_json = result  # Si ya es un objeto Python, úsalo directamente

        # *Almacena los datos en la sesión*
        session['insect_data'] = result_json  # Aquí se almacena la información del insecto en la sesión.

    finally:
        # Elimina la imagen temporal, asegurando que siempre se elimine
        try:
            os.remove(image_path)
        except OSError as e:
            print(f"Error removing the file: {e}")

    # Retorna el resultado como un objeto JSON
    return jsonify(result_json)

# Guardar registro
@app.route('/save_insect_data', methods=['POST'])
def save_insect_data():
    try:
        # Verifica si los datos del insecto están presentes en la sesión
        if 'insect_data' not in session:
            return jsonify({"error": "No insect data available to save"}), 400

        # Recupera los datos desde la sesión
        insect_data = session['insect_data']

        # Llama a la función para almacenar los datos en Firebase
        store_result = services.procesar_informacion_insecto(insect_data)
        
        if not store_result['success']:
            return jsonify({"error": "Error storing insect data", "details": store_result['error']}), 500

        # Elimina los datos de la sesión después de guardarlos
        session.pop('insect_data', None)

        # Retorna una respuesta de éxito
        return jsonify({"success": True, "doc_id": store_result['doc_id']})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    
    app.run(host='0.0.0.0',debug=True)




