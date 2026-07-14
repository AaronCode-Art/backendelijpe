from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_pool

router = APIRouter(prefix="/api/pagos", tags=["pagos"])

PRECIO_ACCESO_PREMIUM = 10.00  # S/. — pago único, incluye: IA mejorada,
                                # chat con especialistas y creación de foros.


class PagoIn(BaseModel):
    usuario_id: str
    metodo: str = "tarjeta"  # tarjeta | yape | plin
    referencia: str | None = None


@router.post("/desbloquear-premium")
async def desbloquear_premium(body: PagoIn):
    """
    Simula/registra el pago único de S/. 10 que desbloquea:
      - Chat de IA mejorado (análisis vocacional profundo + proyección financiera)
      - Chat personalizado con especialistas humanos
      - Creación de foros propios en la Comunidad

    En producción, este endpoint se conecta a una pasarela real (Culqi,
    Niubiz, MercadoPago, etc.) que confirma el pago vía webhook antes de
    marcar `estado = 'aprobado'`. Aquí queda listo el modelo de datos y el
    flujo para enchufar esa pasarela sin cambiar el resto del sistema.
    """
    pool = get_pool()
    user = await pool.fetchrow("SELECT id FROM usuarios WHERE id = $1", body.usuario_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    pago = await pool.fetchrow(
        """
        INSERT INTO pagos (id, usuario_id, monto, metodo, estado, referencia)
        VALUES ($1, $2, $3, $4, 'aprobado', $5)
        RETURNING *
        """,
        str(uuid.uuid4()), body.usuario_id, PRECIO_ACCESO_PREMIUM, body.metodo, body.referencia,
    )
    await pool.execute("UPDATE usuarios SET ia_premium = TRUE WHERE id = $1", body.usuario_id)

    return {"pago": dict(pago), "ia_premium": True}


@router.get("/estado/{usuario_id}")
async def estado_premium(usuario_id: str):
    pool = get_pool()
    row = await pool.fetchrow("SELECT ia_premium FROM usuarios WHERE id = $1", usuario_id)
    if not row:
        raise HTTPException(404, "Usuario no encontrado")
    return {"ia_premium": row["ia_premium"], "precio": PRECIO_ACCESO_PREMIUM}
