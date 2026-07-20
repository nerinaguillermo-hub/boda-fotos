"""
Descarga las fotos nuevas subidas a Cloudinary (dentro de un folder fijo)
y actualiza la carpeta fotos/ y el archivo fotos.json del repo.

Variables de entorno necesarias:
  CLOUDINARY_CLOUD_NAME
  CLOUDINARY_API_KEY
  CLOUDINARY_API_SECRET
  CLOUDINARY_FOLDER (opcional, default "bodaNG")
"""

import json
import os

import requests

CLOUD_NAME = os.environ["CLOUDINARY_CLOUD_NAME"]
API_KEY = os.environ["CLOUDINARY_API_KEY"]
API_SECRET = os.environ["CLOUDINARY_API_SECRET"]
FOLDER = os.environ.get("CLOUDINARY_FOLDER", "bodaNG")

FOTOS_DIR = "fotos"
FOTOS_JSON = "fotos.json"


def buscar_recursos():
    recursos = []
    cursor = None

    while True:
        body = {
            "expression": f'asset_folder="{FOLDER}"',
            "max_results": 500,
            "sort_by": [{"created_at": "asc"}],
        }
        if cursor:
            body["next_cursor"] = cursor

        resp = requests.post(
            f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/resources/search",
            json=body,
            auth=(API_KEY, API_SECRET),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

        recursos.extend(data.get("resources", []))

        cursor = data.get("next_cursor")
        if not cursor:
            break

    return recursos


def timestamp_de(nombre_archivo):
    # El nombre termina en ..._{fecha}_{hora}_{timestamp}_{random}.ext
    # El nombre de la persona puede tener guiones bajos, así que contamos
    # desde el final en vez de usar un índice fijo.
    base = nombre_archivo.rsplit(".", 1)[0]
    partes = base.split("_")

    try:
        return int(partes[-2])
    except (IndexError, ValueError):
        return 0


def main():
    os.makedirs(FOTOS_DIR, exist_ok=True)

    existentes = set(os.listdir(FOTOS_DIR))
    recursos = buscar_recursos()

    if not recursos:
        print(
            f"No se encontraron recursos en el folder '{FOLDER}'. "
            "Si esto no es lo esperado, revisá el nombre del folder en Cloudinary "
            "o probá cambiando la expresión a folder=\"{FOLDER}\" en el script."
        )

    nuevas = 0

    for recurso in recursos:
        public_id = recurso["public_id"]
        formato = recurso["format"]
        nombre_archivo = f"{public_id}.{formato}"

        if nombre_archivo in existentes:
            continue

        respuesta_img = requests.get(recurso["secure_url"], timeout=60)
        respuesta_img.raise_for_status()

        with open(os.path.join(FOTOS_DIR, nombre_archivo), "wb") as archivo:
            archivo.write(respuesta_img.content)

        existentes.add(nombre_archivo)
        nuevas += 1
        print(f"Descargada: {nombre_archivo}")

    todas = sorted(existentes, key=timestamp_de)

    with open(FOTOS_JSON, "w", encoding="utf-8") as archivo:
        json.dump(todas, archivo, ensure_ascii=False, indent=2)

    print(f"Fotos nuevas: {nuevas}")
    print(f"Total de fotos: {len(todas)}")

    salida_gh = os.environ.get("GITHUB_OUTPUT")
    if salida_gh:
        with open(salida_gh, "a", encoding="utf-8") as archivo:
            archivo.write(f"nuevas={nuevas}\n")


if __name__ == "__main__":
    main()
