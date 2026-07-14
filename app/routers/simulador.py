"""
Simulador de convalidación de cursos — con PDF real, de cualquier
universidad o instituto (UTP, UCV, PUCP, etc.) y cualquier carrera.

El estudiante sube el PDF de su récord de notas de origen. Este módulo:

  1. Extrae el texto del PDF con pdfplumber.
  2. Detecta cada curso con DOS estrategias, en este orden:
     a) Formato "tabla con columna ESTADO" (el más común en Perú: UTP, UCV,
        PUCP, etc. imprimen algo como
        "01 100000I02N QUIMICA GENERAL 1 3.00 13 2136 Aprobado"
        con las columnas CICLO · CÓDIGO · CURSO · NRO VEZ · CRÉDITOS · NOTA
        · SECCIÓN · ESTADO). Usamos la palabra de ESTADO (Aprobado /
        Desaprobado / Retirado / En Curso) directamente — es más confiable
        que adivinar por la nota, porque nos dice exactamente si el curso
        está aprobado o no, incluso cuando no hay nota numérica (cursos
        "En Curso" o "Retirado").
     b) Si (a) no encuentra nada (otro formato de PDF), cae a un formato
        más simple "Nombre del curso ......... 15" basado solo en la nota.
  3. Si un curso aparece más de una vez (el alumno lo jaló y lo volvió a
     llevar — columna NRO VEZ), nos quedamos con el mejor intento
     (prioriza "Aprobado" sobre cualquier otro estado).
  4. Compara cada curso extraído contra la malla curricular de la carrera
     y universidad DESTINO (tabla `mallas_curriculares`) usando similitud
     de texto (difflib + comparación por palabras), no coincidencia
     exacta, porque los nombres de cursos casi nunca son idénticos entre
     instituciones.
  5. Devuelve, por curso: si convalida o no, contra qué curso de la malla
     destino, y el nivel de similitud. Guarda el resultado en
     `simulaciones_convalidacion` para que quede en el historial del usuario.

⚠️ Importante: la tabla `mallas_curriculares` viene con datos GENÉRICOS por
carrera (ver schema_update.sql / mallas_todas_universidades.sql), no la
malla oficial real de cada universidad. El PDF sí se lee de forma 100%
real; lo genérico es solo el lado "destino" contra el que se compara,
hasta que cargues la malla oficial de cada universidad.
"""
from __future__ import annotations
import difflib
import io
import re
import unicodedata
import uuid
import json

import pdfplumber
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.database import get_pool

router = APIRouter(prefix="/api/simulador", tags=["simulador"])

# ── Estrategia A: formato con columna ESTADO (UTP, UCV, PUCP, etc.) ────────
# "01 100000I02N QUIMICA GENERAL 1 3.00 13 2136 Aprobado"
#  ciclo  código      curso     nrovez créditos nota sección  estado
ESTADOS_VALIDOS = r"(?:Aprobado|Desaprobado|Retirado|En\s+Curso|Convalidado|Reservado|Inhabilitado|Anulado)"
LINE_REGEX_ESTADO = re.compile(
    rf"^(?P<ciclo>\d{{1,2}})\s+"
    rf"(?P<cod>[A-Z0-9]{{5,12}})\s+"
    rf"(?P<curso>.+?)\s+"
    rf"(?P<nrovez>\d)\s+"
    rf"(?P<creditos>\d{{1,2}}[.,]\d{{1,2}})\s+"
    rf"(?P<nota>\d{{1,2}}|--|-)\s+"
    rf"(?P<seccion>\S+)\s+"
    rf"(?P<estado>{ESTADOS_VALIDOS})\s*$",
    re.IGNORECASE,
)

# ── Estrategia B (respaldo): "Nombre del curso ......... 15" ──────────────
LINE_REGEX_SOLO_NOTA = re.compile(
    r"^(?P<curso>[A-ZÁÉÍÓÚÑa-záéíóúñ0-9 .,\-()]{6,80}?)\s*[.\-\s]{1,}\s*(?P<nota>\d{1,2}(?:[.,]\d)?)\s*$"
)

