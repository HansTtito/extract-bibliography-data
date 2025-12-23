# Guía de Configuración de Base de Datos

## Opción 1: Docker Compose (RECOMENDADO - Más Fácil) 🐳

**No necesitas instalar PostgreSQL**, Docker lo maneja todo automáticamente.

### Requisitos:
- Docker Desktop instalado en Windows
- Descargar desde: https://www.docker.com/products/docker-desktop/

### Pasos:

1. **Iniciar PostgreSQL con Docker**:
```bash
docker-compose up -d
```

Esto descargará e iniciará PostgreSQL automáticamente. La base de datos estará lista en segundos.

2. **Crear archivo `.env`** en la raíz del proyecto:
```
DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@localhost:5432/bibliografia_db
CROSSREF_EMAIL=tu-email@example.com
```

3. **Verificar que está corriendo**:
```bash
docker-compose ps
```

4. **Detener PostgreSQL** (cuando no lo uses):
```bash
docker-compose down
```

5. **Detener y eliminar datos** (si quieres empezar de cero):
```bash
docker-compose down -v
```

---

## Opción 2: PostgreSQL Local (Requiere Instalación)

Si prefieres tener PostgreSQL instalado directamente en tu sistema:

### Pasos:

1. **Instalar PostgreSQL**:
   - Windows: https://www.postgresql.org/download/windows/
   - O usar instalador gráfico: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads

2. **Crear base de datos**:
   - Abrir pgAdmin o línea de comandos
   - Ejecutar: `CREATE DATABASE bibliografia_db;`

3. **Crear archivo `.env`**:
```
DATABASE_URL=postgresql://tu_usuario:tu_contraseña@localhost:5432/bibliografia_db
CROSSREF_EMAIL=tu-email@example.com
```

---

## Opción 3: PostgreSQL en la Nube (Para Producción)

Si planeas desplegar en producción, puedes usar:
- **AWS RDS** (PostgreSQL)
- **Heroku Postgres**
- **Supabase**
- **ElephantSQL**

Luego solo cambias la `DATABASE_URL` en `.env`

---

## Verificación

Después de configurar cualquiera de las opciones, prueba la conexión:

```bash
python -c "from app.database import engine; engine.connect(); print('✓ Conexión exitosa')"
```

O simplemente inicia la aplicación:
```bash
python run.py
```

Si la base de datos está configurada correctamente, las tablas se crearán automáticamente al iniciar.

