from flask import Flask, request, jsonify, send_file, after_this_request
import os
import re
import threading
import zipfile
import base64
import shutil

from flask_cors import CORS

app = Flask(__name__)
cors = CORS(app, resources={r"/convert": {"origins": "*"}})

UPLOAD_FOLDER = '/temporal/upload'
EXTRACT_FOLDER = '/temporal/extract'
MAX_FILENAME_LENGTH = 255

def filtrar_directorios(dirs):
    """
    Filtra y elimina los directorios que comienzan con un punto.

    Args:
        dirs (list): Lista de nombres de directorios.
    """
    # Modifica la lista en su lugar para excluir directorios que comienzan con '.'
    dirs[:] = [d for d in dirs if not d.startswith('.')]

def listar_estructura_markdown(ruta, archivo_salida):
    """
    Genera la estructura del directorio en formato Markdown con listas desordenadas,
    excluyendo directorios ocultos.

    Args:
        ruta (str): Ruta de la carpeta a analizar.
        archivo_salida (str): Nombre del archivo Markdown de salida.
    """
    with open(archivo_salida, 'w', encoding='utf-8') as f:
        f.write("# Estructura del Proyecto\n\n")
        for root, dirs, files in os.walk(ruta):
            # Filtrar directorios ocultos
            filtrar_directorios(dirs)

            # Calcular el nivel de profundidad
            relative_path = os.path.relpath(root, ruta)
            if relative_path == '.':
                level = 0
            else:
                level = relative_path.count(os.sep) + 1
            indent = '    ' * level  # 4 espacios por nivel de indentación

            # Escribir el nombre de la carpeta
            carpeta = os.path.basename(root)
            if carpeta:  # Evitar escribir una línea vacía para la ruta raíz si es necesario
                f.write(f"{indent}- **🗀  {carpeta}/**\n")

            # Escribir los archivos dentro de la carpeta, excluyendo los de directorios ocultos
            for file in files:
                if not file.startswith('.'):  # Opcional: también puedes excluir archivos ocultos
                    file_indent = '    ' * (level + 1)
                    f.write(f"{file_indent}- 🗋  {file}\n")

def extraer_docstring(file_path):
    """
    Extrae el docstring o comentarios iniciales de un archivo según su tipo,
    excluyendo archivos en directorios ocultos.

    Args:
        file_path (str): Ruta completa del archivo.

    Returns:
        str: Contenido del docstring/comentario si se encuentra, de lo contrario, una cadena vacía.
    """
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    doc = ""

    # Excluir archivos en directorios ocultos
    partes = file_path.split(os.sep)
    if any(part.startswith('.') for part in partes):
        return doc

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if ext == '.py':
            # Extraer cadenas triple comillas al inicio del archivo
            match = re.match(r'^\s*(?:\'\'\'|\"\"\")([\s\S]*?)(?:\'\'\'|\"\"\")', content, re.DOTALL)
            if match:
                doc = match.group(1).strip()
            else:
                # Intentar extraer comentarios de una línea al inicio
                comments = []
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("#"):
                        comments.append(line.lstrip("#").strip())
                    elif not line:
                        continue
                    else:
                        break
                if comments:
                    doc = "\n".join(comments)
        elif ext in ['.js', '.php', '.css']:
            if ext == '.php':
                # Eliminar la etiqueta de apertura <?php antes de buscar comentarios
                content = re.sub(r'<\?php\s*', '', content, flags=re.IGNORECASE)
            # Extraer comentarios multilínea /* */ al inicio del archivo
            multiline_match = re.match(r'^\s*/\*([\s\S]*?)\*/', content, re.DOTALL)
            if multiline_match:
                doc = multiline_match.group(1).strip()
            else:
                # Extraer comentarios de una línea // al inicio del archivo
                comments = []
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("//"):
                        comments.append(line.lstrip("//").strip())
                    elif not line:
                        continue
                    else:
                        break
                if comments:
                    doc = "\n".join(comments)
        elif ext == '.html':
            # Extraer comentarios <!-- --> al inicio del archivo
            match = re.match(r'^\s*<!--([\s\S]*?)-->', content, re.DOTALL)
            if match:
                doc = match.group(1).strip()
        else:
            # Tipos de archivo no soportados
            pass

    except Exception as e:
        print(f"Error al procesar el archivo {file_path}: {e}")

    return doc

def agregar_docstrings_markdown(ruta, archivo_salida):
    """
    Agrega docstrings/comentarios de los archivos al documento Markdown,
    excluyendo directorios ocultos.

    Args:
        ruta (str): Ruta de la carpeta a analizar.
        archivo_salida (str): Nombre del archivo Markdown de salida.
    """
    with open(archivo_salida, 'a', encoding='utf-8') as f:
        f.write("\n# Documentación de Archivos\n\n")
        for root, dirs, files in os.walk(ruta):
            # Filtrar directorios ocultos
            filtrar_directorios(dirs)

            for file in files:
                if file.startswith('.'):
                    continue  # Opcional: también puedes excluir archivos ocultos
                file_path = os.path.join(root, file)
                doc = extraer_docstring(file_path)
                if doc:
                    # Crear una ruta relativa para el encabezado
                    relative_path = os.path.relpath(file_path, ruta)
                    f.write(f"## {relative_path}\n\n")
                    f.write(f"{doc}\n\n")

