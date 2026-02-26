import requests
import json

# CONFIGURACIÓN - REEMPLAZA CON TUS DATOS
NPOINT_ID = "https://api.npoint.io/f3098e77b66eb5a7d32c" 

def limpiar_titulo(texto):
    # Elimina extensiones y puntos para que se vea bien en la TV
    limpio = texto.replace(".mp4", "").replace(".mkv", "").replace(".", " ").replace("_", " ")
    # Quita palabras típicas de servidores piratas
    for palabra in ["720p", "1080p", "Dual", "Latino", "cinecalidad", "h264"]:
        limpio = limpio.replace(palabra, "")
    return limpio.strip().capitalize()

def actualizar_catalogo_latino():
    # 1. Obtener lo que ya tenemos en nPoint para no repetir
    try:
        url_npoint = f"https://api.npoint.io/{NPOINT_ID}"
        lista_actual = requests.get(url_npoint).json()
        if not isinstance(lista_actual, list): lista_actual = []
    except:
        lista_actual = []

    titulos_viejos = [p['titulo'] for p in lista_actual]

    # 2. Buscar en Archive.org (Query específica para Latino)
    # Buscamos: "peliculas" + "latino" + formato "mp4"
    query = 'subject:"peliculas latino" AND format:MPEG4'
    search_url = f"https://archive.org/advancedsearch.php?q={query}&fl[]=identifier,title&rows=100&page=1&output=json"
    
    try:
        data = requests.get(search_url).json()
        items = data['response']['docs']
    except:
        return "Error al conectar con el servidor de búsqueda."

    nuevas_agregadas = 0
    for item in items:
        if nuevas_agregadas >= 30: break # Límite de 30 por búsqueda

        titulo_original = item['title']
        identificador = item['identifier']
        
        # Si ya la tenemos, la saltamos
        if titulo_original in titulos_viejos:
            continue

        # Construir link directo (Archive.org standard)
        url_video = f"https://archive.org/download/{identificador}/{identificador}.mp4"
        
        # Intentar buscar una portada (Por ahora genérica, luego podemos usar TMDB)
        portada = f"https://via.placeholder.com/500x750.png?text={identificador}"

        lista_actual.append({
            "titulo": limpiar_titulo(titulo_original),
            "urlPortada": portada,
            "urlVideo": url_video,
            "calidad": "HD",
            "categoria": "Peliculas"
        })
        nuevas_agregadas += 1

    # 3. Subir la lista crecida a nPoint
    if nuevas_agregadas > 0:
        requests.post(url_npoint, json=lista_actual)
        return f"¡Éxito! Se sumaron {nuevas_agregadas} películas en latino. Total en catálogo: {len(lista_actual)}"
    else:
        return "No se encontraron películas nuevas en latino esta vez."








