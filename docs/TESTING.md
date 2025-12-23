# 🧪 Guía de Pruebas Incrementales

Esta guía te ayuda a probar la extracción de referencias paso a paso antes de desplegar.

## 📋 Scripts Disponibles

### 1. `test_references_extraction_simple.py` - Prueba Simple
**Uso rápido para verificar que funciona**

```bash
python test_references_extraction_simple.py <ruta_al_pdf>
```

**Ejemplo:**
```bash
python test_references_extraction_simple.py "C:\Users\hkev2\Downloads\mi_pdf.pdf"
```

**Qué hace:**
- ✅ Lee el PDF
- ✅ Extrae referencias
- ✅ Muestra las primeras 5 referencias
- ✅ Prueba el parsing de las primeras 3
- ✅ Muestra un resumen
- ✅ Opción de guardar resultados en archivo

---

### 2. `test_references_detailed.py` - Prueba Detallada
**Muestra paso a paso qué está haciendo el extractor**

```bash
python test_references_detailed.py <ruta_al_pdf>
```

**Ejemplo:**
```bash
python test_references_detailed.py "C:\Users\hkev2\Downloads\mi_pdf.pdf"
```

**Qué hace:**
- ✅ Muestra cada paso del proceso
- ✅ Indica dónde encuentra la sección de referencias
- ✅ Muestra estadísticas de cada página
- ✅ Verifica patrones en cada referencia
- ✅ Muestra resultados de parsing detallados

---

## 🚀 Cómo Probar

### Paso 1: Prepara tu PDF
Asegúrate de tener un PDF con referencias bibliográficas.

### Paso 2: Ejecuta la prueba simple
```bash
python test_references_extraction_simple.py tu_archivo.pdf
```

### Paso 3: Si hay problemas, usa la versión detallada
```bash
python test_references_detailed.py tu_archivo.pdf
```

### Paso 4: Revisa los resultados
- ✅ Si funciona: Las referencias se extraen correctamente
- ⚠️ Si hay problemas: Revisa los mensajes de error y ajusta según sea necesario

---

## 🔍 Qué Buscar en los Resultados

### ✅ Resultados Esperados (Éxito)
```
✅ PDF leído: 123,456 bytes
✅ Extracción completada
📊 Total de referencias encontradas: 45

Referencia #1:
  Longitud: 234 caracteres
  Texto: García, J., Smith, M. (2020). Title of the paper...
  
✅ Parseado exitosamente:
  - Autores: García, J., Smith, M.
  - Año: 2020
  - Título: Title of the paper...
```

### ⚠️ Posibles Problemas

**1. No se encuentran referencias**
```
⚠️ No se encontraron referencias
```
**Solución:** 
- Verifica que el PDF tenga una sección "REFERENCES"
- Prueba con otro PDF para comparar

**2. Referencias extraídas pero no parseadas**
```
✅ Referencias extraídas: 10
⚠️ No se pudo parsear (campos vacíos)
```
**Solución:**
- El formato de las referencias puede ser diferente
- Revisa el formato de las referencias en el PDF
- Puede necesitar ajustar los patrones en `patterns.py`

**3. Error al leer PDF**
```
❌ Error al leer PDF: ...
```
**Solución:**
- Verifica que el archivo existe
- Verifica que el archivo no esté corrupto
- Verifica permisos de lectura

---

## 📝 Notas

- Estos scripts **NO modifican** el código principal
- Son solo para **pruebas locales**
- Los resultados se pueden guardar en archivo de texto
- Si encuentras problemas, revisa los logs detallados

---

## 🐛 Debugging

Si algo no funciona:

1. **Ejecuta la versión detallada** para ver exactamente qué está pasando
2. **Revisa los mensajes** en cada paso
3. **Compara con un PDF que funcione** para identificar diferencias
4. **Revisa los patrones** en `app/utils/patterns.py` si las referencias no se detectan

---

## 💡 Próximos Pasos

Una vez que las pruebas funcionen:

1. ✅ Verifica que todas las referencias se extraen correctamente
2. ✅ Verifica que el parsing funciona para la mayoría de referencias
3. ✅ Si hay problemas, ajusta los patrones en `patterns.py`
4. ✅ Prueba con múltiples PDFs para asegurar robustez

