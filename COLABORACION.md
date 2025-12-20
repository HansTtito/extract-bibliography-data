# Guía de Colaboración: Cómo Trabajar con Otras Personas

## Escenarios Comunes

### Escenario 1: Solo Compartir Base de Datos (Recomendado) 🗄️

**Situación**: Tú tienes Docker corriendo con PostgreSQL, otra persona quiere usar la misma base de datos.

**¿Qué necesita la otra persona?**
- ✅ El código del proyecto (clonar desde Git o compartir carpeta)
- ✅ Configurar su `.env` apuntando a TU base de datos
- ❌ NO necesita Docker corriendo
- ❌ NO necesita instalar PostgreSQL

**Pasos:**

1. **Tú (en tu laptop con Docker)**:
   ```bash
   # Obtener tu IP local
   ipconfig  # Windows
   # Anota tu IP (ej: 192.168.1.100)
   ```

2. **Modificar docker-compose.yml** para permitir acceso remoto:
   ```yaml
   ports:
     - "0.0.0.0:5432:5432"  # Permite acceso desde otras máquinas
   ```

3. **Reiniciar Docker**:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

4. **Compartir con la otra persona**:
   - Tu IP local (ej: `192.168.1.100`)
   - Credenciales de la base de datos (del docker-compose.yml)

5. **La otra persona configura su `.env`**:
   ```bash
   DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@192.168.1.100:5432/bibliografia_db
   CROSSREF_EMAIL=su-email@example.com
   ```

6. **La otra persona ejecuta**:
   ```bash
   # Clonar/obtener el proyecto
   git clone <tu-repo>  # o compartir carpeta
   
   # Instalar dependencias
   pip install -r requirements.txt
   
   # Ejecutar scripts de prueba
   python test_pdf_extraction.py documento.pdf
   
   # O ejecutar la aplicación
   python run.py
   ```

**Ventajas:**
- ✅ Solo UNA base de datos (todos ven los mismos datos)
- ✅ La otra persona no necesita Docker
- ✅ Fácil de configurar

**Desventajas:**
- ⚠️ Tu laptop debe estar encendida y en la misma red
- ⚠️ Solo funciona en la misma red local

---

### Escenario 2: Cada Uno con su Propia Base de Datos 🔄

**Situación**: Cada persona trabaja independientemente con su propia base de datos.

**¿Qué necesita cada persona?**
- ✅ El código del proyecto
- ✅ Docker instalado (o PostgreSQL local)
- ✅ Su propia base de datos

**Pasos para cada persona:**

1. **Clonar/obtener el proyecto**
2. **Configurar Docker local**:
   ```bash
   docker-compose up -d
   ```
3. **Configurar `.env`**:
   ```bash
   DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@localhost:5432/bibliografia_db
   ```
4. **Ejecutar scripts o aplicación**

**Ventajas:**
- ✅ Cada uno trabaja independientemente
- ✅ No dependen de que tu laptop esté encendida
- ✅ Pueden experimentar sin afectar a otros

**Desventajas:**
- ⚠️ Cada uno tiene datos diferentes
- ⚠️ Necesitan Docker instalado

---

### Escenario 3: Base de Datos Compartida en la Nube ☁️

**Situación**: Todos usan la misma base de datos en la nube.

**¿Qué necesita cada persona?**
- ✅ El código del proyecto
- ✅ La misma URL de conexión (compartida)
- ❌ NO necesita Docker
- ❌ NO necesita PostgreSQL local

**Pasos:**

1. **Crear base de datos en la nube** (una vez):
   - Opción A: **Supabase** (gratis)
     - Crear cuenta: https://supabase.com
     - Crear proyecto
     - Obtener connection string
   
   - Opción B: **Railway** (gratis)
     - Crear cuenta: https://railway.app
     - Crear servicio PostgreSQL
     - Obtener DATABASE_URL

2. **Compartir la URL** con todos:
   ```bash
   DATABASE_URL=postgresql://user:pass@db.xxxxx.supabase.co:5432/postgres
   ```

3. **Cada persona configura su `.env`** con la misma URL

