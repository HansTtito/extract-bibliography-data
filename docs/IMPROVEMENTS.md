# Mejoras de Extracción: Código vs IA

## Problemas Actuales

1. **Encoding de caracteres especiales**: "Fern#_#x00E1;ndez" en lugar de "Fernández"
2. **DOI incompleto**: "10.1371/journal" en lugar de "10.1371/journal.pone.0212485"
3. **Título truncado**: A veces se corta
4. **Autores incorrectos**: A veces toma parte del título como autor

---

## Opción 1: Mejorar Código (Recomendado Primero) 🔧

### Ventajas:
- ✅ **Gratis** (sin costos de API)
- ✅ **Rápido** (sin latencia de API)
- ✅ **Control total** sobre la lógica
- ✅ **Funciona offline**

### Desventajas:
- ⚠️ Requiere ajustes manuales para cada caso
- ⚠️ Puede no cubrir todos los formatos de PDF

### Mejoras Implementadas:
1. ✅ Corrección de encoding en `normalize_text()`
2. ✅ Mejora de extracción de DOI completo
3. ✅ Mejora de extracción de título (múltiples líneas)
4. ✅ Mejora de extracción de autores

**Prueba primero estas mejoras** reiniciando el servidor.

---

## Opción 2: Usar IA (OpenAI/Anthropic) 🤖

### Ventajas:
- ✅ **Muy preciso** para extracción compleja
- ✅ **Maneja formatos variados** automáticamente
- ✅ **Corrige encoding** automáticamente
- ✅ **Entiende contexto** (sabe qué es título, autor, etc.)

### Desventajas:
- ⚠️ **Costo**: ~$0.01-0.10 por PDF (depende del tamaño)
- ⚠️ **Latencia**: 2-5 segundos por PDF
- ⚠️ **Dependencia externa**: Requiere API key
- ⚠️ **Límites de rate**: Puede tener límites de uso

### Implementación con OpenAI:

```python
# app/services/ai_extractor.py
import openai
from app.config import settings

class AIExtractor:
    def __init__(self):
        openai.api_key = settings.openai_api_key
    
    def extract_with_ai(self, pdf_text: str) -> Dict:
        prompt = f"""
        Extrae información bibliográfica del siguiente texto de un PDF académico.
        Retorna JSON con estos campos:
        - autores: Lista de autores separados por comas
        - titulo_original: Título completo del documento
        - ano: Año de publicación (solo número)
        - doi: DOI completo si está presente
        - lugar_publicacion_entrega: Nombre de la revista o lugar de publicación
        - resumen_abstract: Abstract o resumen si está presente
        
        Texto del PDF:
        {pdf_text[:4000]}  # Primeros 4000 caracteres
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",  # Más barato
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
```

### Costo Estimado:
- **GPT-4o-mini**: ~$0.01 por PDF pequeño, ~$0.05 por PDF grande
- **100 PDFs/mes**: ~$1-5/mes
- **1000 PDFs/mes**: ~$10-50/mes

---

## Opción 3: Híbrido (Recomendado) 🎯

### Estrategia:
1. **Primero intentar código** (rápido y gratis)
2. **Si falla o es de baja calidad**, usar IA como respaldo
3. **Combinar resultados** de ambas fuentes

### Implementación:

```python
def extract_with_fallback(self, pdf_content: bytes) -> Dict:
    # 1. Intentar extracción con código
    code_result = pdf_extractor.extract(pdf_content)
    
    # 2. Validar calidad
    quality_score = self._assess_quality(code_result)
    
    # 3. Si calidad es baja, usar IA
    if quality_score < 0.7:
        ai_result = ai_extractor.extract_with_ai(pdf_text)
        # Combinar: priorizar IA para campos críticos
        return self._merge_results(code_result, ai_result)
    
    return code_result

def _assess_quality(self, result: Dict) -> float:
    """Evalúa calidad de extracción (0-1)"""
    score = 0.0
    
    # Título presente y razonable
    if result.get('titulo_original') and len(result['titulo_original']) > 20:
        score += 0.3
    
    # Autores presentes
    if result.get('autores') and len(result['autores']) > 10:
        score += 0.2
    
    # Año presente
    if result.get('ano'):
        score += 0.2
    
    # DOI presente y completo
    if result.get('doi') and '.' in result['doi'].split('/')[1]:
        score += 0.3
    
    return score
```

### Ventajas:
- ✅ **Costo optimizado**: Solo usa IA cuando es necesario
- ✅ **Rápido**: Código para casos simples, IA para complejos
- ✅ **Mejor precisión**: Combina lo mejor de ambos

---

## Recomendación

### Corto Plazo (Ahora):
1. ✅ **Probar las mejoras de código** que acabo de hacer
2. ✅ Reiniciar servidor y probar de nuevo
3. ✅ Si sigue fallando, considerar IA

### Mediano Plazo (Si código no es suficiente):
1. **Implementar híbrido**: Código primero, IA como respaldo
2. **Usar GPT-4o-mini** (más barato que GPT-4)
3. **Cachear resultados** para evitar reprocesar

### Largo Plazo (Si escala mucho):
1. **Entrenar modelo propio** con tus PDFs específicos
2. **Fine-tuning** de modelo open source
3. **Pipeline completo**: OCR + IA + Validación

---

## Comparación de Costos

| Enfoque | Precisión | Velocidad | Costo/Mes (100 PDFs) | Costo/Mes (1000 PDFs) |
|---------|-----------|-----------|----------------------|------------------------|
| **Solo Código** | 70-80% | ⚡⚡⚡ Rápido | $0 | $0 |
| **Solo IA** | 95%+ | ⚡⚡ Medio | $1-5 | $10-50 |
| **Híbrido** | 90%+ | ⚡⚡⚡ Rápido | $0.50-2 | $5-20 |

---

## Próximos Pasos

1. **Probar mejoras de código** (reiniciar servidor)
2. **Si sigue fallando**, puedo implementar:
   - Extracción con IA (OpenAI)
   - Sistema híbrido (código + IA)
   - Validación de calidad automática

¿Quieres que implemente la opción de IA ahora, o prefieres probar primero las mejoras de código?

