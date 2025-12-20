# Acceso Remoto a la Base de Datos

Si tienes Docker corriendo en tu laptop y quieres que alguien en otra máquina pueda usar la aplicación, necesitas configurar el acceso remoto a PostgreSQL.

## ⚠️ Advertencia de Seguridad

**Exponer PostgreSQL directamente a internet NO es recomendado para producción.** Usa estas opciones solo para desarrollo/testing.

---

## Opción 1: Exponer Puerto de PostgreSQL (Solo Red Local) 🔒

### Modificar docker-compose.yml

Cambia el binding del puerto para que escuche en todas las interfaces de red:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: bibliografia_postgres
    environment:
      POSTGRES_USER: bibliografia_user
      POSTGRES_PASSWORD: bibliografia_pass
      POSTGRES_DB: bibliografia_db
    ports:
      - "0.0.0.0:5432:5432"  # Escucha en todas las interfaces
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bibliografia_user"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
```

### Configurar PostgreSQL para aceptar conexiones remotas

1. **Editar `pg_hba.conf`** (dentro del contenedor):

```bash
# Entrar al contenedor
docker exec -it bibliografia_postgres bash

# Editar pg_hba.conf
echo "host    all             all             0.0.0.0/0               md5" >> /var/lib/postgresql/data/pg_hba.conf

# Editar postgresql.conf
echo "listen_addresses = '*'" >> /var/lib/postgresql/data/postgresql.conf

# Reiniciar PostgreSQL
exit
docker restart bibliografia_postgres
```

O más fácil, crea un archivo `init-pg.sh`:

```bash
#!/bin/bash
# init-pg.sh
echo "host    all             all             0.0.0.0/0               md5" >> /var/lib/postgresql/data/pg_hba.conf
echo "listen_addresses = '*'" >> /var/lib/postgresql/data/postgresql.conf
```

Y agrégalo al docker-compose.yml:

```yaml
services:
  postgres:
    # ... otras configuraciones
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-pg.sh:/docker-entrypoint-initdb.d/init-pg.sh
```

### Obtener tu IP local

```bash
# Windows
ipconfig
# Busca "IPv4 Address" (ej: 192.168.1.100)

# Linux/Mac
ifconfig
# o
ip addr show
```

### Configurar en la otra máquina

La otra persona debe configurar su `.env` con:

```bash
DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@TU_IP_LOCAL:5432/bibliografia_db
```

**Reemplaza `TU_IP_LOCAL` con tu IP (ej: 192.168.1.100)**

### ⚠️ Limitaciones

- Solo funciona en la misma red local (WiFi/LAN)
- No funciona si estás en redes diferentes
- Requiere que el firewall permita conexiones en el puerto 5432

---

## Opción 2: Túnel SSH (Recomendado) 🔐

La forma más segura de permitir acceso remoto.

### En tu laptop (servidor SSH):

1. **Asegúrate de tener SSH habilitado** (Windows: OpenSSH Server, Linux/Mac: ya viene)

2. **Crear túnel SSH** (la otra persona ejecuta esto):

```bash
ssh -L 5432:localhost:5432 usuario@TU_IP_PUBLICA
```

O si estás en la misma red local:

```bash
ssh -L 5432:localhost:5432 usuario@TU_IP_LOCAL
```

### En la otra máquina:

Una vez conectado por SSH, puede usar:

```bash
DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@localhost:5432/bibliografia_db
```

**Nota**: El túnel SSH redirige `localhost:5432` en su máquina a `localhost:5432` en tu máquina.

### Ventajas:
- ✅ Seguro (cifrado SSH)
- ✅ Funciona desde cualquier lugar
- ✅ No expone PostgreSQL directamente

### Desventajas:
- ⚠️ Requiere que tu laptop esté encendido y accesible
- ⚠️ Necesitas IP pública o estar en la misma red

---

## Opción 3: ngrok (Fácil pero Temporal) 🌐

ngrok crea un túnel público temporal.

### Instalar ngrok

```bash
# Descargar desde: https://ngrok.com/download
# O con chocolatey (Windows)
choco install ngrok

