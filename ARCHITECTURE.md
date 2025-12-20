# Análisis de Arquitectura: EC2 vs Serverless

## Características de tu Aplicación

Tu aplicación tiene estas características que afectan la decisión:

- ✅ **Procesamiento de PDFs**: Puede tomar varios segundos (5-30s dependiendo del tamaño)
- ✅ **Llamadas a APIs externas**: CrossRef API (puede tener latencia)
- ✅ **Procesamiento por lotes**: Extracción de múltiples referencias de un PDF
- ✅ **Base de datos PostgreSQL**: Necesita conexión persistente
- ✅ **Frontend estático**: Se sirve desde el mismo servidor
- ✅ **Carga variable**: Puede tener picos de uso

---

## Comparación: EC2 vs Serverless

### Opción 1: EC2 (Servidor Tradicional) 🖥️

#### Arquitectura:
```
EC2 Instance (t3.medium o similar)
  ├── FastAPI Application
  ├── PostgreSQL (RDS)
  └── Frontend estático
```

#### ✅ Ventajas:
- **Control total**: Configuras todo como quieras
- **Sin límites de tiempo**: Puedes procesar PDFs grandes sin problemas
- **Costo predecible**: Pago fijo mensual (~$30-50/mes para t3.medium)
- **Más barato para cargas constantes**: Si siempre está en uso
- **Fácil de entender**: Arquitectura tradicional
- **Sin cold starts**: Siempre listo para recibir requests

#### ❌ Desventajas:
- **Mantenimiento**: Tú gestionas actualizaciones, seguridad, backups
- **Escalado manual**: Si necesitas más capacidad, debes cambiar el tamaño
- **Pago aunque no uses**: Pagas 24/7 aunque no haya tráfico
- **Configuración inicial**: Más trabajo para setup

#### Costo Estimado (AWS):
- **EC2 t3.medium**: ~$30/mes
- **RDS db.t3.micro**: ~$15/mes
- **Storage (20GB)**: ~$2/mes
- **Total**: ~$47/mes

---

### Opción 2: Serverless (Lambda + API Gateway + RDS) ⚡

#### Arquitectura:
```
API Gateway
  └── Lambda Functions
      ├── /upload-pdf → Lambda (procesa PDF)
      ├── /upload-reference → Lambda (procesa referencia)
      └── /upload-references-pdf → Lambda (procesa múltiples)
  └── RDS PostgreSQL
  └── S3 (para frontend estático)
```

#### ✅ Ventajas:
- **Escalado automático**: Se adapta automáticamente a la carga
- **Pago por uso**: Solo pagas cuando se usa (puede ser muy barato con poco tráfico)
- **Sin mantenimiento de servidor**: AWS gestiona la infraestructura
- **Alta disponibilidad**: Automático
- **Ideal para cargas variables**: Perfecto si el uso es intermitente

#### ❌ Desventajas:
- **Límite de tiempo**: Lambda máximo 15 minutos (puede ser limitante para PDFs muy grandes)
- **Cold starts**: Primera invocación puede tardar 1-3 segundos
- **Más complejo**: Requiere más configuración (Lambda layers, VPC para RDS, etc.)
- **Puede ser más caro**: Con uso constante, puede superar el costo de EC2
- **Dependencias pesadas**: `pdfplumber` y otras librerías pueden hacer el deployment package grande
- **Conexiones a RDS**: Necesitas configurar VPC y connection pooling

#### Costo Estimado (AWS):
- **Lambda**: ~$0.20 por 1M requests + $0.0000166667 por GB-segundo
- **API Gateway**: ~$3.50 por 1M requests
- **RDS db.t3.micro**: ~$15/mes (igual que EC2)
- **S3 + CloudFront**: ~$1/mes
- **Total estimado**: 
  - Bajo tráfico (1000 requests/mes): ~$16/mes
  - Medio tráfico (10,000 requests/mes): ~$20/mes
  - Alto tráfico (100,000 requests/mes): ~$40/mes

---

### Opción 3: Híbrida (Recomendada) 🎯

#### Arquitectura:
```
EC2 (t3.small) - FastAPI
  ├── Procesamiento de PDFs (síncrono)
  ├── Frontend estático
  └── Conexión a RDS PostgreSQL

SQS + Lambda (opcional)
  └── Para procesamiento asíncrono de lotes grandes
```

#### ✅ Ventajas:
- **Lo mejor de ambos mundos**: Control + escalabilidad
- **Costo optimizado**: EC2 pequeño para operaciones normales
- **Flexibilidad**: Puedes agregar Lambda para tareas pesadas si es necesario
- **Sin límites de tiempo**: Para procesamiento de PDFs

---

## Recomendación por Escenario

### 🟢 Escenario 1: Uso Personal/Pequeño Equipo (< 1000 requests/mes)
**Recomendación: Railway o Render (PaaS)**
- ✅ Más fácil de configurar
- ✅ PostgreSQL incluido
- ✅ ~$5-20/mes
- ✅ Sin mantenimiento
- ✅ Despliegue automático desde GitHub

