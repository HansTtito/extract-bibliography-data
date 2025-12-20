# Plataforma de Extracción Bibliográfica

Plataforma backend con FastAPI para extraer información bibliográfica de PDFs y referencias bibliográficas, con integración a CrossRef API y capacidad de exportación en múltiples formatos.

## Características

- **Extracción desde PDFs**: Sube archivos PDF y extrae automáticamente información bibliográfica (autores, título, año, DOI, etc.)
- **Extracción desde Referencias**: Ingresa referencias bibliográficas en texto libre y extrae información estructurada
- **Extracción desde PDF de Referencias**: Sube un PDF con múltiples referencias y extrae todas automáticamente
- **Enriquecimiento con CrossRef**: Búsqueda automática en CrossRef API para completar información faltante
- **Base de Datos PostgreSQL**: Almacenamiento persistente de todos los documentos extraídos
- **Exportación**: Descarga de datos en formato CSV, Excel (.xlsx) y JSON
- **Frontend Simple**: Interfaz web para interactuar con la plataforma

## 🚀 Despliegue en la Nube

Para desplegar esta aplicación en la nube, consulta la [Guía de Despliegue](DEPLOY.md) que incluye instrucciones para:

- **Railway** (Recomendado - Más fácil)
- **Render**
- **AWS** (Elastic Beanstalk, ECS, EC2)
- **Google Cloud Platform**
- **Heroku**

La aplicación incluye un `Dockerfile` listo para usar en cualquier plataforma que soporte Docker.

### 🤔 ¿EC2 o Serverless?

Para un análisis detallado de arquitecturas y recomendaciones según tu caso de uso, consulta [ARCHITECTURE.md](ARCHITECTURE.md). Incluye comparación de costos, ventajas/desventajas, y recomendaciones específicas para aplicaciones que procesan PDFs.

**💡 Si solo usas la app unas cuantas veces al mes**: Serverless (Lambda) es la mejor opción - ahorra ~$32/mes vs EC2. Ver [DEPLOY_LAMBDA.md](DEPLOY_LAMBDA.md) para guía completa de despliegue en Lambda.

## Requisitos

- Python 3.8+
- PostgreSQL 12+
- pip (gestor de paquetes de Python)

## Instalación

1. **Clonar o descargar el proyecto**

2. **Crear entorno virtual** (recomendado):
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**:
```bash
pip install -r requirements.txt
```

4. **Configurar base de datos PostgreSQL**:

   Opción A: PostgreSQL local
   - Crear base de datos: `CREATE DATABASE bibliografia_db;`
   - Configurar usuario y contraseña

   Opción B: Usar Docker Compose (ver sección Docker)

> 💡 **Colaboración**: Si quieres que otras personas usen la misma base de datos, consulta [COLABORACION.md](COLABORACION.md) para diferentes escenarios.

5. **Configurar variables de entorno**:
   - Copiar `.env.example` a `.env`
   - Editar `.env` con tus credenciales de base de datos:
   ```
   DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/bibliografia_db
   CROSSREF_EMAIL=tu-email@example.com
   ```

## Configuración de Base de Datos

### Opción 1: PostgreSQL Local

1. Instalar PostgreSQL en tu sistema
2. Crear base de datos:
```sql
CREATE DATABASE bibliografia_db;
```
3. Configurar la URL en `.env`:
```
DATABASE_URL=postgresql://usuario:contraseña@localhost:5432/bibliografia_db
```

### Opción 2: Docker Compose

Crear un archivo `docker-compose.yml`:
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: bibliografia_user
      POSTGRES_PASSWORD: bibliografia_pass
      POSTGRES_DB: bibliografia_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

Ejecutar:
```bash
docker-compose up -d
```

## Uso

1. **Inicializar base de datos** (las tablas se crean automáticamente al iniciar):
```bash
python -m app.main
```

2. **Iniciar servidor**:
```bash
uvicorn app.main:app --reload
```

3. **Acceder a la aplicación**:
   - Frontend: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - API Redoc: http://localhost:8000/redoc

## Endpoints de la API

### Subir PDF
```
POST /api/upload-pdf
Content-Type: multipart/form-data
Body: file (PDF)
```

### Subir Referencia Bibliográfica
```
POST /api/upload-reference
Content-Type: application/json
Body: { "reference_text": "..." }
```

