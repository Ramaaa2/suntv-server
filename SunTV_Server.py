import requests
from bs4 import BeautifulSoup

def buscar_peliculas_archive():
    # Buscamos en Archive.org películas con audio latino
    url_busqueda = "https://archive.org/advancedsearch.php?q=subject%3A%22peliculas+latino%22+AND+format%3A%22MPEG4%22&fl[]=identifier,title&output=json"
    
    response = requests.get(url_busqueda).json()
    items = response['response']['docs']
    
    nueva_lista = []
    
    for item in items[:20]: # Traemos las últimas 20 encontradas
        id_item = item['identifier']
        titulo = item['title']
        
        # El link directo en Archive.org suele seguir este patrón:
        link_directo = f"https://archive.org/download/{id_item}/{id_item}.mp4"
        
        # Aquí podrías usar tu lógica de TMDB para sacar la portada
        portada = "https://via.placeholder.com/500x750?text=SunTV" 
        
        nueva_lista.append({
            "titulo": titulo,
            "urlPortada": portada,
            "urlVideo": link_directo,
            "calidad": "HD",
            "categoria": "Peliculas"
        })
    
    return nueva_lista








