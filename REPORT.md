# 🔒 INFORME DE AUDITORÍA DE SEGURIDAD — BJJ-BetSports

> **Fecha de Auditoría**: 2026-04-14
> **Auditor**: Copilot Security Audit Agent (Senior Cybersecurity)
> **Alcance**: Repositorio completo (`backend/`, `frontend/`, infraestructura, CI/CD)
> **Estado**: ⚠️ Requiere acción inmediata en vulnerabilidades críticas

---

## 📋 RESUMEN EJECUTIVO

Se identificaron **48 hallazgos de seguridad** distribuidos en:

| Severidad | Cantidad | Descripción |
|-----------|----------|-------------|
| 🔴 **CRÍTICA** | 8 | Requieren corrección inmediata (< 24h) |
| 🟠 **ALTA** | 18 | Corrección urgente (esta semana) |
| 🟡 **MEDIA** | 14 | Planificar para siguiente sprint |
| 🟢 **BAJA** | 8 | Mejoras recomendables a mediano plazo |

### Áreas Más Afectadas
1. **Dependencias npm** — 18 paquetes con vulnerabilidades conocidas (CVEs activos)
2. **Backend Python** — CORS inseguro, credenciales hardcodeadas, inyección NoSQL
3. **Infraestructura Docker** — Contenedores ejecutándose como root, credenciales en docker-compose
4. **Configuración de seguridad** — Falta CSP, headers de seguridad, cifrado en localStorage

---

## 🔴 VULNERABILIDADES CRÍTICAS

### CRIT-01 · Fallback CORS a Wildcard `["*"]` con Credenciales

- **Archivo**: `backend/src/api/main.py` (líneas 36-47)
- **CVE/CWE**: CWE-942 (Permissive CORS Policy)
- **Descripción**: Si la variable `CORS_ORIGINS` está vacía o no configurada, el middleware CORS usa `["*"]` como fallback combinado con `allow_credentials=True` y `allow_methods=["*"]`. Esto permite a cualquier dominio malicioso realizar solicitudes autenticadas a la API.
- **Impacto**: CSRF, acceso no autorizado a datos, explotación completa de la API desde cualquier origen.
- **Código vulnerable**:

```python
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],  # ⚠️ Fallback peligroso
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- **Acción requerida**:

```
TAREA: Eliminar fallback CORS a wildcard
ARCHIVO: backend/src/api/main.py
CAMBIOS:
  1. Eliminar `or ["*"]` del parámetro allow_origins
  2. Lanzar ValueError si cors_origins está vacío (forzar configuración explícita)
  3. Cambiar allow_methods de ["*"] a lista explícita: ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
  4. Cambiar allow_headers de ["*"] a lista explícita: ["Content-Type", "Authorization", "X-API-Key"]
PRIORIDAD: Inmediata
```

---

### CRIT-02 · Credenciales MongoDB Hardcodeadas en Código Fuente

- **Archivo**: `backend/src/infrastructure/repositories/mongo_repository.py` (líneas 37-39)
- **CVE/CWE**: CWE-798 (Hardcoded Credentials)
- **Descripción**: La URI de conexión a MongoDB incluye credenciales por defecto `admin:adminpassword` como valor de respaldo si no existe la variable de entorno.
- **Impacto**: Acceso no autorizado a la base de datos, fuga de datos, manipulación de registros.
- **Código vulnerable**:

```python
mongo_uri = os.getenv(
    "MONGO_URI", "mongodb://admin:adminpassword@localhost:27017/"
)
```

- **Acción requerida**:

```
TAREA: Eliminar credenciales hardcodeadas de MongoDB
ARCHIVO: backend/src/infrastructure/repositories/mongo_repository.py
CAMBIOS:
  1. Eliminar el valor por defecto con credenciales del os.getenv()
  2. Lanzar ValueError("MONGO_URI debe estar configurado") si la variable no existe
  3. Verificar que .env.example documente el formato esperado sin credenciales reales
  4. Auditar git history para verificar que no se hayan committeado credenciales reales
PRIORIDAD: Inmediata
```

---

### CRIT-03 · Token de GitHub Expuesto en Argumentos de Subprocess

- **Archivo**: `backend/src/infrastructure/services/github_exporter.py` (líneas 71, 126)
- **CVE/CWE**: CWE-214 (Invocation of Process Using Visible Sensitive Information)
- **Descripción**: El token de GitHub se embebe directamente en la URL del repositorio pasada a `subprocess.run()`. El token es visible en la tabla de procesos (`ps`), `/proc/`, logs de error del subprocess, y herramientas de inspección de contenedores Docker.
- **Impacto**: Compromiso del repositorio GitHub, commits no autorizados, escalamiento de privilegios.
- **Código vulnerable**:

```python
repo_url = f"https://{self.github_token}@github.com/{self.github_repo}.git"
subprocess.run(["git", "clone", repo_url, self.local_repo_path], ...)
subprocess.run(["git", "-C", self.local_repo_path, "push", repo_url, "main"], ...)
```

- **Acción requerida**:

```
TAREA: Usar Git credential helper en lugar de embeber token en URL
ARCHIVO: backend/src/infrastructure/services/github_exporter.py
CAMBIOS:
  1. Reemplazar URL con token embebido por URL sin credenciales
  2. Pasar token vía variable de entorno GIT_ASKPASS o ~/.git-credentials con permisos 0600
  3. Alternativa: usar env dict en subprocess.run() con GIT_USERNAME y GIT_PASSWORD
  4. Asegurar que capture_output=True para no exponer en stdout
EJEMPLO:
  env = {**os.environ, "GIT_ASKPASS": "/path/to/askpass_script"}
  subprocess.run(["git", "clone", url_sin_token, path], env=env, check=True, capture_output=True)