### 🟡 Escenario 2: Uso Moderado (1,000 - 10,000 requests/mes)
**Recomendación: EC2 t3.small + RDS**
- ✅ Costo predecible (~$30-40/mes)
- ✅ Sin límites de tiempo para PDFs
- ✅ Control total
- ✅ Fácil de monitorear

### 🔴 Escenario 3: Uso Alto/Variable (10,000+ requests/mes, picos)
**Recomendación: Serverless (Lambda)**
- ✅ Escala automáticamente
- ✅ Pago por uso
- ✅ Alta disponibilidad automática
- ⚠️ Requiere refactorizar código para Lambda

### 🟣 Escenario 4: Producción Empresarial
**Recomendación: ECS Fargate o EKS**
- ✅ Contenedores escalables
- ✅ Sin gestión de servidores
- ✅ Auto-scaling
- ✅ Más control que Lambda

---

## Mi Recomendación Específica para tu Caso

### 🎯 **Recomendación según Frecuencia de Uso**

#### Si usas la app **unas cuantas veces al mes** (uso esporádico):
**✅ Serverless (Lambda) es la MEJOR opción**

**Razones:**
1. **Costo mínimo**: Solo pagas cuando se usa (~$0.20 por 1M requests)
2. **Sin costos fijos**: No pagas $47/mes por un servidor que casi no usas
3. **Escalado automático**: Listo cuando lo necesites
4. **Costo estimado**: ~$1-5/mes vs $47/mes de EC2

**Ejemplo de costo con uso esporádico:**
- 10 requests/mes procesando PDFs
- Lambda: ~$0.01/mes (prácticamente gratis)
- EC2: $47/mes (pagas aunque no lo uses)
- **Ahorro: $46.99/mes** 💰

#### Si usas la app **varias veces por semana** (uso regular):
**✅ Railway o Render (PaaS)**

**Razones:**
1. **Más fácil de configurar**: Sin la complejidad de Lambda
2. **PostgreSQL incluido**: Todo en un solo lugar
3. **Costo razonable**: ~$5-20/mes
4. **Sin cold starts**: Siempre listo

#### Si usas la app **diariamente o constantemente**:
**✅ EC2 + RDS**

**Razones:**
1. **Costo predecible**: $47/mes fijo
2. **Sin límites de tiempo**: Para PDFs grandes
3. **Mejor rendimiento**: Sin cold starts

---

## Migración a Serverless (Si decides hacerlo)

Si en el futuro quieres migrar a serverless, necesitarías:

1. **Separar procesamiento pesado**:
   ```python
   # En lugar de procesar en el endpoint
   @router.post("/upload-pdf")
   async def upload_pdf(file: UploadFile):
       # Subir a S3
       s3_key = upload_to_s3(file)
       # Disparar Lambda asíncrono
       invoke_lambda("process-pdf", {"s3_key": s3_key})
       return {"status": "processing"}
   ```

2. **Usar Lambda Layers** para dependencias pesadas (pdfplumber)

3. **Connection pooling** para RDS desde Lambda

4. **API Gateway** para routing

5. **S3 + CloudFront** para frontend estático

---

## Comparación de Costos (Estimado Mensual)

| Opción | Bajo Tráfico | Medio Tráfico | Alto Tráfico |
|--------|--------------|---------------|--------------|
| **Railway/Render** | $5-10 | $20-30 | $50-100 |
| **EC2 + RDS** | $47 | $47 | $100+ |
| **Lambda + RDS** | $16 | $20 | $40-60 |
| **ECS Fargate** | $30 | $50 | $150+ |

---

## Conclusión

Para tu aplicación de extracción bibliográfica:

### Si usas la app **unas cuantas veces al mes** (uso esporádico):
1. **Serverless (Lambda)** ⭐ - **MEJOR OPCIÓN**
   - Costo: ~$15/mes (vs $47/mes de EC2)
   - Ahorro: ~$32/mes
   - Ver [DEPLOY_LAMBDA.md](DEPLOY_LAMBDA.md) para guía completa

### Si usas la app **varias veces por semana**:
2. **Railway o Render (PaaS)** - Más fácil, económico
   - Costo: ~$5-20/mes
   - PostgreSQL incluido

### Si usas la app **diariamente o constantemente**:
3. **EC2 t3.small + RDS** - Control total, costo predecible
   - Costo: ~$47/mes fijo
   - Sin límites de tiempo

### Si escala mucho:
4. **ECS Fargate** - Escalable, sin gestión de servidores
   - Costo: ~$30-150/mes según uso

---

## Próximos Pasos

1. **Empezar con Railway/Render** (más fácil)
2. **Monitorear uso y costos** durante 1-2 meses
3. **Evaluar migración** a EC2 si:
   - El costo de PaaS sube mucho
   - Necesitas más control
   - Tienes problemas de rendimiento

¿Quieres que te ayude a configurar alguna de estas opciones?

