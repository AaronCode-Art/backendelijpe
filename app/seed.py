"""
Script de siembra (seed) de la base de datos.

Carga:
  1. Las 50 universidades usadas en el frontend (app/data/universities.json,
     extraídas de src/data/universities.ts) dentro de la tabla `universidades`.
  2. Un especialista base por cada especialidad (vocacional, traslado,
     financiero, familiar) en la tabla `especialistas`.
  3. Los foros/canales predefinidos de la Comunidad (los mismos que ya
     existen en el frontend: src/data/communityData.ts) en la tabla `foros`.

Uso:
    python -m app.seed
"""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path

import asyncpg

DATA_FILE = Path(__file__).parent / "data" / "universities.json"

ESPECIALISTAS_BASE = [
    ("Equipo Vocacional ElijePe", "vocacional"),
    ("Equipo de Traslados ElijePe", "traslado"),
    ("Equipo Financiero ElijePe", "financiero"),
    ("Equipo de Acompañamiento Familiar", "familiar"),
]

FOROS_BASE = [
    ("general", "General", "💬", "#0059FF"),
    ("admision", "Admisión y postulación", "📝", "#7C3AED"),
    ("traslados", "Traslados y convalidación", "🔄", "#16A34A"),
    ("becas", "Becas y financiamiento", "🎓", "#D97706"),
    ("vida-universitaria", "Vida universitaria", "🏫", "#0891B2"),
]


async def main():
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        raise SystemExit("Define DATABASE_URL antes de correr el seed (ver .env.example)")

    conn = await asyncpg.connect(database_url)

    # 1. Universidades
    universidades = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    for u in universidades:
        await conn.execute(
            """
            INSERT INTO universidades (
                id, name, short, type, region, city, cost, pension_min, pension_max,
                matricula, rating, img, empleabilidad, sunedu, modalidad, nivel,
                careers, founded, lat, lng, description, cost_history, website
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23)
            ON CONFLICT (id) DO NOTHING
            """,
            u["id"], u["name"], u["short"], u["type"], u["region"], u["city"],
            u["cost"], u["pensionMin"], u["pensionMax"], u["matricula"], u["rating"],
            u["img"], u["empleabilidad"], u["sunedu"], u["modalidad"], u["nivel"],
            u["careers"], u["founded"], u["lat"], u["lng"], u["description"],
            u["costHistory"], u["website"],
        )
    print(f"✔ {len(universidades)} universidades sembradas")

    # 2. Especialistas
    for nombre, especialidad in ESPECIALISTAS_BASE:
        await conn.execute(
            "INSERT INTO especialistas (id, nombre, especialidad) "
            "SELECT uuid_generate_v4(), $1, $2 "
            "WHERE NOT EXISTS (SELECT 1 FROM especialistas WHERE especialidad = $2)",
            nombre, especialidad,
        )
    print(f"✔ {len(ESPECIALISTAS_BASE)} especialistas base sembrados")

    # 3. Foros predefinidos
    for id_, nombre, icono, color in FOROS_BASE:
        existe = await conn.fetchrow("SELECT id FROM foros WHERE nombre = $1", nombre)
        if not existe:
            await conn.execute(
                "INSERT INTO foros (id, nombre, descripcion, icono, color, es_predefinido) "
                "VALUES (uuid_generate_v4(), $1, '', $2, $3, TRUE)",
                nombre, icono, color,
            )
    print(f"✔ {len(FOROS_BASE)} foros predefinidos sembrados")

    await conn.close()
    print("Listo ✅")


if __name__ == "__main__":
    asyncio.run(main())