PRIORIDAD: Inmediata
```

---

### CRIT-04 · Deserialización Insegura con Joblib (Ejecución Arbitraria de Código)

- **Archivos**:
  - `backend/src/domain/services/picks_service.py` (líneas 143-148)
  - `backend/src/domain/services/prediction_service.py`
- **CVE/CWE**: CWE-502 (Deserialization of Untrusted Data)
- **Descripción**: Se usa `joblib.load()` para cargar modelos ML sin verificación de integridad ni restricción de fuentes. Joblib usa pickle internamente, que puede ejecutar código Python arbitrario durante la deserialización.
- **Impacto**: Ejecución Remota de Código (RCE), compromiso completo del sistema.
- **Código vulnerable**:

```python
model = joblib.load(model_path)  # Sin verificación de integridad
```

- **Acción requerida**:

```
TAREA: Agregar verificación de integridad criptográfica a la carga de modelos
ARCHIVOS: backend/src/domain/services/picks_service.py, prediction_service.py
CAMBIOS:
  1. Crear función load_model_safely(path, expected_hash) que:
     a. Calcule SHA-256 del archivo antes de cargarlo
     b. Compare contra hash conocido almacenado en variable de entorno o archivo de manifiesto
     c. Verifique permisos del archivo (no world-writable)
     d. Solo entonces ejecute joblib.load()
  2. Crear archivo model_manifest.json con hashes SHA-256 de modelos válidos
  3. Verificar ownership del archivo (debe pertenecer al usuario de la app)
  4. Considerar migrar a formato ONNX o safetensors a largo plazo
PRIORIDAD: Inmediata
```

---

### CRIT-05 · Credenciales Hardcodeadas en Docker Compose

- **Archivos**:
  - `docker-compose.dev.yml` (líneas 16-17, 37, 79, 100, 120)
  - `docker-compose.labeler.yml` (línea 10)
- **CVE/CWE**: CWE-798 (Hardcoded Credentials)
- **Descripción**: Credenciales de MongoDB en texto plano en archivos docker-compose:
  - `MONGO_INITDB_ROOT_PASSWORD: adminpassword`
  - `MONGO_URI: "mongodb://admin:adminpassword@mongodb:27017/"` (repetido en 5 servicios)
- **Impacto**: Si estos archivos se comparten o exponen, todas las instancias MongoDB quedan comprometidas.

- **Acción requerida**:

```
TAREA: Externalizar credenciales de Docker Compose a archivo .env
ARCHIVOS: docker-compose.dev.yml, docker-compose.labeler.yml
CAMBIOS:
  1. Reemplazar valores hardcodeados por variables de entorno:
     MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD:-cambiar_en_env}
     MONGO_URI: "mongodb://admin:${MONGO_PASSWORD}@mongodb:27017/"
  2. Crear .env.docker.example con las variables requeridas
  3. Agregar .env.docker a .gitignore
  4. Documentar en README.md el setup inicial de credenciales
PRIORIDAD: Inmediata
```

---

### CRIT-06 · Contenedores Docker Ejecutándose como Root

- **Archivos**:
  - `Dockerfile.portable` (sin directiva USER)
  - `backend/Dockerfile` (sin directiva USER)
- **CVE/CWE**: CWE-250 (Execution with Unnecessary Privileges)
- **Descripción**: Ambos Dockerfiles carecen de directiva `USER` y ejecutan todos los procesos como root (UID 0). Si el contenedor es comprometido, el atacante tiene acceso total al sistema.
- **Impacto**: Escalamiento de privilegios, escritura en sistema host, escape de contenedor facilitado.

- **Acción requerida**:

```
TAREA: Agregar usuario no-root a Dockerfiles
ARCHIVOS: Dockerfile.portable, backend/Dockerfile
CAMBIOS:
  1. Agregar antes del CMD final:
     RUN useradd -m -u 1000 -s /bin/bash appuser
     USER appuser
  2. Ajustar permisos de directorios de trabajo (chown appuser)
  3. Verificar que la aplicación funcione con usuario no-root
  4. Implementar multi-stage build para reducir superficie de ataque
PRIORIDAD: Inmediata
```

---

### CRIT-07 · Axios con Vulnerabilidades Críticas (CVEs Activos)

- **Archivo**: `frontend/package.json` (línea 19) — `axios@^1.7.9`
- **CVEs**:
  - GHSA-43fc-jf86-j433 (DoS vía `__proto__` en mergeConfig)
  - GHSA-3p68-rc4w-qgx5 (SSRF por bypass de NO_PROXY)
  - GHSA-fvcv-3m26-pcqx (Exfiltración de metadata cloud vía inyección de headers)
- **Impacto**: DoS, SSRF a red interna, exfiltración de credenciales cloud (AWS/GCP metadata).

- **Acción requerida**:

```
TAREA: Actualizar axios a versión segura
ARCHIVO: frontend/package.json
CAMBIOS:
  1. Ejecutar: cd frontend && npm install axios@latest --save
  2. Verificar que axios >= 1.8.0 (que corrige los 3 CVEs)
  3. Ejecutar npm audit fix para resolver dependencias transitivas
  4. Verificar que no hay breaking changes en la API de axios usada
PRIORIDAD: Inmediata
```

---

### CRIT-08 · Ejecución Arbitraria de Código vía Script Piped desde Internet

- **Archivo**: `scripts/local_checks.sh` (líneas 36, 38)
- **CVE/CWE**: CWE-829 (Inclusion of Functionality from Untrusted Control Sphere)
- **Descripción**: Se descarga y ejecuta un script bash directamente desde GitHub sin verificación de integridad:

```bash
curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash || true
wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash || true
```

- **Impacto**: Un ataque MITM o compromiso de GitHub podría inyectar código malicioso.

- **Acción requerida**:

```
TAREA: Verificar integridad de scripts descargados
ARCHIVO: scripts/local_checks.sh
CAMBIOS:
  1. Descargar script a archivo temporal
  2. Verificar checksum SHA-256 contra valor conocido antes de ejecutar
  3. Eliminar || true que suprime errores
  4. Alternativa: usar gestor de paquetes del sistema (apt/brew install nvm)
