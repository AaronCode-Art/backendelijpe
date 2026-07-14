# ElijePe — Backend (Python + FastAPI + Neon Postgres)

## 0. Compatibilidad de versión de Python

Funciona con **cualquier Python 3.9 o superior** (probado hasta 3.13) — no
está atado a una versión exacta. Esto se logra de dos formas:

- `requirements.txt` usa versiones mínimas (`>=`) en vez de versiones
  exactas (`==`), así `pip` instala automáticamente la versión de cada
  librería compatible con el Python que tengas instalado.
- Cada archivo empieza con `from __future__ import annotations`, que hace
  que anotaciones de tipo modernas (`str | None`, `dict[str, Any]`) no
  rompan en versiones de Python más antiguas.

Verifica tu versión con `python --version`. Si tienes Python 3.8 o
anterior, el código igual debería cargar, pero te recomendamos actualizar
a 3.9+ porque algunas librerías (como pydantic v2) ya no dan soporte
oficial a versiones más viejas.

## 1. Instalación

```bash
cd backend
python -m venv venv
venv\Scripts\Activate.ps1        # Windows PowerShell
# source venv/bin/activate       # Mac/Linux
pip install -r requirements.txt
```

Tu archivo `.env` ya debería tener `DATABASE_URL` (tu connection string de Neon).

## 2. Crear las tablas y cargar datos

**Opción recomendada — un solo archivo con todo:**

Abre el **SQL Editor** de https://console.neon.tech, pega **todo** el contenido de
`ElijePe_BD_COMPLETA_v2.sql` y dale **Run** una sola vez. Ese archivo:

- Borra las tablas si ya existían (empieza de cero, sin conflictos)
- Crea las 14 tablas del sistema
- Carga **60 universidades/sedes** (las 50 originales + 10 sedes nuevas de
  universidades multi-campus conocidas: UTP, César Vallejo, Continental,
  Privada del Norte), vinculadas mediante `universidad_padre_id` / `es_sede`
- Carga **14 carreras con malla curricular** en las 60 universidades/sedes
  (10,080 cursos en total)
- Carga especialistas y foros predefinidos

Al final del script hay un `SELECT` de verificación que te confirma que todo
cargó bien (universidades=60, sedes=12, mallas_curriculares=10080, etc.), y
un ejemplo de cómo consultar todas las sedes de una universidad.

**Opción alternativa — archivos separados** (`schema.sql` → `seed_data.sql` →
`schema_update.sql`): sigue funcionando, pero no incluye las sedes nuevas ni
el resto de carreras — solo la cobertura original (3 universidades x 1
carrera). Úsala solo si por algún motivo no quieres las sedes/carreras
adicionales.

Verifica que todo cargó bien:
```sql
SELECT count(*) FROM universidades;         -- 60
SELECT count(*) FROM universidades WHERE es_sede = TRUE;  -- 12
SELECT count(*) FROM mallas_curriculares;   -- 10080
```

## 3. IA gratuita — Groq (recomendado)

El motor de IA (`app/ai_engine.py`) usa una arquitectura RAG: primero busca datos reales
en tu base de universidades, y luego (opcionalmente) le pasa ese contexto a un modelo de
lenguaje real para redactar la respuesta de forma conversacional. Groq da acceso gratis
(sin tarjeta) a modelos grandes open source (Llama 3.3 70B) corriendo muy rápido:

1. Crea cuenta gratis en https://console.groq.com
2. Ve a **API Keys** → **Create API Key**
3. Copia la key y pégala en `backend/.env`:
   ```
   GROQ_API_KEY=gsk_...
   GROQ_MODEL=llama-3.3-70b-versatile
   ```
4. Reinicia uvicorn.

Si no configuras `GROQ_API_KEY`, el chat sigue funcionando igual, solo que responde con
una plantilla propia en vez de redacción de IA generativa (mira el campo
`usa_ia_generativa` en la respuesta de `/api/ia/chat` para saber cuál se usó).

**¿Por qué no "entrenar" un modelo propio?** Entrenar un modelo de lenguaje desde cero
cuesta computación que no tiene sentido para 50 universidades. La forma correcta de
lograr lo mismo (que la IA "sepa" tus datos) es RAG: cada pregunta se cruza en tiempo real
contra tu base PostgreSQL y ese resultado real se le pasa al modelo — así nunca inventa
datos que no estén en tu base.

## 4. Levantar el servidor

```bash
uvicorn app.main:app --reload --port 8000
```

Swagger interactivo: http://localhost:8000/docs

## 5. Endpoints

| Módulo | Ruta | Qué hace |
|---|---|---|
| Auth | `POST /api/auth/registro`, `/login` | Registro/login real contra la BD |
| Universidades | `GET /api/universidades` | Lista las 60 universidades/sedes (usa `?solo_principales=true` para ocultar sedes duplicadas) |
| Universidades | `GET /api/universidades/{id}/sedes` | Todas las sedes de una misma institución (ej. las 4 sedes de UTP) |
| Universidades | `POST /api/universidades/postular` | "Comprar"/reservar vacante |
| IA | `POST /api/ia/chat` | Chat de IA (RAG + Groq) sobre universidades |
| IA | `GET /api/ia/historial/{usuario_id}` | Historial de conversaciones (para el sidebar) |
| Pagos | `POST /api/pagos/desbloquear-premium` | Pago único S/. 10 → IA + especialistas + foros |
| Especialistas | `POST /api/especialistas/sesiones` | Chat con especialista humano (requiere premium) |
| Foros | `POST /api/foros` | Crea un foro (requiere premium) |
| Foros | `POST /api/foros/posts`, `/posts/comentarios` | Publicar y comentar |
| **Simulador** | `POST /api/simulador/convalidar` | Sube un PDF real de récord de notas y devuelve, curso por curso, si convalida contra la malla de la universidad/carrera destino |

### Ejemplo — simulador con PDF real (multipart/form-data)
```
POST /api/simulador/convalidar
  usuario_id: <uuid del usuario logueado>
  universidad_id: 1
  carrera: "Ingeniería de Sistemas"
  file: <record.pdf>
```
Devuelve, por curso detectado en el PDF: si convalida, contra qué curso de la malla
destino, con qué similitud de texto, y créditos convalidados.

⚠️ La malla curricular es de **ejemplo** (solo Ingeniería de Sistemas en universidades
1, 2 y 3). Para que el resultado sea 100% real, agrega la malla curricular oficial de cada
universidad y carrera en la tabla `mallas_curriculares`.

## 6. Conectar con el frontend

El frontend (`innova/`) ya viene conectado a este backend a través de
`src/services/api.ts`. Solo necesita que:
1. El backend esté corriendo (`uvicorn ...`)
2. El frontend tenga en su `.env`: `VITE_API_URL=http://localhost:8000`

Si el backend no responde, el chat de IA sigue funcionando con un motor local de
respaldo (para que la demo nunca se caiga), y el resto de funciones premium
(especialistas, foros, simulador, postular) piden iniciar sesión o muestran un aviso
claro de que no se pudo conectar.
