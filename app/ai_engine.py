"""
Motor de Inteligencia Artificial de ElijePe.

Este es el motor que le da inteligencia real al chat, no plantillas fijas.
Funciona con una arquitectura RAG (Retrieval-Augmented Generation), que es
la forma correcta de "entrenar con tu base de datos" sin necesidad de
entrenar un modelo desde cero (eso costaría miles de dólares en cómputo y
no tendría sentido para 50 universidades). En vez de eso:

1. CAPA DE RECUPERACIÓN (siempre activa, gratis, sin API key):
   Analiza la pregunta del usuario, la cruza contra la base de universidades
   real en PostgreSQL (tabla `universidades`) y arma el contexto: costos,
   empleabilidad, ubicación, tipo, acreditación SUNEDU, etc.

2. CAPA DE GENERACIÓN (IA real, gratuita, vía Groq):
   Ese contexto se le pasa a un modelo de lenguaje (Llama 3.3 70B) a través
   de la API de Groq, con instrucciones estrictas de responder SOLO con esos
   datos. Groq da acceso gratuito (sin tarjeta de crédito) a modelos open
   source grandes, corriendo en hardware propio (LPU) extremadamente rápido.

   Cómo conseguir tu API key gratis:
     1. Entra a https://console.groq.com y crea una cuenta (gratis).
     2. Ve a "API Keys" -> "Create API Key".
     3. Copia la key y pégala en backend/.env como GROQ_API_KEY=gsk_...
     4. pip install groq

   Si no configuras GROQ_API_KEY, el sistema sigue funcionando: responde
   con la capa 1 (los datos reales, redactados con una plantilla propia),
   solo que sin la redacción conversacional del modelo de lenguaje.
"""
from __future__ import annotations
import os
import re
from typing import Any

from app.database import get_pool

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

REGIONES = [
    "lima", "arequipa", "cusco", "trujillo", "piura", "chiclayo",
    "huancayo", "ica", "tacna", "puno", "iquitos", "ayacucho",
]

CARRERA_KEYWORDS = [
    "medicina", "ingenieria", "ingeniería", "derecho", "administracion",
    "administración", "psicologia", "psicología", "arquitectura",
    "enfermeria", "enfermería", "sistemas", "contabilidad", "marketing",
    "educacion", "educación", "comunicaciones", "economia", "economía",
]


def _detect_intent(msg: str) -> dict[str, Any]:
    """Analiza la pregunta del usuario en busca de señales de tipo/región/precio."""
    m = msg.lower()
    intent: dict[str, Any] = {
        "region": next((r for r in REGIONES if r in m), None),
        "carrera": next((c for c in CARRERA_KEYWORDS if c in m), None),
        "quiere_publicas": bool(re.search(r"p[uú]blic", m)),
        "quiere_privadas": bool(re.search(r"privad", m)),
        "quiere_baratas": bool(re.search(r"barat|econ[oó]mic|menor costo|bajo costo", m)),
        "quiere_empleabilidad": bool(re.search(r"empleab|trabajo|salida laboral|conseguir trabajo", m)),
        "compara": bool(re.search(r"compar|vs\.?|versus|diferencia entre", m)),
    }
    return intent


async def _query_universities(intent: dict[str, Any], limit: int = 6) -> list[dict]:
    pool = get_pool()
    clauses, params = [], []
    idx = 1

    if intent["region"]:
        clauses.append(f"(LOWER(region) LIKE ${idx} OR LOWER(city) LIKE ${idx})")
        params.append(f"%{intent['region']}%")
        idx += 1
    if intent["quiere_publicas"] and not intent["quiere_privadas"]:
        clauses.append("type = 'Pública'")
    if intent["quiere_privadas"] and not intent["quiere_publicas"]:
        clauses.append("type = 'Privada'")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order = "empleabilidad DESC" if intent["quiere_empleabilidad"] else (
        "cost ASC" if intent["quiere_baratas"] else "rating DESC"
    )
    sql = f"SELECT * FROM universidades {where} ORDER BY {order} LIMIT {limit}"
    rows = await pool.fetch(sql, *params)
    return [dict(r) for r in rows]


def _format_soles(n) -> str:
    n = float(n or 0)
    return "Gratuita (universidad pública)" if n == 0 else f"S/. {n:,.0f}"


