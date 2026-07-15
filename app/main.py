from __future__ import annotations
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import database
from app.routers import auth, universidades, ia, pagos, especialistas, foros, simulador, test_resultados

# Dominios permitidos para llamar a esta API. En Render se configura con la
# variable de entorno FRONTEND_URL (ver .env.example). Si no está definida,
# se cae en localhost para desarrollo local.
_frontend_url = os.getenv("FRONTEND_URL", "https://frontelijepe.onrender.com")
ALLOWED_ORIGINS = [origin.strip() for origin in _frontend_url.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()


app = FastAPI(
    title="ElijePe API",
    description="Backend de ElijePe (INNOVA): IA de orientación, chat con "
                 "especialistas, comunidad con foros y postulaciones, sobre PostgreSQL (Neon).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(universidades.router)
app.include_router(ia.router)
app.include_router(pagos.router)
app.include_router(especialistas.router)
app.include_router(foros.router)
app.include_router(simulador.router)
app.include_router(test_resultados.router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "ElijePe API"}



@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc),
            "type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        },
    )