### Obtener Documentos
```
GET /api/documents?skip=0&limit=100
```

### Descargar Datos
```
GET /api/download/csv
GET /api/download/excel
GET /api/download/json
```

## Estructura del Proyecto

```
extract-bibliografia/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Punto de entrada FastAPI
│   ├── config.py               # Configuración
│   ├── database.py             # Configuración DB
│   ├── models.py               # Modelos SQLAlchemy
│   ├── schemas.py              # Schemas Pydantic
│   ├── routers/                # Endpoints
│   │   ├── pdf_upload.py
│   │   ├── reference_upload.py
│   │   ├── documents.py
│   │   └── download.py
│   ├── services/               # Lógica de negocio
│   │   ├── pdf_extractor.py
│   │   ├── reference_parser.py
│   │   ├── crossref_service.py
│   │   └── export_service.py
│   └── utils/                  # Utilidades
│       └── text_processing.py
├── frontend/
│   ├── index.html
│   └── static/
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── main.js
├── requirements.txt
├── .env.example
└── README.md
```

## Campos Extraídos

La plataforma extrae las siguientes 20 columnas según la especificación:

1. N° doc
2. Autor(es)
3. Año
4. Título original
5. Keywords
6. Resumen/Abstract
7. Lugar de publicación/entrega
8. Publicista/editorial
9. Volumen/edición
10. ISBN/ISSN
11. N° artículo/capítulo/informe
12. Páginas
13. DOI
14. Link
15. Idioma
16. Tipo documento
17. Tipo documento (Otro)
18. Peer-reviewed
19. Acceso abierto
20. Full-text asociado a base de datos

## Notas

- **CrossRef API**: Se recomienda configurar un email válido en `CROSSREF_EMAIL` para mejor rate limiting
- **PDF Extraction**: La extracción de PDFs depende de la calidad y estructura del documento
- **Reference Parsing**: El parser usa heurísticas y puede requerir ajustes según el formato de referencias

## Desarrollo

Para desarrollo con recarga automática:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Compartir Temporalmente (Sin Configuración) 🌐

Para compartir tu aplicación temporalmente sin que otros tengan que configurar nada, usa **ngrok**:

```bash
# 1. Iniciar aplicación
python run.py

# 2. En otra terminal, crear túnel público
ngrok http 8001

# 3. Compartir la URL que ngrok te da (ej: https://abc123.ngrok-free.app)
```

Los demás solo necesitan abrir esa URL en su navegador. 

📖 **Guías:**
- [Inicio Rápido](QUICK_START_NGROK.md) - Configuración en 5 minutos
- [Guía Completa](SHARE_TEMPORAL.md) - Más opciones y detalles

## Scripts de Prueba

Puedes probar los extractores directamente sin levantar el servidor:

### Probar Extracción de PDF Individual
```bash
# Extraer información de un PDF
python test_pdf_extraction.py documento.pdf

# Con búsqueda en CrossRef (si hay DOI)
python test_pdf_extraction.py documento.pdf --with-crossref
```

### Probar Extracción de Referencias de un PDF
```bash
# Extraer todas las referencias de un PDF
python test_references_extraction.py referencias.pdf

# También parsear cada referencia
python test_references_extraction.py referencias.pdf --parse

# Guardar resultados en JSON
python test_references_extraction.py referencias.pdf --parse --save

# Limitar a las primeras 5 referencias
python test_references_extraction.py referencias.pdf --limit 5
```

### Probar Parser de Referencias (Texto)
```bash
# Parsear una referencia en texto
python test_reference_parser.py "Smith, J., 2020. Title. Journal, 10, 123-145."

# Con búsqueda en CrossRef
python test_reference_parser.py "Smith, J., 2020. Title. Journal, 10, 123-145." --with-crossref
```

## Limpiar Base de Datos

Para limpiar la base de datos, usa el script `clear_database.py`:

```bash
# Eliminar todos los registros (mantiene tablas)
python clear_database.py clear

# Eliminar y recrear todas las tablas
python clear_database.py recreate

# Solo resetear contador de numero_doc
python clear_database.py reset

# Ver estadísticas
python clear_database.py stats

# Eliminar registros Y resetear contador
python clear_database.py all
```

⚠️ **Advertencia**: Estas operaciones eliminan datos permanentemente. Asegúrate de tener backups si es necesario.

## Licencia

Este proyecto es de código abierto.