# O con brew (Mac)
brew install ngrok
```

### Crear túnel

```bash
ngrok tcp 5432
```

Esto te dará algo como:

```
Forwarding  tcp://0.tcp.ngrok.io:12345 -> localhost:5432
```

### Configurar en la otra máquina

```bash
DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@0.tcp.ngrok.io:12345/bibliografia_db
```

### ⚠️ Limitaciones

- La URL cambia cada vez que reinicias ngrok (a menos que tengas cuenta paga)
- No es para producción
- Puede tener límites de ancho de banda

---

## Opción 4: Mover Base de Datos a la Nube ☁️

La mejor opción para acceso remoto permanente.

### Opciones:

1. **Railway/Render** (PostgreSQL gratuito)
2. **AWS RDS** (db.t3.micro ~$15/mes)
3. **Supabase** (PostgreSQL gratuito)
4. **Neon** (PostgreSQL serverless)

### Ejemplo con Supabase (Gratis):

1. Crear cuenta en https://supabase.com
2. Crear nuevo proyecto
3. Obtener connection string
4. Configurar en ambas máquinas:

```bash
DATABASE_URL=postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres
```

**Ventajas:**
- ✅ Accesible desde cualquier lugar
- ✅ Siempre disponible
- ✅ Backups automáticos
- ✅ Muchas opciones gratuitas

---

## Opción 5: VPN (Para Equipos) 🔒

Si trabajas en un equipo, usar una VPN es la mejor opción.

### Opciones:

- **Tailscale** (fácil, gratis para uso personal)
- **ZeroTier** (gratis)
- **WireGuard** (open source)

Una vez en la VPN, todos pueden acceder como si estuvieran en la misma red local.

---

## Comparación Rápida

| Opción | Seguridad | Facilidad | Costo | Acceso |
|--------|-----------|-----------|-------|--------|
| **Red Local** | ⚠️ Media | ✅ Fácil | Gratis | Solo misma red |
| **SSH Tunnel** | ✅ Alta | ⚠️ Media | Gratis | Cualquier lugar |
| **ngrok** | ⚠️ Media | ✅ Fácil | Gratis* | Cualquier lugar |
| **Nube** | ✅ Alta | ✅ Fácil | Gratis-$15/mes | Cualquier lugar |
| **VPN** | ✅ Alta | ⚠️ Media | Gratis | Cualquier lugar |

---

## Recomendación

### Para Desarrollo/Testing:
- **Misma red local**: Opción 1 (exponer puerto)
- **Redes diferentes**: Opción 2 (SSH) o Opción 3 (ngrok)

### Para Producción/Uso Continuo:
- **Opción 4**: Mover a la nube (Supabase, Railway, etc.)

---

## Ejemplo Completo: Configurar Acceso Local

### 1. Modificar docker-compose.yml

```yaml
ports:
  - "0.0.0.0:5432:5432"  # Cambiar esto
```

### 2. Reiniciar Docker

```bash
docker-compose down
docker-compose up -d
```

### 3. Configurar PostgreSQL (una vez)

```bash
docker exec -it bibliografia_postgres bash
echo "host    all             all             0.0.0.0/0               md5" >> /var/lib/postgresql/data/pg_hba.conf
echo "listen_addresses = '*'" >> /var/lib/postgresql/data/postgresql.conf
exit
docker restart bibliografia_postgres
```

### 4. Obtener tu IP

```bash
# Windows
ipconfig | findstr IPv4

# Linux/Mac
hostname -I
```

### 5. Compartir configuración

La otra persona usa en su `.env`:

```bash
DATABASE_URL=postgresql://bibliografia_user:bibliografia_pass@192.168.1.100:5432/bibliografia_db
```

---

## Troubleshooting

### Error: "Connection refused"
- Verifica que el puerto esté expuesto: `docker ps`
- Verifica firewall: permite conexiones en puerto 5432
- Verifica que estén en la misma red

### Error: "Password authentication failed"
- Verifica usuario/contraseña en docker-compose.yml
- Verifica que `pg_hba.conf` permita conexiones remotas

### Error: "Connection timeout"
- Verifica que tu IP sea accesible desde la otra máquina
- Prueba hacer ping: `ping TU_IP`
- Verifica firewall de Windows/Linux

---

¿Necesitas ayuda configurando alguna de estas opciones?

