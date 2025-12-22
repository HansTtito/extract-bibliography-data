# Crear Túnel con ngrok

## Pasos

### 1. Tu aplicación ya está corriendo ✅
```
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**NO cierres esta terminal.** Déjala corriendo.

### 2. Abre una NUEVA terminal

Abre otra ventana de PowerShell o CMD.

### 3. Ejecuta ngrok

```bash
ngrok http 8001
```

### 4. Copia la URL

ngrok mostrará algo como:

```
Session Status                online
Account                       tu-email@example.com
Version                       3.x.x
Region                        United States (us)
Latency                       -
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok-free.app -> http://localhost:8001

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**La URL que necesitas es:** `https://abc123.ngrok-free.app`

### 5. Comparte esa URL

Esa es la URL que compartes con otros. Pueden abrirla directamente en su navegador.

---

## Notas

- ✅ Mantén ambas terminales abiertas (la app y ngrok)
- ✅ La URL funciona mientras ambas estén corriendo
- ✅ Si cierras ngrok, la URL deja de funcionar
- ✅ Si reinicias ngrok, obtendrás una URL diferente (plan gratis)

---

## Verificar que Funciona

1. Abre tu navegador
2. Ve a: `https://abc123.ngrok-free.app` (tu URL de ngrok)
3. Deberías ver tu aplicación funcionando

---

¡Listo! Ya puedes compartir esa URL.

