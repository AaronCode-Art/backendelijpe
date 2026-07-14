from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_pool

router = APIRouter(prefix="/api/foros", tags=["foros"])


async def _require_premium(pool, usuario_id: str):
    row = await pool.fetchrow("SELECT ia_premium FROM usuarios WHERE id = $1", usuario_id)
    if not row:
        raise HTTPException(404, "Usuario no encontrado")
    if not row["ia_premium"]:
        raise HTTPException(402, "Crear foros requiere el acceso premium (pago único de S/. 10)")


@router.get("")
async def listar_foros():
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT f.*, COUNT(p.id) AS total_posts
        FROM foros f
        LEFT JOIN foro_posts p ON p.foro_id = f.id
        GROUP BY f.id
        ORDER BY f.es_predefinido DESC, f.created_at DESC
        """
    )
    return [dict(r) for r in rows]


class ForoIn(BaseModel):
    usuario_id: str
    nombre: str
    descripcion: str = ""
    icono: str = "💬"
    color: str = "#0059FF"


@router.post("")
async def crear_foro(body: ForoIn):
    """El usuario paga S/. 10 una sola vez y puede crear todos los foros que quiera."""
    pool = get_pool()
    await _require_premium(pool, body.usuario_id)
    row = await pool.fetchrow(
        """
        INSERT INTO foros (id, nombre, descripcion, icono, color, creado_por, es_predefinido)
        VALUES ($1, $2, $3, $4, $5, $6, FALSE)
        RETURNING *
        """,
        str(uuid.uuid4()), body.nombre, body.descripcion, body.icono, body.color, body.usuario_id,
    )
    return dict(row)


# ─── Publicaciones dentro de un foro ──────────────────────────────────────
class PostIn(BaseModel):
    foro_id: str
    autor_id: str
    titulo: str
    contenido: str
    tags: list[str] = []


@router.post("/posts")
async def crear_post(body: PostIn):
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO foro_posts (id, foro_id, autor_id, titulo, contenido, tags)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING *
        """,
        str(uuid.uuid4()), body.foro_id, body.autor_id, body.titulo, body.contenido, body.tags,
    )
    return dict(row)


@router.get("/{foro_id}/posts")
async def listar_posts(foro_id: str):
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT p.*, u.nombre AS autor_nombre, u.apellido AS autor_apellido
        FROM foro_posts p
        JOIN usuarios u ON u.id = p.autor_id
        WHERE p.foro_id = $1
        ORDER BY p.created_at DESC
        """,
        foro_id,
    )
    return [dict(r) for r in rows]


# ─── Comentarios / conversaciones dentro de un post ──────────────────────
class ComentarioIn(BaseModel):
    post_id: str
    autor_id: str
    contenido: str


@router.post("/posts/comentarios")
async def comentar(body: ComentarioIn):
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO foro_comentarios (id, post_id, autor_id, contenido)
        VALUES ($1, $2, $3, $4)
        RETURNING *
        """,
        str(uuid.uuid4()), body.post_id, body.autor_id, body.contenido,
    )
    return dict(row)


@router.get("/posts/{post_id}/comentarios")
async def listar_comentarios(post_id: str):
    pool = get_pool()
    rows = await pool.fetch(
        """
        SELECT c.*, u.nombre AS autor_nombre, u.apellido AS autor_apellido
        FROM foro_comentarios c
        JOIN usuarios u ON u.id = c.autor_id
        WHERE c.post_id = $1
        ORDER BY c.created_at ASC
        """,
        post_id,
    )
    return [dict(r) for r in rows]
