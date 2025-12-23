"""
Servicio para integrar con GROBID (GeneRation Of Bibliographic Data)
GROBID es una herramienta especializada para extraer información bibliográfica de PDFs científicos.
"""
import requests
import logging
from typing import List, Dict, Optional
from xml.etree import ElementTree as ET
from io import BytesIO
from app.config import settings

logger = logging.getLogger(__name__)


class GrobidService:
    """Servicio wrapper para GROBID API"""
    
    def __init__(self):
        self.grobid_url = settings.grobid_url
        self.use_grobid = settings.use_grobid
        self.timeout = settings.grobid_timeout
    
    def _check_grobid_available(self) -> bool:
        """Verifica si GROBID está disponible"""
        if not self.use_grobid or not self.grobid_url:
            return False
        
        try:
            response = requests.get(
                f"{self.grobid_url}/api/isalive",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"GROBID no disponible: {e}")
            return False
    
    def extract_references_from_pdf(self, pdf_content: bytes) -> Optional[List[Dict]]:
        """
        Extrae referencias usando GROBID
        
        Args:
            pdf_content: Contenido del PDF en bytes
            
        Returns:
            Lista de diccionarios con referencias parseadas, o None si falla
        """
        if not self._check_grobid_available():
            return None
        
        try:
            response = requests.post(
                f"{self.grobid_url}/api/processReferences",
                files={'input': pdf_content},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return self._parse_grobid_response(response.text)
            else:
                logger.warning(f"GROBID retornó código {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"GROBID timeout después de {self.timeout}s")
            return None
        except Exception as e:
            logger.warning(f"Error al llamar a GROBID: {e}")
            return None
    
    def extract_header_from_pdf(self, pdf_content: bytes) -> Optional[Dict]:
        """
        Extrae metadata del documento (título, autores, etc.) usando GROBID
        
        Args:
            pdf_content: Contenido del PDF en bytes
            
        Returns:
            Diccionario con metadata, o None si falla
        """
        if not self._check_grobid_available():
            return None
        
        try:
            response = requests.post(
                f"{self.grobid_url}/api/processHeaderDocument",
                files={'input': pdf_content},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return self._parse_grobid_header_response(response.text)
            else:
                logger.warning(f"GROBID header retornó código {response.status_code}")
                return None
                
        except requests.exceptions.Timeout:
            logger.warning(f"GROBID header timeout después de {self.timeout}s")
            return None
        except Exception as e:
            logger.warning(f"Error al llamar a GROBID header: {e}")
            return None
    
    def _parse_grobid_response(self, xml_response: str) -> List[Dict]:
        """
        Parsea respuesta XML de GROBID a formato interno
        
        Args:
            xml_response: Respuesta XML de GROBID
            
        Returns:
            Lista de diccionarios con referencias parseadas
        """
        references = []
        
        try:
            root = ET.fromstring(xml_response)
            
            # GROBID retorna referencias en <biblStruct> o <bibl>
            for bibl in root.findall('.//{http://www.tei-c.org/ns/1.0}biblStruct'):
                ref_dict = self._parse_bibl_struct(bibl)
                if ref_dict:
                    references.append(ref_dict)
            
            # También buscar en formato <bibl>
            for bibl in root.findall('.//{http://www.tei-c.org/ns/1.0}bibl'):
                ref_dict = self._parse_bibl(bibl)
                if ref_dict:
                    references.append(ref_dict)
                    
        except ET.ParseError as e:
            logger.warning(f"Error parseando XML de GROBID: {e}")
        except Exception as e:
            logger.warning(f"Error procesando respuesta de GROBID: {e}")
        
        return references
    
    def _parse_bibl_struct(self, bibl_elem) -> Optional[Dict]:
        """Parsea un elemento <biblStruct> de GROBID"""
        ref_dict = {}
        
        # Título
        title_elem = bibl_elem.find('.//{http://www.tei-c.org/ns/1.0}title[@level="a"]')
        if title_elem is None:
            title_elem = bibl_elem.find('.//{http://www.tei-c.org/ns/1.0}title')
        if title_elem is not None and title_elem.text:
            ref_dict['title'] = title_elem.text.strip()
        
        # Autores
        authors = []
        for author in bibl_elem.findall('.//{http://www.tei-c.org/ns/1.0}author'):
            persname = author.find('.//{http://www.tei-c.org/ns/1.0}persName')
            if persname is not None:
                surname = persname.find('.//{http://www.tei-c.org/ns/1.0}surname')
                forename = persname.find('.//{http://www.tei-c.org/ns/1.0}forename')
                if surname is not None and surname.text:
                    author_name = surname.text.strip()
                    if forename is not None and forename.text:
                        author_name += f", {forename.text.strip()}"
                    authors.append(author_name)
        
        if authors:
            ref_dict['authors'] = ", ".join(authors)
        
        # Año
        date_elem = bibl_elem.find('.//{http://www.tei-c.org/ns/1.0}date')
        if date_elem is not None:
            year = date_elem.get('when') or date_elem.text
            if year:
                try:
                    ref_dict['year'] = int(year[:4])
                except:
                    pass
        
        # DOI
        idno_elem = bibl_elem.find('.//{http://www.tei-c.org/ns/1.0}idno[@type="DOI"]')
        if idno_elem is not None and idno_elem.text:
            ref_dict['doi'] = idno_elem.text.strip()
        
        # Revista/Journal
        monogr = bibl_elem.find('.//{http://www.tei-c.org/ns/1.0}monogr')
        if monogr is not None:
            journal_title = monogr.find('.//{http://www.tei-c.org/ns/1.0}title[@level="j"]')
            if journal_title is None:
                journal_title = monogr.find('.//{http://www.tei-c.org/ns/1.0}title')
            if journal_title is not None and journal_title.text:
                ref_dict['journal'] = journal_title.text.strip()
            
            # Volumen
            biblscope = monogr.find('.//{http://www.tei-c.org/ns/1.0}biblScope[@unit="volume"]')
            if biblscope is not None and biblscope.text:
                ref_dict['volume'] = biblscope.text.strip()
            
            # Páginas
            pages = monogr.findall('.//{http://www.tei-c.org/ns/1.0}biblScope[@unit="page"]')
            if pages:
                page_nums = [p.text.strip() for p in pages if p.text]
                if page_nums:
                    ref_dict['pages'] = "-".join(page_nums)
        
        return ref_dict if ref_dict else None
    
    def _parse_bibl(self, bibl_elem) -> Optional[Dict]:
        """Parsea un elemento <bibl> de GROBID (formato más simple)"""
        ref_dict = {}
        
        # Extraer texto completo
        text = "".join(bibl_elem.itertext()).strip()
        if text:
            ref_dict['raw_text'] = text
        
        return ref_dict if ref_dict else None
    
    def _parse_grobid_header_response(self, xml_response: str) -> Optional[Dict]:
        """
        Parsea respuesta XML del header de GROBID
        
        Args:
            xml_response: Respuesta XML de GROBID
            
        Returns:
            Diccionario con metadata del documento
        """
        header_dict = {}
        
        try:
            root = ET.fromstring(xml_response)
            
            # Título
            title_elem = root.find('.//{http://www.tei-c.org/ns/1.0}title[@type="main"]')
            if title_elem is None:
                title_elem = root.find('.//{http://www.tei-c.org/ns/1.0}title')
            if title_elem is not None and title_elem.text:
                header_dict['title'] = title_elem.text.strip()
            
            # Autores
            authors = []
            for author in root.findall('.//{http://www.tei-c.org/ns/1.0}author'):
                persname = author.find('.//{http://www.tei-c.org/ns/1.0}persName')
                if persname is not None:
                    surname = persname.find('.//{http://www.tei-c.org/ns/1.0}surname')
                    forename = persname.find('.//{http://www.tei-c.org/ns/1.0}forename')
                    if surname is not None and surname.text:
                        author_name = surname.text.strip()
                        if forename is not None and forename.text:
                            author_name += f", {forename.text.strip()}"
                        authors.append(author_name)
            
            if authors:
                header_dict['authors'] = ", ".join(authors)
            
            # Año
            date_elem = root.find('.//{http://www.tei-c.org/ns/1.0}date')
            if date_elem is not None:
                year = date_elem.get('when') or date_elem.text
                if year:
                    try:
                        header_dict['year'] = int(year[:4])
                    except:
                        pass
            
            # DOI
            idno_elem = root.find('.//{http://www.tei-c.org/ns/1.0}idno[@type="DOI"]')
            if idno_elem is not None and idno_elem.text:
                header_dict['doi'] = idno_elem.text.strip()
            
            # Abstract
            abstract_elem = root.find('.//{http://www.tei-c.org/ns/1.0}abstract')
            if abstract_elem is not None:
                abstract_text = "".join(abstract_elem.itertext()).strip()
                if abstract_text:
                    header_dict['abstract'] = abstract_text
            
        except ET.ParseError as e:
            logger.warning(f"Error parseando XML header de GROBID: {e}")
        except Exception as e:
            logger.warning(f"Error procesando header de GROBID: {e}")
        
        return header_dict if header_dict else None
    
    def _convert_grobid_to_text(self, grobid_refs: List[Dict]) -> List[str]:
        """
        Convierte referencias de GROBID a formato de texto para el parser
        
        Args:
            grobid_refs: Lista de diccionarios de GROBID
            
        Returns:
            Lista de strings con referencias en formato texto
        """
        text_refs = []
        
        for ref in grobid_refs:
            # Si tiene raw_text, usarlo directamente
            if 'raw_text' in ref:
                text_refs.append(ref['raw_text'])
                continue
            
            # Construir referencia desde campos parseados
            parts = []
            
            # Autores
            if 'authors' in ref:
                parts.append(ref['authors'])
            
            # Año
            if 'year' in ref:
                parts.append(f"({ref['year']})")
            
            # Título
            if 'title' in ref:
                parts.append(ref['title'])
            
            # Revista
            if 'journal' in ref:
                parts.append(ref['journal'])
            
            # Volumen
            if 'volume' in ref:
                parts.append(f"Vol. {ref['volume']}")
            
            # Páginas
            if 'pages' in ref:
                parts.append(f"pp. {ref['pages']}")
            
            # DOI
            if 'doi' in ref:
                parts.append(f"DOI: {ref['doi']}")
            
            if parts:
                text_refs.append(". ".join(parts))
        
        return text_refs