def agregar_codigo_markdown(ruta, archivo_salida):
    """
    Agrega el código de cada archivo al documento Markdown dentro de bloques de código,
    excluyendo directorios ocultos.

    Args:
        ruta (str): Ruta de la carpeta a analizar.
        archivo_salida (str): Nombre del archivo Markdown de salida.
    """
    with open(archivo_salida, 'a', encoding='utf-8') as f:
        f.write("\n# Código de Archivos\n\n")
        for root, dirs, files in os.walk(ruta):
            # Filtrar directorios ocultos
            filtrar_directorios(dirs)

            for file in files:
                if file.startswith('.'):
                    continue  # Opcional: también puedes excluir archivos ocultos
                file_path = os.path.join(root, file)
                _, ext = os.path.splitext(file)
                ext = ext.lower().lstrip('.')

                # Mapeo de extensiones a lenguajes para resaltado de sintaxis
                lang_map = {
                    'py': 'python',
                    'js': 'javascript',
                    'php': 'php',
                    'css': 'css',
                    'html': 'html',
                    'htm': 'html',
                    # Añade más extensiones y lenguajes si es necesario
                }

                lang = lang_map.get(ext, '')  # Si no se encuentra, no se especifica el lenguaje

                try:
                    with open(file_path, 'r', encoding='utf-8') as code_file:
                        code_content = code_file.read()

                    # Crear una ruta relativa para el encabezado
                    relative_path = os.path.relpath(file_path, ruta)
                    f.write(f"## {relative_path}\n\n")
                    f.write(f"```{lang}\n")
                    f.write(f"{code_content}\n")
                    f.write("```\n\n")

                except Exception as e:
                    print(f"Error al leer el archivo {file_path}: {e}")

def procesar(carpeta, archivo_md, actualizar_label):
    """
    Ejecuta las tres fases del procesamiento y actualiza la etiqueta de estado,
    excluyendo directorios ocultos.

    Args:
        carpeta (str): Ruta de la carpeta a analizar.
        archivo_md (str): Nombre del archivo Markdown de salida.
        actualizar_label (function): Función para actualizar la etiqueta de estado.
    """
    try:
        listar_estructura_markdown(carpeta, archivo_md)
        actualizar_label("Estructura del proyecto generada.")

        agregar_docstrings_markdown(carpeta, archivo_md)
        actualizar_label("Docstrings/comentarios agregados.")

        agregar_codigo_markdown(carpeta, archivo_md)
        actualizar_label("Código de archivos agregado.")

        actualizar_label(f"Proceso completado. Archivo generado: {archivo_md}")
    except Exception as e:
        print(f"Error en procesar: {e}")
        import traceback
        traceback.print_exc()
        actualizar_label(f"Error: {e}")

def iniciar_proceso(carpeta, archivo_md, actualizar_label):
    """
    Inicia el procesamiento en un hilo separado para mantener la UI responsiva.

    Args:
        carpeta (str): Ruta de la carpeta a analizar.
        archivo_md (str): Nombre del archivo Markdown de salida.
        actualizar_label (function): Función para actualizar la etiqueta de estado.
    """
    hilo = threading.Thread(target=procesar, args=(carpeta, archivo_md, actualizar_label))
    hilo.start()
    hilo.join()  # Esperar a que el hilo termine

def removeFolderTemporal():
    if os.path.exists(UPLOAD_FOLDER):
        shutil.rmtree(UPLOAD_FOLDER)
    if os.path.exists(EXTRACT_FOLDER):
        shutil.rmtree(EXTRACT_FOLDER)

@app.route('/convert', methods=['POST'])
def convert():
    try:
        removeFolderTemporal()
        data = request.get_json()
        if 'base64' not in data:
            return jsonify({"error": "No base64 part"}), 400

        base64_zip = data['base64']
        if not base64_zip:
            return jsonify({"error": "No base64 data"}), 400

        # Decode the base64 string
        try:
            zip_data = base64.b64decode(base64_zip)
        except Exception as e:
            return jsonify({"error": "Failed to decode base64", "message": str(e)}), 400

        # Ensure the upload and extract folders exist
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        if not os.path.exists(EXTRACT_FOLDER):
            os.makedirs(EXTRACT_FOLDER)

        # Save the decoded zip file
        filename = "uploaded.zip"
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        with open(save_path, 'wb') as f:
            f.write(zip_data)

        # Extract the zip file
        extract_path = os.path.join(EXTRACT_FOLDER, os.path.splitext(filename)[0])
        try:
            with zipfile.ZipFile(save_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
        except zipfile.BadZipFile as e:
            return jsonify({"error": "File is not a zip file", "message": str(e)}), 400

        # Process the extracted files
        archivo_md = os.path.join(EXTRACT_FOLDER, 'output.md')
        iniciar_proceso(extract_path, archivo_md, lambda msg: print(msg))

        # Ensure the output file exists before sending it
        if not os.path.exists(archivo_md):
            raise FileNotFoundError(f"Output file {archivo_md} not found")
        
        return send_file(archivo_md, as_attachment=True)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)