PRIORIDAD: Alta
```

---

## 🟠 VULNERABILIDADES ALTAS

### ALTA-01 · Comparación de API Key Vulnerable a Timing Attacks

- **Archivo**: `backend/src/api/security.py` (líneas 16-31)
- **CWE**: CWE-208 (Observable Timing Discrepancy)
- **Descripción**: La comparación de la API key admin usa `!=` (comparación de strings estándar), que es vulnerable a ataques de temporización. Un atacante puede deducir la clave carácter por carácter midiendo tiempos de respuesta.

- **Acción requerida**:

```
TAREA: Usar comparación en tiempo constante para API keys
ARCHIVO: backend/src/api/security.py
CAMBIOS:
  1. Importar: from hmac import compare_digest
  2. Reemplazar: if api_key != _ADMIN_API_KEY → if not compare_digest(api_key or "", _ADMIN_API_KEY)
  3. Agregar rate limiting agresivo (máx 5 intentos/minuto) a la validación de key
PRIORIDAD: Urgente
```

---

### ALTA-02 · URL de Base de Datos Expuesta en Logs de Error

- **Archivo**: `backend/src/infrastructure/database/database_service.py` (líneas 59-60, 66-71)
- **CWE**: CWE-532 (Insertion of Sensitive Information into Log File)
- **Descripción**: La URL completa de la base de datos (que puede contener contraseña) se registra en logs de error. Los logs suelen enviarse a servicios de agregación (DataDog, ELK, CloudWatch).

- **Acción requerida**:

```
TAREA: Enmascarar credenciales en logs de conexión a DB
ARCHIVO: backend/src/infrastructure/database/database_service.py
CAMBIOS:
  1. Crear función _mask_connection_string(db_url) que extraiga solo host:port
  2. Reemplazar logging de self.db_url por versión enmascarada
  3. Aplicar el mismo patrón a todos los loggers que manejen URIs de conexión
PRIORIDAD: Urgente
```

---

### ALTA-03 · Inyección NoSQL vía Regex en MongoDB

- **Archivo**: `backend/src/infrastructure/repositories/mongo_repository.py` (líneas 86-90)
- **CWE**: CWE-943 (Improper Neutralization of Special Elements in Data Query Logic)
- **Descripción**: El parámetro `pattern` del usuario se interpola directamente en una expresión regular de MongoDB sin escapar metacaracteres. Un atacante puede usar `.*`, `|`, `()` para evadir filtros.

- **Acción requerida**:

```
TAREA: Escapar metacaracteres regex en consultas MongoDB
ARCHIVO: backend/src/infrastructure/repositories/mongo_repository.py
CAMBIOS:
  1. Importar: import re
  2. Antes de construir el regex, aplicar: escaped = re.escape(pattern).replace("\\%", ".*")
  3. Envolver en try/except para capturar regex inválidos
  4. Considerar usar operadores MongoDB nativos en lugar de $regex donde sea posible
PRIORIDAD: Urgente
```

---

### ALTA-04 · Variables de Entorno Sin Validar en Subprocess

- **Archivo**: `backend/src/api/main.py` (líneas 170-205)
- **CWE**: CWE-20 (Improper Input Validation)
- **Descripción**: Variables de entorno `N_JOBS`, `TRAIN_DAYS`, `PREDICT_LEAGUES` se pasan directamente como argumentos de subprocess sin validación de tipo ni rango.

- **Acción requerida**:

```
TAREA: Validar variables de entorno usadas en subprocess
ARCHIVO: backend/src/api/main.py
CAMBIOS:
  1. Crear funciones de validación: validate_int_env(key, default, min, max) y validate_leagues_env(key, default)
  2. N_JOBS: validar como entero entre 1 y 64
  3. TRAIN_DAYS: validar como entero entre 1 y 3650
  4. PREDICT_LEAGUES: validar con regex ^[A-Z0-9,]+$ (solo letras mayúsculas, números y comas)
PRIORIDAD: Urgente
```

---

### ALTA-05 · Versiones Inconsistentes entre requirements.txt y requirements-worker.txt

- **Archivos**: `backend/requirements.txt`, `backend/requirements-worker.txt`
- **CWE**: CWE-1104 (Use of Unmaintained Third Party Components)
- **Paquetes afectados**:

| Paquete | requirements.txt | requirements-worker.txt |
|---------|-----------------|------------------------|
| pydantic | 2.12.5 | 2.7.4 |
| aiohttp | 3.13.2 | 3.9.5 |
| httpx | 0.26.0 | 0.27.0 |
| python-dotenv | 1.0.0 | 1.0.1 |

- **Acción requerida**:

```
TAREA: Alinear versiones de dependencias entre archivos requirements
ARCHIVOS: backend/requirements.txt, backend/requirements-worker.txt
CAMBIOS:
  1. Unificar todas las versiones al mayor valor disponible
  2. Verificar compatibilidad de APIs entre versiones
  3. Considerar usar un archivo base requirements-common.txt e importar con -r
  4. Fijar versión de orjson (actualmente sin versión fija — riesgo de supply chain)
