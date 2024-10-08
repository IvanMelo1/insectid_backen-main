import google.generativeai as genai
import json
import re
from dotenv import load_dotenv
import os
import firebase_admin
from firebase_admin import credentials, firestore

load_dotenv()
api = os.getenv('API_GEMINI')
genai.configure(api_key=api)

# Conexión DB con python (adjuntar key de sesion)
cred = credentials.Certificate("insectosia-firebase-adminsdk-uwlrs-eae804a7ba.json")
firebase_admin.initialize_app(cred)

# Inicializar Firestore
db = firestore.client()

# Inicio de sesion
def validar_inicio_sesion(nombre, password):
    try:
        # Busca en la colección 'usuarios' el documento que coincida con el email
        usuarios_ref = db.collection('usuarios').where('nombre', '==', nombre).stream()

        # Iterar sobre los documentos devueltos (aunque debería ser uno solo si el email es único)
        for usuario in usuarios_ref:
            usuario_data = usuario.to_dict()    
            if usuario_data['contraseña'] == password:
                return True, "Inicio de sesión exitoso"
            else:
                return False, "Contraseña incorrecta"
        
        # Si no se encuentra el email
        return False, "Usuario no encontrado"
    
    except Exception as e:
        return False, f"Error al validar: {str(e)}"
    
# Creación de usuario
def crear_usuario(nombre, password):
    try:
        # Verificar si ya existe un usuario con el mismo nombre
        usuarios_ref = db.collection('usuarios').where('nombre', '==', nombre).stream()

        # Iterar sobre los documentos devueltos para ver si ya existe un usuario con ese nombre
        for usuario in usuarios_ref:
            return {"status": "fail", "mensaje": f"El usuario {nombre} ya existe"}

        # Si no existe, proceder a crear un nuevo usuario
        doc_ref = db.collection('usuarios').document()
        
        # Establecer los datos del usuario en Firestore
        doc_ref.set({
            'nombre': nombre,
            'contraseña': password
        })

        return {"status": "success", "mensaje": f"Usuario {nombre} creado exitosamente"}
    
    except Exception as e:
        return {"status": "fail", "mensaje": f"Error al crear usuario: {str(e)}"}

# Función para subir la imagen
def image(path: str):
    try:
        sample_file = genai.upload_file(path=path)
        return sample_file
    except Exception as e:
        print("Error al procesar la imagen:", e)
        return None  # Cambiamos a `None` para indicar un fallo en la subida de la imagen

# Función para clasificar el insecto
def classify_insect(sample_file):
    if not sample_file:  # Verificamos si `sample_file` es válido
        return {"error": "No se pudo subir la imagen"}

    model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

    # Generamos el contenido con la imagen y el prompt
    try:
        response = model.generate_content(
            [sample_file, '''
            Responde como un entomólogo experto.
            Analiza la imagen y clasifica el insecto, proporcionando la siguiente información en formato JSON estructurado:
            {
            "Nombre_comun": "nombre común del insecto o null si no se encuentra",
            "Nombre_cientifico": "nombre científico del insecto o null si no se encuentra",
            "Clasificaciones_taxonomicas": "clasificaciones taxonómicas relevantes o null si no se encuentra",
            "Habitat_natural": "hábitat natural del insecto o null si no se encuentra",
            "Dieta": "dieta del insecto o null si no se encuentra",
            "Ciclo_de_vida": "ciclo de vida del insecto o null si no se encuentra",
            "Estado_de_conservacion": "estado de conservación del insecto o null si no se encuentra"
            }
            Si el animal en la imagen no es un insecto, responde con:
            {
            "error": "El animal no es un insecto"
            }
            '''],
            generation_config=genai.types.GenerationConfig(
                temperature=0.3)
        )

        # Intentamos obtener el texto de la respuesta
        response_text = response.text
        print("Response text from model:", response_text)  # Logging de la respuesta para depuración
        json_match = re.search(r"\{.*\}", response_text, re.DOTALL)        
        response_text = json_match.group(0)
        print("", response_text)
        
        # Intentamos deserializar la respuesta a JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print("Error decoding JSON:", e)
            return {"error": "Invalid JSON format from model"}

    except Exception as e:
        print("Error in model generation:", e)
        return {"error": "Error generating response from model"}
    
# Almacenar datos generados
def procesar_informacion_insecto(insect_data: dict) -> dict:
    try:
        # Referencia a la colección "insects" en Firestore
        insects_ref = db.collection('insectos')

        # Añadir los datos a Firestore
        doc_ref = insects_ref.add(insect_data)

        # Devolver una respuesta de éxito con el ID del documento
        return {"success": True, "doc_id": doc_ref[1].id}
    
    except Exception as e:
        print(f"Error storing insect data: {e}")
        return {"success": False, "error": str(e)}



# Función principal que llama a la subida y clasificación de la imagen
def id_insect(path: str) -> dict:
    sample_file = image(path)
    if sample_file is None:
        return {"error": "Error al subir la imagen"}

    Insect_classification = classify_insect(sample_file)
    return Insect_classification

