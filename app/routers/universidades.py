from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_pool

router = APIRouter(prefix="/api/universidades", tags=["universidades"])


@router.get("")
async def listar_universidades(
    region: str | None = None,
    tipo: str | None = None,
    solo_principales: bool = False,
):
    """
    Por defecto devuelve las 60 filas (50 instituciones + 10 sedes).
    Usa `solo_principales=true` para traer solo una fila por institución
    (oculta las sedes adicionales), útil para listados generales donde no
    quieres repetir "Universidad Tecnológica del Perú" tres veces.
    """
    pool = get_pool()
    clauses, params, idx = [], [], 1
    if region:
        clauses.append(f"region ILIKE ${idx}")
        params.append(f"%{region}%")
        idx += 1
    if tipo:
        clauses.append(f"type = ${idx}")
        params.append(tipo)
        idx += 1
    if solo_principales:
        clauses.append("es_sede = FALSE")
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = await pool.fetch(f"SELECT * FROM universidades {where} ORDER BY rating DESC", *params)
    return [dict(r) for r in rows]


@router.get("/{uni_id}/sedes")
async def sedes_de_universidad(uni_id: int):
    """
    Devuelve todas las sedes de la misma institución que `uni_id`
    (incluyéndola a ella misma): si `uni_id` es la sede principal, trae a
    todas sus sedes hijas; si `uni_id` ya es una sede, trae a la principal
    y a sus hermanas.
    """
    pool = get_pool()
    base = await pool.fetchrow("SELECT id, universidad_padre_id FROM universidades WHERE id = $1", uni_id)
    if not base:
        raise HTTPException(404, "Universidad no encontrada")

    padre_id = base["universidad_padre_id"] or base["id"]
    rows = await pool.fetch(
        "SELECT * FROM universidades WHERE id = $1 OR universidad_padre_id = $1 ORDER BY es_sede, id",
        padre_id,
    )
    return [dict(r) for r in rows]


@router.get("/{uni_id}")
async def obtener_universidad(uni_id: int):
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM universidades WHERE id = $1", uni_id)
    if not row:
        raise HTTPException(404, "Universidad no encontrada")
    return dict(row)


# ─── "Comprar" / reservar vacante (postulación) ───────────────────────────
class PostulacionIn(BaseModel):
    usuario_id: str
    universidad_id: int
    carrera: str


@router.post("/postular")
async def postular(body: PostulacionIn):
    pool = get_pool()
    uni = await pool.fetchrow("SELECT id FROM universidades WHERE id = $1", body.universidad_id)
    if not uni:
        raise HTTPException(404, "Universidad no encontrada")

    row = await pool.fetchrow(
        """
        INSERT INTO postulaciones (id, usuario_id, universidad_id, carrera, estado)
        VALUES ($1, $2, $3, $4, 'reservado')
        RETURNING *
        """,
        str(uuid.uuid4()), body.usuario_id, body.universidad_id, body.carrera,
    )
    return dict(row)


@router.get("/postulaciones/{usuario_id}")
async def mis_postulaciones(usuario_id: str):
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT p.*, u.name AS universidad_name, u.short AS universidad_short
        FROM postulaciones p
        JOIN universidades u ON u.id = p.universidad_id
        WHERE p.usuario_id = $1
        ORDER BY p.created_at DESC
        """,
        usuario_id,
    )
    return [dict(r) for r in rows]