PRIORIDAD: Urgente
```

---

### ALTA-06 · Paquete `orjson` sin Versión Fija (Riesgo de Supply Chain)

- **Archivo**: `backend/requirements.txt` (línea 32), `backend/requirements-worker.txt`
- **CWE**: CWE-1357 (Reliance on Insufficiently Trustworthy Component)
- **Descripción**: `orjson` no tiene versión fijada (`==`), permitiendo que cualquier versión sea instalada, incluyendo versiones maliciosas.

- **Acción requerida**:

```
TAREA: Fijar versión exacta de orjson
ARCHIVOS: backend/requirements.txt, backend/requirements-worker.txt
CAMBIOS:
  1. Investigar versión actual en uso: pip show orjson
  2. Fijar con ==: orjson==3.10.14 (o la versión actual estable)
  3. Auditar todas las dependencias sin versión fija en ambos archivos
PRIORIDAD: Urgente
```

---

### ALTA-07 · React Router con Múltiples CVEs (XSS, CSRF)

- **Archivo**: `frontend/package.json` — `react-router-dom@^7.11.0`
- **CVEs**:
  - GHSA-2w69-qvjg-hvjx (XSS vía Open Redirects)
  - GHSA-h5cw-625j-3rxh (CSRF en Actions)
  - GHSA-8v8x-cx79-35w7 (XSS en SSR ScrollRestoration)

- **Acción requerida**:

```
TAREA: Actualizar react-router-dom a versión parcheada
ARCHIVO: frontend/package.json
CAMBIOS:
  1. Ejecutar: cd frontend && npm install react-router-dom@latest --save
  2. Verificar compatibilidad con rutas existentes en App.tsx
  3. Ejecutar npm audit para confirmar resolución
PRIORIDAD: Urgente
```

---

### ALTA-08 · Vite con Vulnerabilidades de Path Traversal

- **Archivo**: `frontend/package.json` — `vite@^7.3.0`
- **CVEs**:
  - GHSA-4w7w-66w2-5vf9 (Path Traversal en manejo de .map)
  - GHSA-v2wj-q39q-566r (Bypass de server.fs.deny con queries)
  - GHSA-p9ff-h696-f583 (Lectura arbitraria de archivos vía WebSocket)

- **Acción requerida**:

```
TAREA: Actualizar vite a versión parcheada
ARCHIVO: frontend/package.json
CAMBIOS:
  1. Ejecutar: cd frontend && npm install vite@latest --save-dev
  2. Verificar que vite >= 7.4.0
  3. Revisar configuración de server.fs.deny en vite.config.ts
PRIORIDAD: Urgente
```

---

### ALTA-09 · Serialize-JavaScript con RCE (Dependencia Transitiva)

- **Origen**: Dependencia transitiva vía `vite-plugin-pwa`
- **CVEs**:
  - GHSA-5c6j-r48x-rmvq (RCE vía RegExp.flags)
  - GHSA-qj8w-gfj5-8c6v (DoS por CPU Exhaustion)

- **Acción requerida**:

```
TAREA: Actualizar dependencias transitivas de vite-plugin-pwa
ARCHIVO: frontend/package.json
CAMBIOS:
  1. Ejecutar: cd frontend && npm install vite-plugin-pwa@latest --save-dev
  2. Forzar actualización: npm install serialize-javascript@latest --save-dev
  3. Ejecutar npm audit fix --force si es necesario
PRIORIDAD: Urgente
```

---

### ALTA-10 · Lodash con Prototype Pollution (CVEs Activos)

- **CVEs**:
  - GHSA-xxjr-mmjv-4gpg (Prototype Pollution en `_.unset` y `_.omit`)
  - GHSA-r5fr-rjxr-66jc (Code Injection vía `_.template`)
  - GHSA-f23m-r3pf-42rh (Array path bypass)

- **Acción requerida**:

```
TAREA: Actualizar lodash y evaluar reemplazo
ARCHIVO: frontend/package.json (dependencia transitiva)
CAMBIOS:
  1. Ejecutar: cd frontend && npm install lodash@latest
  2. Evaluar reemplazo por lodash-es o funciones nativas de ES2024
  3. Si es dependencia transitiva: npm audit fix
PRIORIDAD: Urgente
```

---

### ALTA-11 · Fallback HTTP Inseguro en Configuración de API

- **Archivos**:
  - `frontend/src/infrastructure/api/client.ts` (línea 4)
  - `frontend/src/infrastructure/api/analytics.ts` (línea 1)
  - `frontend/vite.config.ts` (línea 93)
- **CWE**: CWE-319 (Cleartext Transmission of Sensitive Information)
- **Descripción**: Los fallbacks usan `http://localhost:8000` en lugar de `https://`. En producción esto puede filtrarse si las variables de entorno no están configuradas.

- **Acción requerida**:

```
TAREA: Asegurar HTTPS en todos los fallbacks de URL de API
ARCHIVOS: frontend/src/infrastructure/api/client.ts, analytics.ts, vite.config.ts
CAMBIOS:
  1. Cambiar http:// a https:// en todos los fallbacks de URL
  2. En producción, lanzar error si VITE_API_URL no está definido
  3. Agregar validación de protocolo al crear el cliente axios
PRIORIDAD: Urgente
```

---

### ALTA-12 · Falta Content Security Policy (CSP)

- **Archivo**: `frontend/index.html`
- **CWE**: CWE-1021 (Improper Restriction of Rendered UI Layers)
- **Descripción**: No hay meta tag de Content Security Policy, permitiendo carga de scripts/estilos desde cualquier origen.

- **Acción requerida**:

```
TAREA: Agregar Content Security Policy a index.html
ARCHIVO: frontend/index.html
CAMBIOS:
  1. Agregar meta tag CSP con directivas:
     default-src 'self'
     script-src 'self' 'unsafe-inline' (minimizar unsafe-inline progresivamente)
     style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com
     img-src 'self' https: data:
     font-src 'self' https://fonts.gstatic.com
     connect-src 'self' [URL_API_PRODUCCION] https://site.api.espn.com
     frame-ancestors 'none'
     base-uri 'self'
     form-action 'self'
PRIORIDAD: Urgente
```

