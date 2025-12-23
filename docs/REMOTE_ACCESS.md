# Acceso Remoto y Compartir la Aplicación

Esta guía cubre diferentes formas de compartir tu aplicación y base de datos con otros usuarios.

## Tabla de Contenidos

1. [Compartir la Aplicación Web (ngrok)](#compartir-la-aplicación-web-ngrok)
2. [Compartir Base de Datos](#compartir-base-de-datos)
3. [Escenarios de Colaboración](#escenarios-de-colaboración)

---

## Compartir la Aplicación Web (ngrok)

### Instalación Rápida

**Windows:**
```bash
choco install ngrok
# O descargar desde: https://ngrok.com/download
```

**Mac:**
```bash
brew install ngrok
```

**Linux:**
```bash
snap install ngrok
# O descargar desde: https://ngrok.com/download
```

### Configuración Inicial

1. **Crear cuenta gratuita**: https://ngrok.com/signup
2. **Obtener authtoken**: https://dashboard.ngrok.com/get-started/your-authtoken
3. **Configurar ngrok:**
```bash
ngrok config add-authtoken TU_AUTHTOKEN
```

### Uso

1. **Iniciar tu aplicación** (Terminal 1):
```bash
python run.py
```

2. **Crear túnel** (Terminal 2):
```bash
ngrok http 8001
```

3. **Compartir la URL** que aparece:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8001
```

**Comparte:** `https://abc123.ngrok-free.app`

### Limitaciones del Plan Gratuito

- ⚠️ La URL cambia cada vez que reinicias ngrok
- ⚠️ Límite de conexiones simultáneas
- ⚠️ Banner de advertencia (se puede quitar con plan pago)

---

## Compartir Base de Datos

### Opción 1: Base de Datos en la Nube (Recomendado)

**Ventajas:**
- ✅ Accesible desde cualquier lugar
- ✅ Siempre disponible
- ✅ No depende de tu laptop

**Opciones gratuitas:**
- **Supabase**: https://supabase.com
- **Railway**: https://railway.app
- **Neon**: https://neon.tech

**Configuración:**
1. Crear cuenta y proyecto
2. Obtener connection string
3. Configurar en `.env`:
```bash
DATABASE_URL=postgresql://user:pass@db.xxxxx.supabase.co:5432/postgres
```

### Opción 2: Base de Datos Remota (Red Local)

**Para desarrollo en la misma red:**

1. **Modificar `docker-compose.yml`:**
```yaml
ports:
  - "0.0.0.0:5432:5432"  # Permite acceso remoto
```

2. **Obtener tu IP local:**
```bash
# Windows
ipconfig
# Busca "IPv4 Address" (ej: 192.168.1.100)
```

3. **Compartir configuración:**
```bash
DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@192.168.1.100:5432/bibliografia_db
```

**Limitaciones:**
- ⚠️ Solo funciona en la misma red local
- ⚠️ Tu laptop debe estar encendida

### Opción 3: Túnel SSH (Seguro)

**Para acceso desde cualquier lugar:**

```bash
# La otra persona ejecuta:
ssh -L 5432:localhost:5432 usuario@TU_IP_PUBLICA
```

Luego usa en `.env`:
```bash
DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@localhost:5432/bibliografia_db
```

---

## Escenarios de Colaboración

### Escenario 1: Solo Compartir Base de Datos

**Situación:** Tú tienes Docker corriendo, otra persona quiere usar la misma base de datos.

**Pasos:**
1. Modificar `docker-compose.yml` para exponer puerto
2. Compartir tu IP y credenciales
3. La otra persona configura `.env` con tu IP

**Ventajas:**
- ✅ Solo UNA base de datos (todos ven los mismos datos)
- ✅ La otra persona no necesita Docker

### Escenario 2: Cada Uno con su Propia Base de Datos

**Situación:** Cada persona trabaja independientemente.

**Pasos:**
1. Cada persona clona el proyecto
2. Cada persona ejecuta `docker-compose up -d`
3. Cada persona configura su propio `.env`

**Ventajas:**
- ✅ Cada uno trabaja independientemente
- ✅ No dependen de que tu laptop esté encendida

### Escenario 3: Base de Datos Compartida en la Nube

**Situación:** Todos usan la misma base de datos en la nube.

**Pasos:**
1. Crear base de datos en Supabase/Railway/etc.
2. Compartir la URL de conexión
3. Cada persona configura `.env` con la misma URL

**Ventajas:**
- ✅ Todos ven los mismos datos
- ✅ Funciona desde cualquier lugar
- ✅ Siempre disponible

---

## Comparación Rápida

| Método | Facilidad | Acceso | Costo | Recomendado Para |
|--------|-----------|--------|-------|------------------|
| **ngrok (App)** | ⭐⭐⭐⭐⭐ | Cualquier lugar | Gratis | Compartir aplicación temporal |
| **BD en Nube** | ⭐⭐⭐⭐ | Cualquier lugar | Gratis-$15/mes | Producción/Colaboración |
| **BD Remota (Red Local)** | ⭐⭐⭐ | Solo misma red | Gratis | Desarrollo local |
| **SSH Tunnel** | ⭐⭐ | Cualquier lugar | Gratis | Acceso seguro remoto |

---

## Recomendación

- **Para compartir la aplicación temporalmente:** Usa ngrok
- **Para colaboración continua:** Usa base de datos en la nube
- **Para desarrollo en oficina:** Usa base de datos remota (red local)

---

## Troubleshooting

### ngrok: "command not found"
- Verifica que ngrok esté instalado y en PATH
- Reinicia la terminal después de instalar

### ngrok: "authtoken required"
- Crea cuenta en ngrok.com
- Obtén tu authtoken del dashboard
- Ejecuta: `ngrok config add-authtoken TU_TOKEN`

### Base de datos: "Connection refused"
- Verifica que el puerto esté expuesto en docker-compose.yml
- Verifica firewall (permite conexiones en puerto 5432)
- Verifica que estén en la misma red (si es red local)

---

Para más detalles sobre configuración específica, consulta:
- [SETUP_DATABASE.md](SETUP_DATABASE.md) - Configuración de base de datos
- [DEPLOY.md](DEPLOY.md) - Despliegue en la nube
