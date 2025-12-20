# Guía de Despliegue en la Nube

Esta guía te ayudará a desplegar la plataforma de extracción bibliográfica en diferentes servicios en la nube.

## Opciones de Despliegue

### 1. Railway (Recomendado - Más Fácil) ⭐

**Railway** es una plataforma muy fácil de usar que soporta PostgreSQL y aplicaciones Python.

#### Pasos:

1. **Crear cuenta en Railway**: https://railway.app

2. **Instalar Railway CLI** (opcional, pero recomendado):
   ```bash
   npm i -g @railway/cli
   railway login
   ```

3. **Crear nuevo proyecto**:
   ```bash
   railway init
   ```

4. **Agregar servicio PostgreSQL**:
   - En el dashboard de Railway, click en "New" → "Database" → "PostgreSQL"
   - Railway creará automáticamente las variables de entorno

5. **Agregar servicio de aplicación**:
   - Click en "New" → "GitHub Repo" (o "Empty Project")
   - Conecta tu repositorio o sube el código

6. **Configurar variables de entorno**:
   - En el dashboard, ve a "Variables"
   - Agrega:
     ```
     DATABASE_URL=<automáticamente configurado por Railway>
     CROSSREF_EMAIL=tu-email@example.com
     ```

7. **Configurar build**:
   - Railway detectará automáticamente el Dockerfile
   - O puedes configurar:
     - Build Command: `pip install -r requirements.txt`
     - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

8. **Desplegar**:
   - Railway desplegará automáticamente cuando hagas push a GitHub
   - O manualmente: `railway up`

**Ventajas**: Muy fácil, PostgreSQL incluido, despliegue automático desde GitHub

---

### 2. Render

**Render** es otra opción popular y fácil de usar.

#### Pasos:

1. **Crear cuenta**: https://render.com

2. **Crear servicio PostgreSQL**:
   - Dashboard → "New" → "PostgreSQL"
   - Anota la "Internal Database URL"

3. **Crear servicio Web**:
   - Dashboard → "New" → "Web Service"
   - Conecta tu repositorio de GitHub
   - Configuración:
     - **Environment**: Python 3
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     - **Environment Variables**:
       ```
       DATABASE_URL=<URL de PostgreSQL de Render>
       CROSSREF_EMAIL=tu-email@example.com
       ```

4. **Desplegar**:
   - Render desplegará automáticamente desde GitHub

**Ventajas**: Fácil, gratis para empezar, PostgreSQL incluido

---

### 3. AWS (Amazon Web Services)

Para producción a gran escala.

#### Opción A: AWS Elastic Beanstalk (Más Fácil)

1. **Instalar EB CLI**:
   ```bash
   pip install awsebcli
   ```

2. **Inicializar EB**:
   ```bash
   eb init -p python-3.11 bibliografia-app
   eb create bibliografia-env
   ```

3. **Configurar RDS (PostgreSQL)**:
   - En AWS Console → RDS → Create Database
   - Selecciona PostgreSQL
   - Anota el endpoint y credenciales

4. **Configurar variables de entorno**:
   ```bash
   eb setenv DATABASE_URL=postgresql://user:pass@host:5432/db
   eb setenv CROSSREF_EMAIL=tu-email@example.com
   ```

5. **Desplegar**:
   ```bash
   eb deploy
   ```

#### Opción B: AWS ECS con Docker

1. **Crear ECR (Elastic Container Registry)**:
   ```bash
   aws ecr create-repository --repository-name bibliografia-app
   ```

2. **Construir y subir imagen**:
   ```bash
   docker build -t bibliografia-app .
   docker tag bibliografia-app:latest <account-id>.dkr.ecr.<region>.amazonaws.com/bibliografia-app:latest
   aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
   docker push <account-id>.dkr.ecr.<region>.amazonaws.com/bibliografia-app:latest
   ```

3. **Crear servicio ECS** con la imagen

**Ventajas**: Escalable, robusto, para producción

---

### 4. Google Cloud Platform (GCP)

#### Usando Cloud Run (Recomendado)