---

### ALTA-13 · Headers de Seguridad HTTP Faltantes

- **CWE**: CWE-693 (Protection Mechanism Failure)
- **Descripción**: No se configuran headers de seguridad HTTP a nivel de servidor/proxy.

- **Acción requerida**:

```
TAREA: Configurar headers de seguridad HTTP en el servidor
ARCHIVOS: render.yaml o configuración de proxy reverso
CAMBIOS:
  Agregar los siguientes headers en respuestas HTTP:
  1. Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
  2. X-Content-Type-Options: nosniff
  3. X-Frame-Options: DENY
  4. X-XSS-Protection: 1; mode=block
  5. Referrer-Policy: strict-origin-when-cross-origin
  6. Permissions-Policy: geolocation=(), microphone=(), camera=()
PRIORIDAD: Urgente
```

---

### ALTA-14 · Datos Sensibles en localStorage sin Cifrar

- **Archivos**:
  - `frontend/src/application/stores/useParleyStore.ts` (línea 70)
  - `frontend/src/infrastructure/storage/LocalStorageObserver.ts` (líneas 97-98)
- **CWE**: CWE-922 (Insecure Storage of Sensitive Information)
- **Descripción**: Los datos de estado de la aplicación se persisten en localStorage como JSON plano, accesible por XSS y extensiones de navegador.

- **Acción requerida**:

```
TAREA: Cifrar datos sensibles en localStorage
ARCHIVOS: frontend/src/application/stores/useParleyStore.ts, LocalStorageObserver.ts
CAMBIOS:
  1. Crear wrapper de localStorage que cifre/descifre datos con AES-256
  2. Usar clave de cifrado derivada de VITE_ENCRYPTION_KEY
  3. Aplicar a todas las stores de Zustand con persistencia
  4. Para datos de sesión, preferir httpOnly cookies
PRIORIDAD: Urgente
```

---

### ALTA-15 · Puerto MongoDB Expuesto a Todas las Interfaces

- **Archivo**: `docker-compose.dev.yml` (línea 20)
- **CWE**: CWE-668 (Exposure of Resource to Wrong Sphere)
- **Descripción**: `ports: "27017:27017"` expone MongoDB a `0.0.0.0` (todas las interfaces de red).

- **Acción requerida**:

```
TAREA: Restringir acceso MongoDB a localhost
ARCHIVO: docker-compose.dev.yml
CAMBIOS:
  1. Cambiar: "27017:27017" → "127.0.0.1:27017:27017"
  2. Agregar red dedicada para servicios backend
PRIORIDAD: Urgente
```

---

### ALTA-16 · Flag --break-system-packages en pip (Docker)

- **Archivo**: `Dockerfile.portable` (líneas 23-24)
- **CWE**: CWE-1104
- **Descripción**: Uso de `--break-system-packages` que bypasea protecciones de Python PEP 668.

- **Acción requerida**:

```
TAREA: Usar virtualenv en lugar de --break-system-packages
ARCHIVO: Dockerfile.portable
CAMBIOS:
  1. Agregar: RUN python3 -m venv /opt/venv
  2. Agregar: ENV PATH="/opt/venv/bin:$PATH"
  3. Instalar dependencias en el venv sin --break-system-packages
  4. Implementar multi-stage build
PRIORIDAD: Urgente
```

---

### ALTA-17 · Sin Aislamiento de Red en Docker Compose

- **Archivo**: `docker-compose.dev.yml` (todo el archivo)
- **CWE**: CWE-668 (Exposure of Resource to Wrong Sphere)
- **Descripción**: Todos los servicios usan la red bridge por defecto sin segmentación. El worker ML puede acceder directamente a endpoints de la API.

- **Acción requerida**:

```
TAREA: Implementar segmentación de red en Docker Compose
ARCHIVO: docker-compose.dev.yml
CAMBIOS:
  1. Definir redes: frontend, backend, database
  2. Asignar servicios solo a las redes necesarias
  3. MongoDB solo en red database
  4. Frontend solo en red frontend y backend
  5. ML worker solo en red backend y database
PRIORIDAD: Urgente
```

---

### ALTA-18 · Múltiples Paquetes npm con ReDoS y DoS

- **Paquetes afectados**: minimatch, picomatch, flatted, brace-expansion, @isaacs/brace-expansion, ajv
- **Tipo**: ReDoS (Regular Expression Denial of Service), Prototype Pollution

- **Acción requerida**:

```
TAREA: Ejecutar npm audit fix completo
ARCHIVO: frontend/
CAMBIOS:
  1. cd frontend && npm audit fix
  2. Si quedan vulnerabilidades: npm audit fix --force
  3. Verificar que la app compila y funciona tras las actualizaciones
  4. Documentar paquetes que no pudieron actualizarse y razón
PRIORIDAD: Urgente
```

---

## 🟡 VULNERABILIDADES MEDIAS

### MEDIA-01 · Validación de Input Insuficiente en Parámetro de Fecha

- **Archivo**: `backend/src/api/routers/matches.py` (líneas 79-85)
- **Descripción**: El manejador de excepciones es demasiado amplio (`Exception`), sin validación de longitud ni rango de año. `league_id` no tiene validación alguna.

```
TAREA: Agregar validación estricta de parámetros de entrada
ARCHIVO: backend/src/api/routers/matches.py
CAMBIOS:
  1. Validar longitud de date (máx 10 caracteres)
  2. Validar formato con regex antes de strptime
  3. Validar rango de año (1900-2100)
  4. Agregar whitelist de league_id válidos
  5. Cambiar except Exception por except ValueError
```

---

### MEDIA-02 · Uso de `datetime.utcnow()` Deprecado (Python 3.12+)

