from __future__ import annotations
import json
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_pool
from app.ai_engine import generate_answer, construir_saludo

router = APIRouter(prefix="/api/ia", tags=["ia"])


class PreguntaIn(BaseModel):
    usuario_id: str
    sesion_id: str | None = None
    mensaje: str


@router.post("/chat")
async def chat(body: PreguntaIn):
    pool = get_pool()

    sesion_id = body.sesion_id
    if not sesion_id:
        row = await pool.fetchrow(
            "INSERT INTO chat_ia_sesiones (id, usuario_id, titulo) VALUES ($1, $2, $3) RETURNING id",
            str(uuid.uuid4()), body.usuario_id, body.mensaje[:60],
        )
        sesion_id = str(row["id"])

    await pool.execute(
        "INSERT INTO chat_ia_mensajes (id, sesion_id, role, content) VALUES ($1, $2, 'user', $3)",
        str(uuid.uuid4()), sesion_id, body.mensaje,
    )

    test_row = await pool.fetchrow(
        """
        SELECT respuestas, carreras FROM test_resultados
        WHERE usuario_id = $1 ORDER BY created_at DESC LIMIT 1
        """,
        body.usuario_id,
    )
    test_resultado = (
        {"respuestas": json.loads(test_row["respuestas"]), "carreras": json.loads(test_row["carreras"])}
        if test_row else None
    )

    result = await generate_answer(body.mensaje, test_resultado)

    await pool.execute(
        "INSERT INTO chat_ia_mensajes (id, sesion_id, role, content) VALUES ($1, $2, 'assistant', $3)",
        str(uuid.uuid4()), sesion_id, result["answer"],
    )

    return {"sesion_id": sesion_id, **result}


@router.get("/saludo/{usuario_id}")
async def saludo(usuario_id: str):
    """
    Saludo inicial personalizado para arrancar el chat: usa el nombre y el
    tipo de cuenta (egresado | traslado | padre) elegido al registrarse, y
    devuelve preguntas sugeridas acordes a ese perfil.
    """
    pool = get_pool()
    row = await pool.fetchrow("SELECT nombre, tipo FROM usuarios WHERE id = $1", usuario_id)
    if not row:
        raise HTTPException(404, "Usuario no encontrado")
    return construir_saludo(row["nombre"], row["tipo"])


@router.get("/historial/{usuario_id}")
async def historial(usuario_id: str):
    pool = get_pool()
    sesiones = await pool.fetch(
        "SELECT * FROM chat_ia_sesiones WHERE usuario_id = $1 ORDER BY created_at DESC",
        usuario_id,
    )
    out = []
    for s in sesiones:
        mensajes = await pool.fetch(
            "SELECT * FROM chat_ia_mensajes WHERE sesion_id = $1 ORDER BY created_at ASC",
            s["id"],
        )
        out.append({**dict(s), "mensajes": [dict(m) for m in mensajes]})
    return out
