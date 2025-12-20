# Compartir Aplicación Temporalmente (Sin Configuración)

Guía para compartir tu aplicación de forma temporal sin que otros tengan que configurar nada.

## 🎯 Solución: ngrok (URL Pública Temporal)

**ngrok** crea un túnel público que expone tu aplicación local. Los demás solo necesitan una URL, sin instalar ni configurar nada.

---

## Paso 1: Instalar ngrok

### Windows:
```bash
# Opción A: Chocolatey
choco install ngrok

# Opción B: Descargar manualmente
# Ir a: https://ngrok.com/download
# Descargar, descomprimir, agregar a PATH
```

### Mac:
```bash
brew install ngrok
```

### Linux:
```bash
# Descargar desde: https://ngrok.com/download
# O usar snap
snap install ngrok
```

### Crear cuenta (gratis):
1. Ir a: https://ngrok.com/signup
2. Crear cuenta gratuita
3. Obtener tu authtoken del dashboard
4. Configurar:
```bash
ngrok config add-authtoken TU_AUTHTOKEN
```

---

## Paso 2: Iniciar tu Aplicación

Asegúrate de que tu aplicación esté corriendo:

```bash
python run.py
```

O si prefieres especificar el host:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

---

## Paso 3: Crear Túnel con ngrok

En otra terminal, ejecuta:

```bash
ngrok http 8001
```

Esto te dará algo como:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8001
```

**¡Esa URL es la que compartes!** 🎉

---

## Paso 4: Compartir la URL

Simplemente comparte la URL que ngrok te dio:

```
https://abc123.ngrok-free.app
```

Los demás pueden:
- ✅ Abrirla en su navegador
- ✅ Usar la API directamente
- ✅ Subir PDFs y referencias
- ❌ NO necesitan instalar nada
- ❌ NO necesitan configurar nada

---

## Ejemplo de Uso

**Tú (en tu laptop):**
```bash
# Terminal 1: Iniciar aplicación
python run.py

# Terminal 2: Crear túnel
ngrok http 8001
```

**Otra persona (en su máquina):**
```
Abre navegador: https://abc123.ngrok-free.app
¡Listo! Ya puede usar la aplicación
```

---

## Ventajas de ngrok

- ✅ **Cero configuración** para los usuarios
- ✅ **Funciona desde cualquier lugar** (no necesita misma red)
- ✅ **HTTPS automático** (seguro)
- ✅ **Temporal** (perfecto para pruebas)
- ✅ **Gratis** para uso básico

---

## Limitaciones del Plan Gratuito

- ⚠️ La URL cambia cada vez que reinicias ngrok
- ⚠️ Límite de conexiones simultáneas
- ⚠️ Puede tener límite de ancho de banda
- ⚠️ Banner de advertencia (se puede quitar con plan pago)

---

## Alternativa: ngrok con URL Fija (Plan Pago)

Si quieres una URL que no cambie:

```bash
ngrok http 8001 --domain=tu-dominio.ngrok.app
```

Requiere plan pago (~$8/mes), pero la URL es permanente.

---

## Otras Opciones Temporales

### 1. Cloudflare Tunnel (Gratis, URL Fija)

```bash
# Instalar cloudflared
# Windows: choco install cloudflared
# Mac: brew install cloudflared

# Crear túnel
cloudflared tunnel --url http://localhost:8001
```

### 2. localtunnel (Gratis, Simple)

```bash
# Instalar
npm install -g localtunnel

# Crear túnel
lt --port 8001
```

### 3. serveo (Sin Instalación)

```bash
ssh -R 80:localhost:8001 serveo.net
```

---

## Comparación Rápida

| Opción | Instalación | URL Fija | Gratis | Facilidad |
|--------|-------------|----------|--------|-----------|
| **ngrok** | ✅ Fácil | ❌ No* | ✅ Sí | ⭐⭐⭐⭐⭐ |
| **Cloudflare** | ✅ Fácil | ✅ Sí | ✅ Sí | ⭐⭐⭐⭐ |
| **localtunnel** | ✅ Fácil | ❌ No | ✅ Sí | ⭐⭐⭐⭐ |
| **serveo** | ❌ No | ❌ No | ✅ Sí | ⭐⭐⭐ |

*ngrok tiene URL fija con plan pago

---

## Recomendación

**Para uso temporal sin configuración: ngrok** ⭐

Es la opción más fácil y popular. Los usuarios solo necesitan la URL que compartes.

---

## Ejemplo Completo

### Tú (Servidor):

```bash
# 1. Iniciar aplicación
python run.py
# Aplicación corriendo en http://localhost:8001

# 2. En otra terminal, crear túnel
ngrok http 8001

# 3. Copiar la URL que aparece:
# https://abc123.ngrok-free.app

# 4. Compartir esa URL
```

### Otra Persona (Cliente):

```
1. Abre navegador
2. Ve a: https://abc123.ngrok-free.app
3. ¡Listo! Puede usar la aplicación
```

---

## Troubleshooting

### Error: "ngrok: command not found"
- Verifica que ngrok esté instalado y en PATH
- Reinicia la terminal después de instalar

### Error: "authtoken required"
- Crea cuenta en ngrok.com
- Obtén tu authtoken
- Ejecuta: `ngrok config add-authtoken TU_TOKEN`

### La URL no funciona
- Verifica que tu aplicación esté corriendo en el puerto correcto
- Verifica que ngrok esté corriendo
- Prueba la URL en modo incógnito (a veces hay cache)

---

## Seguridad

⚠️ **Importante**: 
- La URL de ngrok es **pública** (cualquiera con el link puede acceder)
- Solo comparte la URL con personas de confianza
- Para producción, usa autenticación o despliegue en la nube

---

¿Quieres que te ayude a configurar ngrok paso a paso?