- **Archivos**:
  - `backend/src/domain/entities/suggested_pick.py`
  - `backend/src/domain/entities/betting_feedback.py`
- **Descripción**: `datetime.utcnow()` está deprecado desde Python 3.12 y retorna datetime naive (sin timezone).

```
TAREA: Reemplazar datetime.utcnow() por datetime.now(timezone.utc)
ARCHIVOS: Todos los archivos en backend/src/domain/entities/
CAMBIOS:
  1. Buscar todas las ocurrencias de datetime.utcnow()
  2. Reemplazar por datetime.now(timezone.utc)
  3. Importar timezone desde datetime
  4. Ajustar field(default_factory=) a usar lambda
```

---

### MEDIA-03 · Placeholder de API Key Admin Revela Formato

- **Archivo**: `backend/.env.example` (línea 64)
- **Descripción**: El valor ejemplo `cambiar-por-un-valor-aleatorio-seguro` revela que la key es un string simple.

```
TAREA: Mejorar guía de generación de API key en .env.example
ARCHIVO: backend/.env.example
CAMBIOS:
  1. Agregar comentario con comando para generar key segura:
     # Generar con: python -c "import secrets; print(secrets.token_urlsafe(32))"
  2. Cambiar placeholder por: ADMIN_API_KEY=<GENERAR_CON_COMANDO_ANTERIOR>
```

---

### MEDIA-04 · Pre-commit Hooks No Cubren Seguridad

- **Archivo**: `.pre-commit-config.yaml`
- **Descripción**: Faltan hooks de: escaneo de secretos, lint YAML, lint Docker, escaneo de vulnerabilidades.

```
TAREA: Agregar hooks de seguridad a pre-commit
ARCHIVO: .pre-commit-config.yaml
CAMBIOS:
  1. Agregar detect-secrets (Yelp/detect-secrets)
  2. Agregar yamllint
  3. Agregar hadolint para Dockerfiles
  4. Agregar bandit para análisis estático de seguridad Python
```

---

### MEDIA-05 · GitHub Actions Sin Permisos Mínimos Explícitos

- **Archivos**: `.github/workflows/*.yml`
- **Descripción**: Los workflows no definen bloque `permissions` con scopes mínimos. Si un commit malicioso ejecuta CI, podría exfiltrar secretos.

```
TAREA: Agregar permisos mínimos a todos los workflows de GitHub Actions
ARCHIVOS: .github/workflows/*.yml
CAMBIOS:
  1. Agregar permissions: contents: read a nivel global de cada workflow
  2. Solo agregar permisos adicionales donde sean explícitamente necesarios
  3. Revisar que setup-branch-protection.yml (que usa administration: write) sea el único con permisos elevados
```

---

### MEDIA-06 · Follow-redirects Filtra Headers de Autenticación

- **Origen**: Dependencia transitiva de axios
- **CVE**: GHSA-r4q5-vmmm-2653
- **Descripción**: Headers de autenticación personalizados se filtran a destinos de redireccionamiento cross-domain.

```
TAREA: Actualizar axios (que incluye follow-redirects actualizado)
ARCHIVO: frontend/package.json
CAMBIOS: Se resuelve al actualizar axios (ver CRIT-07)
```

---

### MEDIA-07 · Sin Lock Files para Dependencias Python

- **Descripción**: Solo existen `requirements.txt` con versiones fijadas, pero las dependencias transitivas no están bloqueadas.

```
TAREA: Implementar pip-compile para lock files
ARCHIVOS: backend/
CAMBIOS:
  1. Instalar pip-tools
  2. Generar requirements.lock desde requirements.txt
  3. En CI/CD, instalar desde .lock con --require-hashes
  4. Documentar flujo de actualización de dependencias
```

---

### MEDIA-08 · URLs Hardcodeadas con Riesgo de Subdomain Takeover

- **Archivo**: `render.yaml` (líneas 25, 40, 48)
- **Descripción**: URLs de subdominios Render hardcodeadas. Si el servicio se elimina/migra, el subdominio puede ser reclamado.

```
TAREA: Usar referencias dinámicas en render.yaml
ARCHIVO: render.yaml
CAMBIOS:
  1. Reemplazar URLs hardcodeadas por fromService references
  2. Marcar API keys como isSecret: true
```

---

### MEDIA-09 · Supresión de Errores con `|| true` en Scripts

- **Archivo**: `scripts/local_checks.sh` (líneas 83, 89, 96)
- **Descripción**: `|| true` silencia errores que podrían indicar problemas de seguridad.

```
TAREA: Reemplazar || true por manejo de errores explícito
ARCHIVO: scripts/local_checks.sh
CAMBIOS:
  1. Agregar set -euo pipefail al inicio del script
  2. Reemplazar || true por bloques if/then con mensajes descriptivos
  3. Solo mantener || true donde el fallo es esperado y documentado
```

---

### MEDIA-10 · Sin Validación de Input en Variables Docker

- **Archivo**: `backend/scripts/local_mlops_pipeline.sh` (líneas 4-6, 13-16)
- **Descripción**: Variables `TRAIN_DAYS`, `N_JOBS` se usan directamente en comandos Python sin validación de tipo.

```
TAREA: Agregar validación numérica a variables de entorno en scripts
ARCHIVO: backend/scripts/local_mlops_pipeline.sh
CAMBIOS:
  1. Validar con regex que TRAIN_DAYS y N_JOBS son numéricos
  2. Validar rangos razonables (máx 3650 días, máx 64 jobs)
  3. Salir con error si la validación falla
```

---

### MEDIA-11 · ESPN API sin Validación de Respuesta

- **Archivo**: `frontend/src/infrastructure/external/espn.ts`
- **Descripción**: Las respuestas de la API de ESPN se consumen sin validación de schema ni sanitización.

