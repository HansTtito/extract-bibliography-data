# Configuración de GROBID

Esta guía explica cómo configurar y usar GROBID para mejorar la extracción de información bibliográfica.

## ¿Qué es GROBID?

GROBID (GeneRation Of Bibliographic Data) es una herramienta especializada para extraer información estructurada de documentos científicos en PDF. Ofrece mayor precisión que métodos basados en regex, especialmente para:

- Extracción de referencias bibliográficas
- Metadata de documentos (título, autores, año, DOI)
- Parsing de estructuras complejas

## Arquitectura

```
┌─────────────────┐
│   FastAPI App   │
│   (Lambda)      │
└────────┬────────┘
         │
         │ HTTP Request
         ▼
┌─────────────────┐
│  GROBID Service │
│  (ECS/EC2)      │
│  Port 8070      │
└─────────────────┘
```

## Configuración

### Variables de Entorno

Agregar al `.env` o configuración de Lambda:

```bash
# Activar GROBID
USE_GROBID=true

# URL de GROBID (según despliegue)
GROBID_URL=http://localhost:8070              # Desarrollo local
GROBID_URL=http://ec2-ip:8070                # EC2
GROBID_URL=http://grobid-alb-dns:8070        # ECS Fargate

# Timeout (segundos)
GROBID_TIMEOUT=30

# Límites de tamaño
MAX_PDF_SIZE_MB=10
MAX_BATCH_COUNT=10
MAX_BATCH_TOTAL_MB=50
```

### Desarrollo Local

1. **Iniciar GROBID con Docker:**

```bash
cd infrastructure/grobid
docker-compose -f docker-compose.grobid.yml up -d
```

2. **Verificar que funciona:**

```bash
curl http://localhost:8070/api/isalive
```

3. **Configurar `.env`:**

```bash
USE_GROBID=true
GROBID_URL=http://localhost:8070
```

4. **Iniciar aplicación:**

```bash
python run.py
```

## Estrategia de Extracción

La aplicación usa una estrategia **GROBID-first con fallback a regex**:

1. **Si GROBID está disponible:**
   - Intenta extraer con GROBID
   - Valida calidad de extracción (70% de referencias con título y año)
   - Si calidad es buena → usa resultados de GROBID
   - Si calidad es baja → fallback a regex

2. **Si GROBID no está disponible:**
   - Usa método regex directamente

### Para Referencias de PDF

```python
# En references_pdf_extractor.py
def extract_references(self, pdf_content: bytes) -> List[str]:
    # 1. Intentar GROBID
    if self.grobid_service.use_grobid:
        grobid_refs = self.grobid_service.extract_references_from_pdf(pdf_content)
        if grobid_refs and self._validate_grobid_quality(grobid_refs):
            return grobid_refs
    
    # 2. Fallback a regex
    return self._extract_with_regex(pdf_content)
```

### Para Metadata de PDF

```python
# En pdf_extractor.py
def extract(self, pdf_content: bytes) -> Dict:
    # 1. Intentar GROBID header
    if self.grobid_service.use_grobid:
        grobid_header = self.grobid_service.extract_header_from_pdf(pdf_content)
        if grobid_header:
            # Usar datos de GROBID como base
            doc.update(grobid_header)
    
    # 2. Complementar con regex para campos faltantes
    # ...
```

## Despliegue en Producción

### Opción 1: EC2 Spot (Recomendado para empezar)

**Costo:** ~$2-3/mes

```bash
# Usar script de despliegue
./infrastructure/scripts/deploy_grobid.sh prod ec2
```

O manualmente:
1. Crear instancia EC2 t3.small spot
2. Ejecutar `infrastructure/grobid/ec2-setup.sh`
3. Configurar Security Group (puerto 8070)
4. Obtener IP pública y configurar en Lambda

### Opción 2: ECS Fargate (Más estable)

**Costo:** ~$15-25/mes

```bash
cd infrastructure/terraform
terraform init
terraform apply -var="environment=prod" -var="grobid_deployment=fargate"
```

Ver [infrastructure/grobid/README.md](../infrastructure/grobid/README.md) para más detalles.

## Monitoreo

### Health Check

```bash
curl http://GROBID_URL/api/isalive
```

### Logs

**ECS Fargate:**
```bash
aws logs tail /ecs/grobid-service-prod --follow
```

**EC2:**
```bash
docker logs grobid
```

### Métricas CloudWatch

- `GrobidSuccessRate`: % de éxito de GROBID
- `GrobidResponseTime`: Tiempo de respuesta
- `GrobidFallbackRate`: % de veces que se usa fallback

## Troubleshooting

### GROBID no responde

1. Verificar que el servicio esté corriendo
2. Verificar conectividad de red (Security Groups, VPC)
3. Verificar logs para errores

### Timeout en requests

- Aumentar `GROBID_TIMEOUT` (default: 30s)
- Verificar que GROBID tenga suficiente memoria (mínimo 2GB)
- Verificar latencia de red

### Calidad baja de extracción

- GROBID funciona mejor con PDFs nativos (no escaneados)
- Para PDFs escaneados, considerar AWS Textract
- Verificar que el PDF tenga estructura de paper científico

### Fallback frecuente a regex

- Verificar logs de GROBID para errores
- Verificar que GROBID tenga suficiente memoria
- Considerar aumentar recursos (CPU/memoria)

## Costos

| Opción | Costo Mensual | Uso Recomendado |
|--------|---------------|-----------------|
| **Local (Docker)** | $0 | Desarrollo |
| **EC2 Spot** | $2-3 | Producción pequeña |
| **ECS Fargate** | $15-25 | Producción estable |

## Referencias

- [GROBID Documentation](https://grobid.readthedocs.io/)
- [GROBID GitHub](https://github.com/kermitt2/grobid)
- [Infrastructure README](../infrastructure/grobid/README.md)

