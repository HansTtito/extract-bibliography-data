# Despliegue de GROBID

GROBID (GeneRation Of Bibliographic Data) es una herramienta especializada para extraer información bibliográfica de PDFs científicos.

## Opciones de Despliegue

### 1. Desarrollo Local (Docker Compose)

La forma más fácil para desarrollo y pruebas:

```bash
cd infrastructure/grobid
docker-compose -f docker-compose.grobid.yml up -d
```

GROBID estará disponible en: `http://localhost:8070`

Verificar que funciona:
```bash
curl http://localhost:8070/api/isalive
```

### 2. EC2 Spot Instance (Más Barato)

Ideal para producción con bajo costo:

```bash
# Usar el script de despliegue
./infrastructure/scripts/deploy_grobid.sh sandbox ec2
```

O manualmente:
1. Crear instancia EC2 (t3.small spot)
2. Ejecutar `infrastructure/grobid/ec2-setup.sh` en la instancia
3. Configurar Security Group para permitir puerto 8070
4. Obtener IP pública y configurar en Lambda

**Costo:** ~$2-3/mes

### 3. ECS Fargate (Más Estable)

Ideal para producción con alta disponibilidad:

```bash
# Usar Terraform
cd infrastructure/terraform
terraform init
terraform apply -var="environment=prod" -var="grobid_deployment=fargate"
```

**Costo:** ~$15-25/mes

## Configuración en la Aplicación

### Variables de Entorno

```bash
# Activar GROBID
USE_GROBID=true

# URL de GROBID
GROBID_URL=http://localhost:8070  # Desarrollo local
GROBID_URL=http://ec2-ip:8070      # EC2
GROBID_URL=http://grobid-alb-dns:8070  # ECS Fargate

# Timeout (segundos)
GROBID_TIMEOUT=30
```

### Límites de Tamaño

```bash
# Tamaño máximo de PDF individual (MB)
MAX_PDF_SIZE_MB=10

# Límites para batch
MAX_BATCH_COUNT=10
MAX_BATCH_TOTAL_MB=50
```

## Verificación

### Health Check

```bash
curl http://GROBID_URL/api/isalive
```

Debería retornar: `200 OK`

### Probar Extracción

```bash
curl -X POST \
  -F "input=@documento.pdf" \
  http://GROBID_URL/api/processReferences
```

## Monitoreo

### CloudWatch Metrics (ECS Fargate)

- `CPUUtilization`: Uso de CPU
- `MemoryUtilization`: Uso de memoria
- `HealthyHostCount`: Número de instancias saludables

### Logs

```bash
# Ver logs de GROBID en ECS
aws logs tail /ecs/grobid-service-prod --follow

# Ver logs en EC2
docker logs grobid
```

## Troubleshooting

### GROBID no responde

1. Verificar que el contenedor esté corriendo:
   ```bash
   docker ps | grep grobid
   ```

2. Verificar logs:
   ```bash
   docker logs grobid
   ```

3. Verificar puerto:
   ```bash
   netstat -tuln | grep 8070
   ```

### Timeout en requests

- Aumentar `GROBID_TIMEOUT` en configuración
- Verificar que GROBID tenga suficiente memoria (mínimo 2GB)
- Verificar latencia de red si GROBID está en la nube

### Calidad baja de extracción

- GROBID funciona mejor con PDFs nativos (no escaneados)
- Para PDFs escaneados, considerar AWS Textract
- Verificar que el PDF tenga estructura de paper científico

## Costos Estimados

| Opción | Costo Mensual | Ventajas | Desventajas |
|--------|---------------|----------|-------------|
| **Local (Docker)** | $0 | Gratis, fácil | Solo desarrollo |
| **EC2 Spot** | $2-3 | Muy barato | Puede interrumpirse |
| **ECS Fargate** | $15-25 | Estable, escalable | Más caro |

## Referencias

- [GROBID Documentation](https://grobid.readthedocs.io/)
- [GROBID GitHub](https://github.com/kermitt2/grobid)
- [Docker Image](https://hub.docker.com/r/lfoppiano/grobid)