```
TAREA: Agregar validación de schema a respuestas de API externa
ARCHIVO: frontend/src/infrastructure/external/espn.ts
CAMBIOS:
  1. Definir schema Zod para respuestas esperadas de ESPN
  2. Parsear respuestas con safeParse antes de usarlas
  3. Manejar errores de parsing con fallback seguro
```

---

### MEDIA-12 · AJV con ReDoS (Dependencia Transitiva)

- **CVE**: GHSA-2g4f-4pwh-qvx6

```
TAREA: Actualizar ajv vía npm audit fix
CAMBIOS: Se resuelve con npm audit fix (ver ALTA-18)
```

---

### MEDIA-13 · YAML Stack Overflow (Dependencia Transitiva)

- **CVE**: GHSA-48c2-rrv3-qjmp

```
TAREA: Actualizar yaml vía npm audit fix
CAMBIOS: Se resuelve con npm audit fix (ver ALTA-18)
```

---

### MEDIA-14 · .dockerignore Incompleto

- **Archivo**: `.dockerignore`
- **Descripción**: Falta excluir: `.github/`, `docs/`, `specs/`, `tests/`, `learning_weights.json`, `triage-*.json`, `*.md`

```
TAREA: Ampliar .dockerignore con archivos sensibles
ARCHIVO: .dockerignore
CAMBIOS:
  1. Agregar: .github/, docs/, specs/, tests/
  2. Agregar: learning_weights.json, triage-*.json
  3. Agregar: *.md (excepto README necesarios), *.bak, *.tmp
```

---

## 🟢 VULNERABILIDADES BAJAS

### BAJA-01 · Sin Verificación de Build Output en Docker

- **Archivo**: `Dockerfile.portable` (línea 36)
- **Descripción**: `npm run build` podría fallar silenciosamente sin verificación de que dist/index.html existe.

```
TAREA: Agregar verificación post-build en Dockerfile
ARCHIVO: Dockerfile.portable
CAMBIOS: Agregar test -f /workspace/frontend/dist/index.html después de npm run build
```

---

### BAJA-02 · Archivos de Pesos ML y Triage en Repositorio Git

- **Archivos**: `learning_weights.json`, `triage-c901.json`, `triage-e402-f821.json`
- **Descripción**: Datos de entrenamiento y diagnóstico almacenados en Git. Deberían estar en almacenamiento externo cifrado.

```
TAREA: Mover archivos de pesos ML a almacenamiento externo
CAMBIOS:
  1. Migrar a cloud blob storage (S3/GCS) con cifrado at-rest
  2. Agregar al .gitignore
  3. Crear script de descarga segura para desarrollo local
```

---

### BAJA-03 · Sin Configuración de Rate Limiting en .env

- **Archivo**: `backend/.env.example`
- **Descripción**: No hay parámetros de rate limiting documentados en .env.

```
TAREA: Documentar parámetros de rate limiting en .env.example
ARCHIVO: backend/.env.example
CAMBIOS: Agregar RATE_LIMIT_ENABLED, RATE_LIMIT_REQUESTS_PER_MINUTE, RATE_LIMIT_ADMIN_REQUESTS_PER_MINUTE
```

---

### BAJA-04 · Falta Interceptor de Autenticación en Cliente Axios

- **Archivo**: `frontend/src/infrastructure/api/client.ts`
- **Descripción**: No hay mecanismo de autenticación implementado en el cliente HTTP.

```
TAREA: Agregar interceptor de autenticación al cliente axios
ARCHIVO: frontend/src/infrastructure/api/client.ts
CAMBIOS:
  1. Agregar request interceptor para inyectar Bearer token
  2. Agregar response interceptor para manejar 401 (redirect a login)
  3. Implementar withCredentials: true para enviar cookies
```

---

### BAJA-05 · No Hay Multi-stage Build en Dockerfiles

- **Archivos**: `Dockerfile.portable`, `backend/Dockerfile`
- **Descripción**: Builds de una sola etapa incluyen herramientas de compilación en la imagen final.

```
TAREA: Implementar multi-stage builds
ARCHIVOS: Dockerfile.portable, backend/Dockerfile
CAMBIOS:
  1. Separar en: stage builder (compilación) y stage runtime (solo binarios)
  2. COPY --from=builder solo los artefactos necesarios
  3. Reducir imagen final a -slim base
```

---

### BAJA-06 · pytest Desactualizado (7.x vs 8.x)

- **Archivo**: `backend/requirements.txt`
- **Descripción**: pytest 7.4.4 está desactualizado (actual: 8.x).

```
TAREA: Evaluar actualización de pytest a 8.x
ARCHIVO: backend/requirements.txt
CAMBIOS: Actualizar pytest==7.4.4 → pytest==8.x.x tras verificar compatibilidad
```

---

### BAJA-07 · Sin Cookie SameSite para Datos de Sesión

- **Descripción**: Se usa localStorage en lugar de httpOnly cookies con SameSite=Strict.

```
TAREA: Evaluar migración a httpOnly cookies para sesión
CAMBIOS: Configurar Set-Cookie con HttpOnly; Secure; SameSite=Strict desde el backend
```

---

### BAJA-08 · Sin Render Secret Management Explícito

- **Archivo**: `render.yaml` (líneas 16-19)
- **Descripción**: API keys sin flag `isSecret: true`.

```
TAREA: Marcar API keys como secrets en render.yaml
ARCHIVO: render.yaml
CAMBIOS: Agregar isSecret: true a FOOTBALL_DATA_ORG_KEY y THE_ODDS_API_KEY
```

---

## 📊 MATRIZ DE PRIORIZACIÓN