1. **Instalar gcloud CLI**:
   ```bash
   # Descargar desde: https://cloud.google.com/sdk/docs/install
   gcloud init
   ```

2. **Habilitar APIs**:
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable sqladmin.googleapis.com
   ```

3. **Crear Cloud SQL (PostgreSQL)**:
   ```bash
   gcloud sql instances create bibliografia-db \
     --database-version=POSTGRES_15 \
     --tier=db-f1-micro \
     --region=us-central1
   ```

4. **Construir y desplegar**:
   ```bash
   gcloud builds submit --tag gcr.io/PROJECT-ID/bibliografia-app
   gcloud run deploy bibliografia-app \
     --image gcr.io/PROJECT-ID/bibliografia-app \
     --platform managed \
     --region us-central1 \
     --set-env-vars DATABASE_URL=<cloud-sql-connection-string>,CROSSREF_EMAIL=tu-email@example.com
   ```

**Ventajas**: Escalable, pago por uso

---

### 5. Heroku

1. **Instalar Heroku CLI**:
   ```bash
   # Descargar desde: https://devcenter.heroku.com/articles/heroku-cli
   heroku login
   ```

2. **Crear aplicación**:
   ```bash
   heroku create bibliografia-app
   ```

3. **Agregar PostgreSQL**:
   ```bash
   heroku addons:create heroku-postgresql:mini
   ```

4. **Configurar variables**:
   ```bash
   heroku config:set CROSSREF_EMAIL=tu-email@example.com
   # DATABASE_URL se configura automáticamente
   ```

5. **Desplegar**:
   ```bash
   git push heroku main
   ```

**Nota**: Heroku eliminó su plan gratuito, ahora es de pago.

---

## Configuración Común para Todos

### Variables de Entorno Necesarias

```bash
DATABASE_URL=postgresql://usuario:contraseña@host:5432/bibliografia_db
CROSSREF_EMAIL=tu-email@example.com
```

### Archivos Necesarios

Asegúrate de tener estos archivos en tu repositorio:
- `Dockerfile` (para despliegues con Docker)
- `requirements.txt`
- `.env.example` (sin credenciales reales)
- `.dockerignore`

### Configuración de Base de Datos

Después del despliegue, necesitas inicializar las tablas:

```bash
# Opción 1: Desde el código (si agregas un comando de inicialización)
# Opción 2: Conectarte a la base de datos y ejecutar:
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

O mejor, agrega esto a tu código de inicio (ya está en `app/main.py`).

---

## Recomendaciones

### Para Desarrollo/Pruebas:
- **Railway** o **Render** (más fácil, gratis para empezar)

### Para Producción Pequeña/Media:
- **Railway** o **Render** (planes de pago) ⭐ **Recomendado**

### Para Producción a Gran Escala:
- **AWS EC2 + RDS** (servidor tradicional, mejor para procesamiento de PDFs)
- **AWS ECS Fargate** (contenedores escalables)
- **Google Cloud Run**
- **Azure App Service**

> 💡 **Nota**: Para un análisis detallado de arquitecturas (EC2 vs Serverless), consulta [ARCHITECTURE.md](ARCHITECTURE.md)

---

## Checklist Pre-Despliegue

- [ ] Variables de entorno configuradas
- [ ] Base de datos PostgreSQL creada
- [ ] Dockerfile probado localmente
- [ ] `.env` no está en el repositorio (usar `.env.example`)
- [ ] CORS configurado correctamente (si es necesario)
- [ ] Dominio personalizado configurado (opcional)
- [ ] SSL/HTTPS habilitado (automático en la mayoría de plataformas)

---

## Pruebas Post-Despliegue

1. Verificar que la aplicación está corriendo:
   ```bash
   curl https://tu-app.railway.app/api/health
   ```

2. Probar subir un PDF o referencia

3. Verificar que la base de datos funciona

4. Probar descarga de datos

---

## Soporte

Si tienes problemas con el despliegue, verifica:
- Logs de la aplicación en el dashboard de la plataforma
- Variables de entorno están correctas
- La base de datos está accesible
- El puerto está configurado correctamente (usar `$PORT` en la nube)


