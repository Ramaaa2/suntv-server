import requests
from bs4 import BeautifulSoup
import json

# CONFIGURACIÓN
NPOINT_ID = "https://api.npoint.io/f3098e77b66eb5a7d32c" # El código final de tu URL de nPoint
API_TMDB = "f89f1b10ba76c14e544f07a1473f7d08"

def obtener_json_actual():
    try:
        res = requests.get(f"https://api.npoint.io/{NPOINT_ID}")
        return res.json()
    except:
        return []

def buscar_nuevas_peliculas(cantidad=30, omitir_titulos=[]):
    # Buscamos archivos mp4 en Archive.org con temática de películas
    query = "subject:(feature movies) AND format:(MPEG4)"
    url = f"https://archive.org/advancedsearch.php?q={query}&fl[]=identifier,title&rows=100&page=1&output=json"
    
    response = requests.get(url).json()
    items = response['response']['docs']
    
    nuevas = []
    for item in items:
        if len(nuevas) >= cantidad:
            break
            
        titulo_sucio = item['title']
        # Evitamos repetir si ya existe en el JSON
        if titulo_sucio in omitir_titulos:
            continue
            
        identificador = item['identifier']
        link_video = f"https://archive.org/download/{identificador}/{identificador}.mp4"
        
        # Intentamos obtener portada de TMDB (Opcional)
        portada = "https://via.placeholder.com/500x750.png?text=SunTV+Movie"
        
        nuevas.append({
            "titulo": titulo_sucio,
            "urlPortada": portada,
            "urlVideo": link_video,
            "calidad": "HD",
            "categoria": "Peliculas"
        })
    return nuevas

def actualizar_catalogo():
    # 1. Bajamos lo que ya tenemos
    lista_vieja = obtener_json_actual()
    titulos_existentes = [p['titulo'] for p in lista_vieja]
    
    # 2. Buscamos 30 que no tengamos
    nuevas_pelis = buscar_nuevas_peliculas(30, titulos_existentes)
    
    if nuevas_pelis:
        # 3. Sumamos las nuevas a las viejas
        lista_final = lista_vieja + nuevas_pelis
        
        # 4. Subimos de nuevo a nPoint
        res = requests.post(
            f"https://api.npoint.io/{NPOINT_ID}",
            json=lista_final
        )
        return f"Éxito: Se agregaron {len(nuevas_pelis)} películas nuevas."
    else:
        return "No se encontraron películas nuevas para agregar."

# Esto lo podés llamar desde una ruta de Flask en Render