### Fase 1 — Inmediata (< 24 horas)
| ID | Vulnerabilidad | Esfuerzo |
|----|---------------|----------|
| CRIT-01 | CORS Wildcard Fallback | Bajo |
| CRIT-02 | Credenciales MongoDB Hardcodeadas | Bajo |
| CRIT-03 | Token GitHub en Subprocess | Medio |
| CRIT-05 | Credenciales Docker Compose | Bajo |
| CRIT-07 | Actualizar Axios | Bajo |

### Fase 2 — Urgente (Esta Semana)
| ID | Vulnerabilidad | Esfuerzo |
|----|---------------|----------|
| CRIT-04 | Deserialización Joblib Insegura | Medio |
| CRIT-06 | Docker como Root | Bajo |
| ALTA-01 | Timing Attack en API Key | Bajo |
| ALTA-02 | DB URL en Logs | Bajo |
| ALTA-03 | Inyección NoSQL Regex | Bajo |
| ALTA-07 | Actualizar React Router | Bajo |
| ALTA-08 | Actualizar Vite | Bajo |
| ALTA-18 | npm audit fix | Bajo |

### Fase 3 — Sprint Actual
| ID | Vulnerabilidad | Esfuerzo |
|----|---------------|----------|
| ALTA-04 | Validar Env Vars Subprocess | Medio |
| ALTA-05 | Alinear Versiones Requirements | Medio |
| ALTA-06 | Fijar Versión orjson | Bajo |
| ALTA-11 | HTTPS en Fallbacks | Bajo |
| ALTA-12 | Content Security Policy | Medio |
| ALTA-13 | Security Headers | Medio |
| ALTA-15 | Puerto MongoDB Localhost | Bajo |
| ALTA-16 | Virtualenv en Docker | Medio |
| ALTA-17 | Red Docker Segmentada | Medio |

### Fase 4 — Siguiente Sprint
| ID | Rango |
|----|-------|
| MEDIA-01 a MEDIA-14 | Todas las medias |
| BAJA-01 a BAJA-08 | Todas las bajas |

---

## 🤖 INSTRUCCIONES PARA IMPLEMENTACIÓN POR MODELO IA

> Las siguientes instrucciones están diseñadas para que otro modelo Claude pueda implementar las correcciones automáticamente.

### Prompt de Implementación Sugerido

```markdown
# Instrucciones de Remediación de Seguridad — BJJ-BetSports

Eres un ingeniero de seguridad senior. Tu tarea es implementar las correcciones
de seguridad documentadas en REPORT.md del repositorio BJJ-BetSports.

## Reglas de Implementación

1. Procesa las vulnerabilidades en orden de severidad: CRÍTICA → ALTA → MEDIA → BAJA
2. Cada corrección debe ser un commit atómico con mensaje en formato Conventional Commits:
   - fix(security): corregir [ID] - [descripción breve]
3. Después de cada cambio:
   - Ejecuta los tests existentes: cd backend && pytest -v
   - Ejecuta el linter del frontend: cd frontend && npm run lint
   - Ejecuta el build: cd frontend && npm run build
4. NO modifiques la lógica de negocio, solo la capa de seguridad
5. Si una corrección podría romper funcionalidad, agrega un flag de feature (env var) para desactivarla
6. Documenta cada cambio en el commit message con referencia al ID del hallazgo

## Orden de Ejecución

### Batch 1: Correcciones de configuración (sin cambios de código)
- CRIT-05: Externalizar credenciales docker-compose
- CRIT-06: Agregar USER a Dockerfiles
- ALTA-15: MongoDB solo localhost
- ALTA-06: Fijar versión orjson
- MEDIA-14: Ampliar .dockerignore

### Batch 2: Actualizaciones de dependencias
- CRIT-07: npm install axios@latest
- ALTA-07: npm install react-router-dom@latest
- ALTA-08: npm install vite@latest
- ALTA-18: npm audit fix
- ALTA-05: Alinear versiones requirements.txt

### Batch 3: Correcciones de código backend
- CRIT-01: Eliminar CORS ["*"] fallback
- CRIT-02: Eliminar credenciales MongoDB hardcodeadas
- CRIT-03: Usar credential helper para GitHub token
- CRIT-04: Agregar verificación de integridad a joblib.load
- ALTA-01: Usar compare_digest para API key
- ALTA-02: Enmascarar DB URL en logs
- ALTA-03: Escapar regex en MongoDB
- ALTA-04: Validar env vars de subprocess

### Batch 4: Correcciones de código frontend
- ALTA-11: HTTPS en fallbacks
- ALTA-12: Agregar CSP a index.html
- ALTA-14: Cifrar localStorage

### Batch 5: Infraestructura
- ALTA-16: Virtualenv en Docker
- ALTA-17: Segmentación de red Docker
- MEDIA-04: Pre-commit hooks de seguridad
- MEDIA-05: Permisos mínimos en GitHub Actions
```

---

## 📝 NOTAS FINALES

1. **No se encontró código malicioso** intencionalmente insertado en el repositorio.
2. **No se encontraron archivos `.env` con secretos reales** commiteados en el repositorio (solo `.env.example`).
3. Las vulnerabilidades más graves son de **configuración** (CORS, credenciales) y **dependencias desactualizadas** (npm audit reporta 18 paquetes vulnerables con CVEs activos).
4. La arquitectura general del proyecto es sólida, pero requiere **hardening de seguridad** en múltiples capas.
5. Se recomienda implementar **Dependabot** o **Renovate** para actualización automática de dependencias.
6. Se recomienda agregar **SAST** (Static Application Security Testing) al pipeline de CI/CD con herramientas como Bandit (Python) y ESLint security plugins (JS).

---

> **Próxima auditoría recomendada**: Tras implementar las correcciones de Fase 1 y Fase 2.
> **Contacto**: Ejecutar este reporte como input a un agente Claude con las instrucciones de implementación de la sección anterior.
