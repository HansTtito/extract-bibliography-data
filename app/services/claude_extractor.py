"""
Servicio para extraer información bibliográfica usando Claude vía AWS Bedrock
Ideal para informes, tesis, libros y documentos no estándar
"""
import boto3
import logging
import json
import re
import os
import pdfplumber
from typing import Dict, Optional, List
from io import BytesIO
from app.config import settings
from app.utils.text_processing import normalize_text

logger = logging.getLogger(__name__)


class ClaudeExtractor:
    """Servicio wrapper para Claude usando AWS Bedrock"""
    
    def __init__(self):
        # Inicializar con valores por defecto seguros
        self.use_claude = False
        self.model_id = settings.claude_model
        self.max_tokens = settings.claude_max_tokens
        self.bedrock_client = None
        self.region = None
        
        # Solo intentar inicializar si está habilitado
        if not settings.use_claude:
            logger.debug("Claude deshabilitado en configuración")
            return
        
        try:
            # Detectar región automáticamente (Lambda proporciona AWS_REGION automáticamente)
            try:
                import boto3
                session = boto3.Session()
                self.region = session.region_name or os.getenv("AWS_REGION") or settings.aws_region
            except:
                self.region = os.getenv("AWS_REGION") or settings.aws_region
            
            # Intentar inicializar cliente de Bedrock
            try:
                from botocore.config import Config
                # Configurar timeout más corto para evitar que API Gateway timeout (29 segundos)
                config = Config(
                    read_timeout=20,  # 20 segundos para leer respuesta
                    connect_timeout=5,  # 5 segundos para conectar
                    retries={'max_attempts': 1}  # Sin reintentos para ser más rápido
                )
                self.bedrock_client = boto3.client(
                    'bedrock-runtime',
                    region_name=self.region,
                    config=config
                )
                self.use_claude = True
                logger.info(f"Claude extractor inicializado con Bedrock (model: {self.model_id}, region: {self.region})")
            except Exception as e:
                logger.warning(f"No se pudo inicializar Bedrock (continuando sin Claude): {e}")
                self.use_claude = False
                self.bedrock_client = None
                
        except Exception as e:
            # Si hay cualquier error, continuar sin Claude (no debe romper la app)
            logger.warning(f"Error inicializando ClaudeExtractor (continuando sin Claude): {e}")
            self.use_claude = False
            self.bedrock_client = None
    
    def extract_from_first_pages(
        self, 
        pdf_content: bytes, 
        num_pages: int = 5,
        doc_type_hint: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        Extrae información bibliográfica de las primeras N páginas usando Claude
        
        Args:
            pdf_content: Contenido del PDF en bytes
            num_pages: Número de páginas a analizar (default: 5)
            doc_type_hint: Tipo de documento detectado previamente (opcional)
        
        Returns:
            Diccionario con información extraída
        """
        if not self.use_claude:
            logger.warning("Claude no está disponible")
            return {}
        
        try:
            # Extraer texto de las primeras páginas
            first_pages_text = self._extract_text_from_pages(pdf_content, num_pages)
            
            if not first_pages_text or len(first_pages_text) < 100:
                logger.warning("Texto insuficiente en primeras páginas")
                return {}
            
            # Limitar tamaño para Claude (evitar costos altos)
            # Claude tiene límite de contexto, usar ~10k caracteres
            if len(first_pages_text) > 10000:
                first_pages_text = first_pages_text[:10000] + "\n[... texto truncado ...]"
            
            # Crear prompt estructurado
            prompt = self._create_extraction_prompt(first_pages_text, doc_type_hint)
            
            # Llamar a Claude
            response = self._call_claude(prompt)
            
            # Parsear respuesta
            extracted_data = self._parse_claude_response(response)
            
            logger.info(f"Claude extrajo {len([k for k, v in extracted_data.items() if v])} campos")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extrayendo con Claude: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def validate_and_enrich(
        self,
        extracted_data: Dict[str, Optional[str]],
        pdf_content: bytes,
        num_pages: int = 3
    ) -> Dict[str, Optional[str]]:
        """
        Valida y enriquece datos extraídos usando Claude
        Útil para verificar/mejorar resultados de GROBID o regex
        
        Args:
            extracted_data: Datos ya extraídos (de GROBID/regex)
            pdf_content: Contenido del PDF
            num_pages: Páginas a analizar para validación
        
        Returns:
            Diccionario enriquecido/validado
        """
        if not self.use_claude:
            return extracted_data
        
        try:
            # Extraer texto de primeras páginas
            first_pages_text = self._extract_text_from_pages(pdf_content, num_pages)
            if len(first_pages_text) > 10000:
                first_pages_text = first_pages_text[:10000]
            
            # Crear prompt de validación
            prompt = self._create_validation_prompt(extracted_data, first_pages_text)
            
            # Llamar a Claude
            response = self._call_claude(prompt)
            
            # Parsear y combinar resultados
            validated_data = self._parse_claude_response(response)
            
            # Combinar: priorizar datos validados/enriquecidos de Claude
            enriched = extracted_data.copy()
            for key, value in validated_data.items():
                if value:  # Solo actualizar si Claude encontró algo
                    enriched[key] = value
            
            return enriched
            
        except Exception as e:
            logger.error(f"Error validando con Claude: {e}")
            return extracted_data
    
    def _extract_text_from_pages(self, pdf_content: bytes, num_pages: int) -> str:
        """Extrae texto de las primeras N páginas"""
        text_parts = []
        
        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                pages_to_analyze = pdf.pages[:num_pages]
                
                for i, page in enumerate(pages_to_analyze, 1):
                    page_text = page.extract_text() or ""
                    if page_text:
                        text_parts.append(f"--- PÁGINA {i} ---\n{page_text}\n")
        
        except Exception as e:
            logger.error(f"Error extrayendo texto: {e}")
        
        return "\n".join(text_parts)
    
    def _create_extraction_prompt(self, text: str, doc_type_hint: Optional[str] = None) -> str:
        """Crea prompt estructurado para extracción"""
        
        doc_type_context = ""
        if doc_type_hint:
            doc_type_context = f"\nTipo de documento detectado: {doc_type_hint}"
        
        prompt = f"""Eres un experto en extracción de información bibliográfica. Analiza el siguiente texto de las primeras páginas de un documento y extrae la información bibliográfica solicitada.

{doc_type_context}

TEXTO DEL DOCUMENTO:
{text}

INSTRUCCIONES CRÍTICAS:
1. **SOLO extrae información que esté EXPLÍCITAMENTE escrita en el texto del documento**
2. **NO inventes, infieras, asumas o completes información que no esté en el texto**
3. **Si un campo no está en el texto, DEBES usar null (no inventar valores)**
4. **NO uses información de documentos similares o conocimiento general**
5. Para autores, extrae TODOS los autores que encuentres en el texto. Formatos comunes:
   - "Apellido1, Inicial1., Apellido2, Inicial2."
   - "Apellido1 Inicial1, Apellido2 Inicial2"
   - "Apellido1, Inicial1; Apellido2, Inicial2"
   - Busca en la primera página, después del título, antes del abstract
   - Busca en secciones como: "Autores", "Authors", "Equipo de Trabajo", "Investigador Responsable", "Responsable", "Coordinador", "Director"
   - Si hay múltiples líneas de autores, únelas con comas
   - Si hay "Equipo de Trabajo" o "Investigador Responsable", extrae los nombres que aparecen después
   - Formato final: "Apellido1, Inicial1., Apellido2, Inicial2., ..."
6. Para tipo_documento, usa uno de estos valores exactos SOLO si está claro en el texto:
   - "Artículo en revista científica"
   - "Capítulo de libro"
   - "Libro"
   - "Tesis"
   - "Informe técnico"
   - "Artículo en actas"
   - "Preprint"
   - "Conjunto de datos"
   - "Otro"

7. Para extraer información de artículos en revistas, busca en el HEADER de la primera página:
   - Formato común: "Journal, Location, Volume: Pages, Year"
   - Ejemplo: "Invest. Mar., Valparaíso, 28: 39-52, 2000"
   - El AÑO suele estar al final: ", 2000"
   - El VOLUMEN suele estar antes de ":": "28:"
   - Las PÁGINAS suelen estar entre ":" y ",": "39-52"
   - La REVISTA suele estar al inicio: "Invest. Mar."
   - La UBICACIÓN suele estar después de la revista: "Valparaíso"
   - Si encuentras este formato, extrae TODOS estos campos
   - El año del header es MÁS CONFIBLE que años mencionados en el abstract o texto

EJEMPLOS ESPECÍFICOS DE HEADERS:
- "Invest. Mar., Valparaíso, 28: 39-52, 2000" → 
  lugar_publicacion_entrega: "Invest. Mar., Valparaíso"
  volumen_edicion: "28"
  paginas: "39-52"
  ano: 2000
  tipo_documento: "Artículo en revista científica"
- "J. Fish Biol., 45: 123-145, 1994" →
  lugar_publicacion_entrega: "J. Fish Biol."
  volumen_edicion: "45"
  paginas: "123-145"
  ano: 1994
  tipo_documento: "Artículo en revista científica"

EJEMPLOS:
- Si NO ves un ISBN/ISSN en el texto → "isbn_issn": null
- Si NO ves una revista/editorial en el texto → "lugar_publicacion_entrega": null
- Si NO ves un DOI en el texto → "doi": null
- Si NO ves páginas en el texto → "paginas": null

Devuelve SOLO un objeto JSON válido con esta estructura exacta:
{{
    "titulo_original": "título completo que esté en el texto o null",
    "autores": "TODOS los autores encontrados en formato 'Apellido1, Inicial1., Apellido2, Inicial2.' (buscar en primera página, después del título, antes del abstract, o en sección 'Autores'). Si no encuentras autores explícitos, usa null",
    "ano": año numérico que esté en el texto o null,
    "tipo_documento": "tipo exacto de la lista si está claro en el texto o null",
    "lugar_publicacion_entrega": "revista, institución, editorial que esté en el texto o null",
    "publicista_editorial": "editorial o publicista que esté en el texto o null",
    "volumen_edicion": "volumen o edición que esté en el texto o null",
    "isbn_issn": "ISBN o ISSN que esté EXPLÍCITAMENTE en el texto o null",
    "numero_articulo_capitulo_informe": "número que esté en el texto o null",
    "paginas": "rango de páginas que esté en el texto o null",
    "doi": "DOI que esté EXPLÍCITAMENTE en el texto o null",
    "link": "URL que esté en el texto o null",
    "resumen_abstract": "resumen o abstract que esté en el texto. IMPORTANTE: Máximo 500 palabras (aproximadamente 3000 caracteres). Si el resumen es más largo, extrae solo las primeras 500 palabras y termina con '...'. CRÍTICO: NO incluyas texto de footers, metadata de páginas web, URLs (como 'www.redalyc.org'), o información de copyright (como 'Proyecto académico sin fines de lucro'). Si encuentras texto que parece ser de una página web o footer en lugar del abstract real, usa null. Si no encuentras un resumen explícito, usa null",
    "keywords": "palabras clave que estén en el texto separadas por comas o null",
    "idioma": "idioma del documento (español, inglés, etc.) si está en el texto o null",
    "peer_reviewed": "\"Sí\" o \"No\" SOLO si está explícitamente mencionado en el texto, o null",
    "acceso_abierto": "\"Sí\" o \"No\" SOLO si está explícitamente mencionado en el texto, o null",
    "full_text_asociado_base_datos": "\"Sí\" o \"No\" SOLO si está explícitamente mencionado en el texto, o null",
    "tipo_documento_otro": "especificar solo si tipo_documento es 'Otro' y hay más detalles en el texto, o null"
}}

IMPORTANTE: 
- Devuelve SOLO el JSON, sin texto adicional antes o después
- Si no estás 100% seguro de que algo está en el texto, usa null
- NO inventes datos bajo ninguna circunstancia"""

        return prompt
    
    def _create_validation_prompt(
        self, 
        extracted_data: Dict[str, Optional[str]], 
        text: str
    ) -> str:
        """Crea prompt para validar/enriquecer datos existentes"""
        
        prompt = f"""Eres un experto en validación de información bibliográfica. Revisa los datos extraídos y valida/corrige/enriquece usando el texto del documento.

DATOS ACTUALES (pueden tener errores o estar incompletos):
{json.dumps(extracted_data, indent=2, ensure_ascii=False)}

TEXTO DEL DOCUMENTO:
{text[:8000]}

INSTRUCCIONES:
1. Valida cada campo comparándolo con el texto
2. Corrige errores si los encuentras
3. Completa campos faltantes si están en el texto
4. Mantén el formato de autores: "Apellido, Inicial."

Devuelve SOLO un objeto JSON con los campos CORREGIDOS/ENRIQUECIDOS. Si un campo está correcto, mantenlo. Si no está en el texto, usa null.

Estructura JSON (solo incluye campos que corregiste o enriqueciste):
{{
    "titulo_original": "...",
    "autores": "...",
    "ano": ...,
    "tipo_documento": "...",
    ...
}}

IMPORTANTE: Devuelve SOLO el JSON, sin texto adicional."""

        return prompt
    
    def _call_claude(self, prompt: str) -> str:
        """Llama a Claude usando AWS Bedrock"""
        try:
            # Formato de request para Bedrock (Anthropic Claude)
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.max_tokens,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
            
            # Llamar a Bedrock (timeout ya configurado en __init__)
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=body
            )
            
            # Parsear respuesta
            response_body = json.loads(response['body'].read())
            response_text = response_body['content'][0]['text']
            
            return response_text
            
        except Exception as e:
            error_code = getattr(e, 'response', {}).get('Error', {}).get('Code', '')
            if error_code == 'ValidationException':
                logger.error(f"Error de validación en Bedrock: {e}")
            elif error_code == 'AccessDeniedException':
                logger.error(f"Acceso denegado a Bedrock. Verifica permisos IAM: {e}")
            else:
                logger.error(f"Error llamando a Bedrock: {e}")
            raise
    
    def _parse_claude_response(self, response: str) -> Dict[str, Optional[str]]:
        """Parsea la respuesta de Claude (extrae JSON)"""
        try:
            # Intentar extraer JSON de la respuesta
            # Claude a veces agrega texto antes/después del JSON
            
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                # Normalizar valores
                normalized = {}
                MAX_ABSTRACT_LENGTH = 5000  # Máximo 5000 caracteres (~800 palabras)
                
                for key, value in data.items():
                    if value is None or value == "null" or value == "":
                        normalized[key] = None
                    elif isinstance(value, str):
                        # Validar y truncar resumen si es muy largo
                        if key == 'resumen_abstract' and len(value) > MAX_ABSTRACT_LENGTH:
                            # Truncar en palabra completa
                            truncated = value[:MAX_ABSTRACT_LENGTH]
                            last_space = truncated.rfind(' ')
                            if last_space > MAX_ABSTRACT_LENGTH * 0.9:
                                truncated = truncated[:last_space]
                            value = truncated + "... [truncado]"
                            logger.warning(f"Resumen truncado de {len(data[key])} a {len(value)} caracteres")
                        
                        normalized[key] = normalize_text(value)
                    else:
                        normalized[key] = value
                
                return normalized
            else:
                logger.warning("No se encontró JSON en la respuesta de Claude")
                return {}
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON de Claude: {e}")
            logger.debug(f"Respuesta recibida: {response[:500]}")
            return {}
        except Exception as e:
            logger.error(f"Error parseando respuesta de Claude: {e}")
            return {}
