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
            doc['titulo_original'] = normalize_text(titles[0])
        
        # DOI
        if 'DOI' in crossref_data:
            doc['doi'] = crossref_data['DOI']
        
        # Link
        if 'URL' in crossref_data:
            doc['link'] = crossref_data['URL']
        elif 'DOI' in crossref_data:
            doc['link'] = f"https://doi.org/{crossref_data['DOI']}"
        
        # Lugar de publicación (journal o container)
        container = crossref_data.get('container-title', [])
        if container:
            doc['lugar_publicacion_entrega'] = normalize_text(container[0])
        
        # Publicista/Editorial
        publisher = crossref_data.get('publisher')
        if publisher:
            doc['publicista_editorial'] = normalize_text(publisher)
        
        # Volumen
        volume = crossref_data.get('volume')
        if volume:
            doc['volumen_edicion'] = str(volume)
        
        # Número de artículo
        issue = crossref_data.get('issue')
        if issue:
            doc['numero_articulo_capitulo_informe'] = str(issue)
        
        # Páginas
        page = crossref_data.get('page')
        if page:
            doc['paginas'] = page
        
        # ISBN/ISSN
        isbn = crossref_data.get('ISBN', [])
        issn = crossref_data.get('ISSN', [])
        if isbn:
            doc['isbn_issn'] = isbn[0]
        elif issn:
            doc['isbn_issn'] = issn[0]
        
        # Idioma (no disponible directamente en CrossRef, usar "NA" o detectar)
        doc['idioma'] = None  # Se puede inferir del título o contenido
        
        # Tipo documento
        doc_type = crossref_data.get('type')
        if doc_type:
            type_mapping = {
                'journal-article': 'Artículo en revista científica',
                'book-chapter': 'Capítulo de libro',
                'book': 'Libro',
                'report': 'Informe técnico',
                'dissertation': 'Tesis'
            }
            doc['tipo_documento'] = type_mapping.get(doc_type, 'Otro')
        else:
            doc['tipo_documento'] = 'Artículo en revista científica'  # Default
        
        # Peer-reviewed (CrossRef no lo indica directamente, pero artículos de revista generalmente sí)
        if doc_type == 'journal-article':
            doc['peer_reviewed'] = 'Sí'
        else:
            doc['peer_reviewed'] = None
        
        # Acceso abierto
        license_info = crossref_data.get('license', [])
        if license_info:
            doc['acceso_abierto'] = 'Sí'
        else:
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

