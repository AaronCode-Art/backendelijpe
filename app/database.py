"""
Conexión a la base de datos PostgreSQL (Neon DB).

Neon es Postgres serverless: solo necesitas copiar el "Connection string"
que te da el dashboard de https://neon.tech y ponerlo en la variable de
entorno DATABASE_URL (ver .env.example). El pool se abre una sola vez
cuando arranca la aplicación FastAPI (ver app/main.py -> lifespan).
"""
from __future__ import annotations
import os
from typing import Optional

import asyncpg
from dotenv import load_dotenv

# Carga el archivo .env ANTES de leer cualquier variable de entorno.
# Debe ejecutarse a nivel de módulo (no solo dentro de connect()), para que
# quede cargado apenas arranca el proceso de uvicorn.
load_dotenv()

_pool: Optional[asyncpg.Pool] = None


async def connect() -> None:
    global _pool
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL no está configurada. Revisa que exista un archivo "
            "backend/.env con tu connection string de Neon (ver .env.example) "
            "y que estés corriendo uvicorn desde la carpeta backend/."
        )
    # Neon requiere SSL; asyncpg lo maneja solo si el string trae ?sslmode=require
    _pool = await asyncpg.create_pool(database_url, min_size=1, max_size=5)
    print(f"✔ Conectado a PostgreSQL (Neon): {database_url.split('@')[-1].split('?')[0]}")


async def disconnect() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("El pool de la base de datos aún no está inicializado.")
    return _pool