NOTA_APROBATORIA = 11  # escala vigesimal peruana (0-20), solo se usa en la Estrategia B
UMBRAL_SIMILITUD = 0.45  # relajado: la normalización ya elimina la mayoría del ruido

ESTADOS_APROBADOS = {"aprobado", "convalidado"}
ESTADOS_EN_CURSO = {"en curso"}
ESTADOS_NO_APROBADOS = {"desaprobado", "retirado", "inhabilitado", "anulado"}


def _extraer_cursos_por_estado(texto: str) -> list[dict]:
    cursos = []
    for line in texto.split("\n"):
        line = line.strip()
        m = LINE_REGEX_ESTADO.match(line)
        if not m:
            continue
        curso = m.group("curso").strip(" .-")
        if len(curso) < 4:
            continue
        nota_raw = m.group("nota")
        nota = None if nota_raw in ("--", "-") else float(nota_raw.replace(",", "."))
        estado_txt = re.sub(r"\s+", " ", m.group("estado")).strip().lower()
        cursos.append({
            "curso": curso,
            "nota": nota,
            "estado_origen": estado_txt,
            "nro_vez": int(m.group("nrovez")),
        })
    return cursos


def _extraer_cursos_solo_nota(texto: str) -> list[dict]:
    cursos = []
    for line in texto.split("\n"):
        line = line.strip()
        m = LINE_REGEX_SOLO_NOTA.match(line)
        if not m:
            continue
        nota = float(m.group("nota").replace(",", "."))
        if not (0 <= nota <= 20):
            continue
        curso = m.group("curso").strip(" .-")
        if len(curso) < 4:
            continue
        estado_txt = "aprobado" if nota >= NOTA_APROBATORIA else "desaprobado"
        cursos.append({"curso": curso, "nota": nota, "estado_origen": estado_txt, "nro_vez": 1})
    return cursos


def _extraer_cursos(pdf_bytes: bytes) -> list[dict]:
    texto_completo = ""
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            texto_completo += (page.extract_text() or "") + "\n"

    cursos = _extraer_cursos_por_estado(texto_completo)
    if not cursos:
        # El PDF no tiene el formato "con columna ESTADO" → probamos el formato simple
        cursos = _extraer_cursos_solo_nota(texto_completo)

    # Si el alumno llevó el mismo curso más de una vez (lo jaló y lo repitió),
    # nos quedamos con el mejor intento: prioriza "aprobado", y entre iguales
    # prioriza el NRO VEZ más alto (el intento más reciente).
    mejores: dict[str, dict] = {}
    for c in cursos:
        clave = _normalizar(c["curso"])
        actual = mejores.get(clave)
        if actual is None:
            mejores[clave] = c
            continue
        c_aprobado = c["estado_origen"] in ESTADOS_APROBADOS
        actual_aprobado = actual["estado_origen"] in ESTADOS_APROBADOS
        if c_aprobado and not actual_aprobado:
            mejores[clave] = c
        elif c_aprobado == actual_aprobado and c["nro_vez"] >= actual["nro_vez"]:
            mejores[clave] = c

    return list(mejores.values())


