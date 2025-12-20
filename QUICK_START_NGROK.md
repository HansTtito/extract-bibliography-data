# Inicio Rápido: Compartir con ngrok

## Pasos Rápidos (5 minutos)

### 1. Instalar ngrok

**Windows:**
```bash
# Opción A: Chocolatey
choco install ngrok

# Opción B: Descargar manual
# 1. Ir a: https://ngrok.com/download
# 2. Descargar para Windows
# 3. Descomprimir
# 4. Agregar carpeta a PATH o usar desde la carpeta
```

**Mac:**
```bash
brew install ngrok
```

**Linux:**
```bash
# Descargar desde: https://ngrok.com/download
# O
snap install ngrok
```

### 2. Crear Cuenta (Gratis)

1. Ir a: https://ngrok.com/signup
2. Crear cuenta
3. Ir a: https://dashboard.ngrok.com/get-started/your-authtoken
4. Copiar tu authtoken

### 3. Configurar ngrok

```bash
ngrok config add-authtoken TU_AUTHTOKEN_AQUI
```

### 4. Iniciar tu Aplicación

```bash
python run.py
```

Deberías ver: `Uvicorn running on http://0.0.0.0:8001`

### 5. Crear Túnel (en otra terminal)

```bash
ngrok http 8001
```

### 6. Compartir la URL

ngrok mostrará algo como:

```
Session Status                online
Account                       tu-email@example.com
Forwarding                    https://abc123.ngrok-free.app -> http://localhost:8001
```

**Comparte esta URL:** `https://abc123.ngrok-free.app`

---

## ✅ Listo!

Los demás pueden:
- Abrir esa URL en su navegador
- Usar la aplicación completa
- Subir PDFs y referencias
- Ver documentos guardados

**Sin instalar ni configurar nada.**

---

## Troubleshooting

### "ngrok: command not found"
- Verifica que ngrok esté instalado
- Reinicia la terminal
- Verifica que esté en PATH

### "authtoken required"
- Asegúrate de haber creado cuenta
- Copia el authtoken del dashboard
- Ejecuta: `ngrok config add-authtoken TU_TOKEN`

### La URL no carga
- Verifica que `python run.py` esté corriendo
- Verifica que ngrok esté corriendo
- Prueba en modo incógnito

---

## Nota Importante

⚠️ La URL es **pública**. Solo compártela con personas de confianza.

La URL cambia cada vez que reinicias ngrok (plan gratis). Si necesitas URL fija, considera el plan pago.

---

¿Todo listo? ¡Prueba y comparte la URL!

