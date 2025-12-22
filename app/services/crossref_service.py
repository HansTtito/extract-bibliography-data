import requests
from typing import Optional, Dict, Any
from app.config import settings
from app.utils.text_processing import format_authors, normalize_text


class CrossRefService:
    BASE_URL = "https://api.crossref.org/works"
    
    def __init__(self):
        self.email = settings.crossref_email or "example@example.com"
        self.headers = {
            "User-Agent": f"BibliografiaExtractor/1.0 (mailto:{self.email})",
            "Accept": "application/json"
        }
    
    def search_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Busca un documento por DOI"""
        try:
            url = f"{self.BASE_URL}/{doi}"
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok' and 'message' in data:
                    return self._map_crossref_to_document(data['message'])
        except Exception as e:
            print(f"Error searching by DOI {doi}: {e}")
        return None
    
    def search_by_title_author(self, title: str, authors: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Busca un documento por título y opcionalmente autores"""
        try:
            params = {
                "query.title": title[:200],  # Limitar longitud
                "rows": 1
            }
            if authors:
                params["query.author"] = authors[:200]
            
            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok' and data.get('message', {}).get('items'):
                    item = data['message']['items'][0]
                    return self._map_crossref_to_document(item)
        except Exception as e:
            print(f"Error searching by title/author: {e}")
        return None
    
    def _map_crossref_to_document(self, crossref_data: Dict[str, Any]) -> Dict[str, Any]:
        """Mapea datos de CrossRef a formato de documento"""
        doc = {}
        
        # Autores
        authors = crossref_data.get('author', [])
        if authors:
            doc['autores'] = format_authors(authors)
        
        # Año
        date_parts = crossref_data.get('published-print', {}).get('date-parts', [[]])
        if not date_parts[0]:
            date_parts = crossref_data.get('published-online', {}).get('date-parts', [[]])
        if date_parts and date_parts[0]:
            doc['ano'] = date_parts[0][0]
        
        # Título
        titles = crossref_data.get('title', [])
        if titles:
            title = normalize_text(titles[0])
            # Corregir encoding común: "á;" -> "á"
            if title:
                title = title.replace('á;', 'á').replace('é;', 'é').replace('í;', 'í')
                title = title.replace('ó;', 'ó').replace('ú;', 'ú').replace('ñ;', 'ñ')
                title = title.replace('Á;', 'Á').replace('É;', 'É').replace('Í;', 'Í')
                title = title.replace('Ó;', 'Ó').replace('Ú;', 'Ú').replace('Ñ;', 'Ñ')
            doc['titulo_original'] = title
        
        # DOI
        if 'DOI' in crossref_data:
            doc['doi'] = crossref_data['DOI']
        
        # Link
        if 'URL' in crossref_data:
            doc['link'] = crossref_data['URL']
        elif 'DOI' in crossref_data:
            doc['link'] = f"https://doi.org/{crossref_data['DOI']}"
        
        # Lugar de publicación (journal o container)
        # Puede venir en diferentes formatos
        container = crossref_data.get('container-title', [])
        if container:
            # Tomar el primer título de contenedor (generalmente la revista)
            if isinstance(container, list) and len(container) > 0:
                doc['lugar_publicacion_entrega'] = normalize_text(container[0])
            elif isinstance(container, str):
                doc['lugar_publicacion_entrega'] = normalize_text(container)
        
        # Publicista/Editorial
        publisher = crossref_data.get('publisher')
        if publisher:
            doc['publicista_editorial'] = normalize_text(publisher)
        
        # Volumen
        volume = crossref_data.get('volume')
        if volume:
            doc['volumen_edicion'] = str(volume)
        
        # Número de artículo/capítulo/informe (issue)
        issue = crossref_data.get('issue')
        if issue:
            doc['numero_articulo_capitulo_informe'] = str(issue)
        
        # Páginas
        # Puede venir como string "123-456" o como lista
        page = crossref_data.get('page')
        if page:
            if isinstance(page, str):
                doc['paginas'] = page
            elif isinstance(page, list) and len(page) > 0:
                doc['paginas'] = str(page[0])
        
        # ISBN/ISSN
        isbn = crossref_data.get('ISBN', [])
        issn = crossref_data.get('ISSN', [])
        if isbn:
            # Puede ser lista o string
            if isinstance(isbn, list) and len(isbn) > 0:
                doc['isbn_issn'] = isbn[0] if isinstance(isbn[0], str) else str(isbn[0])
            elif isinstance(isbn, str):
                doc['isbn_issn'] = isbn
        elif issn:
            # Puede ser lista o string
            if isinstance(issn, list) and len(issn) > 0:
                doc['isbn_issn'] = issn[0] if isinstance(issn[0], str) else str(issn[0])
            elif isinstance(issn, str):
                doc['isbn_issn'] = issn
        
        # Idioma (no disponible directamente en CrossRef)
        doc['idioma'] = None
        
        # Tipo documento
        doc_type = crossref_data.get('type')
        if doc_type:
            type_mapping = {
                'journal-article': 'Artículo en revista científica',
                'book-chapter': 'Capítulo de libro',
                'book': 'Libro',
                'report': 'Informe técnico',
                'dissertation': 'Tesis',
                'proceedings-article': 'Artículo en actas',
                'dataset': 'Conjunto de datos'
            }
            doc['tipo_documento'] = type_mapping.get(doc_type, 'Otro')
        else:
            # Inferir tipo por presencia de container-title (revista)
            if container:
                doc['tipo_documento'] = 'Artículo en revista científica'
            else:
                doc['tipo_documento'] = None
        
        # Peer-reviewed (artículos de revista generalmente sí)
        if doc_type == 'journal-article' or (not doc_type and container):
            doc['peer_reviewed'] = 'Sí'
        else:
            doc['peer_reviewed'] = None
        
        # Acceso abierto
        # Verificar en license o en is-referenced-by-count (indicador indirecto)
        license_info = crossref_data.get('license', [])
        if license_info:
            doc['acceso_abierto'] = 'Sí'
        else:
            # Algunos artículos tienen indicador de acceso abierto en otros campos
            doc['acceso_abierto'] = None
        
        # Keywords y Abstract (no siempre disponibles en CrossRef)
        # El abstract puede venir en diferentes formatos en CrossRef
        abstract = None
        if 'abstract' in crossref_data:
            abstract = crossref_data['abstract']
        elif 'abstracts' in crossref_data and crossref_data['abstracts']:
            # A veces viene en una lista
            abstract = crossref_data['abstracts'][0].get('value', '')
        
        if abstract:
            # Si es un string, usarlo directamente; si es dict, extraer el valor
            if isinstance(abstract, dict):
                abstract = abstract.get('value', '') or abstract.get('text', '')
            if isinstance(abstract, str) and len(abstract.strip()) > 0:
                # Limpiar etiquetas XML/HTML (como <jats:p>, <p>, etc.)
                import re
                # Remover etiquetas XML/HTML
                abstract = re.sub(r'<[^>]+>', '', abstract)
                # Limpiar espacios múltiples y normalizar
                abstract = re.sub(r'\s+', ' ', abstract).strip()
                doc['resumen_abstract'] = normalize_text(abstract)
        
        # Keywords - CrossRef no las proporciona directamente, pero algunas APIs las tienen
        # Intentar buscar en diferentes campos
        keywords = None
        if 'subject' in crossref_data and crossref_data['subject']:
            # A veces las keywords vienen en 'subject'
            keywords_list = crossref_data['subject']
            if isinstance(keywords_list, list):
                keywords = ', '.join([k for k in keywords_list if isinstance(k, str)])
        
        if keywords:
            doc['keywords'] = normalize_text(keywords)
        
        return doc