def _local_answer(question: str, unis: list[dict], test_resultado: dict | None = None) -> str:
    """Respuesta generada localmente (capa 1: sin depender de ninguna API externa)."""
    intro = ""
    carreras = (test_resultado or {}).get("carreras") or []
    if carreras:
        top = carreras[0]
        intro = (
            f"Según tu test vocacional, tu carrera con mayor afinidad es "
            f"**{top['career']}** ({top['pct']}%). "
        )

    if not unis:
        return (
            intro + "No encontré universidades que calcen exactamente con tu búsqueda. "
            "¿Puedes darme más detalles, como la región o si buscas una universidad "
            "pública o privada?"
        )

    lines = [intro + f"Encontré {len(unis)} universidades que podrían interesarte:\n"] if intro else [
        f"Encontré {len(unis)} universidades que podrían interesarte:\n"
    ]
    for u in unis:
        lines.append(
            f"**{u['name']} ({u['short']})** — {u['type']}, {u['city']}\n"
            f"  • Pensión: {_format_soles(u['pension_min'])} – {_format_soles(u['pension_max'])} /mes\n"
            f"  • Empleabilidad al egreso: {u['empleabilidad']}%\n"
            f"  • Rating: {u['rating']}/5 · Acreditación SUNEDU: {'Sí' if u['sunedu'] else 'No'}\n"
        )
    lines.append(
        "\n¿Quieres que compare 2 o 3 de estas a detalle, o que te muestre el "
        "costo proyectado a 5 años de alguna en particular?"
    )
    return "\n".join(lines)


def _build_context(unis: list[dict]) -> str:
    if not unis:
        return "Sin universidades que coincidan exactamente con la búsqueda."
    return "\n".join(
        f"- {u['name']} ({u['short']}): {u['type']}, ubicada en {u['city']} ({u['region']}). "
        f"Pensión mensual: S/.{u['pension_min']}-{u['pension_max']}. Matrícula: S/.{u['matricula']}. "
        f"Empleabilidad al egreso: {u['empleabilidad']}%. Rating: {u['rating']}/5. "
        f"Acreditada por SUNEDU: {'sí' if u['sunedu'] else 'no'}. Modalidad: {u['modalidad']}. "
        f"Carreras: {u['careers']}. Fundada en {u['founded']}."
        for u in unis
    )


def _build_test_context(test_resultado: dict | None) -> str:
    """Convierte el resultado real del test vocacional del usuario (guardado
    en test_resultados) en texto que la IA puede leer. Si el usuario nunca
    hizo el test, se le dice explícitamente a la IA que no invente uno."""
    if not test_resultado:
        return "Este usuario todavía no ha hecho el test vocacional."
    carreras = test_resultado.get("carreras", [])
    if not carreras:
        return "Este usuario todavía no ha hecho el test vocacional."
    lines = ["Resultado real del test vocacional que este usuario ya completó, de mayor a menor afinidad:"]
    for c in carreras:
        lines.append(f"- {c['career']} ({c['cluster']}): {c['pct']}% de afinidad")
    return "\n".join(lines)