4. **Cada persona ejecuta**:
   ```bash
   pip install -r requirements.txt
   python test_pdf_extraction.py documento.pdf
   # o
   python run.py
   ```

**Ventajas:**
- ✅ Todos ven los mismos datos
- ✅ Funciona desde cualquier lugar
- ✅ No depende de laptops individuales
- ✅ Siempre disponible

**Desventajas:**
- ⚠️ Requiere cuenta en servicio de nube
- ⚠️ Puede tener límites en planes gratuitos

---

## Comparación de Escenarios

| Escenario | Compartir Código | Compartir BD | Docker Necesario | Acceso Remoto |
|-----------|-----------------|--------------|------------------|---------------|
| **1. BD Remota (Tu Laptop)** | ✅ Sí | ✅ Sí | Solo tú | Misma red |
| **2. BD Local (Cada Uno)** | ✅ Sí | ❌ No | Todos | No aplica |
| **3. BD en Nube** | ✅ Sí | ✅ Sí | ❌ No | ✅ Sí |

---

## Recomendación por Caso de Uso

### 🎓 Para Desarrollo/Testing en Equipo:
**Escenario 3 (Nube)** - Todos usan la misma BD, fácil de configurar

### 🏠 Para Trabajo en Casa/Oficina (Misma Red):
**Escenario 1 (BD Remota)** - Rápido, sin configuración de nube

### 🔬 Para Experimentación Individual:
**Escenario 2 (BD Local)** - Cada uno prueba sin afectar a otros

---

## Ejemplo Completo: Configurar Colaboración

### Paso 1: Preparar el Proyecto para Compartir

Asegúrate de tener un `.env.example`:

```bash
# .env.example
DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@localhost:5432/bibliografia_db
CROSSREF_EMAIL=tu-email@example.com
```

### Paso 2: Compartir el Proyecto

**Opción A: Git (Recomendado)**
```bash
# Crear repositorio
git init
git add .
git commit -m "Initial commit"
# Subir a GitHub/GitLab
git remote add origin <url>
git push -u origin main
```

**Opción B: Compartir Carpeta**
- Zip del proyecto
- Compartir por email/Drive/etc.

### Paso 3: Instrucciones para la Otra Persona

Crea un archivo `SETUP_COLABORADOR.md`:

```markdown
# Setup para Colaborador

1. Clonar/obtener el proyecto
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Configurar `.env`:
   ```bash
   DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@192.168.1.100:5432/bibliografia_db
   CROSSREF_EMAIL=tu-email@example.com
   ```
4. Probar:
   ```bash
   python test_pdf_extraction.py documento.pdf
   ```
```

---

## Preguntas Frecuentes

### ¿La otra persona necesita tener Docker?
**Solo si usa Escenario 2** (cada uno con su BD local). Para Escenarios 1 y 3, NO necesita Docker.

### ¿Pueden ejecutar scripts sin el servidor corriendo?
**Sí**, los scripts de prueba (`test_pdf_extraction.py`, etc.) NO necesitan el servidor, solo la base de datos.

### ¿Qué pasa si mi laptop se apaga?
- **Escenario 1**: La otra persona no podrá acceder
- **Escenario 2**: No afecta (cada uno tiene su BD)
- **Escenario 3**: No afecta (BD en la nube)

### ¿Pueden modificar el código?
**Sí**, cada persona puede modificar el código localmente. Si quieren compartir cambios, usa Git.

---

## Resumen Rápido

**Para que otra persona ejecute scripts usando TU base de datos:**

1. ✅ Comparte el proyecto (Git o carpeta)
2. ✅ Modifica `docker-compose.yml` para exponer puerto
3. ✅ Comparte tu IP y credenciales
4. ✅ La otra persona configura `.env` con tu IP
5. ✅ La otra persona ejecuta: `python test_pdf_extraction.py documento.pdf`

**NO necesita:**
- ❌ Docker en su máquina
- ❌ PostgreSQL instalado
- ❌ Que levantes el servidor FastAPI

¿Necesitas ayuda configurando alguno de estos escenarios?