def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes, sin puntuación, espacios colapsados. Así
    'Base de Datos I' y 'BASE DE DATOS I.' o 'Base de datos 1' se comparan
    de forma justa, sin que el acentuado/mayúsculas/puntuación arruine el match."""
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    t = t.lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _similaridad(a: str, b: str) -> float:
    na, nb = _normalizar(a), _normalizar(b)
    # Similitud por secuencia de caracteres (sensible a orden y redacción)
    ratio_secuencia = difflib.SequenceMatcher(None, na, nb).ratio()
    # Similitud por conjunto de palabras (tolera orden distinto y palabras de más/menos)
    set_a, set_b = set(na.split()), set(nb.split())
    ratio_palabras = (
        len(set_a & set_b) / len(set_a | set_b) if (set_a or set_b) else 0.0
    )
    return max(ratio_secuencia, ratio_palabras)


@router.post("/convalidar")
async def convalidar(
    usuario_id: str = Form(...),
    universidad_id: int = Form(...),
    carrera: str = Form(...),
    file: UploadFile = File(...),
):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Sube el récord de notas en formato PDF")

    pdf_bytes = await file.read()
    cursos_extraidos = _extraer_cursos(pdf_bytes)

    if not cursos_extraidos:
        raise HTTPException(
            422,
            "No se pudo extraer ningún curso del PDF. Asegúrate de que el "
            "documento tenga texto seleccionable (no una foto escaneada). "
            "Se probaron dos formatos de récord académico y ninguno calzó "
            "con el tuyo — escríbenos el nombre de tu universidad para "
            "agregar soporte a su formato.",
        )

    pool = get_pool()
    malla = await pool.fetch(
        "SELECT curso, creditos, ciclo FROM mallas_curriculares "
        "WHERE universidad_id = $1 AND carrera ILIKE $2",
        universidad_id, f"%{carrera}%",
    )
    malla = [dict(r) for r in malla]

    if not malla:
        raise HTTPException(
            404,
            f"No hay malla curricular cargada todavía para esa universidad y "
            f"carrera ('{carrera}'). Agrégala en la tabla mallas_curriculares.",
        )

    resultados = []
    total_creditos_convalidados = 0
    for c in cursos_extraidos:
        mejor, mejor_score = None, 0.0
        for m in malla:
            score = _similaridad(c["curso"], m["curso"])
            if score > mejor_score:
                mejor, mejor_score = m, score

        coincide = mejor is not None and mejor_score >= UMBRAL_SIMILITUD
        estado_origen = c["estado_origen"]

        if estado_origen in ESTADOS_EN_CURSO:
            # Todavía no tiene nota final: no se puede convalidar ni descartar aún.
            estado = "en_curso"
        elif coincide and estado_origen in ESTADOS_APROBADOS:
            estado = "convalidado"
            total_creditos_convalidados += mejor["creditos"]
        elif coincide and estado_origen in ESTADOS_NO_APROBADOS:
            estado = "no_convalidado_nota_insuficiente"
        elif coincide:
            estado = "no_convalidado_nota_insuficiente"
        else:
            estado = "sin_equivalencia"

        resultados.append({
            "curso_origen": c["curso"],
            "nota_origen": c["nota"],
            "estado_origen": estado_origen,
            "curso_destino": mejor["curso"] if coincide else None,
            "creditos_destino": mejor["creditos"] if coincide else None,
            "similitud": round(mejor_score, 2),
            "estado": estado,
        })

    resumen = {
        "total_cursos_detectados": len(cursos_extraidos),
        "total_convalidados": sum(1 for r in resultados if r["estado"] == "convalidado"),
        "total_creditos_convalidados": total_creditos_convalidados,
        "resultados": resultados,
    }

    row = await pool.fetchrow(
        """
        INSERT INTO simulaciones_convalidacion
            (id, usuario_id, universidad_id, carrera, archivo_nombre, resultado)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        RETURNING id, created_at
        """,
        str(uuid.uuid4()), usuario_id, universidad_id, carrera, file.filename, json.dumps(resumen),
    )

    return {"simulacion_id": str(row["id"]), "created_at": row["created_at"], **resumen}


@router.get("/historial/{usuario_id}")
async def historial_simulaciones(usuario_id: str):
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT s.*, u.name AS universidad_name
        FROM simulaciones_convalidacion s
        JOIN universidades u ON u.id = s.universidad_id
        WHERE s.usuario_id = $1
        ORDER BY s.created_at DESC
        """,
        usuario_id,
    )
    return [dict(r) for r in rows]
