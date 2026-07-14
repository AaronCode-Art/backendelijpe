from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_pool

router = APIRouter(prefix="/api/especialistas", tags=["especialistas"])


async def _require_premium(pool, usuario_id: str):
    row = await pool.fetchrow("SELECT ia_premium FROM usuarios WHERE id = $1", usuario_id)
    if not row:
        raise HTTPException(404, "Usuario no encontrado")
    if not row["ia_premium"]:
        raise HTTPException(402, "Esta función requiere el acceso premium (pago único de S/. 10)")


@router.get("")
async def listar_especialistas():
    pool = get_pool()
    rows = await pool.fetch("SELECT * FROM especialistas WHERE activo = TRUE")
    return [dict(r) for r in rows]


class IniciarSesionIn(BaseModel):
    usuario_id: str
    especialidad: str  # vocacional | traslado | financiero | familiar


@router.post("/sesiones")
async def iniciar_sesion(body: IniciarSesionIn):
    pool = get_pool()
    await _require_premium(pool, body.usuario_id)

    especialista = await pool.fetchrow(
        "SELECT id FROM especialistas WHERE especialidad = $1 AND activo = TRUE LIMIT 1",
        body.especialidad,
    )
    sesion = await pool.fetchrow(
        """
        INSERT INTO especialista_sesiones (id, usuario_id, especialista_id, especialidad, estado)
        VALUES ($1, $2, $3, $4, 'activo')
        RETURNING *
        """,
        str(uuid.uuid4()), body.usuario_id,
        especialista["id"] if especialista else None, body.especialidad,
    )
    return dict(sesion)


class MensajeIn(BaseModel):
    sesion_id: str
    role: str  # user | especialista
    content: str


@router.post("/mensajes")
async def enviar_mensaje(body: MensajeIn):
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO especialista_mensajes (id, sesion_id, role, content)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        str(uuid.uuid4()), body.sesion_id, body.role, body.content,
    )
    return dict(row)


@router.get("/sesiones/{sesion_id}/mensajes")
async def obtener_mensajes(sesion_id: str):
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT * FROM especialista_mensajes WHERE sesion_id = $1 ORDER BY created_at ASC",
        sesion_id,
    )
    return [dict(r) for r in rows]


@router.get("/sesiones/usuario/{usuario_id}")
async def sesiones_de_usuario(usuario_id: str):
    pool = get_pool()
    rows = await pool.fetch(
        "SELECT * FROM especialista_sesiones WHERE usuario_id = $1 ORDER BY created_at DESC",
        usuario_id,
    )
    return [dict(r) for r in rows]
