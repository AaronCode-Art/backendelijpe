from __future__ import annotations
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
import bcrypt

from app.database import get_pool

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegistroIn(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    password: str
    dni: str | None = None
    telefono: str | None = None
    tipo: str = "egresado"
    region: str | None = None


@router.post("/registro")
async def registro(body: RegistroIn):
    pool = get_pool()
    existente = await pool.fetchrow("SELECT id FROM usuarios WHERE email = $1", body.email)
    if existente:
        raise HTTPException(409, "Ya existe una cuenta con ese correo")

    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()
    row = await pool.fetchrow(
        """
        INSERT INTO usuarios (id, nombre, apellido, email, password_hash, dni, telefono, tipo, region)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, nombre, apellido, email, tipo, region, ia_premium, created_at
        """,
        str(uuid.uuid4()), body.nombre, body.apellido, body.email, hashed,
        body.dni, body.telefono, body.tipo, body.region,
    )
    return dict(row)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
async def login(body: LoginIn):
    pool = get_pool()
    row = await pool.fetchrow("SELECT * FROM usuarios WHERE email = $1", body.email)
    if not row or not bcrypt.checkpw(body.password.encode(), row["password_hash"].encode()):
        raise HTTPException(401, "Credenciales inválidas")

    user = dict(row)
    user.pop("password_hash")
    return user