async def _groq_answer(question: str, context: str, test_context: str) -> str | None:
    """Capa 2: genera la respuesta con un modelo real (Llama 3.3 70B) vía Groq (gratis)."""
    if not GROQ_API_KEY:
        return None
    try:
        from groq import Groq
    except ImportError:
        return None

    try:
        client = Groq(api_key=GROQ_API_KEY)
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            temperature=0.4,
            max_tokens=550,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres el orientador vocacional de ElijePe, una plataforma peruana de "
                        "orientación universitaria. Respondes en español, de forma breve, cálida "
                        "y directa. SOLO puedes usar los datos de universidades que se te pasan "
                        "en el contexto; si el contexto no alcanza para responder algo, dilo con "
                        "honestidad en vez de inventar cifras. No repitas literalmente el listado "
                        "completo si el usuario ya lo vio antes en la conversación; conversa de "
                        "forma natural.\n\n"
                        "Lenguaje accesible (importante): usa oraciones cortas, una idea por "
                        "oración, palabras simples y evita jerga técnica o administrativa sin "
                        "explicarla. Si das varios datos, usa listas breves en vez de párrafos "
                        "largos. No sobrecargues de información: responde solo lo que se preguntó "
                        "y ofrece ampliar si hace falta, en vez de volcar todo de una vez.\n\n"
                        "ADVERTENCIA — 'simple' NO es 'vago': nunca sacrifiques exactitud por "
                        "brevedad. Da siempre el dato concreto (la cifra exacta, el nombre exacto "
                        "de la universidad, el sí/no claro), nunca una respuesta ambigua o "
                        "genérica tipo 'depende' o 'varía' cuando el contexto sí tiene el dato "
                        "preciso. Si de verdad no tienes el dato exacto, dilo explícitamente "
                        "('no tengo ese dato') en vez de dar un rodeo vago. Simplificar es quitar "
                        "adornos y palabras difíciles, no quitar precisión.\n\n"
                        "Si el usuario ya hizo el test vocacional (te paso su resultado real "
                        "abajo), úsalo como base de tus recomendaciones de carrera y conéctalo "
                        "con las universidades del contexto. Nunca inventes un resultado de test "
                        "que no se te haya dado; si no lo hizo, puedes sugerirle que lo haga."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Resultado del test vocacional del usuario:\n{test_context}\n\n"
                        f"Contexto (datos reales de la base de ElijePe):\n{context}\n\n"
                        f"Pregunta del estudiante: {question}"
                    ),
                },
            ],
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"⚠ Error llamando a Groq, usando respuesta local: {e}")
        return None


async def generate_answer(question: str, test_resultado: dict | None = None) -> dict[str, Any]:
    """Punto de entrada usado por app/routers/ia.py.

    test_resultado es el último resultado real del test vocacional del
    usuario (leído de la tabla test_resultados), o None si nunca lo hizo.
    """
    intent = _detect_intent(question)
    unis = await _query_universities(intent)
    context = _build_context(unis)
    test_context = _build_test_context(test_resultado)

    ia_answer = await _groq_answer(question, context, test_context)
    used_ai = ia_answer is not None
    answer = ia_answer or _local_answer(question, unis, test_resultado)

    return {
        "answer": answer,
        "universidades_referenciadas": [u["id"] for u in unis],
        "usa_ia_generativa": used_ai,
        "test_considerado": test_resultado is not None,
    }


# ─── Saludo inicial personalizado por rol ──────────────────────────────────
# El "tipo" de cuenta se elige al registrarse (egresado | traslado | padre) y
# determina el mensaje de bienvenida y las preguntas sugeridas del chat, para
# que la IA no arranque genérica sino ya encaminada a lo que esa persona
# probablemente necesita.
SALUDOS_POR_TIPO: dict[str, dict[str, Any]] = {
    "egresado": {
        "frase": "Veo que acabas de terminar el colegio y estás eligiendo tu carrera y universidad.",
        "preguntas": [
            "¿Qué carrera me conviene según lo que me gusta?",
            "¿Cuáles son las universidades con mejor empleabilidad?",
            "¿Qué becas puedo postular como egresado?",
        ],
    },
    "traslado": {
        "frase": "Veo que ya estás en la universidad y quieres trasladarte a otra.",
        "preguntas": [
            "¿Qué cursos se me convalidarían si me traslado?",
            "¿Qué documentos necesito para un traslado externo?",
            "¿Qué universidades tienen el mejor proceso de convalidación?",
        ],
    },
    "padre": {
        "frase": "Veo que eres padre o madre de familia, buscando la mejor decisión para tu hijo(a).",
        "preguntas": [
            "¿Cuál es el costo total de la carrera a 5 años?",
            "¿Qué universidades tienen mejor relación costo-beneficio?",
            "¿Qué becas o financiamiento existen para reducir el costo?",
        ],
    },
}
SALUDO_GENERICO = {
    "frase": "Cuéntame qué estás buscando y te ayudo a encontrar la mejor opción.",
    "preguntas": [
        "¿Qué carrera me conviene según mis intereses?",
        "¿Cuáles son las universidades con mejor empleabilidad?",
        "¿Cómo comparo el costo entre dos universidades?",
    ],
}


def construir_saludo(nombre: str, tipo: str) -> dict[str, Any]:
    datos = SALUDOS_POR_TIPO.get(tipo, SALUDO_GENERICO)
    saludo = f"¡Hola, {nombre}! 👋 {datos['frase']}"
    return {"saludo": saludo, "preguntas_sugeridas": datos["preguntas"]}
