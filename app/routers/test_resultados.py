from __future__ import annotations
import json
import uuid
from fastapi import APIRouter
from pydantic import BaseModel

from app.database import get_pool
from ml.model import get_modelo

router = APIRouter(prefix="/api/test", tags=["test"])


class ResultadoIn(BaseModel):
    usuario_id: str
    respuestas: dict
    carreras: list


class RespuestasIn(BaseModel):
    respuestas: dict[str, list[str]]  # { "1": ["prog"], "4": ["math","chem"], ... }


@router.post("/predecir-ml")
async def predecir_ml(body: RespuestasIn):
    """Predicción real de Machine Learning (Random Forest de scikit-learn,
    ver ml/model.py) sobre las respuestas del test vocacional. Devuelve los
    clusters de carrera ordenados por probabilidad aprendida por el modelo,
    no por una simple suma de pesos."""
    modelo = get_modelo()
    selections = {int(k): v for k, v in body.respuestas.items()}
    ranking = modelo.predecir(selections)
    return {
        "ranking": ranking,
        "modelo": {
            "tipo": "RandomForestClassifier (scikit-learn)",
            "muestras_entrenamiento": modelo.n_samples,
            "accuracy_test": round(modelo.test_accuracy, 3),
        },
    }


@router.post("/resultado")
async def guardar_resultado(body: ResultadoIn):
    """Guarda el resultado real del test (respuestas + carreras calculadas
    en el frontend a partir de esas respuestas). La IA lo lee después desde
    aquí para dar recomendaciones basadas en el test real del usuario."""
    pool = get_pool()
    row = await pool.fetchrow(
        """
        INSERT INTO test_resultados (id, usuario_id, respuestas, carreras)
        VALUES ($1, $2, $3, $4)
        RETURNING id, created_at
        """,
        str(uuid.uuid4()),
        body.usuario_id,
        json.dumps(body.respuestas),
        json.dumps(body.carreras),
    )
    return {"id": str(row["id"]), "created_at": row["created_at"].isoformat()}


@router.get("/resultado/{usuario_id}")
async def ultimo_resultado(usuario_id: str):
    """Último resultado guardado del usuario, o null si nunca hizo el test."""
    pool = get_pool()
    row = await pool.fetchrow(
        """
        SELECT id, respuestas, carreras, created_at FROM test_resultados
        WHERE usuario_id = $1 ORDER BY created_at DESC LIMIT 1
        """,
        usuario_id,
    )
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "respuestas": json.loads(row["respuestas"]),
        "carreras": json.loads(row["carreras"]),
        "created_at": row["created_at"].isoformat(),
    }
